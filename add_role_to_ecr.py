"""Add a role ARN to the `ECRWrite` statement of every ECR repo policy.

Idempotent — if the role is already in the principal list, the repo is
skipped. If the policy doesn't have an `ECRWrite` statement, the repo is
left untouched (we don't invent a policy from scratch).
"""
from __future__ import annotations

import json
import sys

from _common import LOG, aws_client, common_arg_parser, configure_logging


def add_role_to_policy(policy: dict, role_arn: str, sid: str) -> bool:
    """Mutate `policy` in place so `role_arn` is in the named statement.

    Returns True if a change was made, False if the role was already there.
    """
    for statement in policy.get("Statement", []):
        if statement.get("Sid") != sid:
            continue
        principal = statement.get("Principal", {})
        aws_principals = principal.get("AWS")
        if isinstance(aws_principals, str):
            aws_principals = [aws_principals]
        elif aws_principals is None:
            aws_principals = []
        if role_arn in aws_principals:
            return False
        aws_principals.append(role_arn)
        principal["AWS"] = aws_principals
        statement["Principal"] = principal
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--role-arn", required=True,
                        help="IAM role ARN to add to the policy statement.")
    parser.add_argument("--statement-sid", default="ECRWrite",
                        help="Statement Sid to update (default: ECRWrite).")
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ecr = aws_client("ecr", region=args.region)
    paginator = ecr.get_paginator("describe_repositories")

    updated = 0
    skipped_no_policy = 0
    skipped_no_change = 0
    skipped_no_sid = 0

    for page in paginator.paginate():
        for repo in page["repositories"]:
            name = repo["repositoryName"]
            try:
                resp = ecr.get_repository_policy(repositoryName=name)
            except ecr.exceptions.RepositoryPolicyNotFoundException:
                LOG.debug("%s: no policy attached, skipping", name)
                skipped_no_policy += 1
                continue

            policy = json.loads(resp["policyText"])
            changed = add_role_to_policy(policy, args.role_arn, args.statement_sid)
            if not changed:
                # Could be already-present or sid not found; tell them apart.
                has_sid = any(s.get("Sid") == args.statement_sid
                              for s in policy.get("Statement", []))
                if has_sid:
                    skipped_no_change += 1
                    LOG.debug("%s: role already in %s", name, args.statement_sid)
                else:
                    skipped_no_sid += 1
                    LOG.warning("%s: no statement with Sid=%s", name, args.statement_sid)
                continue

            if args.dry_run:
                LOG.info("[dry-run] %s would gain %s in %s",
                         name, args.role_arn, args.statement_sid)
                updated += 1
                continue

            ecr.set_repository_policy(repositoryName=name, policyText=json.dumps(policy))
            LOG.info("%s policy updated", name)
            updated += 1

    LOG.info(
        "%supdated=%d skipped(no-policy)=%d skipped(no-sid)=%d skipped(no-change)=%d",
        "[dry-run] " if args.dry_run else "",
        updated, skipped_no_policy, skipped_no_sid, skipped_no_change,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
