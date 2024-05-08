"""Dump every security group ID in a region to a text file (one per line).

Useful as the first step of a tag-cleanup pipeline: get the list, then
filter it manually or feed it into one of the tagging scripts.
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import LOG, aws_client, common_arg_parser, configure_logging


def get_all_security_group_ids(client) -> list[str]:
    """Return every SG id in the current region, handling pagination."""
    ids: list[str] = []
    paginator = client.get_paginator("describe_security_groups")
    for page in paginator.paginate():
        ids.extend(sg["GroupId"] for sg in page["SecurityGroups"])
    return ids


def write_to_file(path: Path, ids: list[str]) -> None:
    path.write_text("\n".join(ids) + "\n", encoding="utf-8")
    LOG.info("wrote %d ids to %s", len(ids), path)


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("sg_ids.txt"),
        help="Output file path (default: sg_ids.txt).",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ec2 = aws_client("ec2", region=args.region)
    ids = get_all_security_group_ids(ec2)

    if args.dry_run:
        LOG.info("[dry-run] would write %d ids to %s", len(ids), args.output)
        for sg_id in ids[:10]:
            LOG.info("[dry-run]   %s", sg_id)
        if len(ids) > 10:
            LOG.info("[dry-run]   ... %d more", len(ids) - 10)
        return 0

    write_to_file(args.output, ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
