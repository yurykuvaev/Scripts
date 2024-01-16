import boto3

# Initialize a boto3 IAM client
iam_client = boto3.client('iam')

# Define the role name patterns
role_patterns = [
    'ecs-t1le-*',   
    'ecs-1le-*',    
    'ecs-t12le',   #Changed for security reasons
    'task-e1le-*',  
    'task-r1e-*'    
]

# Policy ARN to check for
policy_arn_to_check = 'arn:aws:iam::123:policy/EcsRoleTaggingPolicy'

def list_roles():
    """List all IAM roles."""
    roles = []
    paginator = iam_client.get_paginator('list_roles')
    for response in paginator.paginate():
        roles.extend(response['Roles'])
    return roles

def is_policy_attached(role_name, policy_arn):
    """Check if a specific policy is attached to a role."""
    attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
    for policy in attached_policies:
        if policy['PolicyArn'] == policy_arn:
            return True
    return False

roles_without_policy = []

# Check each role and see if the policy is attached
for role in list_roles():
    if any(role['RoleName'].startswith(pattern) for pattern in role_patterns):
        if not is_policy_attached(role['RoleName'], policy_arn_to_check):
            roles_without_policy.append(role['RoleName'])

# Write roles without the policy to a file
with open('1.txt', 'w') as file:
    for role in roles_without_policy:
        file.write(role + '\n')

print(f"Roles without the policy {policy_arn_to_check} have been listed in 1.txt")
