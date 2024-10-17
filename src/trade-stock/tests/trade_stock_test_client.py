import boto3
from botocore.config import Config
import os
import argparse
from argparse import RawTextHelpFormatter
from trade_utils.trade_parameter_name import TradeParameterName
from circuitbreaker import circuit
import requests
from circuitbreaker import CircuitBreakerMonitor

parser = argparse.ArgumentParser(prog="Trade Stock Test Client",
                                 description="Test Trade Stock Resiliency",
                                 formatter_class=RawTextHelpFormatter)
parser.add_argument(
    "--test",
    help='''Choose a test to run
    1/ Stress Test''',
    type=int,
    required=True)


@circuit(failure_threshold=10, expected_exception=requests.exceptions.HTTPError, recovery_timeout=60)
def make_call():
    rsp = requests.get("https://digital.nhs.uk/developer/api-catalogue/hello-word")
    rsp.raise_for_status()
    return rsp


def get_url():
    region = 'AWS_PRIMARY_REGION'
    endpoint = None
    ssm = boto3.client("ssm", config=Config(region_name=os.getenv(region)))
    endpoint = ssm.get_parameter(Name=TradeParameterName.TRADE_ORDER_API_ENDPOINT.value)['Parameter']['Value']
    print(endpoint)
    return endpoint


args = parser.parse_args()

test = args.test

if test == 1:
    command = "artillery run trade-stock-stress-test.yml --variables '{ \"url\": \"{url}\" }'".replace(
        "{url}", get_url())
    print(command)
    os.system(command)
if test == 2:
    for i in range(1, 20):
        print(CircuitBreakerMonitor.get("make_call").state)
        try:
            print(make_call())
        except:
            print("error!")

else:
    print("invalid test case, please try again")
