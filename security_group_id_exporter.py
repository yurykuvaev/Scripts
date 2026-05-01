"""Dump security group IDs to a text file with optional filters.

By default lists every SG in the region. With `--vpc-id` narrows to one VPC.
With `--missing-tag KEY` keeps only SGs that DO NOT have the named tag -
useful as the input file for a tag-cleanup pipeline.
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import LOG, aws_client, common_arg_parser, configure_logging


def list_security_groups(client, vpc_id: str | None) -> list[dict]:
    """Return every SG in the region (or one VPC), with full attributes."""
    sgs: list[dict] = []
    filters = []
    if vpc_id:
        filters.append({"Name": "vpc-id", "Values": [vpc_id]})

    paginator = client.get_paginator("describe_security_groups")
    kwargs: dict = {}
    if filters:
        kwargs["Filters"] = filters
    for page in paginator.paginate(**kwargs):
        sgs.extend(page["SecurityGroups"])
    return sgs


def filter_by_missing_tag(sgs: list[dict], required_keys: list[str]) -> list[dict]:
    """Keep only SGs that lack ALL of the given tag keys (i.e. no key is present)."""
    if not required_keys:
        return sgs
    out: list[dict] = []
    for sg in sgs:
        present = {t["Key"] for t in sg.get("Tags", [])}
        if not any(k in present for k in required_keys):
            out.append(sg)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("sg_ids.txt"),
        help="Output file path (default: sg_ids.txt).",
    )
    parser.add_argument(
        "--vpc-id",
        default=None,
        help="Limit to security groups in this VPC.",
    )
    parser.add_argument(
        "--missing-tag",
        action="append",
        default=[],
        metavar="KEY",
        help="Keep only SGs that DO NOT have this tag key. Repeatable.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ec2 = aws_client("ec2", region=args.region)
    sgs = list_security_groups(ec2, args.vpc_id)
    LOG.info("found %d security groups%s", len(sgs),
             f" in {args.vpc_id}" if args.vpc_id else "")

    if args.missing_tag:
        sgs = filter_by_missing_tag(sgs, args.missing_tag)
        LOG.info("%d remain after filtering missing-tag=%s", len(sgs), args.missing_tag)

    ids = [sg["GroupId"] for sg in sgs]

    if args.dry_run:
        LOG.info("[dry-run] would write %d ids to %s", len(ids), args.output)
        for sg_id in ids[:10]:
            LOG.info("[dry-run]   %s", sg_id)
        if len(ids) > 10:
            LOG.info("[dry-run]   ... %d more", len(ids) - 10)
        return 0

    args.output.write_text("\n".join(ids) + ("\n" if ids else ""), encoding="utf-8")
    LOG.info("wrote %d ids to %s", len(ids), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
