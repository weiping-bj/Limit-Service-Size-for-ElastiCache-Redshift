import json
import os
import boto3

numLimit = os.environ['NUM_OF_NODES']

def lambda_handler(event, context):
    if "replicationGroupId" in event['requestParameters'] and "numCacheClusters" in event['requestParameters']:
        nodeNum = event['requestParameters']['numCacheClusters']
    elif "replicationGroupId" in event['requestParameters'] and "numNodeGroups" in event['requestParameters']:
        nodeNum = event['requestParameters']['numNodeGroups'] x (event['requestParameters']['replicasPerNodeGroup']+1)
    
    if nodeNum > numLimit:
        result = "BANNED"
    else:
        result = "ALLOWED"
    
    return {
        'statusCode': 200,
        'check': result
    }
