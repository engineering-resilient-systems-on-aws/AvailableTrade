#!/usr/bin/env python3
"""
News Insights CDK Stack
Chapter 9 - News Feed Ingestion Architecture

CDK stack for news feed ingestion with article downloading, 
data replication, and search capabilities.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path
from typing import Tuple
import boto3
from botocore.exceptions import ClientError
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticache as elasticache,
    aws_opensearchservice as opensearch,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_logs as logs,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3 as s3,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct

# Environment variables for AWS account and region
if not (AWS_ACCOUNT_ID:= os.environ.get("AWS_DEFAULT_ACCOUNT", "593793064122")):
    raise ValueError("AWS_DEFAULT_ACCOUNT environment variable is not set.")
if not (AWS_DEFAULT_REGION:= os.environ.get("AWS_DEFAULT_REGION", "us-east-1")):
    raise ValueError("AWS_DEFAULT_REGION environment variable is not set.")

def build_lambda_layer():
    """
    Build Lambda layer with Redis and OpenSearch dependencies.
    Returns the path to the layer directory.
    """
    current_dir = Path(__file__).parent
    layers_dir = current_dir / "layers"
    python_dir = layers_dir / "python"
    layer_zip = layers_dir / "lambda-layer.zip"
    
    # Check if layer already exists and is recent
    if layer_zip.exists():
        print(f"Layer zip already exists at {layer_zip}")
        return str(layers_dir)
    
    print("Building Lambda layer for Redis and OpenSearch dependencies...")
    
    # Create the layers directory structure
    if python_dir.exists():
        shutil.rmtree(python_dir)
    
    python_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Install packages directly to the python directory
        print("Installing dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "redis>=5.0.0,<6.0.0",
            "opensearch-py>=2.4.0,<3.0.0",
            "-t", str(python_dir),
            "--upgrade",
            "--no-cache-dir"
        ], check=True, capture_output=True, text=True)
        
        # Clean up unnecessary files
        cleanup_patterns = [
            "*.dist-info",
            "__pycache__",
            "*.pyc",
        ]
        
        for pattern in cleanup_patterns:
            for item in python_dir.rglob(pattern):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    item.unlink(missing_ok=True)
        
        print("Layer built successfully!")
        return str(layers_dir)
        
    except subprocess.CalledProcessError as e:
        print(f"Error building layer: {e}")
        # Fall back to using existing structure if build fails
        if layers_dir.exists():
            return str(layers_dir)
        raise


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


class NewsInsightsStack(Stack):
    """
    CDK Stack for News Feed Ingestion Architecture
    
    Components:
    - Article Downloader: ECS-based orchestrated download system
    - Data Replicator: CDC process using Redis Streams
    - Search API: Decoupled search interface with OpenSearch
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get or create default VPC (cost-efficient approach for tutorials)
        vpc = get_or_create_default_vpc(self)

        # Create shared security group for all services
        shared_security_group = self._create_shared_security_group(vpc)

        # Create core infrastructure components
        articles_bucket = self._create_s3_bucket()
        redis_cluster = self._create_redis_cluster(vpc, shared_security_group)
        opensearch_domain = self._create_opensearch_cluster(vpc, shared_security_group)
        
        # Create ECS components for article downloading
        ecs_cluster, article_downloader_service = self._create_ecs_components(
            vpc, articles_bucket, redis_cluster, opensearch_domain, shared_security_group
        )
        
        # Create Lambda components for data processing
        lambda_layer = self._create_lambda_layer()
        data_replicator, search_api = self._create_lambda_functions(
            vpc, redis_cluster, opensearch_domain, lambda_layer, shared_security_group
        )
        
        # Create API Gateway
        search_api_gateway = self._create_api_gateway(search_api)
        
        # Create EventBridge rules for scheduling
        self._create_eventbridge_rules(data_replicator, ecs_cluster, article_downloader_service)
        
        # Create outputs
        self._create_outputs(search_api_gateway, opensearch_domain)

    def _create_shared_security_group(self, vpc: ec2.IVpc) -> ec2.SecurityGroup:
        """Create a single security group for all services in the tutorial"""
        sg = ec2.SecurityGroup(
            self, "NewsInsightsSecurityGroup",
            vpc=vpc,
            description="Security group for all News Insights services",
            allow_all_outbound=True
        )
        
        # Allow all traffic within the security group (services can talk to each other)
        sg.add_ingress_rule(
            peer=sg,
            connection=ec2.Port.all_traffic(),
            description="Allow all communication within News Insights services"
        )
        
        # Allow Redis access from VPC
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(6379),
            description="Redis access from VPC"
        )
        
        # Allow OpenSearch access from VPC
        sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="OpenSearch HTTPS access from VPC"
        )
        
        return sg

    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for storing downloaded articles"""
        return s3.Bucket(
            self, "ArticlesBucket",
            versioned=False,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

    def _create_redis_cluster(self, vpc: ec2.IVpc, security_group: ec2.SecurityGroup) -> elasticache.CfnReplicationGroup:
        """Create Redis cluster for MemoryDB and CDC"""
        # Redis subnet group
        redis_subnet_group = elasticache.CfnSubnetGroup(
            self, "RedisSubnetGroup",
            description="Subnet group for Redis cluster",
            subnet_ids=[subnet.subnet_id for subnet in vpc.public_subnets]
        )

        # Redis cluster
        redis_cluster = elasticache.CfnReplicationGroup(
            self, "RedisCluster",
            replication_group_description="Redis cluster for news insights",
            cache_node_type="cache.t3.micro",
            engine="redis",
            num_cache_clusters=1,
            cache_subnet_group_name=redis_subnet_group.ref,
            security_group_ids=[security_group.security_group_id],
            automatic_failover_enabled=False,
            multi_az_enabled=False
        )

        return redis_cluster

    def _create_opensearch_cluster(self, vpc: ec2.IVpc, security_group: ec2.SecurityGroup) -> opensearch.Domain:
        """Create OpenSearch cluster for search capabilities"""
        # OpenSearch domain - requires exactly one subnet for single node
        opensearch_domain = opensearch.Domain(
            self, "NewsSearchDomain",
            version=opensearch.EngineVersion.OPENSEARCH_2_11,
            capacity=opensearch.CapacityConfig(
                data_nodes=1,
                data_node_instance_type="t3.small.search"
            ),
            ebs=opensearch.EbsOptions(
                volume_size=10,
                volume_type=ec2.EbsDeviceVolumeType.GP3
            ),
            vpc=vpc,
            vpc_subnets=[ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC, 
                availability_zones=[vpc.availability_zones[0]]  # Use exactly one subnet
            )],
            security_groups=[security_group],
            removal_policy=RemovalPolicy.DESTROY,
        )

        return opensearch_domain

    def _create_ecs_components(
        self, 
        vpc: ec2.IVpc, 
        articles_bucket: s3.Bucket, 
        redis_cluster: elasticache.CfnReplicationGroup,
        opensearch_domain: opensearch.Domain,
        security_group: ec2.SecurityGroup
    ) -> Tuple[ecs.Cluster, ecs.FargateService]:
        """Create ECS cluster and service for article downloading"""
        # ECS cluster
        ecs_cluster = ecs.Cluster(
            self, "NewsDownloaderCluster",
            vpc=vpc,
        )

        # ECS task definition
        article_downloader_task = ecs.FargateTaskDefinition(
            self, "ArticleDownloaderTask",
            memory_limit_mib=512,
            cpu=256
        )

        article_downloader_task.add_container(
            "ArticleDownloader",
            image=ecs.ContainerImage.from_registry("public.ecr.aws/lambda/python:3.12"),
            command=[
                "sh", "-c",
                "pip install requests beautifulsoup4 boto3 && python -c \"import time; print('Article downloader running'); time.sleep(300)\""
            ],
            environment={
                "REDIS_ENDPOINT": redis_cluster.attr_primary_end_point_address,
                "ARTICLES_BUCKET": articles_bucket.bucket_name,
                "OPENSEARCH_ENDPOINT": opensearch_domain.domain_endpoint
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="article-downloader",
                log_retention=logs.RetentionDays.ONE_WEEK
            )
        )

        # Grant permissions to task
        articles_bucket.grant_read_write(article_downloader_task.task_role)
        opensearch_domain.grant_read_write(article_downloader_task.task_role)

        # ECS service (using the shared security group)
        article_downloader_service = ecs.FargateService(
            self, "ArticleDownloaderService",
            cluster=ecs_cluster,
            task_definition=article_downloader_task,
            desired_count=1,
            assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[security_group]
        )

        return ecs_cluster, article_downloader_service

    def _create_lambda_layer(self) -> lambda_.LayerVersion:
        """Create Lambda layer for dependencies"""
        # Build or check for Lambda layer
        layer_path = build_lambda_layer()
        
        return lambda_.LayerVersion(
            self, "NewsInsightsDependenciesLayer",
            code=lambda_.Code.from_asset(layer_path),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            layer_version_name="news-insights-deps",
            description="Redis and OpenSearch dependencies for news insights"
        )

    def _create_lambda_functions(
        self,
        vpc: ec2.IVpc,
        redis_cluster: elasticache.CfnReplicationGroup,
        opensearch_domain: opensearch.Domain,
        lambda_layer: lambda_.LayerVersion,
        security_group: ec2.SecurityGroup
    ) -> Tuple[lambda_.Function, lambda_.Function]:
        """Create Lambda functions for data processing and search API"""
        
        # Data replicator Lambda function
        data_replicator = lambda_.Function(
            self, "DataReplicator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handlers.DataReplicator_handler",
            code=lambda_.Code.from_asset("functions"),
            environment={
                'REDIS_ENDPOINT': redis_cluster.attr_primary_end_point_address,
                'OPENSEARCH_ENDPOINT': opensearch_domain.domain_endpoint
            },
            timeout=Duration.minutes(5),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            allow_public_subnet=True,
            security_groups=[security_group],
            layers=[lambda_layer]
        )

        # Grant permissions to data replicator
        opensearch_domain.grant_read_write(data_replicator)

        # Search API Lambda function
        search_api = lambda_.Function(
            self, "SearchAPI",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handlers.SearchAPI_handler",
            code=lambda_.Code.from_asset("functions"),
            environment={
                'OPENSEARCH_ENDPOINT': opensearch_domain.domain_endpoint
            },
            timeout=Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            allow_public_subnet=True,
            security_groups=[security_group],
            layers=[lambda_layer]
        )

        # Grant permissions to search API
        opensearch_domain.grant_read(search_api)

        return data_replicator, search_api

    def _create_api_gateway(self, search_api: lambda_.Function) -> apigateway.RestApi:
        """Create API Gateway for search API"""
        # API Gateway
        search_api_gateway = apigateway.RestApi(
            self, "NewsSearchAPI",
            rest_api_name="news-search-api",
            description="API for searching news articles",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )

        # API Gateway resources
        search_resource = search_api_gateway.root.add_resource("search")
        
        search_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(search_api),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_models={
                        "application/json": apigateway.Model.EMPTY_MODEL
                    }
                )
            ]
        )

        return search_api_gateway

    def _create_eventbridge_rules(
        self,
        data_replicator: lambda_.Function,
        ecs_cluster: ecs.Cluster,
        article_downloader_service: ecs.FargateService
    ) -> None:
        """Create EventBridge rules for scheduling"""
        # EventBridge rule to trigger data replication
        replication_rule = events.Rule(
            self, "DataReplicationRule",
            description="Trigger data replication every 5 minutes",
            schedule=events.Schedule.rate(Duration.minutes(5))
        )

        replication_rule.add_target(targets.LambdaFunction(data_replicator))

        # EventBridge rule for scheduled article downloading
        download_rule = events.Rule(
            self, "ArticleDownloadRule",
            description="Trigger article download every hour",
            schedule=events.Schedule.rate(Duration.hours(1))
        )

        # Get the task definition from the service
        task_definition = article_downloader_service.task_definition

        download_rule.add_target(targets.EcsTask(
            cluster=ecs_cluster,
            task_definition=task_definition,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=article_downloader_service.connections.security_groups
        ))

    def _create_outputs(
        self,
        search_api_gateway: apigateway.RestApi,
        opensearch_domain: opensearch.Domain
    ) -> None:
        """Create CloudFormation outputs"""
        CfnOutput(
            self, "SearchAPIURL",
            value=search_api_gateway.url,
            description="Search API URL"
        )

        CfnOutput(
            self, "OpenSearchDomainEndpoint",
            value=opensearch_domain.domain_endpoint,
            description="OpenSearch domain endpoint"
        )

# CDK App
app = cdk.App()
NewsInsightsStack(app, "NewsInsightsStack",
                  env=cdk.Environment(
                    account=AWS_ACCOUNT_ID,
                    region=AWS_DEFAULT_REGION
                ))
app.synth()