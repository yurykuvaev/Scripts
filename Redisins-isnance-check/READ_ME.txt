# ECS Redis Cluster Usage Checker

## Overview
The `ECSRedisClusterUsageChecker` tool is designed to audit and report on the usage of specified Redis clusters within AWS ECS services in a given production cluster. It helps in ensuring that ECS services are correctly configured to use the intended Redis clusters.

## Features
- Checks specified AWS ECS services to determine if they are utilizing predefined Redis clusters.
- Customizable for different Redis cluster names and AWS ECS production cluster.
- Reports on ECS services that match the specified Redis usage criteria.

## Prerequisites
- AWS CLI installed and configured with the necessary permissions to access ECS and Redis clusters.
- Python 3.x.
- Boto3 library installed.

## Setup and Configuration
1. Clone this repository to your local machine or server.
2. Navigate to the `ECSRedisClusterUsageChecker` folder.
3. Update the `redis_clusters` list in the script with the Redis clusters you want to check.
4. Set the `prod_cluster_name` to the name of your AWS ECS production cluster.

## Usage
Run the script using the command:
python3 redisserviceauditforecs.py