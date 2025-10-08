# logs_to_firehose

Subscribe a single CloudWatch Log Group to a Kinesis Firehose delivery
stream so its events get forwarded onward (Splunk, S3, Elasticsearch — wherever
the Firehose ends up).

`cloudwatch_to_kinesis_firehose.py` resolves the AWS account ID via STS, so
the destination ARN is built dynamically — no hardcoded account number.

## Usage

```bash
# Dry-run first
python cloudwatch_to_kinesis_firehose.py \
    --region us-east-1 \
    --log-group /ecs/my-service \
    --stream firehose-splunk \
    --role-arn arn:aws:iam::123456789012:role/CWLtoKinesisFirehoseRole \
    --dry-run

# Apply
python cloudwatch_to_kinesis_firehose.py \
    --region us-east-1 \
    --log-group /ecs/my-service \
    --stream firehose-splunk \
    --role-arn arn:aws:iam::123456789012:role/CWLtoKinesisFirehoseRole
```

For the bulk variant (every log group at once), see
[`subscription_filters/`](../subscription_filters/).

## IAM the role needs

The role passed via `--role-arn` must trust `logs.amazonaws.com` and have
`firehose:PutRecord` / `PutRecordBatch` on the destination stream. AWS docs:
https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/SubscriptionFilters.html
