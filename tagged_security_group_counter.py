"""Count security groups that already carry every tag key in a given list.

Useful as a compliance check: "how many of our SGs have Product / Service /
SupportGroup set?" - run as a baseline before a tagging push and again
after to confirm coverage.
"""
from __future__ import annotations

import sys

from _common import LOG, aws_client, common_arg_parser, configure_logging


def count_with_tags(client, required_keys: list[str]) -> tuple[int, int]:
    """Return (compliant_count, total_count)."""
    compliant = 0
    total = 0
    paginator = client.get_paginator("describe_security_groups")
    for page in paginator.paginate():
        for sg in page["SecurityGroups"]:
            total += 1
            sg_tags = {t["Key"]: t["Value"] for t in sg.get("Tags", [])}
            if all(k in sg_tags for k in required_keys):
                compliant += 1
    return compliant, total


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--require-key",
        action="append",
        required=True,
        metavar="KEY",
        help="Tag key that must be present. Pass multiple times for multiple keys.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ec2 = aws_client("ec2", region=args.region)
    compliant, total = count_with_tags(ec2, args.require_key)

    pct = (compliant / total * 100.0) if total else 0.0
    LOG.info(
        "%d / %d security groups carry all required keys (%.1f%% compliant): %s",
        compliant, total, pct, ",".join(args.require_key),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
