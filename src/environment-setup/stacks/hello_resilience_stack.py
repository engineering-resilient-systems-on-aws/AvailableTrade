from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway
)
import aws_cdk as cdk
from constructs import Construct


class HelloResilienceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        hello_resilience = _lambda.Function(
            self, "HelloResilience",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda"),
            handler='hello_resilience.handler'
        )

        hello_resilience_api = apigateway.RestApi(
            self, "HelloResilienceApi",
            deploy_options=apigateway.StageOptions(
                data_trace_enabled=True,
                tracing_enabled=True
            ))

        hello_resilience_endpoint = hello_resilience_api.root.add_resource(
                                                                "getHello")
        hello_resilience_endpoint.add_method(
            "GET",
            apigateway.LambdaIntegration(hello_resilience))

        cdk.CfnOutput(self, "HelloResilienceEndpoint",
                      value=hello_resilience_api.url_for_path("/getHello/"))
