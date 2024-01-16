import boto3

# Initialize a session using AWS SDK
session = boto3.Session()

# Create an EC2 client
ec2_client = session.client('ec2')

def count_security_groups_with_tags(tags_to_check):
    # Get all security groups
    response = ec2_client.describe_security_groups()
    security_groups = response['SecurityGroups']

    # Counter for security groups with the specified tags
    count_sg_with_tags = 0

    # Check each security group for the specified tags
    for sg in security_groups:
        # Extract the tags from the security group
        sg_tags = sg.get('Tags', [])
        sg_tags_dict = {tag['Key']: tag['Value'] for tag in sg_tags}
        
        # Check if all the specified tag keys are present in the security group's tags
        if all(key in sg_tags_dict for key in tags_to_check):
            count_sg_with_tags += 1

    return count_sg_with_tags

# Tags to check for in each security group
required_tags = ['Product', 'Service', 'SupportGroup']

# Get the count of security groups with the required tags
sg_count = count_security_groups_with_tags(required_tags)

# Print out the count
print(f"Number of security groups with the specified tags: {sg_count}")
