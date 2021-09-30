import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

regionName = os.environ['AWS_REGION']
topicArn = os.environ['TOPIC_ARN']
sns_client = boto3.client('sns', region_name=regionName)
rs_client = boto3.client('redshift', region_name=regionName)

def lambda_handler(event, context):
    userInfo = event['userIdentity']['arn']
    clusterId = event['requestParameters']['clusterIdentifier']
    try:
        rs_client.delete_cluster(
            ClusterIdentifier=clusterId,
            SkipFinalClusterSnapshot=True
        )
    except Exception as e:
        logger.error(e)
    
    output = {'Action': "A banned redshift cluster has been deleted",
              'ClusterIdentifier': clusterId,
              'CreatorARN': userInfo
              }
    
    sns_client.publish(
        TopicArn=topicArn,
        Subject="RedshiftDeleted",
        Message=json.dumps(output))
    
    
    return {
        'statusCode': 200,
        'body': json.dumps(output)
    }
