"""Deregister unused AMIs and reclaim their EBS snapshots.

An AMI is "unused" if no running instance, Launch Template version, or
Auto Scaling Group references it. `--keep-last-n` retains the N newest
per name prefix so a release doesn't immediately wipe your fallback.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from _common import LOG, aws_client, common_arg_parser, configure_logging


def list_owned_amis(client) -> list[dict[str, Any]]:
    """All AMIs owned by the calling account."""
    resp = client.describe_images(Owners=["self"])
    return resp.get("Images", [])


def in_use_by_instances(client) -> set[str]:
    used: set[str] = set()
    paginator = client.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                state = instance.get("State", {}).get("Name")
                if state not in {"terminated", "shutting-down"}:
                    used.add(instance["ImageId"])
    return used


def in_use_by_launch_templates(client) -> set[str]:
    used: set[str] = set()
    lts = client.get_paginator("describe_launch_templates")
    for page in lts.paginate():
        for lt in page["LaunchTemplates"]:
            versions = client.get_paginator("describe_launch_template_versions")
            for vp in versions.paginate(LaunchTemplateId=lt["LaunchTemplateId"]):
                for v in vp["LaunchTemplateVersions"]:
                    image_id = v.get("LaunchTemplateData", {}).get("ImageId")
                    if image_id:
                        used.add(image_id)
    return used


def in_use_by_asg(client_asg, _client_ec2) -> set[str]:
    """ASGs may use a Launch Configuration (legacy) or a Launch Template."""
    used: set[str] = set()
    lc_names: set[str] = set()
    paginator = client_asg.get_paginator("describe_auto_scaling_groups")
    for page in paginator.paginate():
        for asg in page["AutoScalingGroups"]:
            if asg.get("LaunchConfigurationName"):
                lc_names.add(asg["LaunchConfigurationName"])
            # LT-based ASGs are already covered by in_use_by_launch_templates.

    if lc_names:
        lc_pages = client_asg.get_paginator("describe_launch_configurations")
        for page in lc_pages.paginate(LaunchConfigurationNames=list(lc_names)):
            for lc in page["LaunchConfigurations"]:
                if lc.get("ImageId"):
                    used.add(lc["ImageId"])

    return used


def group_by_prefix(amis: list[dict], prefix_pattern: re.Pattern[str]) -> dict[str, list[dict]]:
    """Group AMIs by the prefix captured from their Name field.

    AMIs with no name or no match form a single 'unnamed' bucket.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for ami in amis:
        name = ami.get("Name", "")
        m = prefix_pattern.match(name)
        key = m.group(1) if m else "<unnamed>"
        groups[key].append(ami)
    return groups


def parse_creation(ami: dict) -> datetime:
    return datetime.fromisoformat(ami["CreationDate"].replace("Z", "+00:00"))


def keep_recent_per_prefix(
    amis: list[dict], prefix_pattern: re.Pattern[str], keep_n: int
) -> list[dict]:
    """Return AMIs to drop, retaining the keep_n newest per name prefix."""
    drops: list[dict] = []
    for prefix, group in group_by_prefix(amis, prefix_pattern).items():
        group.sort(key=parse_creation, reverse=True)  # newest first
        kept = group[:keep_n]
        dropped = group[keep_n:]
        if dropped:
            LOG.debug("prefix %s: keeping %d, dropping %d",
                      prefix, len(kept), len(dropped))
        drops.extend(dropped)
    return drops


def snapshots_for(ami: dict) -> list[str]:
    return [
        bdm["Ebs"]["SnapshotId"]
        for bdm in ami.get("BlockDeviceMappings", [])
        if "Ebs" in bdm and "SnapshotId" in bdm["Ebs"]
    ]


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--name-prefix-regex",
        default=r"^([a-zA-Z0-9-]+?)(?:-\d|$)",
        help=(
            "Regex with one capture group for the prefix. "
            "Default splits 'myapp-2026-04-30' into 'myapp'."
        ),
    )
    parser.add_argument(
        "--keep-last-n",
        type=int,
        default=3,
        help="Per name prefix, keep the N newest AMIs even if unused (default: 3).",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually deregister AMIs and delete their snapshots.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ec2 = aws_client("ec2", region=args.region)
    asg = aws_client("autoscaling", region=args.region)

    LOG.info("collecting owned AMIs...")
    amis = list_owned_amis(ec2)
    LOG.info("  total owned: %d", len(amis))

    LOG.info("collecting in-use AMI ids...")
    used = (
        in_use_by_instances(ec2)
        | in_use_by_launch_templates(ec2)
        | in_use_by_asg(asg, ec2)
    )
    LOG.info("  in use: %d", len(used))

    candidates = [a for a in amis if a["ImageId"] not in used]
    LOG.info("  unused candidates: %d", len(candidates))

    pattern = re.compile(args.name_prefix_regex)
    to_delete = keep_recent_per_prefix(candidates, pattern, args.keep_last_n)
    LOG.info("after keep-last-%d retention: %d to remove",
             args.keep_last_n, len(to_delete))

    for ami in to_delete:
        LOG.info("  %s  %s  created=%s",
                 ami["ImageId"], ami.get("Name", "-"), ami["CreationDate"])

    if not args.delete:
        LOG.info("report-only mode (pass --delete to remove them)")
        return 0

    deleted = 0
    snap_deleted = 0
    failed = 0
    now = datetime.now(timezone.utc)

    for ami in to_delete:
        ami_id = ami["ImageId"]
        snaps = snapshots_for(ami)

        if args.dry_run:
            LOG.info("[dry-run] would deregister %s (snaps: %d)", ami_id, len(snaps))
            deleted += 1
            snap_deleted += len(snaps)
            continue

        try:
            ec2.deregister_image(ImageId=ami_id)
            LOG.info("deregistered %s (created %s ago)",
                     ami_id, now - parse_creation(ami))
            deleted += 1
        except Exception as e:
            LOG.error("FAILED deregister %s: %s", ami_id, e)
            failed += 1
            continue

        for snap_id in snaps:
            try:
                ec2.delete_snapshot(SnapshotId=snap_id)
                LOG.info("  deleted snap %s", snap_id)
                snap_deleted += 1
            except Exception as e:
                LOG.error("  FAILED snap %s: %s", snap_id, e)
                failed += 1

    LOG.info("done: %sami=%d snapshots=%d failed=%d",
             "[dry-run] " if args.dry_run else "", deleted, snap_deleted, failed)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
