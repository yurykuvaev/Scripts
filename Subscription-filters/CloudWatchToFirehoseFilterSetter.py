"""Bulk-set CloudWatch Logs subscription filters across every log group.

Same idea as LogsToFirehose/CloudWatchToKinesisFirehose.py but applied to
EVERY log group in a region. Account ID is detected via STS so the
destination ARN doesn't need hardcoding.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import LOG, aws_client, common_arg_parser, configure_logging  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--stream", required=True,
                        help="Kinesis Firehose delivery stream name.")
    parser.add_argument("--filter-name", default="Destination",
                        help="Subscription filter name (default: Destination).")
    parser.add_argument("--filter-pattern", default="",
                        help="Filter pattern (default: empty = forward everything).")
    parser.add_argument("--role-arn", required=True,
                        help="IAM role ARN that grants CWL → Firehose put.")
    parser.add_argument(
        "--name-substring",
        action="append",
        default=[],
        help="If set, only attach to log groups whose name contains one of these. "
             "Pass multiple times.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    sts = aws_client("sts", region=args.region)
    account_id = sts.get_caller_identity()["Account"]

    logs = aws_client("logs", region=args.region)
    region = logs.meta.region_name
    destination_arn = f"arn:aws:firehose:{region}:{account_id}:deliverystream/{args.stream}"

    paginator = logs.get_paginator("describe_log_groups")
    attached = 0
    skipped = 0
    failed: list[tuple[str, str]] = []

    for page in paginator.paginate():
        for lg in page["logGroups"]:
            name = lg["logGroupName"]
            if args.name_substring and not any(s in name for s in args.name_substring):
                skipped += 1
                continue

            if args.dry_run:
                LOG.info("[dry-run] %s -> %s", name, destination_arn)
                attached += 1
                continue

            try:
                logs.put_subscription_filter(
                    logGroupName=name,
                    filterName=args.filter_name,
                    filterPattern=args.filter_pattern,
                    destinationArn=destination_arn,
                    roleArn=args.role_arn,
                )
                attached += 1
                LOG.info("attached: %s", name)
            except Exception as e:
                failed.append((name, str(e)))
                LOG.error("FAILED %s: %s", name, e)

    LOG.info("done: %s attached=%d skipped(filter)=%d failed=%d",
             "[dry-run] " if args.dry_run else "", attached, skipped, len(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
