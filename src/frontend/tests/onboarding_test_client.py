import boto3
from botocore.config import Config
import json
import os
import argparse
from argparse import RawTextHelpFormatter
import requests
import random
from uuid import uuid4

parser = argparse.ArgumentParser(prog="Front End Website Test Client",
                                 description="Test Front End Website Resiliency",
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument(
    "--test",
    help='''Choose a test to run
    1/ Load Test''',
    type=int,
    required=True)

def get_url(primary):
    region = 'AWS_PRIMARY_REGION' 
    print(region)
    stack = "FrontEnd-WebsiteStack" 
    print(stack)
    endpoint = None
    cf = boto3.client("cloudformation", config=Config(region_name=os.getenv(region)))
    stacks = cf.describe_stacks(StackName=stack)  # might use an arg to toggle primary or recovery
    outputs = stacks["Stacks"][0]["Outputs"]
    for output in outputs:
        if "WebsiteURL" in output["OutputKey"]:
            endpoint = output["OutputValue"]
            print(endpoint)
    return endpoint


args = parser.parse_args()

test = args.test

if test == 1:
    command = "artillery run front-end-website-load-test.yml --variables '{ \"url\": \"{url}\" }'".replace(
        "{url}", get_url(True))    
    print(command)
    os.system(command)
else:
    print("invalid test case, please try again")
