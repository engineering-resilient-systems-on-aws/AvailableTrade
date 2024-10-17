import os
from aws_cdk import (
    Stack,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_lambda_event_sources as eventsources,
    aws_iam as iam,
    aws_apigateway as apigateway,
    aws_logs as logs,
    aws_ssm as ssm,
)
import aws_cdk as cdk
from constructs import Construct


class ProcessStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, recovery_region: bool,
                 idempotency_table: str, accounts_table: str, failover_bucket: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.topic = sns.Topic(self, "NewAccountTopic", display_name="New Account Opening",
                               topic_name=cdk.PhysicalName.GENERATE_IF_NEEDED)

        function_timeout_seconds = 5

        dlq = sqs.Queue(self, "DLQ_NewAccountQueue", encryption=sqs.QueueEncryption.UNENCRYPTED,
                        visibility_timeout=cdk.Duration.seconds(5))
        dead_letter_queue = sqs.DeadLetterQueue(max_receive_count=3, queue=dlq)
        self.queue = sqs.Queue(self, "NewAccountQueue", dead_letter_queue=dead_letter_queue,
                               encryption=sqs.QueueEncryption.UNENCRYPTED,
                               visibility_timeout=cdk.Duration.seconds(
                                   6 * function_timeout_seconds))

        self.new_account_function = lambda_.Function(
            self, "New Account", runtime=lambda_.Runtime.PYTHON_3_9, handler="new_account.handler",
            code=lambda_.Code.from_asset(os.path.join(os.path.dirname("./functions/new_account.py"))),
            environment={"RECOVERY_REGION": str(recovery_region), 'POWERTOOLS_SERVICE_NAME': "AccountOpen",
                         'POWERTOOLS_METRICS_NAMESPACE': 'ResilientBrokerage',
                         'IDEMPOTENCY_TABLE': idempotency_table, 'ACCOUNTS_TABLE': accounts_table,
                         'FAILOVER_BUCKET': failover_bucket, 'LOG_LEVEL': 'DEBUG'},
            tracing=lambda_.Tracing.ACTIVE, timeout=cdk.Duration.seconds(function_timeout_seconds),
            log_retention=cdk.aws_logs.RetentionDays.FIVE_DAYS
        )
        self.new_account_function.add_event_source(
            eventsources.SqsEventSource(self.queue, batch_size=10, max_concurrency=15,
                                        report_batch_item_failures=True,
                                        max_batching_window=cdk.Duration.seconds(1)))
        self.new_account_function.add_layers(
            lambda_.LayerVersion.from_layer_version_arn(
                self, id='lambdapowertools',
                layer_version_arn=
                f"arn:aws:lambda:{cdk.Stack.of(self).region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:45"))

        gateway_execution_role = iam.Role(self, "GatewayExecutionRole",
                                          assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"))
        self.topic.grant_publish(gateway_execution_role)

        api_log_group = logs.LogGroup(self, "NewAccountApiLogs")

        api = apigateway.RestApi(self, "NewAccountApi", endpoint_types=[apigateway.EndpointType.REGIONAL],
                                 default_cors_preflight_options=apigateway.CorsOptions(
                                     allow_methods=['PUT', 'OPTIONS'],
                                     allow_headers=['Content-Type',
                                                    'Cache-Control',
                                                    'Authorization'],
                                     allow_origins=apigateway.Cors.ALL_ORIGINS
                                 ),
                                 deploy_options=apigateway.StageOptions(
                                     stage_name="prod",
                                     access_log_destination=apigateway.LogGroupLogDestination(api_log_group),
                                     logging_level=apigateway.MethodLoggingLevel.INFO,
                                     data_trace_enabled=True,
                                     metrics_enabled=True,
                                     tracing_enabled=True,
                                     access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(caller=True, http_method=True, ip=True,protocol=True,request_time=True, resource_path=True, response_length=True, status=True, user=True),
                                     throttling_rate_limit=100,
                                     throttling_burst_limit=25,
                                 ), cloud_watch_role=True)
        sns_integration = apigateway.AwsIntegration(
            service="sns",
            # path=f"{self.account}/{self.topic.topic_name}"
            path=f"{self.account}/{self.topic.topic_name}",
            integration_http_method="POST",
            options=apigateway.IntegrationOptions(
                credentials_role=gateway_execution_role,
                timeout=cdk.Duration.seconds(2),
                passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
                request_parameters={'integration.request.header.Content-Type': "'application/x-www-form-urlencoded'"},
                request_templates={
                    "application/json":
                        f"Action=Publish&TopicArn=$util.urlEncode('{self.topic.topic_arn}')&Message"
                        f"=$util.urlEncode($input.body)"
                },
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={"application/json": '{"status": "message added to topic"}'},
                        response_parameters={
                            'method.response.header.Access-Control-Allow-Headers': "'Access-Control-Allow-Origin,Content-Length,Content-Type,Date,X-Amz-Apigw-Id,X-Amzn-Requestid,X-Amzn-Trace-Id'",
                            'method.response.header.Access-Control-Allow-Methods': "'OPTIONS,PUT'",
                            'method.response.header.Access-Control-Allow-Origin': "'*'"}  # * for local dev only,
                        # deploy with proper domain for production
                    ),
                    apigateway.IntegrationResponse(
                        status_code="400",
                        selection_pattern="^\[Error\].*",
                        response_templates={
                            "application/json": "{\"state\":\"error\",\"message\":\"$util.escapeJavaScript($input.path('$.errorMessage'))\"}",
                        }
                    )
                ]
            )
        )

        account_model = apigateway.Model(
            self, "account-schema",
            rest_api=api,
            content_type="application/json",
            description="validate account open json",
            model_name="Account",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="AccountRequest",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "request_token": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "customer_first_name": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "customer_last_name": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "account_type": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "comment": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "beneficiaries": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.ARRAY,
                        properties={"name": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                                    "percentage": apigateway.JsonSchema(type=apigateway.JsonSchemaType.INTEGER)}),
                    "suitability": {
                        "liquidity": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                        "time_horizon": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                        "risk_tolerance": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    },
                    "instructions": {
                        "dividends": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                    }
                },
                required=["request_token", "user_id", "account_type"]
            )
        )

        api.root.add_method("PUT", sns_integration, method_responses=[
            apigateway.MethodResponse(status_code="200",
                                      response_parameters={"method.response.header.Access-Control-Allow-Headers": True,
                                                           "method.response.header.Access-Control-Allow-Methods": True,
                                                           "method.response.header.Access-Control-Allow-Origin": True}),
            apigateway.MethodResponse(status_code="400")],
                            api_key_required=False,
                            request_validator=apigateway.RequestValidator(
                                self,
                                "AccountValidator",
                                rest_api=api,
                                validate_request_body=True,
                                validate_request_parameters=False,
                                request_validator_name="AccountValidation"),
                            request_models={"application/json": account_model})

        # ToDo create the custom metric for account failures (api count - account create) > 0
        # ToDo put the custom metric on a dashboard
        # replication latency, funtion latency, messages visible, few other things you'd want to monitor
        # api.metric_count

        cdk.CfnOutput(self, "SNS topic", value=self.topic.topic_arn)

        ssm.StringParameter(self, "AccountOpenRegionalEndpoint",
                            description="Account Open Regional Endpoint",
                            parameter_name=f"AccountOpenRegionalEndpoint_{self.region}",
                            string_value=api.url)
        
        # Write the APIID arn to a ssm parameter named NewAccountAPIID
        ssm.StringParameter(self, "NewAccountAPIID",
                                                   parameter_name="NewAccountAPIID",
                                                   string_value=api.rest_api_id,
                                                   )        
