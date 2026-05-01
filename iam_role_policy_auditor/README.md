# iam_role_policy_auditor

Audit IAM roles by name prefix for an expected attached policy.

`ecs_role_policy_compliance_check.py` walks every IAM role whose name
starts with one of the given `--role-prefix` values and checks that
`--policy-arn` is attached. Roles that miss the policy are written to
`--output` (or stdout). Exits non-zero if anything is non-compliant -
drop it into CI and the build fails when a new role drifts.

## Usage

```bash
# Print non-compliant role names to stdout
python ecs_role_policy_compliance_check.py \
    --role-prefix ecs-task- \
    --role-prefix task-runner- \
    --policy-arn arn:aws:iam::123456789012:policy/EcsRoleTaggingPolicy

# Save to a file, useful as input to a remediation script
python ecs_role_policy_compliance_check.py \
    --role-prefix ecs-task- \
    --policy-arn arn:aws:iam::123456789012:policy/EcsRoleTaggingPolicy \
    -o non_compliant.txt
```

IAM is global, so `--region` is accepted but ignored.

## Exit codes

- `0` - every matched role has the policy
- `1` - at least one role is missing it (also the case in --dry-run)
