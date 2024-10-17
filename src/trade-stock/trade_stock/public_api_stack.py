from aws_cdk import (
    aws_apigateway as apigateway,
    aws_logs as cw_logs,
    aws_ssm as ssm,
)
from constructs import Construct
import aws_cdk as cdk
from trade_utils.trade_parameter_name import TradeParameterName


class PublicApiStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, private_lb, resource_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api_logs = cw_logs.LogGroup(self, "TradeStockApiLogs")
        restful_trades = apigateway.RestApi(
            self,
            "TradeStockApi", endpoint_types=[apigateway.EndpointType.REGIONAL],
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_methods=['PUT', 'GET', 'OPTIONS'],
                allow_headers=['Content-Type',
                               'Cache-Control',
                               'Authorization'],
                allow_origins=apigateway.Cors.ALL_ORIGINS
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="resilient",
                access_log_destination=apigateway.LogGroupLogDestination(api_logs),
                logging_level=apigateway.MethodLoggingLevel.INFO,
                access_log_format=apigateway.AccessLogFormat.clf(),
                data_trace_enabled=True,
                metrics_enabled=True,
                tracing_enabled=True,
                throttling_rate_limit=10000,
                throttling_burst_limit=500,
            ), cloud_watch_role=True,
        )

        trade_response_model = restful_trades.add_model(
            "TradeResponseModel",
            content_type="application/json",
            model_name="TradeResponseModel",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="trade",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "id": apigateway.JsonSchema(type=apigateway.JsonSchemaType.INTEGER),
                    "type": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "price": apigateway.JsonSchema(type=apigateway.JsonSchemaType.INTEGER),
                },
            ),
        )

        api_vpc_link = apigateway.VpcLink(self, "ApiVpcLink", targets=[private_lb.nlb])

        api_integration = apigateway.Integration(
            type=apigateway.IntegrationType.HTTP,
            options=apigateway.IntegrationOptions(
                connection_type=apigateway.ConnectionType.VPC_LINK,
                vpc_link=api_vpc_link,
                integration_responses=[apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Headers': "'Access-Control-Allow-Origin,Content-Length,Content-Type,Date,X-Amz-Apigw-Id,X-Amzn-Requestid,X-Amzn-Trace-Id'",
                        'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,PUT'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'"}
                )],
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
                timeout=cdk.Duration.seconds(2),
                request_parameters={'integration.request.header.Content-Type': "'application/json'"}
            ),
            integration_http_method="POST",
            uri="http://{}/{}/".format(
                private_lb.nlb.load_balancer_dns_name, resource_name
            ),
        )

        api_resource = restful_trades.root.add_resource(resource_name)
        api_resource.add_method(
            "PUT",
            api_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Content-Type": True,
                        "method.response.header.Content-Length": True,
                        "method.response.header.Connection": True,
                        "method.response.header.Server": True,
                        'method.response.header.Access-Control-Allow-Headers': True,
                        'method.response.header.Access-Control-Allow-Methods': True,
                        'method.response.header.Access-Control-Allow-Origin': True,
                    },
                    # Validate the schema on the response
                    response_models={"application/json": trade_response_model},
                )
            ],
        )

        health_resource = restful_trades.root.add_resource("region-az")
        health_integration = apigateway.Integration(
            type=apigateway.IntegrationType.HTTP,
            options=apigateway.IntegrationOptions(
                connection_type=apigateway.ConnectionType.VPC_LINK,
                vpc_link=api_vpc_link,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            'method.response.header.Access-Control-Allow-Headers': "'Access-Control-Allow-Origin,Content-Length,Content-Type,Date,X-Amz-Apigw-Id,X-Amzn-Requestid,X-Amzn-Trace-Id'",
                            'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,GET'",
                            'method.response.header.Access-Control-Allow-Origin': "'*'"}
                    ),
                    apigateway.IntegrationResponse(
                        status_code="400",
                        selection_pattern="^\[Error\].*",
                        response_templates={
                            "application/json": "{\"state\":\"error\",\"message\":\"$util.escapeJavaScript($input.path('$.errorMessage'))\"}",
                        }
                    ),
                    apigateway.IntegrationResponse(
                        status_code="500",
                        selection_pattern="^\[Error\].*",
                        response_templates={
                            "application/json": "{\"state\":\"error\",\"message\":\"$util.escapeJavaScript($input.path('$.errorMessage'))\"}",
                        }
                    )
                ],
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
            ),
            integration_http_method="GET",
            uri="http://{}/region-az/".format(private_lb.nlb.load_balancer_dns_name),
        )
        health_resource.add_method(
            "GET",
            health_integration,
            method_responses=[
                apigateway.MethodResponse(status_code="200",
                                          response_parameters={
                                              "method.response.header.Content-Type": True,
                                              "method.response.header.Content-Length": True,
                                              "method.response.header.Connection": True,
                                              "method.response.header.Server": True,
                                              'method.response.header.Access-Control-Allow-Headers': True,
                                              'method.response.header.Access-Control-Allow-Methods': True,
                                              'method.response.header.Access-Control-Allow-Origin': True,
                                          }),
                apigateway.MethodResponse(status_code="400"),
                apigateway.MethodResponse(status_code="500"),
            ],
        )

        stress_resource = restful_trades.root.add_resource("db-stress")
        stress_integration = apigateway.Integration(
            type=apigateway.IntegrationType.HTTP,
            options=apigateway.IntegrationOptions(
                connection_type=apigateway.ConnectionType.VPC_LINK,
                vpc_link=api_vpc_link,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                    ),
                    apigateway.IntegrationResponse(
                        status_code="400",
                        selection_pattern="^\[Error\].*",
                        response_templates={
                            "application/json": "{\"state\":\"error\",\"message\":\"$util.escapeJavaScript($input.path('$.errorMessage'))\"}",
                        }
                    ),
                    apigateway.IntegrationResponse(
                        status_code="500",
                        selection_pattern="^\[Error\].*",
                        response_templates={
                            "application/json": "{\"state\":\"error\",\"message\":\"$util.escapeJavaScript($input.path('$.errorMessage'))\"}",
                        }
                    )
                ],
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_TEMPLATES,
            ),
            integration_http_method="GET",
            uri="http://{}/db-health/".format(private_lb.nlb.load_balancer_dns_name),
        )

        stress_resource.add_method(
            "GET",
            stress_integration,
            method_responses=[
                apigateway.MethodResponse(status_code="200",
                                          response_parameters={
                                              "method.response.header.Content-Type": True,
                                              "method.response.header.Content-Length": True,
                                              "method.response.header.Connection": True,
                                              "method.response.header.Server": True
                                          }),
                apigateway.MethodResponse(status_code="400"),
                apigateway.MethodResponse(status_code="500"),
            ],
        )

        ssm.StringParameter(self, "OrderApiDNSEndpoint",
                            description="Order API DNS endpoint",
                            parameter_name=TradeParameterName.TRADE_ORDER_API_ENDPOINT.value,
                            string_value=restful_trades.url)

        ssm.StringParameter(self, "TradeStockAPIID",
                            parameter_name="TradeStockAPIID",
                            string_value=restful_trades.rest_api_id,
                            )
