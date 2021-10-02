## Control-Redshift-Size

中文 ｜ [English](Redis-ENG.md)

### 介绍
本示例中针对 Redshift 进行控制，仅允许用户创建指定实例规格、制定节点数量的 Redshift 服务。所需创建的服务资源及说明如下表：

序号 | 资源类型 | 资源名称 | 说明 
----|------|------|------
1 | SNS Topic | NotifyMe | 如资源违规，删除资源后向管理员发送通知邮件
2 | EventBridge Rule | redisControl | 过滤出 ElastiCache 服务下所有创建集群的 API 调用
3 | Step Functions State machines | RedisLimit | 检查 redis 创建是否合规的状态机
4 | Lambda Function | parameterCheck | 检查所请求的参数是否符合要求
5 | Lambda Function | statusCheck | 检查 redis 的状态
6 | Lambda Function | deleteCluster | 删除 redis

当 CloudTrail 捕获到创建资源的 API 调用后，会触发 Step Functions 中定义好的状态机，该状态机进行如下判断：

![stateMachine](png/05-redshift-SF-graph.png "stateMachine")

状态机会依次对请求参数中资源的实例类型、数量进行判断，如发现任意一项超出了限制，将会启动资源删除的环节。在 AWS 上，任意资源如果没有进入 Available 状态，则不能删除。因此为了正常删除资源，状态机必须先进入状态检查的环节（RedisStatusCheck），如发现资源不是 Available 状态，则等待 60 秒后重新检查状态。待资源进入 Available 状态后，删除资源。

### 部署
**1. （可选步骤）创建 CloudTrail**  

>如当前账户中已经创建了 CloudTrail trail，则可以跳过此步骤

- 创建 S3 存储桶：

```
BUCKET_NAME=bucket4trail	#可根据需要自定义 S3 存储桶的名称

aws s3api create-bucket --bucket $BUCKET_NAME --region cn-north-1 --create-bucket-configuration LocationConstraint=cn-north-1
```

注意，如果创建的桶不在 us-east-1，则必须增加 --region 和 --create-bucket-configuration 两个参数。上述命令是在 BJS 区域创建一个 S3 存储桶。

- 修改存储桶策略：

```
TRAIL_NAME=rscLimit	#可根据需要自定义 trail 的名称

ACCOUNT_ID=`aws sts get-caller-identity | jq -r ".Account"`

cat << EOF > s3policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AWSCloudTrailAclCheck20150319",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:GetBucketAcl",
            "Resource": "arn:aws-cn:s3:::$BUCKET_NAME"
        },
        {
            "Sid": "AWSCloudTrailWrite20150319",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudtrail.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws-cn:s3:::$BUCKET_NAME/AWSLogs/$ACCOUNT_ID/*",
            "Condition": {
                "StringEquals": {
                    "s3:x-amz-acl": "bucket-owner-full-control"
                }
            }
        }
    ]
}
EOF

aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://s3policy.json 
```

- 创建 CloudTrail trail：

```
aws cloudtrail create-trail --name $TRAIL_NAME --s3-bucket-name $BUCKET_NAME
```

**2. 创建 SNS Topic**

```
TOPIC_NAME=notifyMe	#可根据需要自定义 topic 的名称

NOTIFY_TOPIC_ARN=`aws sns create-topic --name $TOPIC_NAME --region cn-north-1 | jq -r ".TopicArn"`
```

通过 AWS 控制台选择 ```Amazon SNS > 订阅 > 创建订阅```，输入网络管理员邮件地址，如下图：  
![TopicSubscription](png/02-Subscription.png "TopicSubscription")

需要通过管理员的邮箱确认上述订阅。

**3. 创建 IAM 角色**

```
cat << EOF > roleLambda.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF


ROLE_NAME=redshiftLimitRole	#可根据需要自定义 role 的名称

aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://roleLambda.json --region cn-north-1

aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws-cn:iam::aws:policy/CloudWatchLogsFullAccess

aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws-cn:iam::aws:policy/AmazonRedshiftFullAccess

aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws-cn:iam::aws:policy/AmazonSNSFullAccess
```

**4. 创建 parameterCheck 函数**

```
aws lambda create-function --function-name resLimit-01-parameterCheck \
--role "arn:aws-cn:iam::"$ACCOUNT_ID":role/"$ROLE_NAME"" \
--runtime python3.6 \
--handler lambda_function.lambda_handler \
--timeout 3 \
--zip-file fileb://deployment/rsLimit-01-parameterCheck.zip \
--environment "Variables={ \
NUM_OF_NODES=2, \
RS_INSTANCE_TYPE=dc2.large}" \
--region cn-north-1
```

该函数将检查服务启动请求中所要求的实例类型是否符合要求，并给出检查结果，可从 [这里](code/rsLimit-01-parameterCheck.py) 查看函数代码。函数配置了环境变量 <code>NUM\_OF\_NODES</code> 和 <code>RS\_INSTANCE\_TYPE</code>，用于指明用户允许启动的实例类型和实例数量。如果需要允许用户启动多个类型的实例，可以在环境变量变量中设置多个类型，并用英文 “,” 隔开。

**5. 创建 statusCheck 函数**

```
aws lambda create-function --function-name rsLimit-02-statusCheck \
--role "arn:aws-cn:iam::"$ACCOUNT_ID":role/"$ROLE_NAME"" \
--runtime python3.6 \
--handler lambda_function.lambda_handler \
--timeout 3 \
--zip-file fileb://deployment/rsLimit-02-statusCheck.zip \
--region cn-north-1
```

该函数将检查请求启动的资源是否已经启动完毕，并给出检查结果，可从 [这里](code/rsLimit-02-statusCheck.py) 检查函数代码。

**6. 创建 deleteCluster 函数**

```
aws lambda create-function --function-name rsLimit-03-deleteCluster \
--role "arn:aws-cn:iam::"$ACCOUNT_ID":role/"$ROLE_NAME"" \
--runtime python3.6 \
--handler lambda_function.lambda_handler \
--timeout 3 \
--zip-file fileb://deployment/rsLimit-03-deleteCluster.zip \
--environment "Variables={ \
TOPIC_ARN="$NOTIFY_TOPIC_ARN"}" \
--region cn-north-1
```

该函数将删除启动的资源，可从 [这里](code/rsLimit-03-deleteCluster.py) 检查函数代码。

**7. 创建 Step Functions 的状态机**

创建状态机需要的 IAM 角色：

```
SF_NAME=rsLimit

ROLE_NAME=sf-$SF_NAME-role   #可根据需要自定义 role 的名称

aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://deployment/sf-trusted.json --region cn-north-1

sed -i "" 's/<ACCOUNT_ID>/'$ACCOUNT_ID'/g' deployment/sf-rs-lambdInvoke-policy.json

aws iam create-policy --policy-name $SF_NAME --policy-document file://deployment/sf-rs-lambdInvoke-policy.json

aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws-cn:iam::$ACCOUNT_ID\:policy/rsLimit

aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws-cn:iam::aws:policy/AWSXrayFullAccess 

aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn arn:aws-cn:iam::aws:policy/CloudWatchLogsFullAccess
```

创建 Step Functions 的状态机

```
sed -i "" 's/<ACCOUNT_ID>/'$ACCOUNT_ID'/g' deployment/rs-SF-sample.json

aws stepfunctions create-state-machine --name $SF_NAME --definition file://deployment/rs-SF-sample.json --role-arn arn:aws-cn:iam::$ACCOUNT_ID\:role/sf-rsLimit-role --region cn-north-1
```
 
**8. 创建 EventBridge 的规则**

创建 EventBridge 规则所需要的 IAM 角色：

```
ROLE_NAME=eb-$SF_NAME-role   #可根据需要自定义 role 的名称

aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://deployment/eb-trusted.json --region cn-north-1

sed -i "" 's/<ACCOUNT_ID>/'$ACCOUNT_ID'/g' deployment/eb-sfInvoke-rs-policy.json

aws iam create-policy --policy-name $SF_NAME --policy-document file://deployment/eb-sfInvoke-rs-policy.json
```

创建 EventBridge 规则：

```
RULE_NAME=rsLimitRule	#可根据需要自定义 rule 的名称

aws events put-rule --name $RULE_NAME --event-pattern file://deployment/eb-rs-eventPattern.json --role-arn arn:aws-cn:iam::$ACCOUNT_ID\:role/eb-rsLimit-role --region cn-north-1

```

将第 7 步中创建的状态机作为目标关联给这条 EventBridge 规则：

```
aws events put-targets --rule $RULE_NAME --targets Id=Target1,Arn=arn:aws-cn:states:cn-north-1:$ACCOUNT_ID\:stateMachine:rsLimit,RoleArn=arn:aws-cn:iam::$ACCOUNT_ID\:role/eb-rsLimit-role --region cn-north-1
```

部署完毕。

[返回 README](README.md)