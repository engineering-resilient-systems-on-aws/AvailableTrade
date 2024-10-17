from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_secretsmanager as secretsmanager
)
from constructs import Construct
import aws_cdk as cdk
from cdk_ecs_service_extensions import Service

from trade_utils.trade_parameter_name import TradeParameterName


class TradeDatabaseSecondaryStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        readers = []
        index = 1
        for az in vpc.availability_zones:
            reader = rds.ClusterInstance.serverless_v2("readerV2-{}".format(index), scale_with_writer=index == 1,
                                                       enable_performance_insights=True)
            readers.append(reader)
            index += 1

        writer = rds.ClusterInstance.serverless_v2("writer", publicly_accessible=False,
                                                   enable_performance_insights=True)

        self.cluster = rds.DatabaseCluster(self, "TradeCluster",
                                           engine=rds.DatabaseClusterEngine.aurora_postgres(
                                               version=rds.AuroraPostgresEngineVersion.VER_16_2),
                                           writer=writer,
                                           readers=readers,
                                           serverless_v2_min_capacity=0.5, serverless_v2_max_capacity=2,
                                           storage_type=rds.DBClusterStorageType.AURORA_IOPT1,
                                           storage_encrypted=False,
                                           vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                                           vpc=vpc,
                                           cluster_identifier='stock',
                                           backup=rds.BackupProps(retention=cdk.Duration.days(15)),
                                           preferred_maintenance_window="Sun:23:45-Mon:00:15",
                                           cloudwatch_logs_exports=["postgresql"],
                                           cloudwatch_logs_retention=cdk.aws_logs.RetentionDays.TWO_WEEKS)

        cfn_cluster = self.cluster.node.default_child
        cfn_cluster.global_cluster_identifier = "global-trade-cluster"
        cfn_cluster.master_username = None
        cfn_cluster.master_user_password = None

        order_api_user_name = "order_api_user"

        # create a regional task role, give it access to the api user secret and the
        self.task_role = iam.Role(self, "TradingApiTaskRole",
                                  role_name=cdk.PhysicalName.GENERATE_IF_NEEDED,
                                  assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))
        self.task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["secretsmanager:ListSecrets"]))
        self.task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["ssm:GetParameter"]))
        self.task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["cloudwatch:PutMetricData"]))

        order_api_db_secret = secretsmanager.Secret.from_secret_name_v2(self, "order_api_db_secret",
                                                                        "order_api_db_secret")
        order_api_db_secret.grant_read(self.task_role)

        proxy = self.cluster.add_proxy("proxy", borrow_timeout=cdk.Duration.seconds(30), max_connections_percent=95,
                                       secrets=[order_api_db_secret], vpc=vpc, db_proxy_name="TradeProxy")

        proxy.grant_connect(self.task_role, order_api_user_name)
        self.cluster.connections.allow_from(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(5432))
        proxy.connections.allow_from(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(5432))

        reader_endpoint = rds.CfnDBProxyEndpoint(self, 'TradeProxyReadOnlyEndpoint', db_proxy_name=proxy.db_proxy_name,
                                                 target_role='READ_ONLY',
                                                 db_proxy_endpoint_name='TradeProxyReadOnlyEndpoint',
                                                 vpc_subnet_ids=vpc.select_subnets(
                                                     subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnet_ids
                                                 )
        reader_endpoint.node.add_dependency(proxy)

        ssm.StringParameter(self, "TradeOrderApiDbSecretId",
                            description="Order API Database Secret Id",
                            parameter_name=TradeParameterName.TRADE_ORDER_API_SECRET_ID.value,
                            string_value=order_api_db_secret.secret_name)

        ssm.StringParameter(self, "TradeRdsProxyEndpoint",
                            description="Trade Database Proxy Endpoint",
                            parameter_name=TradeParameterName.TRADE_RDS_PROXY_ENDPOINT.value,
                            string_value=proxy.endpoint)

        ssm.StringParameter(self, "TradeRdsProxyReadOnlyEndpoint",
                            description="Trade Database Proxy Read Only Endpoint",
                            parameter_name=TradeParameterName.TRADE_RDS_PROXY_READ_ONLY_ENDPOINT.value,
                            string_value=reader_endpoint.attr_endpoint)
        
        ssm.StringParameter(self, "TradeRdsSecondaryClusterArn",
                            description="Trade Database Secondary Cluster ARN",
                            parameter_name=TradeParameterName.TRADE_RDS_SECONDARY_CLUSTER_ARN.value,
                            string_value=self.cluster.cluster_arn)     
