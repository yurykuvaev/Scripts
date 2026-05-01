# subscription_filters

Bulk-attach CloudWatch Logs subscription filters across every log group in
a region. Use this when standing up a new Firehose pipeline that should
capture *all* logs (or all logs matching a name pattern).

## Usage

```bash
# Dry-run: show what would happen, don't touch anything
python cloudwatch_to_firehose_filter_setter.py \
    --region us-east-1 \
    --stream FirehoseSplunkDeliveryStream \
    --role-arn arn:aws:iam::123456789012:role/CWLtoKinesisFirehoseRole \
    --dry-run

# Limit to log groups containing 'prod' or 'staging' in the name
python cloudwatch_to_firehose_filter_setter.py \
    --region us-east-1 \
    --stream FirehoseSplunkDeliveryStream \
    --role-arn arn:aws:iam::123456789012:role/CWLtoKinesisFirehoseRole \
    --name-substring prod \
    --name-substring staging
```

The script tallies `attached / skipped / failed` at the end and exits
non-zero if any `put_subscription_filter` call raised - friendly for CI
or a make-style pipeline.

For a single-group attach, see [`../logs_to_firehose/`](../logs_to_firehose/).
