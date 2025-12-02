"""Apply a fixed set of tags to security groups.

Two modes:
- `--input <file>`        — read SG IDs (one per line) from file
- `--all-in-region`       — fetch every SG in the region, no file needed
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import LOG, aws_client, common_arg_parser, configure_logging, parse_kv_pairs


def read_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def all_sg_ids_in_region(client) -> list[str]:
    ids: list[str] = []
    paginator = client.get_paginator("describe_security_groups")
    for page in paginator.paginate():
        ids.extend(sg["GroupId"] for sg in page["SecurityGroups"])
    return ids


def add_missing_tags(client, sg_id: str, desired: dict[str, str], dry_run: bool) -> int:
    """Apply only the tags that aren't already on this SG. Returns count applied."""
    resp = client.describe_tags(Filters=[{"Name": "resource-id", "Values": [sg_id]}])
    current = {t["Key"]: t["Value"] for t in resp.get("Tags", [])}
    new_tags = [{"Key": k, "Value": v} for k, v in desired.items() if k not in current]

    if not new_tags:
        LOG.debug("%s already has all required keys", sg_id)
        return 0

    if dry_run:
        LOG.info("[dry-run] %s would add: %s", sg_id, [t["Key"] for t in new_tags])
        return len(new_tags)

    client.create_tags(Resources=[sg_id], Tags=new_tags)
    LOG.info("%s added: %s", sg_id, [t["Key"] for t in new_tags])
    return len(new_tags)


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "-i", "--input",
        type=Path,
        help="File with SG IDs, one per line.",
    )
    source.add_argument(
        "--all-in-region",
        action="store_true",
        help="Tag every SG in the region (skip the file step).",
    )
    parser.add_argument(
        "--tag",
        action="append",
        required=True,
        metavar="KEY=VALUE",
        help="Tag to apply. Pass multiple times for multiple tags.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    desired = parse_kv_pairs(args.tag)
    ec2 = aws_client("ec2", region=args.region)

    if args.all_in_region:
        sg_ids = all_sg_ids_in_region(ec2)
        LOG.info("fetched %d SG(s) in region", len(sg_ids))
    else:
        sg_ids = read_ids(args.input)
        LOG.info("loaded %d SG(s) from %s", len(sg_ids), args.input)

    if not sg_ids:
        LOG.warning("no SG IDs to process — nothing to do")
        return 0

    total_added = 0
    for sg_id in sg_ids:
        total_added += add_missing_tags(ec2, sg_id, desired, args.dry_run)

    LOG.info("%s%d tag(s) applied across %d SG(s)",
             "[dry-run] " if args.dry_run else "", total_added, len(sg_ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
