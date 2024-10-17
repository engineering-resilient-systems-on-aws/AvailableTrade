from aws_cdk import (
    Stack,
    aws_route53 as route53,
)
from constructs import Construct

import boto3

class OrchestrationRoute53Stack(Stack):
    def __init__(self, scope: Construct, id: str, domain_name: str, is_primary: bool, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)                 

        try:
            # Function to fetch API Gateway info
            def get_api_gateway_info(custom_domain_name):
                api_gw_client = boto3.client('apigateway', region_name=self.region)  # Create client with correct region
                domain_name_info = api_gw_client.get_domain_name(domainName=custom_domain_name)
                return (
                    domain_name_info.get('regionalDomainName'),
                    domain_name_info.get('regionalHostedZoneId')
                )

            account_regional_domain_name, account_regional_hosted_zone = get_api_gateway_info(f"api-account.{domain_name}")
            trade_regional_domain_name, trade_regional_hosted_zone = get_api_gateway_info(f"api-trade.{domain_name}")            
            hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=domain_name)        
            if is_primary:                  
                ## This deploys but fails for Resource handler returned message: "Invalid request provided: AWS::Route53::HealthCheck" (RequestToken: 7876d7e6-097c-8f18-a982-ecc66dc635e8, HandlerErrorCode: InvalidRequest)
                health_check = route53.CfnHealthCheck(
                    self,
                    "AvailableTradeCloudWatchHealthCheck",
                    health_check_config=route53.CfnHealthCheck.HealthCheckConfigProperty(
                        type="CLOUDWATCH_METRIC",
                        alarm_identifier=route53.CfnHealthCheck.AlarmIdentifierProperty(
                            name="AvailableTradeFailoverAlarm",
                            region="us-west-2"
                        ),                        
                        insufficient_data_health_status="LastKnownStatus", # Or choose 'HEALTHY' or 'UNHEALTHY'
                    ),
                )     
            # Create record sets (loop for DRYness)
            for subdomain, regional_domain_name, regional_hosted_zone_id in [
                ("api-account", account_regional_domain_name, account_regional_hosted_zone),
                ("api-trade", trade_regional_domain_name, trade_regional_hosted_zone),
            ]:
                # Use ApiGateway helper for automatic alias target creation
                target = route53.CfnRecordSet.AliasTargetProperty(
                        dns_name=regional_domain_name,
                        hosted_zone_id=regional_hosted_zone_id,
                        evaluate_target_health=True if is_primary else False
                )           

                ## Create the primary record set for both api-account and api-trade
                route53.CfnRecordSet(
                    self, f"{subdomain.replace('-', '')}Record",
                    hosted_zone_id=hosted_zone.hosted_zone_id,
                    name=f"{subdomain}.{domain_name}",
                    type="A",
                    failover="PRIMARY" if is_primary else "SECONDARY",
                    health_check_id=health_check.ref if is_primary else None, 
                    set_identifier=f"{subdomain.replace('-', '')}Record-" + self.region,     
                    alias_target=target
                )               
        except Exception as e:
            print(f"An unexpected error occurred: {e}")       
