# IAM Role Policy Auditor

## Overview
`ECSRolePolicyComplianceCheck.py` is a script designed to audit AWS IAM roles, specifically focusing on ECS roles. It checks for specific role naming patterns and verifies whether a designated policy is attached to these roles. This is crucial for maintaining security and compliance in AWS ECS environments.

## Features
- Identifies IAM roles based on customizable name patterns.
- Verifies the attachment of a specified policy to these roles.
- Outputs a list of roles lacking the required policy.

## Prerequisites
- AWS CLI installed and configured with necessary permissions.
- Python 3.x.
- Boto3 library installed.

## Setup and Configuration
1. Clone this repository to your local machine or server.
2. Navigate to the `IAMRolePolicyAuditor` folder.
3. Update `role_patterns` and `policy_arn_to_check` in the script as per your requirements.
