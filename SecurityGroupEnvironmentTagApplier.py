import boto3

# Initialize a session using AWS SDK
session = boto3.Session()

# Create EC2 client
ec2_client = session.client('ec2')

def read_sg_env_pairs(file_name):
    pairs = {}
    with open(file_name, 'r') as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) == 2:
                pairs[parts[0]] = parts[1]
    return pairs

def tag_security_group(sg_id, env):
    # Retrieve current tags for the security group
    response = ec2_client.describe_tags(
        Filters=[{'Name': 'resource-id', 'Values': [sg_id]}]
    )
    current_tags = response.get('Tags', [])

    # Check if 'Environment' tag exists and its value
    env_tag = next((tag for tag in current_tags if tag['Key'] == 'Environment'), None)
    if env_tag and env_tag['Value'] != 'dev' and env_tag['Value'] != env:
        return  # Skip if a different environment tag exists

    # Update or add the 'Environment' tag
    ec2_client.create_tags(
        Resources=[sg_id],
        Tags=[{'Key': 'Environment', 'Value': env}]
    )

# File containing the SG and environment pairs
file_name = 'sg_env_pairs.txt'

# Read SG ID and environment pairs from the file
sg_env_pairs = read_sg_env_pairs(file_name)

# Apply tags to the security groups
for sg_id, env in sg_env_pairs.items():
    tag_security_group(sg_id, env)
