import boto3

# Set these variables
region = 'us-east-1'  # Replace with your AWS region if different
log_group_name = '/ecs/ddos-123-dev-05'  # Updated log group name
kinesis_firehose_stream_name = 'kinesis-splunk'  # Updated Kinesis Firehose stream name
filter_name = 'Destination'  # Filter name (can be customized)
filter_pattern = ''  # Filter pattern (empty for all logs)
role_arn = 'arn:aws:iam::123:role/CWLtoKinesisFirehoseRole'  # Replace with your IAM role ARN if different

# Initialize the STS client to get the account ID
sts_client = boto3.client('sts', region_name=region)
account_id = sts_client.get_caller_identity()["Account"]

# Initialize the CloudWatch Logs client
logs_client = boto3.client('logs', region_name=region)

# Create the subscription filter
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
    print(f'Error adding subscription filter: {e}')
