# scripts

Operational helpers I wrote while working on AWS infrastructure. Each one
solves a real chore that came up enough times to deserve a script.

## Quick index

| Script | What it does |
|---|---|
| `SecurityGroupIDExporter.py` | Dump every security group ID in the region to a text file |
| `AddTagsToSecurityGroup.py` | Apply a fixed tag set to a list of SG IDs from a file |
| `SecurityGroupEnvironmentTagApplier.py` | Apply per-SG `Environment` tag from a `<sg> <env>` pairs file |
| `TaggedSecurityGroupCounter.py` | Count SGs that carry a given set of tag keys (compliance check) |
| `TagLogGroups.py` | Tag every CloudWatch Log Group; infer `Environment` from the name |
| `DevEnvironmentTaggerForLogGroups.py` | Tag log groups whose name contains `dev` with `Environment=dev` |
| `AddRoleToECR.py` | Add a role ARN to the `ECRWrite` statement of every ECR repo policy |
| `IAMRolePolicyAuditor/` | Audit a list of IAM roles for forbidden `*:*` permissions |
| `LogsToFirehose/` | Forward CloudWatch Logs subscription to a Firehose delivery stream |
| `Redisins-isnance-check/` | Audit ECS task envs for the Redis URL they point at |
| `Subscription-filters/` | Bulk-set subscription filters on a list of log groups |

## Running

These are standalone scripts, not a package. Each takes its inputs via CLI flags:

```bash
python SecurityGroupIDExporter.py --region us-east-1 --output sg_ids.txt
python TagLogGroups.py --region us-east-1 --tag Product=foo --tag Service=bar --dry-run
```

Pass `--dry-run` (where supported) to preview the API calls without touching AWS.

AWS credentials are read from the standard chain (env vars, `~/.aws/credentials`,
or the EC2/ECS instance role if running there). Set `AWS_PROFILE` to switch profiles.

## Install

```bash
pip install -r requirements.txt
```

Python 3.10+.

## License

MIT — see [LICENSE](LICENSE).
