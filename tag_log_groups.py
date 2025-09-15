"""Tag every CloudWatch Log Group; infer `Environment` from the name.

Each log group gets the static `--tag KEY=VALUE` set, plus an `Environment`
tag if any of the substrings in --env-substring matches the log group name.
"""
from __future__ import annotations

import sys

from _common import LOG, aws_client, common_arg_parser, configure_logging, parse_kv_pairs


def find_environment(name: str, env_substrings: list[str]) -> str | None:
    for env in env_substrings:
        if env in name:
            return env
    return None


def existing_tags(client, log_group_name: str) -> dict[str, str]:
    resp = client.list_tags_log_group(logGroupName=log_group_name)
    return resp.get("tags", {}) or {}


def tag_log_group(client, name: str, desired: dict[str, str], dry_run: bool) -> int:
    """Apply only the keys that aren't already on this log group."""
    current = existing_tags(client, name)
    new_tags = {k: v for k, v in desired.items() if k not in current}
    if not new_tags:
        return 0
    if dry_run:
        LOG.info("[dry-run] %s would add: %s", name, list(new_tags))
        return len(new_tags)
    client.tag_log_group(logGroupName=name, tags=new_tags)
    LOG.info("%s added: %s", name, list(new_tags))
    return len(new_tags)


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--tag",
        action="append",
        required=True,
        metavar="KEY=VALUE",
        help="Tag to apply to every log group. Repeat for multiple tags.",
    )
    parser.add_argument(
        "--env-substring",
        action="append",
        default=[],
        metavar="STRING",
        help="If the log group name contains this substring, set Environment=<substring>.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    desired_static = parse_kv_pairs(args.tag)

    logs = aws_client("logs", region=args.region)
    paginator = logs.get_paginator("describe_log_groups")
    total_groups = 0
    total_added = 0

    for page in paginator.paginate():
        for lg in page["logGroups"]:
            name = lg["logGroupName"]
            total_groups += 1

            tags = dict(desired_static)
            env = find_environment(name, args.env_substring)
            if env:
                tags["Environment"] = env

            total_added += tag_log_group(logs, name, tags, args.dry_run)

    LOG.info("%s%d tag(s) applied across %d log group(s)",
             "[dry-run] " if args.dry_run else "", total_added, total_groups)
    return 0


if __name__ == "__main__":
    sys.exit(main())
