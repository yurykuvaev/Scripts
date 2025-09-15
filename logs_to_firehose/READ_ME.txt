# CloudWatch Logs to Kinesis Firehose Subscription Filter

## Overview
This script, `CloudWatchToKinesisFirehose`, automates the process of creating a subscription filter in AWS CloudWatch Logs to forward logs to a specified Kinesis Firehose stream. This is particularly useful for log analysis and real-time data streaming to other services or applications.

## Features
- Automatically sets up a subscription filter in CloudWatch Logs.
- Configurable for different AWS regions, log groups, and Kinesis Firehose streams.
- Supports custom filter patterns and names.

## Prerequisites
- AWS CLI installed and configured with necessary permissions.
- Python 3.x.
- Boto3 library installed.
- An IAM role with the necessary permissions.

## Setup and Configuration
1. Clone this repository to your local machine or server.
2. Navigate to the `CloudWatchToKinesisFirehose` folder.
3. Open the script and update the following variables:
    - `region`
    - `log_group_name`
    - `kinesis_firehose_stream_name`
    - `filter_name`
    - `filter_pattern`
    - `role_arn`
4. Save the changes to the script.
