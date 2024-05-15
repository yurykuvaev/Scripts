"""Apply a fixed set of tags to security groups listed in a file.

Reads SG IDs (one per line) from --input, applies any of the --tag KEY=VALUE
pairs that are missing on each SG. Existing tags are left untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

from _common import LOG, aws_client, common_arg_parser, configure_logging, parse_kv_pairs


def read_ids(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def add_missing_tags(client, sg_id: str, desired: dict[str, str], dry_run: bool) -> int:
    """Apply only the tags that aren't already on this SG. Returns number applied."""
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
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=Path("sg_ids.txt"),
        help="File with SG IDs, one per line.",
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
    sg_ids = read_ids(args.input)
    if not sg_ids:
        LOG.warning("no SG IDs found in %s — nothing to do", args.input)
        return 0

    ec2 = aws_client("ec2", region=args.region)
    total_added = 0
    for sg_id in sg_ids:
        total_added += add_missing_tags(ec2, sg_id, desired, args.dry_run)

    LOG.info("%s%d tag(s) applied across %d SG(s)",
             "[dry-run] " if args.dry_run else "", total_added, len(sg_ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())
