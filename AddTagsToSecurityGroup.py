import boto3

session = boto3.Session()

ec2_client = session.client('ec2')

def add_tags_to_security_group(security_group_id, tags_to_add):
    response = ec2_client.describe_tags(
        Filters=[
            {'Name': 'resource-id', 'Values': [security_group_id]}
        ]
    )
    current_tags = response.get('Tags', [])

    current_tags_dict = {tag['Key']: tag['Value'] for tag in current_tags}

    tags_to_create = []
    for key, value in tags_to_add.items():
        if key not in current_tags_dict:
            tags_to_create.append({'Key': key, 'Value': value})
    
    if tags_to_create:
        ec2_client.create_tags(Resources=[security_group_id], Tags=tags_to_create)

required_tags = {
    'Product': '123',
    'Service': '123',       #Changed for security resons
    'SupportGroup': '123'
}

with open('sg_ids.txt', 'r') as file:
    security_group_ids = [line.strip() for line in file.readlines()]

for sg_id in security_group_ids:
    add_tags_to_security_group(sg_id, required_tags)
