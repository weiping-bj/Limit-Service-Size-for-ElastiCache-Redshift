import json
import boto3
import os

regionName = os.environ['AWS_REGION']
rs_client = boto3.client('redshift', region_name=regionName)

def lambda_handler(event, context):
    response = rs_client.describe_clusters(
        ClusterIdentifier=event
        )
    status = response['Clusters'][0]['ClusterStatus']
    print("The cluster status is: " + status)
    return {
        'statusCode': 200,
        'status': status
    }
