import boto3
import json

ecr_client = boto3.client('ecr')
new_role_arn = "arn:aws:iam::123:role/cicd-ecs-deploy"
repositories = ecr_client.describe_repositories()['repositories']

for repo in repositories:
    repo_name = repo['repositoryName']

    try:
        response = ecr_client.get_repository_policy(repositoryName=repo_name)
        policy = json.loads(response['policyText'])

        updated = False
        for statement in policy['Statement']:
            if statement['Sid'] == "ECRWrite":
                if new_role_arn not in statement['Principal']['AWS']:
                    if isinstance(statement['Principal']['AWS'], list):
                        statement['Principal']['AWS'].append(new_role_arn)
                    else:
                        statement['Principal']['AWS'] = [statement['Principal']['AWS'], new_role_arn]
                    updated = True

        if updated:
            ecr_client.set_repository_policy(
                repositoryName=repo_name,
                policyText=json.dumps(policy)
            )

            print(f"Updated policy for repository: {repo_name}")
    except ecr_client.exceptions.RepositoryPolicyNotFoundException:
        print(f"No policy found for repository: {repo_name}")
    except Exception as e:
        print(f"Error updating policy for repository: {repo_name}. Error: {str(e)}")
