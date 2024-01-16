import boto3

logs_client = boto3.client('logs')
tagging_client = boto3.client('resourcegroupstaggingapi')

environments = [
    "qa", "dev-01", "dev-02", "dev-03", "dev-04", "dev-05"
]

def find_environment(log_group_name):
    """ Find the environment based on the log group name """
    for env in environments:
        if env in log_group_name:
            return env
    return None

def tag_log_group(log_group_name, tags):
    """ Tag a log group if it doesn't have the specified tags """
    response = tagging_client.get_resources(
        ResourceTypeFilters=['logs'],
        TagFilters=[{'Key': 'log-group-name', 'Values': [log_group_name]}]
    )

    existing_tags = response.get('ResourceTagMappingList', [])[0].get('Tags', {}) if response.get('ResourceTagMappingList') else {}
    
    new_tags = {k: v for k, v in tags.items() if k not in existing_tags}
    if new_tags:
        logs_client.tag_log_group(logGroupName=log_group_name, tags=new_tags)

def main():
    paginator = logs_client.get_paginator('describe_log_groups')
    for page in paginator.paginate():
        for log_group in page['logGroups']:
            log_group_name = log_group['logGroupName']
            env = find_environment(log_group_name)
            tags = {
                'Product': '123',
                'Service': '123',       #Changed for security reasons
                'SupportGroup': '123'
            }
            if env:
                tags['Environment'] = env

            tag_log_group(log_group_name, tags)

if __name__ == "__main__":
    main()