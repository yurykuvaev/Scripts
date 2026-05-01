"""Audit IAM roles for an expected attached policy.

Iterates every IAM role whose name starts with one of --role-prefix, then
emits the names of those that DO NOT have --policy-arn attached. Output is
written to --output (default: stdout) so it can pipe into a follow-up
remediation script.
"""
from __future__ import annotations

import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import LOG, common_arg_parser, configure_logging


def list_matching_roles(client, prefixes: list[str]):
    """Yield IAM Role objects whose name starts with any of the given prefixes."""
    paginator = client.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            name = role["RoleName"]
            if any(name.startswith(p) for p in prefixes):
                yield role


def has_policy(client, role_name: str, policy_arn: str) -> bool:
    paginator = client.get_paginator("list_attached_role_policies")
    for page in paginator.paginate(RoleName=role_name):
        if any(p["PolicyArn"] == policy_arn for p in page["AttachedPolicies"]):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument(
        "--role-prefix",
        action="append",
        required=True,
        help="Role name prefix to audit. Repeat for multiple prefixes.",
    )
    parser.add_argument("--policy-arn", required=True,
                        help="Expected attached policy ARN.")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Write missing role names here (default: stdout).",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    iam = boto3.client("iam")
    missing: list[str] = []
    checked = 0
    for role in list_matching_roles(iam, args.role_prefix):
        checked += 1
        if not has_policy(iam, role["RoleName"], args.policy_arn):
            missing.append(role["RoleName"])

    LOG.info("checked %d role(s) matching prefixes; %d missing %s",
             checked, len(missing), args.policy_arn)

    text = "\n".join(missing) + ("\n" if missing else "")
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        LOG.info("wrote %d names to %s", len(missing), args.output)
    else:
        sys.stdout.write(text)

    # Non-zero exit if anything is non-compliant - useful in CI.
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
