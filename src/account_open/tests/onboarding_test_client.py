import boto3
from botocore.config import Config
import json
import os
import argparse
from argparse import RawTextHelpFormatter
import requests
import random
from uuid import uuid4

parser = argparse.ArgumentParser(prog="Account Open Test Client",
                                 description="Test Account Open Resiliency",
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument(
    "--test",
    help='''Choose a test to run
    1/ Submit a valid request.  
    2/ Submit a invalid request missing account_type.
    3/ Retries - see text, use CDK deployments. 
    4/ Test load throttling.
    5/ Poison pill, test DLQ.
    6/ Switch to secondary region. 
    7/ Switch back to primary.
    8/ Test in recovery/green region.''',
    type=int,
    required=True)
parser.add_argument("--request_token",
                    help="Use specified request token instead of generating at random. Good for idempotency testing.",
                    type=str,
                    default='')
parser.add_argument("--user_id",
                    help="Create accounts for specified user_id instead of randomly generating a user_id.",
                    type=str,
                    default='')


def in_recovery_mode(s3_client, failover_bucket_name):
    objects = s3_client.list_objects_v2(Bucket=failover_bucket_name)
    for obj in objects.get('Contents', []):
        if 'failover.txt' in obj['Key']:
            return True
    return False


def get_url(primary):
    region = 'AWS_PRIMARY_REGION' if primary is True else 'AWS_SECONDARY_REGION'
    stack = "ProcessStack-primary" if primary is True else "ProcessStack-secondary"
    endpoint = None
    cf = boto3.client("cloudformation", config=Config(region_name=os.getenv(region)))
    stacks = cf.describe_stacks(
        StackName=stack)  # might use an arg to toggle primary or recovery
    outputs = stacks["Stacks"][0]["Outputs"]
    for output in outputs:
        if "NewAccountApiEndpoint" in output["OutputKey"]:
            endpoint = output["OutputValue"]
            print(endpoint)
    return endpoint


def request_account(file, endpoint):
    payload = json.load(open(file))
    payload["request_token"] = args.request_token if len(
        args.request_token) > 2 else f"{uuid4()}"
    payload["user_id"] = args.user_id if len(args.user_id) > 2 else f"user{random.randrange(999)}"
    print(payload)
    r = requests.put(endpoint, json=payload)
    print(r)


args = parser.parse_args()

test = args.test
filename = "failover.txt"

if test == 1:
    request_account('account_valid.json', get_url(True))
elif test == 2:
    request_account('account_invalid.json', get_url(True))
elif test == 3:
    print("Use CDK deployments to test retries, this test client does not support the use case")
elif test == 4:
    command = "artillery run new-account-load-test.yml --variables '{ \"url\": \"{url}\" }'".replace(
        "{url}", get_url(True).replace('/prod/', ''))
    print(command)
    os.system(command)
elif test == 5:
    request_account('account_poison_pill.json', get_url(True))
elif test == 6:
    s3 = boto3.client("s3", config=Config(region_name=os.getenv('AWS_SECONDARY_REGION')))  # secondary?
    failover_bucket = f"failover-bucket-{os.getenv('AWS_SECONDARY_REGION')}-{os.getenv('AWS_ACCOUNT_ID')}"
    print(failover_bucket)
    if in_recovery_mode(s3, failover_bucket):
        print("already in secondary region")
    else:

        with open(filename, "rb") as f:
            response = s3.upload_fileobj(f, failover_bucket, filename)
        print("Switched to secondary region")
elif test == 7:
    s3 = boto3.client("s3", config=Config(region_name=os.getenv('AWS_SECONDARY_REGION')))  # secondary?
    failover_bucket = f"failover-bucket-{os.getenv('AWS_SECONDARY_REGION')}-{os.getenv('AWS_ACCOUNT_ID')}"
    if not in_recovery_mode(s3, failover_bucket):
        print("Primary region is already active")
    else:
        s3.delete_object(Bucket=failover_bucket, Key=filename)
        print("Switched to primary region")
elif test == 8:
    request_account('account_valid.json', get_url(False))
else:
    print("invalid test case, please try again")
