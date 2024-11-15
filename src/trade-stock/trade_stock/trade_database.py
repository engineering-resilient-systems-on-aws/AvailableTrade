from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_ssm as ssm
)
from constructs import Construct
import aws_cdk as cdk
from cdk_ecs_service_extensions import Service

from trade_utils.trade_parameter_name import TradeParameterName


class TradeDatabaseStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, secondary_region: str, **kwargs) -> None:
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
        database_name = 'trades'
        cluster_admin = "clusteradmin"

        parameter_group = rds.ParameterGroup(
            self,
            "ParameterGroup",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_2
            ),
            parameters={
                "max_connections": "28"
            }
        )

        self.cluster = rds.DatabaseCluster(self, "TradeCluster",
                                           engine=rds.DatabaseClusterEngine.aurora_postgres(
                                               version=rds.AuroraPostgresEngineVersion.VER_16_2),
                                           credentials=rds.Credentials.from_generated_secret(cluster_admin),
                                           writer=writer,
                                           readers=readers,
                                           serverless_v2_min_capacity=0.5, serverless_v2_max_capacity=2,
                                           storage_type=rds.DBClusterStorageType.AURORA_IOPT1,
                                           storage_encrypted=False,
                                           vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
                                           vpc=vpc, default_database_name=database_name, cluster_identifier='stock',
                                           backup=rds.BackupProps(retention=cdk.Duration.days(15)),
                                           parameter_group=parameter_group,
                                           preferred_maintenance_window="Sun:23:45-Mon:00:15",
                                           cloudwatch_logs_exports=["postgresql"],
                                           cloudwatch_logs_retention=cdk.aws_logs.RetentionDays.TWO_WEEKS)

        global_cluster = rds.CfnGlobalCluster(
            self, "global-trade-cluster",
            deletion_protection=False,
            global_cluster_identifier='global-trade-cluster',
            source_db_cluster_identifier=self.cluster.cluster_identifier
        )

        order_api_user_name = "order_api_user"
        order_api_secret = rds.DatabaseSecret(self, "order_api_secret", username=order_api_user_name,
                                              secret_name="order_api_db_secret", master_secret=self.cluster.secret,
                                              exclude_characters="{}[]()'\"", dbname=database_name)
        order_api_secret.attach(self.cluster)
        order_api_secret.add_replica_region(secondary_region)
        self.cluster.add_rotation_single_user(automatically_after=cdk.Duration.days(1))
        self.cluster.add_rotation_multi_user(order_api_user_name, automatically_after=cdk.Duration.days(1),
                                             secret=order_api_secret)

        self.cluster.metric_serverless_database_capacity(period=cdk.Duration.minutes(10)).create_alarm(self, "capacity",
                                                                                                       threshold=1.5,
                                                                                                       evaluation_periods=3)
        self.cluster.metric_acu_utilization(period=cdk.Duration.minutes(10)).create_alarm(self, "alarm",
                                                                                          evaluation_periods=3,
                                                                                          threshold=90)

        self.cluster_credentials = self.cluster.secret
        admin_client = ec2.BastionHostLinux(self, "AdminClient", instance_name="AdminClient", vpc=vpc,
                                            require_imdsv2=True,
                                            subnet_selection=ec2.SubnetSelection(
                                                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED))

        proxy = self.cluster.add_proxy("proxy", borrow_timeout=cdk.Duration.seconds(30), max_connections_percent=95,
                                       secrets=[order_api_secret], vpc=vpc, db_proxy_name="TradeProxy")

        # allow admin actions
        admin_client.role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["secretsmanager:ListSecrets"]))
        admin_client.role.add_to_policy(
            iam.PolicyStatement(resources=["*"], actions=["elasticloadbalancing:DescribeLoadBalancers"]))
        admin_client.role.add_to_policy(
            iam.PolicyStatement(resources=["*"], actions=["ssm:GetParameter", "ssm:PutParameter"]))
        self.cluster_credentials.grant_read(admin_client.role)
        order_api_secret.grant_read(admin_client.role)
        proxy.grant_connect(admin_client.role, cluster_admin)
        proxy.grant_connect(admin_client.role, order_api_user_name)
        self.cluster.connections.allow_from(admin_client, ec2.Port.tcp(5432))
        proxy.connections.allow_from(admin_client, ec2.Port.tcp(5432))

        # allow DML from order api
        self.task_role = iam.Role(self, "TradingApiTaskRole",
                                  role_name=cdk.PhysicalName.GENERATE_IF_NEEDED,
                                  assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))
        self.task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["secretsmanager:ListSecrets"]))
        self.task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["ssm:GetParameter"]))
        self.task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["cloudwatch:PutMetricData"]))
        order_api_secret.grant_read(self.task_role)
        proxy.grant_connect(self.task_role, order_api_user_name)
        self.cluster.connections.allow_from(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(5432))
        proxy.connections.allow_from(ec2.Peer.ipv4(vpc.vpc_cidr_block), ec2.Port.tcp(5432))
        # preferable to above, but creates a cyclic reference, except not really, so confusing
        # self.cluster.connections.allow_from(service.ecs_service, ec2.Port.tcp(5432))

        ro_proxy_sg = ec2.SecurityGroup(self, "TradeProxyReadOnlySG", vpc=vpc)
        ro_proxy_sg.add_ingress_rule(ec2.Peer.ipv4("10.0.0.0/16"), ec2.Port.tcp(5432),
                                     "access from any IP in VPC for ECS tasks")
        reader_endpoint = rds.CfnDBProxyEndpoint(self, 'TradeProxyReadOnlyEndpoint', db_proxy_name=proxy.db_proxy_name,
                                                 target_role='READ_ONLY',
                                                 db_proxy_endpoint_name='TradeProxyReadOnlyEndpoint',
                                                 vpc_subnet_ids=vpc.select_subnets(
                                                     subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnet_ids,
                                                 vpc_security_group_ids=[ro_proxy_sg.security_group_id]
                                                 )
        reader_endpoint.node.add_dependency(proxy)

        ssm.StringParameter(self, "TradeDatabaseSecretId",
                            description="Trade Database Secret Id",
                            parameter_name=TradeParameterName.TRADE_DATABASE_SECRET_ID.value,
                            string_value=self.cluster.secret.secret_name)

        ssm.StringParameter(self, "TradeOrderApiDbSecretId",
                            description="Order API Database Secret Id",
                            parameter_name=TradeParameterName.TRADE_ORDER_API_SECRET_ID.value,
                            string_value=order_api_secret.secret_name)

        ssm.StringParameter(self, "TradeRdsProxyEndpoint",
                            description="Trade Database Proxy Endpoint",
                            parameter_name=TradeParameterName.TRADE_RDS_PROXY_ENDPOINT.value,
                            string_value=proxy.endpoint)

        ssm.StringParameter(self, "TradeRdsProxyReadOnlyEndpoint",
                            description="Trade Database Proxy Read Only Endpoint",
                            parameter_name=TradeParameterName.TRADE_RDS_PROXY_READ_ONLY_ENDPOINT.value,
                            string_value=reader_endpoint.attr_endpoint)
