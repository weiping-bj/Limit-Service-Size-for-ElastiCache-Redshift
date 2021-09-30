import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

regionName = os.environ['AWS_REGION']
topicArn = os.environ['TOPIC_ARN']
sns_client = boto3.client('sns', region_name=regionName)
ec_client = boto3.client('elasticache', region_name=regionName)

def lambda_handler(event, context):
    userInfo = event['userIdentity']['arn']
    try:
        if "cacheClusterId" in event['requestParameters']:
            redisName = event['requestParameters']['cacheClusterId']
            ec_client.delete_cache_cluster(
                CacheClusterId=redisName
            )
        else:
            redisName = event['requestParameters']['replicationGroupId']
            ec_client.delete_replication_group(
                ReplicationGroupId=redisName,
                RetainPrimaryCluster=False
            )
    except Exception as e:
        logger.error(e)    

    output = {'Action': "A banned Redis has been deleted",
              'RedisIdentifier': redisName,
              'CreatorARN': userInfo
              }
        
    return {
        'statusCode': 200,
        'body': json.dumps(output)
    }
