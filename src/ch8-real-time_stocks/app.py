#!/usr/bin/env python3
"""
Real-Time Stock Market Data Analytics CDK Stack
Chapter 8 - Streaming Architecture for Market Data

Clean, focused CDK stack for learning streaming architectures.
"""

import os
import boto3
from botocore.exceptions import ClientError
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_msk as msk,
    aws_ec2 as ec2,
    aws_apigateway as apigateway,
    aws_kinesisfirehose as firehose,
    aws_s3 as s3,
    aws_athena as athena,
    aws_glue as glue,
    aws_iam as iam,
    aws_lambda as lambda_,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from aws_cdk.aws_lambda_event_sources import ManagedKafkaEventSource
from constructs import Construct

# Environment variables for AWS account and region
if not (AWS_ACCOUNT_ID:= os.environ.get("AWS_DEFAULT_ACCOUNT", "593793064122")):
    raise ValueError("AWS_DEFAULT_ACCOUNT environment variable is not set.")
if not (AWS_DEFAULT_REGION:= os.environ.get("AWS_DEFAULT_REGION", "us-east-1")):
    raise ValueError("AWS_DEFAULT_REGION environment variable is not set.")


def get_or_create_default_vpc(scope: Construct) -> ec2.IVpc:
    """
    Get the default VPC or create one if it doesn't exist.
    Uses boto3 to create a default VPC for cost efficiency.
    Returns the VPC to use for the stack.
    """
    try:
        # Try to lookup the default VPC first
        vpc = ec2.Vpc.from_lookup(scope, "DefaultVPC", is_default=True)
        print("Found existing default VPC")
        return vpc
    except Exception as e:
        print(f"Default VPC not found: {e}")
        print("Creating default VPC using AWS API for cost-efficient tutorial setup...")
        
        # Use boto3 to create a default VPC
        try:
            ec2_client = boto3.client('ec2')
            
            # Create default VPC - this is free and creates minimal infrastructure
            response = ec2_client.create_default_vpc()
            vpc_id = response['Vpc']['VpcId']
            print(f"Created default VPC: {vpc_id}")
            
            # Wait a moment for the VPC to be fully available
            import time
            time.sleep(15)  # Increased wait time for stability
            
            # Now lookup the newly created default VPC
            vpc = ec2.Vpc.from_lookup(scope, "DefaultVPC", is_default=True)
            print("Successfully retrieved newly created default VPC")
            return vpc
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'DefaultVpcAlreadyExists':
                print("Default VPC already exists, looking up again...")
                # Try lookup again
                vpc = ec2.Vpc.from_lookup(scope, "DefaultVPC", is_default=True)
                return vpc
            elif error_code == 'UnauthorizedOperation':
                print("Error: Insufficient permissions to create default VPC")
                print("Please ensure your AWS credentials have ec2:CreateDefaultVpc permission")
                raise
            else:
                print(f"Error creating default VPC: {e}")
                raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

class RealtimeStocksStack(Stack):
    """
    CDK Stack for Real-Time Stock Market Data Analytics
    
    Components:
    - Amazon MSK for data ingestion
    - API Gateway for data enrichment
    - Kinesis Data Firehose for data delivery
    - Amazon Athena for data analytics
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get or create default VPC (cost-efficient approach for tutorials)
        vpc = get_or_create_default_vpc(self)

        # Create MSK security group ONCE
        msk_sg = self._create_msk_security_group(vpc)

        # S3 bucket for data storage
        data_bucket = s3.Bucket(
            self, "StockDataBucket",
            versioned=False,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # MSK cluster configuration
        msk_config = msk.CfnConfiguration(
            self, "MSKConfig",
            name="realtime-stocks-config",
            description="Configuration for real-time stocks MSK cluster",
            server_properties="""
auto.create.topics.enable=true
default.replication.factor=2
min.insync.replicas=2
num.partitions=3
log.retention.hours=24
log.retention.bytes=1073741824
""".strip()
        )

        # Get subnets sorted by preference: private subnets first, then public subnets
        all_subnets = list(vpc.private_subnets) + list(vpc.public_subnets)
        selected_subnets = all_subnets[:2]  # Take first 2 subnets
        
        if len(selected_subnets) < 2:
            raise ValueError(f"VPC must have at least 2 subnets for MSK cluster. Found {len(all_subnets)} subnets.")

        # MSK cluster
        msk_cluster = msk.CfnCluster(
            self, "StockDataCluster",
            cluster_name="realtime-stocks-cluster",
            kafka_version="3.8.x",
            number_of_broker_nodes=2,
            broker_node_group_info=msk.CfnCluster.BrokerNodeGroupInfoProperty(
                instance_type="kafka.t3.small",
                client_subnets=[
                    subnet.subnet_id for subnet in selected_subnets
                ],
                storage_info=msk.CfnCluster.StorageInfoProperty(
                    ebs_storage_info=msk.CfnCluster.EBSStorageInfoProperty(
                        volume_size=10
                    )
                ),
                security_groups=[msk_sg.security_group_id]
            ),
            configuration_info=msk.CfnCluster.ConfigurationInfoProperty(
                arn=msk_config.attr_arn,
                revision=1
            ),
            encryption_info=msk.CfnCluster.EncryptionInfoProperty(
                encryption_in_transit=msk.CfnCluster.EncryptionInTransitProperty(
                    client_broker="TLS",
                    in_cluster=True
                )
            )
        )

        # IAM role for Firehose
        firehose_role = iam.Role(
            self, "FirehoseDeliveryRole",
            assumed_by=iam.ServicePrincipal("firehose.amazonaws.com"),
            inline_policies={
                "S3DeliveryPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:AbortMultipartUpload",
                                "s3:GetBucketLocation",
                                "s3:GetObject",
                                "s3:ListBucket",
                                "s3:ListBucketMultipartUploads",
                                "s3:PutObject"
                            ],
                            resources=[
                                data_bucket.bucket_arn,
                                f"{data_bucket.bucket_arn}/*"
                            ]
                        )
                    ]
                )
            }
        )

        # Kinesis Data Firehose delivery stream
        firehose_stream = firehose.CfnDeliveryStream(
            self, "StockDataFirehose",
            delivery_stream_name="realtime-stocks-firehose",
            delivery_stream_type="DirectPut",
            s3_destination_configuration=firehose.CfnDeliveryStream.S3DestinationConfigurationProperty(
                bucket_arn=data_bucket.bucket_arn,
                prefix="year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/",
                error_output_prefix="errors/",
                buffering_hints=firehose.CfnDeliveryStream.BufferingHintsProperty(
                    interval_in_seconds=60,
                    size_in_m_bs=1
                ),
                compression_format="GZIP",
                role_arn=firehose_role.role_arn
            )
        )

        # Lambda function for data processing
        stock_processor = lambda_.Function(
            self, "StockDataProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handlers.StockDataProcessor_handler",
            code=lambda_.Code.from_asset("functions"),
            timeout=Duration.minutes(5),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            allow_public_subnet=True,  # <-- added to allow Lambda in public subnet
            security_groups=[self._create_lambda_security_group(vpc, msk_sg)]
        )

        # MSK event source mapping (use ManagedKafkaEventSource instead of EventSourceMapping)
        stock_processor.add_event_source(
            ManagedKafkaEventSource(
                cluster_arn=msk_cluster.attr_arn,
                topic="stock-prices",
                starting_position=lambda_.StartingPosition.LATEST,
                batch_size=10,
                max_batching_window=Duration.seconds(5)
            )
        )

        # Grant permissions to Lambda
        stock_processor.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kafka:DescribeCluster",
                    "kafka:DescribeClusterV2",
                    "kafka:GetBootstrapBrokers"
                ],
                resources=[msk_cluster.attr_arn]
            )
        )
        
        stock_processor.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "firehose:PutRecord",
                    "firehose:PutRecordBatch"
                ],
                resources=[f"arn:aws:firehose:{self.region}:{self.account}:deliverystream/{firehose_stream.ref}"]
            )
        )

        # API Gateway for data enrichment
        api = apigateway.RestApi(
            self, "StockDataAPI",
            rest_api_name="realtime-stocks-api",
            description="API for real-time stock data enrichment",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )

        # API Lambda function
        api_lambda = lambda_.Function(
            self, "StockAPIHandler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handlers.StockAPIHandler_handler",
            code=lambda_.Code.from_asset("functions"),
            timeout=Duration.seconds(30)
        )

        # API Gateway resources
        stocks_resource = api.root.add_resource("stocks")
        symbol_resource = stocks_resource.add_resource("{symbol}")
        
        symbol_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(api_lambda),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL
                    }
                )
            ]
        )

        # Glue database for Athena
        glue_database = glue.CfnDatabase(
            self, "StockDataDatabase",
            catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name="realtime_stocks_db",
                description="Database for real-time stock market data analytics"
            )
        )

        # Glue table for Athena queries
        glue_table = glue.CfnTable(
            self, "StockDataTable",
            catalog_id=self.account,
            database_name=glue_database.ref,
            table_input=glue.CfnTable.TableInputProperty(
                name="stock_data",
                description="Table for stock market data",
                storage_descriptor=glue.CfnTable.StorageDescriptorProperty(
                    columns=[
                        glue.CfnTable.ColumnProperty(name="symbol", type="string"),
                        glue.CfnTable.ColumnProperty(name="price", type="double"),
                        glue.CfnTable.ColumnProperty(name="volume", type="bigint"),
                        glue.CfnTable.ColumnProperty(name="timestamp", type="string"),
                        glue.CfnTable.ColumnProperty(name="processed_timestamp", type="string"),
                        glue.CfnTable.ColumnProperty(name="partition_key", type="string")
                    ],
                    location=f"s3://{data_bucket.bucket_name}/",
                    input_format="org.apache.hadoop.mapred.TextInputFormat",
                    output_format="org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                    serde_info=glue.CfnTable.SerdeInfoProperty(
                        serialization_library="org.openx.data.jsonserde.JsonSerDe"
                    )
                ),
                partition_keys=[
                    glue.CfnTable.ColumnProperty(name="year", type="string"),
                    glue.CfnTable.ColumnProperty(name="month", type="string"),
                    glue.CfnTable.ColumnProperty(name="day", type="string"),
                    glue.CfnTable.ColumnProperty(name="hour", type="string")
                ]
            )
        )

        # S3 bucket for Athena query results
        athena_results_bucket = s3.Bucket(
            self, "AthenaResultsBucket",
            versioned=False,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Athena workgroup
        athena_workgroup = athena.CfnWorkGroup(
            self, "StockDataWorkgroup",
            name="realtime-stocks-workgroup",
            description="Workgroup for real-time stock data analytics",
            work_group_configuration=athena.CfnWorkGroup.WorkGroupConfigurationProperty(
                result_configuration=athena.CfnWorkGroup.ResultConfigurationProperty(
                    output_location=f"s3://{athena_results_bucket.bucket_name}/query-results/"
                ),
                enforce_work_group_configuration=True,
                publish_cloud_watch_metrics_enabled=False
            )
        )

        # Essential outputs only
        CfnOutput(
            self, "APIGatewayURL", 
            value=api.url,
            description="API Gateway URL for stock data enrichment"
        )
        
        # CfnOutput(
        #     self, "MSKBootstrapServers", 
        #     value=msk_cluster.broker_node_group_info.connectivity_info.to_string(),
        #     description="MSK Bootstrap Servers"
        # )

    def _create_msk_security_group(self, vpc: ec2.IVpc) -> ec2.SecurityGroup:
        """Create security group for MSK cluster"""
        sg = ec2.SecurityGroup(
            self, "MSKSecurityGroup",
            vpc=vpc,
            description="Security group for MSK cluster",
            allow_all_outbound=True
        )
        
        sg.add_ingress_rule(
            peer=sg,
            connection=ec2.Port.tcp(9092),
            description="Kafka broker communication"
        )
        
        sg.add_ingress_rule(
            peer=sg,
            connection=ec2.Port.tcp(2181),
            description="Zookeeper communication"
        )
        
        return sg

    def _create_lambda_security_group(self, vpc: ec2.IVpc, msk_sg: ec2.SecurityGroup) -> ec2.SecurityGroup:
        """Create security group for Lambda function and allow access to MSK SG"""
        lambda_sg = ec2.SecurityGroup(
            self, "LambdaSecurityGroup",
            vpc=vpc,
            description="Security group for Lambda functions",
            allow_all_outbound=True
        )
        # Allow Lambda to communicate with MSK
        msk_sg.add_ingress_rule(
            peer=lambda_sg,
            connection=ec2.Port.tcp(9092),
            description="Allow Lambda to access MSK"
        )
        return lambda_sg

# CDK App
app = cdk.App()
RealtimeStocksStack(app, "RealtimeStocksStack",
                    env=cdk.Environment(
                        account=AWS_ACCOUNT_ID,
                        region=AWS_DEFAULT_REGION
                    ))
app.synth()