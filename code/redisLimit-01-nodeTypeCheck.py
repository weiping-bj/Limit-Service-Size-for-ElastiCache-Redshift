import json
import os

typeLimit = os.environ['REDIS_INSTANCE_TYPE']

def lambda_handler(event, context):
    nodeTypes=[]
    types = typeLimit.split(',')
    if "," in typeLimit:
        i=0
        while i<len(rs):
            nodeTypes.append(types[i].strip())
            i=i+1
    else:
        nodeTypes.append(typeLimit.strip())
    
    if event['detail']['requestParameters']['cacheNodeType'] in nodeTypes and event['detail']['requestParameters']['engine'] == "redis":
        result = "ALLOWED"
    else:
        result = "BANNED"
    
    return {
        'statusCode': 200,
        'checkCode': result
    }
