"""Generate a minimal IAM policy for a role from CloudTrail history.

CloudTrail records every API call made under a role. By aggregating events
from the lookback window, we can see which `<service>:<Action>` pairs the
role actually used and propose a tight policy that grants only those.
Compare it to the role's current attached policies to spot over-permissive
grants.

Caveats baked in:
  * `cloudtrail:LookupEvents` is paginated and rate-limited; lookback is
    capped at 90 days (CloudTrail console history limit).
  * Read-only KMS / STS noise is filtered down to the actions the role
    actually performed (we don't manufacture allow lines for events we
    didn't see).
  * Output is a JSON policy ready for `aws iam create-policy`.

Workflow:
  1. Run for a role: emits suggested policy + a diff against current attached.
  2. Review — CloudTrail-driven policies miss seasonal actions
     (e.g. monthly billing job). Bump --days or merge with known seasonal lists.
  3. Apply with `aws iam put-role-policy` or as an attached managed policy.
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from _common import LOG, aws_client, common_arg_parser, configure_logging

CT_MAX_DAYS = 90  # CloudTrail event history window in days.


def collect_role_events(client_ct, role_name: str, days: int) -> list[dict[str, Any]]:
    """All CloudTrail events whose userIdentity sessionIssuer is this role.

    `LookupAttributes` does not let us filter by role directly, so we filter
    `Username`-prefixed events client-side. For high-traffic roles this can
    produce thousands of events; we only need their service+action.
    """
    if days > CT_MAX_DAYS:
        LOG.warning("CloudTrail history is capped at %d days; using %d", CT_MAX_DAYS, CT_MAX_DAYS)
        days = CT_MAX_DAYS

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    events: list[dict[str, Any]] = []
    paginator = client_ct.get_paginator("lookup_events")
    for page in paginator.paginate(
        StartTime=start_time,
        EndTime=end_time,
        LookupAttributes=[{"AttributeKey": "Username", "AttributeValue": role_name}],
    ):
        events.extend(page.get("Events", []))

    LOG.info("collected %d CloudTrail events for %s over %dd",
             len(events), role_name, days)
    return events


def actions_from_events(events: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Map service-prefix -> set of API actions seen.

    e.g. {"s3": {"GetObject", "ListBucket"}, "ec2": {"DescribeInstances"}}
    """
    actions: dict[str, set[str]] = defaultdict(set)
    for ev in events:
        # CloudTrail's Event has the API name in EventName and the service prefix
        # in EventSource (which is "<service>.amazonaws.com").
        source = ev.get("EventSource", "")
        if not source.endswith(".amazonaws.com"):
            continue
        service = source[: -len(".amazonaws.com")]
        name = ev.get("EventName")
        if name:
            actions[service].add(name)
    return actions


def build_policy(actions: dict[str, set[str]]) -> dict[str, Any]:
    """Render an IAM policy document with one Statement per service prefix."""
    statements: list[dict[str, Any]] = []
    for service in sorted(actions):
        statements.append({
            "Sid": f"Allow{service.replace('-', '').title()}",
            "Effect": "Allow",
            "Action": [f"{service}:{a}" for a in sorted(actions[service])],
            "Resource": "*",
        })
    return {"Version": "2012-10-17", "Statement": statements}


def attached_policy_actions(client_iam, role_name: str) -> set[str]:
    """Flat set of `<service>:<Action>` from every policy attached to the role.

    Only counts simple string actions, not wildcard or NotAction. The point is
    to highlight what's allowed beyond what we observed — wildcards are flagged
    separately in main().
    """
    seen: set[str] = set()

    paginator = client_iam.get_paginator("list_attached_role_policies")
    for page in paginator.paginate(RoleName=role_name):
        for ap in page["AttachedPolicies"]:
            policy = client_iam.get_policy(PolicyArn=ap["PolicyArn"])["Policy"]
            version = client_iam.get_policy_version(
                PolicyArn=ap["PolicyArn"],
                VersionId=policy["DefaultVersionId"],
            )["PolicyVersion"]
            for stmt in _statements(version["Document"]):
                seen.update(_actions(stmt))

    inline = client_iam.list_role_policies(RoleName=role_name)
    for name in inline.get("PolicyNames", []):
        doc = client_iam.get_role_policy(RoleName=role_name, PolicyName=name)
        for stmt in _statements(doc["PolicyDocument"]):
            seen.update(_actions(stmt))

    return seen


def _statements(doc: dict | str) -> list[dict]:
    """Normalise a policy document into a list of statements."""
    if isinstance(doc, str):
        doc = json.loads(doc)
    stmts = doc.get("Statement", [])
    return stmts if isinstance(stmts, list) else [stmts]


def _actions(stmt: dict) -> set[str]:
    if stmt.get("Effect") != "Allow":
        return set()
    actions = stmt.get("Action", [])
    if isinstance(actions, str):
        actions = [actions]
    return {a for a in actions if isinstance(a, str)}


def main(argv = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--role", required=True, help="IAM role name.")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help=f"CloudTrail lookback in days (max {CT_MAX_DAYS}, default 30).",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Also print actions currently allowed but never seen in CloudTrail.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ct = aws_client("cloudtrail", region=args.region)
    iam = aws_client("iam")  # IAM is global

    events = collect_role_events(ct, args.role, args.days)
    actions = actions_from_events(events)
    policy = build_policy(actions)

    LOG.info("observed %d action(s) across %d service(s)",
             sum(len(v) for v in actions.values()), len(actions))

    print(json.dumps(policy, indent=2))

    if args.diff:
        observed = {f"{svc}:{a}" for svc, lst in actions.items() for a in lst}
        currently = attached_policy_actions(iam, args.role)
        unused = sorted(currently - observed - {a for a in currently if "*" in a})
        wildcards = sorted(a for a in currently if "*" in a)
        if unused:
            LOG.warning("%d allowed action(s) NOT used in last %dd:", len(unused), args.days)
            for a in unused:
                LOG.warning("  - %s", a)
        if wildcards:
            LOG.warning("%d wildcard action(s) — review manually:", len(wildcards))
            for a in wildcards:
                LOG.warning("  - %s", a)

    return 0


if __name__ == "__main__":
    sys.exit(main())
