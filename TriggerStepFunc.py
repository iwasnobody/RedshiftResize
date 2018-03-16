import boto3
import os

client = boto3.client('stepfunctions',region_name='ap-northeast-1')

def lambda_handler(event, context):
    response = client.start_execution(
        stateMachineArn=os.environ['StepFuncArn'],
        input="{\"Action\" : \"stopdms\",\"Error-info\" : \"None\"}"
    )
