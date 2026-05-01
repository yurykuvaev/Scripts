"""Find — and optionally delete — security groups that nothing uses.

A security group is "unused" if no ENI references it AND no other SG's
ingress/egress rules reference it AND no Launch Template version mentions
it. This is the conservative definition: an unused SG by this script will
not break anything when removed.

Two modes:
  default  — report only (read-only)
  --delete — actually call ec2:DeleteSecurityGroup. Honours --dry-run.

Inter-SG references are resolved with a topological order: orphan SGs
that reference each other are deleted in the right sequence so we don't
get blocked by DependencyViolation.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from typing import Any

from _common import LOG, aws_client, common_arg_parser, configure_logging


def all_security_groups(client) -> list[dict[str, Any]]:
    sgs: list[dict[str, Any]] = []
    paginator = client.get_paginator("describe_security_groups")
    for page in paginator.paginate():
        sgs.extend(page["SecurityGroups"])
    return sgs


def sgs_referenced_by_enis(client) -> set[str]:
    referenced: set[str] = set()
    paginator = client.get_paginator("describe_network_interfaces")
    for page in paginator.paginate():
        for eni in page["NetworkInterfaces"]:
            for group in eni.get("Groups", []):
                referenced.add(group["GroupId"])
    return referenced


def sgs_referenced_by_launch_templates(client) -> set[str]:
    """Inspect every LT version's NetworkInterfaces[].Groups."""
    referenced: set[str] = set()
    lts = client.get_paginator("describe_launch_templates")
    for page in lts.paginate():
        for lt in page["LaunchTemplates"]:
            versions = client.get_paginator("describe_launch_template_versions")
            for vp in versions.paginate(LaunchTemplateId=lt["LaunchTemplateId"]):
                for v in vp["LaunchTemplateVersions"]:
                    data = v.get("LaunchTemplateData", {})
                    referenced.update(data.get("SecurityGroupIds") or [])
                    for ni in data.get("NetworkInterfaces", []) or []:
                        referenced.update(ni.get("Groups") or [])
    return referenced


def cross_references(all_sgs: list[dict]) -> dict[str, set[str]]:
    """Map sg -> set of OTHER sgs it references in its ingress/egress rules."""
    refs: dict[str, set[str]] = defaultdict(set)
    for sg in all_sgs:
        gid = sg["GroupId"]
        for rule_set in (sg.get("IpPermissions", []), sg.get("IpPermissionsEgress", [])):
            for rule in rule_set:
                for pair in rule.get("UserIdGroupPairs", []):
                    other = pair.get("GroupId")
                    if other and other != gid:
                        refs[gid].add(other)
    return refs


def topo_sort_for_delete(unused: list[str], refs: dict[str, set[str]]) -> list[str]:
    """Return unused SG ids in delete-safe order.

    SGs that reference other unused SGs go FIRST (their referenced rules vanish
    when they are deleted, freeing the dependency on the other SG).
    """
    unused_set = set(unused)
    out: list[str] = []
    seen: set[str] = set()

    def visit(node: str) -> None:
        if node in seen:
            return
        seen.add(node)
        for dep in refs.get(node, ()):
            if dep in unused_set:
                visit(dep)
        # Post-order: leaf-most first (dep) — but for SG delete we want
        # the *referrer* deleted first. Flip by appending after visiting deps.
        out.append(node)

    for sg in unused:
        visit(sg)
    # We've appended deps before referrers; reverse so referrers are first.
    return list(reversed(out))


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete unused SGs. Combine with --dry-run for a preview.",
    )
    parser.add_argument(
        "--exclude-default",
        action="store_true",
        default=True,
        help="Skip the per-VPC 'default' SG (default: on; AWS won't let you delete it anyway).",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ec2 = aws_client("ec2", region=args.region)

    LOG.info("collecting security groups...")
    all_sgs = all_security_groups(ec2)
    by_id = {sg["GroupId"]: sg for sg in all_sgs}
    LOG.info("  total SGs: %d", len(all_sgs))

    LOG.info("collecting ENI references...")
    eni_refs = sgs_referenced_by_enis(ec2)
    LOG.info("  SGs referenced by ENIs: %d", len(eni_refs))

    LOG.info("collecting Launch Template references...")
    lt_refs = sgs_referenced_by_launch_templates(ec2)
    LOG.info("  SGs referenced by Launch Templates: %d", len(lt_refs))

    cross = cross_references(all_sgs)
    cross_refs = {dep for parent in cross.values() for dep in parent}

    used = eni_refs | lt_refs | cross_refs
    candidates = []
    for sg in all_sgs:
        gid = sg["GroupId"]
        if gid in used:
            continue
        if args.exclude_default and sg.get("GroupName") == "default":
            continue
        candidates.append(gid)

    LOG.info("unused candidates: %d", len(candidates))
    for gid in candidates:
        sg = by_id[gid]
        LOG.info("  %s  vpc=%s  name=%s",
                 gid, sg.get("VpcId", "-"), sg.get("GroupName", "-"))

    if not args.delete:
        LOG.info("report-only mode (pass --delete to remove them)")
        return 0

    order = topo_sort_for_delete(candidates, cross)
    deleted = 0
    failed: list[tuple[str, str]] = []
    for gid in order:
        if args.dry_run:
            LOG.info("[dry-run] would delete %s", gid)
            deleted += 1
            continue
        try:
            ec2.delete_security_group(GroupId=gid)
            LOG.info("deleted %s", gid)
            deleted += 1
        except Exception as e:
            failed.append((gid, str(e)))
            LOG.error("FAILED %s: %s", gid, e)

    LOG.info("done: %sdeleted=%d failed=%d",
             "[dry-run] " if args.dry_run else "", deleted, len(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
