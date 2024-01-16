import boto3

region = 'us-east-1'
kinesis_firehose_stream_name = 'FirehoseSplunkDeliveryStream'
filter_name = 'Destination'
filter_pattern = ''
account_id = '123'
role_arn = f'arn:aws:iam::{account_id}:role/CWLK8nesisFirehoseRole'

logs_client = boto3.client('logs', region_name=region)

try:
    log_groups = logs_client.describe_log_groups()['logGroups']
except Exception as e:
    print(f'Error retrieving log groups: {e}')
    log_groups = []

for log_group in log_groups:
    log_group_name = log_group['logGroupName']
    try:
        logs_client.put_subscription_filter(
            logGroupName=log_group_name,
            filterName=filter_name,
            filterPattern=filter_pattern,
            destinationArn=f'arn:aws:firehose:{region}:{account_id}:deliverystream/{kinesis_firehose_stream_name}',
            roleArn=role_arn
        )
        print(f'Subscription filter added to {log_group_name}')
    except Exception as e:
        print(f'Error adding subscription filter to {log_group_name}: {e}')
