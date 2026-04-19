# scripts

[![CI](https://github.com/yurykuvaev/Scripts/actions/workflows/ci.yml/badge.svg)](https://github.com/yurykuvaev/Scripts/actions/workflows/ci.yml)

Operational helpers I wrote while working on AWS infrastructure. Each one
solves a real chore that came up enough times to deserve a script.

## Quick index

### Tagging & inventory
| Script | What it does |
|---|---|
| `security_group_id_exporter.py` | Dump SG IDs (with `--vpc-id` and `--missing-tag` filters) |
| `add_tags_to_security_group.py` | Apply `KEY=VALUE` tags from a file or to every SG in the region |
| `security_group_environment_tag_applier.py` | Apply per-SG `Environment` tag from a `<sg> <env>` pairs file |
| `tagged_security_group_counter.py` | Count SGs that carry a given set of tag keys (compliance check) |
| `tag_log_groups.py` | Tag CloudWatch Log Groups, inferring `Environment` from the name |

### Cost / cleanup
| Script | What it does |
|---|---|
| `unused_security_groups.py` | Find SGs nothing references; optional `--delete` with topo-sorted order |
| `ami_cleanup.py` | Deregister unused AMIs and reclaim EBS snapshots, with per-prefix retention |
| `ecr_image_aging.py` | Pull-aware ECR cleanup with `--keep-tag-pattern` and `--keep-last-n` safety nets |

### IAM / compliance
| Script | What it does |
|---|---|
| `iam_policy_minimizer.py` | Generate a least-privilege policy for a role from CloudTrail history |
| `iam_role_policy_auditor/` | Audit IAM roles by name prefix for an expected policy (CI-friendly exit code) |
| `add_role_to_ecr.py` | Add a role ARN to a named statement in every ECR repo policy |

### Observability
| Script | What it does |
|---|---|
| `logs_to_firehose/` | Subscribe a single log group to a Firehose delivery stream |
| `subscription_filters/` | Bulk-attach subscription filters across log groups |
| `redis_instance_check/` | Find ECS services pointing at a list of Redis hosts |

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

## IAM permissions per script

Minimum permissions an executor identity needs. All actions are read-only
unless the script is invoked with `--delete` (and where applicable
`--all-in-region`).

| Script | Read | Write (only when --delete / not --dry-run) |
|---|---|---|
| `security_group_id_exporter.py` | `ec2:DescribeSecurityGroups` | — |
| `add_tags_to_security_group.py` | `ec2:DescribeSecurityGroups`, `ec2:DescribeTags` | `ec2:CreateTags` |
| `security_group_environment_tag_applier.py` | `ec2:DescribeTags` | `ec2:CreateTags` |
| `tagged_security_group_counter.py` | `ec2:DescribeSecurityGroups` | — |
| `tag_log_groups.py` | `logs:DescribeLogGroups`, `logs:ListTagsLogGroup` | `logs:TagLogGroup` |
| `add_role_to_ecr.py` | `ecr:DescribeRepositories`, `ecr:GetRepositoryPolicy` | `ecr:SetRepositoryPolicy` |
| `unused_security_groups.py` | `ec2:DescribeSecurityGroups`, `ec2:DescribeNetworkInterfaces`, `ec2:DescribeLaunchTemplates`, `ec2:DescribeLaunchTemplateVersions` | `ec2:DeleteSecurityGroup` |
| `ami_cleanup.py` | `ec2:DescribeImages`, `ec2:DescribeInstances`, `ec2:DescribeLaunchTemplates`, `ec2:DescribeLaunchTemplateVersions`, `autoscaling:DescribeAutoScalingGroups`, `autoscaling:DescribeLaunchConfigurations` | `ec2:DeregisterImage`, `ec2:DeleteSnapshot` |
| `ecr_image_aging.py` | `ecr:DescribeRepositories`, `ecr:DescribeImages` | `ecr:BatchDeleteImage` |
| `iam_policy_minimizer.py` | `cloudtrail:LookupEvents`, `iam:ListAttachedRolePolicies`, `iam:ListRolePolicies`, `iam:GetPolicy`, `iam:GetPolicyVersion`, `iam:GetRolePolicy` | — (read-only; emits a JSON suggestion) |
| `iam_role_policy_auditor/...` | `iam:ListRoles`, `iam:ListAttachedRolePolicies` | — |
| `logs_to_firehose/...` | `sts:GetCallerIdentity` | `logs:PutSubscriptionFilter` |
| `redis_instance_check/...` | `ecs:ListServices`, `ecs:DescribeServices`, `ecs:DescribeTaskDefinition` | — |
| `subscription_filters/...` | `sts:GetCallerIdentity`, `logs:DescribeLogGroups` | `logs:PutSubscriptionFilter` |

The IAM role passed via `--role-arn` to scripts that wire up CloudWatch
subscription filters needs its own trust policy on `logs.amazonaws.com`
plus `firehose:PutRecord`/`firehose:PutRecordBatch` on the destination.

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
