# redis_instance_check

Find ECS services whose task definitions still point at a list of Redis
hostnames. Useful when migrating Redis fleet — gives a list of services
that need their `REDIS_URL` env var rotated to the new endpoint.

## How it works

`redis_service_audit_for_ecs.py` walks every service in the given ECS
cluster, fetches its task definition, and checks each container's
`environment` for a `REDIS_URL` whose value contains any of the
substrings passed via `--redis-host`. Read-only — no mutations.

## Usage

```bash
# What ECS services in the prod cluster still hit either of these Redis nodes?
python redis_service_audit_for_ecs.py \
    --region us-east-1 \
    --cluster prod \
    --redis-host old-cache-1.abc.cache.amazonaws.com \
    --redis-host old-cache-2.abc.cache.amazonaws.com
```

Output is one line per matching service:

```
INFO arn:aws:ecs:us-east-1:.../service/prod/foo -> task-def:42 contains REDIS_URL match in: ['app']
INFO arn:aws:ecs:us-east-1:.../service/prod/bar -> task-def:11 contains REDIS_URL match in: ['app', 'worker']
```
