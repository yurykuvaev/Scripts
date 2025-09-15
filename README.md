# scripts

[![CI](https://github.com/yurykuvaev/Scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/yurykuvaev/Scripts/actions/workflows/ci.yml)

Operational helpers I wrote while working on AWS infrastructure. Each one
solves a real chore that came up enough times to deserve a script.

## Quick index

| Script | What it does |
|---|---|
| `security_group_id_exporter.py` | Dump every security group ID in the region to a text file |
| `add_tags_to_security_group.py` | Apply `KEY=VALUE` tags to a list of SG IDs from a file |
| `security_group_environment_tag_applier.py` | Apply per-SG `Environment` tag from a `<sg> <env>` pairs file |
| `tagged_security_group_counter.py` | Count SGs that carry a given set of tag keys (compliance check) |
| `tag_log_groups.py` | Tag every CloudWatch Log Group; infer `Environment` from the name |
| `dev_environment_tagger_for_log_groups.py` | Tag log groups whose name contains a substring with `Environment=<value>` |
| `add_role_to_ecr.py` | Add a role ARN to a named statement in every ECR repo policy |
| `iam_role_policy_auditor/` | Audit IAM roles by name prefix for an expected attached policy (CI-friendly exit code) |
| `logs_to_firehose/` | Subscribe a single log group to a Firehose delivery stream |
| `redis_instance_check/` | Find ECS services pointing at a list of Redis hosts |
| `subscription_filters/` | Bulk-attach subscription filters across log groups |

## Running

Every script takes its inputs via CLI flags. They share a common base so
the same `--region`, `--dry-run`, `--verbose` flags work everywhere:

```bash
# Inventory
python security_group_id_exporter.py --region us-east-1 -o sg_ids.txt

# Tagging — preview first
python add_tags_to_security_group.py \
    --region us-east-1 \
    --input sg_ids.txt \
    --tag Product=ingest --tag Service=api --tag SupportGroup=platform \
    --dry-run

# When happy, run for real
python add_tags_to_security_group.py \
    --region us-east-1 \
    --input sg_ids.txt \
    --tag Product=ingest --tag Service=api --tag SupportGroup=platform

# Compliance check — exits non-zero if any role is missing the policy
python iam_role_policy_auditor/ecs_role_policy_compliance_check.py \
    --role-prefix ecs-task- \
    --policy-arn arn:aws:iam::123456789012:policy/EcsRoleTaggingPolicy
```

`--dry-run` is supported by every script that calls a write API; output
shows the API calls that would be made without actually making them.

AWS credentials are read from the standard chain (env vars,
`~/.aws/credentials`, or the EC2/ECS instance role). Set `AWS_PROFILE` to
switch profiles.

## Development

```bash
make install     # boto3 + ruff + mypy + pytest
make lint        # ruff check
make test        # pytest
make all         # lint + type + test
```

CI runs the same on every push. See [.github/workflows/ci.yml](.github/workflows/ci.yml).

Python 3.10+.

## License

MIT — see [LICENSE](LICENSE).
