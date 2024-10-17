from aws_cdk import (
    Stack, 
    aws_certificatemanager as acm,
    aws_ssm as ssm,
    aws_apigateway as apigateway,
)
from constructs import Construct

class OrchestrationPrimaryStack(Stack):
    def __init__(self, scope: Construct, id: str, domain_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)     

        ## Retrieve ACM Certificate for custom domain
        certificate = acm.Certificate.from_certificate_arn(
            self, "Certificate",
            certificate_arn=ssm.StringParameter.value_for_string_parameter(
                self, "CertificateARN"
            ),
        )
        
        ## Retrieve ssm parameter names NewAccountAPIID
        account_api_id = ssm.StringParameter.value_for_string_parameter(
            self, "NewAccountAPIID"
        )

        ## Get a reference to the APIG
        account_api = apigateway.RestApi.from_rest_api_id(
            self, "NewAccountApi-Primary",
            rest_api_id=account_api_id,
        )

        ## Create the custom domain name
        account_api.add_domain_name("NewAccountCustomDomain-Primary",
            domain_name=f"api-account.{domain_name}",
            certificate=certificate,        
        )

        ## Retrieve ssm parameter names NewAccountAPIID
        trade_api_id = ssm.StringParameter.value_for_string_parameter(
            self, "TradeStockAPIID"
        )

        ## Get a reference to the APIG
        trade_api = apigateway.RestApi.from_rest_api_id(
            self, "TradeStockAPI-Primary",
            rest_api_id=trade_api_id,
        )

        ## Create the custom domain name
        trade_api.add_domain_name("TradeStockCustomDomain-Primary",
            domain_name=f"api-trade.{domain_name}",
            certificate=certificate,        
        )       

       

