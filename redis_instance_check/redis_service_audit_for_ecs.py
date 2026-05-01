"""Find ECS services whose task definitions point at a known Redis cluster.

Walks every service in the given cluster, fetches its current task
definition, and prints any container whose REDIS_URL env var contains
one of the substrings in --redis-host. Useful when migrating a Redis
fleet - gives a list of services that need a config update.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import LOG, aws_client, common_arg_parser, configure_logging


def task_def_uses_redis(task_def: dict, redis_hosts: list[str]) -> list[str]:
    """Return container names that reference any of `redis_hosts` in REDIS_URL."""
    matches: list[str] = []
    for container in task_def.get("containerDefinitions", []):
        for env_var in container.get("environment", []):
            if env_var.get("name") != "REDIS_URL":
                continue
            value = env_var.get("value", "")
            if any(host in value for host in redis_hosts):
                matches.append(container.get("name", "<unnamed>"))
    return matches


def audit_cluster(ecs, cluster: str, redis_hosts: list[str]) -> int:
    """Print and return the count of services using one of redis_hosts."""
    paginator = ecs.get_paginator("list_services")
    hits = 0
    for page in paginator.paginate(cluster=cluster):
        for service_arn in page["serviceArns"]:
            svc_resp = ecs.describe_services(cluster=cluster, services=[service_arn])
            services = svc_resp.get("services", [])
            if not services:
                continue
            td_arn = services[0]["taskDefinition"]
            td = ecs.describe_task_definition(taskDefinition=td_arn)["taskDefinition"]

            matched_containers = task_def_uses_redis(td, redis_hosts)
            if matched_containers:
                hits += 1
                LOG.info("%s -> %s contains REDIS_URL match in: %s",
                         service_arn, td_arn, matched_containers)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = common_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--cluster", required=True,
                        help="ECS cluster name to audit.")
    parser.add_argument(
        "--redis-host",
        action="append",
        required=True,
        help="Substring of a Redis hostname/URL to match. Repeat for multiple.",
    )
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    ecs = aws_client("ecs", region=args.region)
    hits = audit_cluster(ecs, args.cluster, args.redis_host)
    LOG.info("done: %d service(s) reference one of %s in cluster %s",
             hits, args.redis_host, args.cluster)
    return 0


if __name__ == "__main__":
    sys.exit(main())
