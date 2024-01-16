import boto3

session = boto3.Session()

ec2_client = session.client('ec2')

def get_all_security_group_ids():
    response = ec2_client.describe_security_groups()
    security_groups = response['SecurityGroups']

    sg_ids = [sg['GroupId'] for sg in security_groups]
    return sg_ids

def write_to_file(file_name, sg_ids):
    with open(file_name, 'w') as file:
        for sg_id in sg_ids:
            file.write(sg_id + '\n')
    print(f"Security group IDs written to {file_name}")

security_group_ids = get_all_security_group_ids()

write_to_file('sg_ids.txt', security_group_ids)
