"""Set `Environment=dev` on every log group whose name contains 'dev'.

Narrower variant of TagLogGroups.py — handy when you only want the
`Environment` tag and don't need a full inventory of static tags.
"""
from __future__ import annotations

import sys

from _common import LOG, aws_client, common_arg_parser, configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--substring",
        default="dev",
        help="Substring to look for in log group names (default: dev).",
    )
    parser.add_argument(
        "--env-value",
        default="dev",
        help="Value for the Environment tag (default: dev).",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    logs = aws_client("logs", region=args.region)
    paginator = logs.get_paginator("describe_log_groups")

    matched = 0
    tagged = 0
    for page in paginator.paginate():
        for lg in page["logGroups"]:
            name = lg["logGroupName"]
            if args.substring not in name:
                continue
            matched += 1

            existing = (logs.list_tags_log_group(logGroupName=name).get("tags") or {})
            if "Environment" in existing:
                continue

            if args.dry_run:
                LOG.info("[dry-run] %s would set Environment=%s", name, args.env_value)
            else:
                logs.tag_log_group(logGroupName=name, tags={"Environment": args.env_value})
                LOG.info("%s set Environment=%s", name, args.env_value)
            tagged += 1

    LOG.info("%s%d / %d matched groups got Environment=%s",
             "[dry-run] " if args.dry_run else "", tagged, matched, args.env_value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
