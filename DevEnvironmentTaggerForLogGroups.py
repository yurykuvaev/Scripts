import boto3

# Initialize the CloudWatch Logs and ResourceGroupsTaggingAPI clients
logs_client = boto3.client('logs')
tagging_client = boto3.client('resourcegroupstaggingapi')

def tag_log_group_if_dev(log_group_name):
    """ Tag a log group with environment = dev if 'dev' is in the name and the tag doesn't exist """
    # Check existing tags
    response = tagging_client.get_resources(
        ResourceTypeFilters=['logs'],
        TagFilters=[{'Key': 'log-group-name', 'Values': [log_group_name]}]
    )

    existing_tags = response.get('ResourceTagMappingList', [])[0].get('Tags', {}) if response.get('ResourceTagMappingList') else {}

    # Add 'Environment' tag with value 'dev' if not present and 'dev' is in the log group name
    if 'dev' in log_group_name and 'Environment' not in existing_tags:
        logs_client.tag_log_group(logGroupName=log_group_name, tags={'Environment': 'dev'})

def main():
    # Get all log groups
    paginator = logs_client.get_paginator('describe_log_groups')
    for page in paginator.paginate():
        for log_group in page['logGroups']:
            log_group_name = log_group['logGroupName']
            # Tag the log group if it meets the criteria
            tag_log_group_if_dev(log_group_name)

if __name__ == "__main__":
    main()
