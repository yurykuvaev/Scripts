import boto3

# Define the Redis clusters to check for
redis_clusters = ["iassa-u", "qa-sg-rdis"]

# Specify the production cluster name
prod_cluster_name = "prod"  # Replace with your production cluster name

# Create a Boto3 client for ECS
ecs_client = boto3.client('ecs')

# Function to check if a task definition uses a specific Redis cluster
def uses_redis_cluster(task_definition, redis_clusters):
    for container_definition in task_definition['containerDefinitions']:
        # Check environment variables and other configuration as needed
        for env_var in container_definition.get('environment', []):
            if env_var['name'] == 'REDIS_URL' and any(redis_cluster in env_var['value'] for redis_cluster in redis_clusters):
                return True
    return False

# List all ECS services in the specified production cluster
def check_ecs_services_for_redis(cluster_name):
    paginator = ecs_client.get_paginator('list_services')
    for page in paginator.paginate(cluster=cluster_name):
        service_arns = page['serviceArns']
        for service_arn in service_arns:
            # Describe the service to get task definition
            service = ecs_client.describe_services(cluster=cluster_name, services=[service_arn])
            task_definition_arn = service['services'][0]['taskDefinition']
            task_definition = ecs_client.describe_task_definition(taskDefinition=task_definition_arn)

            # Check if the task definition uses one of the Redis clusters
            if uses_redis_cluster(task_definition['taskDefinition'], redis_clusters):
                print(f"Service {service_arn} in cluster {cluster_name} uses one of the specified Redis clusters.")

check_ecs_services_for_redis(prod_cluster_name)
