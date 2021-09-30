import json
import os

typeLimit = os.environ['RS_INSTANCE_TYPE']
numLimit = os.environ['NUM_OF_NODES']


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
    
    print("Node limit is: " + typeLimit)
    print("Node request is: " + event['detail']['requestParameters']['nodeType'])

    
    if event['detail']['requestParameters']['nodeType'] in nodeTypes:
        if "numberOfNodes" in event['detail']['requestParameters']:
            print("Request node number is: " + str(event['detail']['requestParameters']['numberOfNodes']))
            print("Number Limit is: " + str(numLimit))
            if int(event['detail']['requestParameters']['numberOfNodes']) > int(numLimit):
                result = "BANNED"
            else:
                result = "ALLOWED"
        else:
            result = "ALLOWED"
    else:
        result = "BANNED"
    
    print("This redshift cluster is "+ result)
    
    return {
        'statusCode': 200,
        'checkCode': result,
        'clusterID': event['detail']['requestParameters']['clusterIdentifier']
    }
