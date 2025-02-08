"""Add a CloudWatch Logs subscription filter that forwards a single log
group to a Kinesis Firehose delivery stream.

Account ID is detected via STS so the destination ARN is built without
hardcoding it.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Subdirectory script — pull _common from parent.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import LOG, aws_client, common_arg_parser, configure_logging  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--log-group", required=True,
                        help="Log group name to subscribe.")
    parser.add_argument("--stream", required=True,
                        help="Kinesis Firehose delivery stream name.")
    parser.add_argument("--filter-name", default="Destination",
                        help="Subscription filter name (default: Destination).")
    parser.add_argument("--filter-pattern", default="",
                        help="Filter pattern (default: empty = forward everything).")
    parser.add_argument("--role-arn", required=True,
                        help="IAM role ARN that grants CWL → Firehose put permission.")
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    region = args.region
    sts = aws_client("sts", region=region)
    account_id = sts.get_caller_identity()["Account"]

    # If region wasn't passed, use whatever the boto3 session resolved.
    region = region or aws_client("logs").meta.region_name
    destination_arn = f"arn:aws:firehose:{region}:{account_id}:deliverystream/{args.stream}"

    if args.dry_run:
        LOG.info("[dry-run] would put subscription filter on %s -> %s",
                 args.log_group, destination_arn)
        return 0

    logs = aws_client("logs", region=region)
    logs.put_subscription_filter(
        logGroupName=args.log_group,
        filterName=args.filter_name,
        filterPattern=args.filter_pattern,
        destinationArn=destination_arn,
        roleArn=args.role_arn,
    )
    LOG.info("subscription filter %s attached to %s -> %s",
             args.filter_name, args.log_group, args.stream)
    return 0


if __name__ == "__main__":
    sys.exit(main())
