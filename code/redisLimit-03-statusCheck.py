import json
import boto3
import os

regionName = os.environ['AWS_REGION']
ec_client = boto3.client('elasticache', region_name=regionName)

def lambda_handler(event, context):
    if "replicationGroupId" in event['requestParameters']:
        response = ec_client.describe_replication_groups(
            ReplicationGroupId=event['requestParameters']['replicationGroupId']
        )
        redisStatus = response['ReplicationGroups'][0]['Status']
    else:
        response = ec_client.describe_cache_clusters(
            CacheClusterId=event['requestParameters']['cacheClusterId']
        )
        redisStatus = response['CacheClusters'][0]['CacheClusterStatus']
    
    return {
        'statusCode': 200,
        'redisStatus': redisStatus
    }
