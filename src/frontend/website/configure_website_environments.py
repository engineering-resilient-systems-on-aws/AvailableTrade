import sys
import boto3
from botocore.config import Config
import os
from trade_utils.trade_parameter_name import TradeParameterName 
from account_utils.account_open_parameter_name import AccountOpenParameterName 
from enum import Enum


class ViteConfigEnum(Enum):
    VITE_NEW_ACCOUNT_ENDPOINT = 'VITE_NEW_ACCOUNT_ENDPOINT'
    VITE_TRADE_STOCK_ENDPOINT = 'VITE_TRADE_STOCK_ENDPOINT'
    VITE_RUM_APPLICATION_ID = 'VITE_RUM_APPLICATION_ID'


def generate_config_files(parameter_api, parameter_domain_name):
    """Generates .env.development and .env.production files based on parameters.

    Args:
        parameter_api (str): 'y' to use custom domain name, 'n' to use regional endpoints
        parameter_domain_name (str): Domain name
    """
    
    lines = []

    ssm_client = boto3.client('ssm')
    primary_region = os.getenv('AWS_PRIMARY_REGION')

    ## Check if parameter_api is equal to 'n'
    if parameter_api == 'n':
        account_open_endpoint = ssm_client.get_parameter(
            Name=f"{AccountOpenParameterName.ACCOUNT_OPEN_REGIONAL_ENDPOINT.value}{primary_region}")[
            'Parameter']['Value']
        trade_order_endpoint = ssm_client.get_parameter(
            Name=TradeParameterName.TRADE_ORDER_API_ENDPOINT.value)['Parameter']['Value']
    else: 
        if parameter_domain_name == '':
            print("Error: Domain name is required when using parameter = 'y'")
            sys.exit(1)  
        account_open_endpoint = 'https://api-account.' + parameter_domain_name + '/prod/'
        trade_order_endpoint = 'https://api-trade.' + parameter_domain_name + '/resilient/'

    lines.append(f"{ViteConfigEnum.VITE_NEW_ACCOUNT_ENDPOINT.value}={account_open_endpoint}\n")
    lines.append(f"{ViteConfigEnum.VITE_TRADE_STOCK_ENDPOINT.value}={trade_order_endpoint}\n")

    cloudfront_client = boto3.client("cloudformation", config=Config(region_name=os.getenv(primary_region)))
    outputs = []
    try:
        stack = cloudfront_client.describe_stacks(StackName="FrontEnd-RumStack")
        outputs = stack["Stacks"][0]["Outputs"]
    except:
        print("warning: RUM stack not deployed")

    dev_lines = lines.copy()
    prod_lines = lines.copy()

    for output in outputs:
        if "LocalRumAppMonitorId" in output["OutputKey"]:
            endpoint = output["OutputValue"]
            dev_lines.append(f"{ViteConfigEnum.VITE_RUM_APPLICATION_ID.value}={endpoint}\n")

        if "DeployedRumAppMonitorId" in output["OutputKey"]:
            endpoint = output["OutputValue"]
            prod_lines.append(f"{ViteConfigEnum.VITE_RUM_APPLICATION_ID.value}={endpoint}\n")

    with open(".env.development", "w") as dev_config:
        dev_config.writelines(dev_lines)

    with open(".env.production", "w") as prod_config:
        prod_config.writelines(prod_lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:  # Check for at least one parameter
        print("Error: At least one parameter is required (y/n for local RUM ID commenting)")
        sys.exit(1)
    elif len(sys.argv) == 2:  # If only one parameter is given
        generate_config_files(sys.argv[1], None)  # Pass only custom endpoint creation flag
    else:
        generate_config_files(sys.argv[1], sys.argv[2])  # Pass both parameters