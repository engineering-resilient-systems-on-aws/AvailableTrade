from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_ssm as ssm,
)
import os
import aws_cdk as cdk
from aws_cdk import Stack
from cdk_ecs_service_extensions import (
    Container,
    Environment,
    Service,
    ServiceDescription,
    EnvironmentCapacityType,
    AutoScalingOptions,
)
import shutil
from trade_utils.trade_parameter_name import TradeParameterName
from trade_utils.private_lb_extension import PrivateAlbExtension
from trade_utils.x_ray_extension import XRayExtension
from constructs import Construct


class TradeOrderStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, task_role: iam.Role, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        trading_api_image = ecr.DockerImageAsset(self, 'order_api_image',
                                                 directory=os.path.join(os.path.dirname('.'), 'order_api'))
        trading_api_image.repository.image_scan_on_push = True

        cluster = ecs.Cluster(self, "TradeOrderCluster", container_insights=True, vpc=vpc)
        service = ServiceDescription()
        container = Container(cpu=256, memory_mib=512, traffic_port=80,
                              image=ecs.ContainerImage.from_docker_image_asset(asset=trading_api_image))

        service.add(container)
        self.private_lb = PrivateAlbExtension()
        service.add(self.private_lb)
        #service.add(XRayExtension(image_id=f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/xray-sidecar"))
        environment = Environment(self, "TradeOrderDev", vpc=vpc, cluster=cluster,
                                  capacity_type=EnvironmentCapacityType.FARGATE)

        self.service = Service(self, "OrderApi", environment=environment,
                               service_description=service,
                               desired_count=len(vpc.availability_zones) * 3,
                               task_role=task_role,
                               auto_scale_task_count=AutoScalingOptions(
                                   min_task_count=len(vpc.availability_zones),
                                   max_task_count=len(vpc.availability_zones) * 8,
                                   target_cpu_utilization=70,
                                   target_memory_utilization=50))

        auth_failure_metric = logs.MetricFilter(self, "TradeOrderDBAuthFailure",
                                                log_group=container.log_group,
                                                metric_name="OrderApiDbAuthFailure",
                                                metric_namespace="TradeStock",
                                                metric_value="1",
                                                unit=cloudwatch.Unit.COUNT,
                                                filter_pattern=logs.FilterPattern.string_value(
                                                    json_field="$.exc_info", comparison="=",
                                                    value="*password authentication failed*"),
                                                dimensions={"AvailabilityZone": "$.az"}
                                                )

        db_connection_exhaustions = logs.MetricFilter(self, "TradeOrderConnectionExhaustion",
                                                         log_group=container.log_group,
                                                         metric_name="OrderApiConnectionExhaustion",
                                                         metric_namespace="TradeStock",
                                                         metric_value="1",
                                                         unit=cloudwatch.Unit.COUNT,
                                                         filter_pattern=logs.FilterPattern.string_value(
                                                             json_field="$.exc_info", comparison="=",
                                                             value="*remaining connection slots are reserved*"),
                                                         dimensions={"AvailabilityZone": "$.az"}
                                                         )

        log_exceptions = logs.MetricFilter(self, "TradeOrderErrors",
                                           log_group=container.log_group,
                                           metric_name="AllErrors",
                                           metric_namespace="TradeStock",
                                           metric_value="1",
                                           unit=cloudwatch.Unit.COUNT,
                                           filter_pattern=logs.FilterPattern.string_value(
                                               json_field="$.levelname", comparison="=",
                                               value="ERROR"),
                                           dimensions={"AvailabilityZone": "$.az"}
                                           )

        ssm.StringParameter(self, "OrderApiDNSEndpoint",
                            description="Order API DNS endpoint",
                            parameter_name=TradeParameterName.TRADE_ORDER_ENDPOINT.value,
                            string_value=self.private_lb.alb.load_balancer_dns_name)

        dashboard = cloudwatch.Dashboard(self, f"TradeStockDashboard{self.region}",
                                         dashboard_name=f"TradeStockDashboard{self.region}")
        dashboard.add_widgets(cloudwatch.GraphWidget(
            title="Stock Cluster DB Connections", width=8, left=[
                cloudwatch.Metric(metric_name="DatabaseConnections", namespace="AWS/RDS",
                                  dimensions_map={"DBClusterIdentifier": "stock"},
                                  unit=cloudwatch.Unit.COUNT, label='count', statistic=cloudwatch.Stats.SUM,
                                  period=cdk.Duration.seconds(60))]))

        dashboard.add_widgets(
            cloudwatch.GraphWidget(title="Trade Stock API Errors", width=8, statistic=cloudwatch.Stats.SUM,
                                   left=[auth_failure_metric.metric(),
                                         log_exceptions.metric(), db_connection_exhaustions.metric()]))

        service_cpu_dimensions = {"ServiceName": self.service.ecs_service.service_name}
        service_cpu_dimensions.update(cluster.metric_memory_utilization().dimensions)
        dashboard.add_widgets(
            cloudwatch.GraphWidget(title="Trade Stock API CPU", width=8, statistic=cloudwatch.Stats.MINIMUM,

                                   left=[
                                       cloudwatch.Metric(
                                           metric_name=cluster.metric_cpu_utilization().metric_name,
                                           namespace=cluster.metric_cpu_utilization().namespace,
                                           dimensions_map=service_cpu_dimensions,
                                           unit=cloudwatch.Unit.PERCENT, label='Max',
                                           statistic=cloudwatch.Stats.MAXIMUM,
                                           period=cdk.Duration.seconds(60)),
                                       cloudwatch.Metric(
                                           metric_name=cluster.metric_cpu_utilization().metric_name,
                                           namespace=cluster.metric_cpu_utilization().namespace,
                                           dimensions_map=service_cpu_dimensions,
                                           unit=cloudwatch.Unit.PERCENT, label='Avg',
                                           statistic="Avg",
                                           period=cdk.Duration.seconds(60)),
                                       cloudwatch.Metric(
                                           metric_name=cluster.metric_cpu_utilization().metric_name,
                                           namespace=cluster.metric_cpu_utilization().namespace,
                                           dimensions_map=service_cpu_dimensions,
                                           unit=cloudwatch.Unit.PERCENT, label='Min',
                                           statistic=cloudwatch.Stats.MINIMUM,
                                           period=cdk.Duration.seconds(60))
                                   ]))

        service_mem_dimensions = {"ServiceName": self.service.ecs_service.service_name}
        service_mem_dimensions.update(cluster.metric_memory_utilization().dimensions)
        dashboard.add_widgets(
            cloudwatch.GraphWidget(title="Trade Stock API Memory", width=8, statistic=cloudwatch.Stats.MINIMUM,
                                   left=[
                                       cloudwatch.Metric(
                                           metric_name=cluster.metric_memory_utilization().metric_name,
                                           namespace=cluster.metric_memory_utilization().namespace,
                                           dimensions_map=service_mem_dimensions,
                                           unit=cloudwatch.Unit.PERCENT, label='Max',
                                           statistic=cloudwatch.Stats.MAXIMUM,
                                           period=cdk.Duration.seconds(60)),
                                       cloudwatch.Metric(
                                           metric_name=cluster.metric_memory_utilization().metric_name,
                                           namespace=cluster.metric_memory_utilization().namespace,
                                           dimensions_map=service_mem_dimensions,
                                           unit=cloudwatch.Unit.PERCENT, label='Avg',
                                           statistic="Avg",
                                           period=cdk.Duration.seconds(60)),
                                       cloudwatch.Metric(
                                           metric_name=cluster.metric_memory_utilization().metric_name,
                                           namespace=cluster.metric_memory_utilization().namespace,
                                           dimensions_map=service_mem_dimensions,
                                           unit=cloudwatch.Unit.PERCENT, label='Min',
                                           statistic=cloudwatch.Stats.MINIMUM,
                                           period=cdk.Duration.seconds(60))
                                   ]))

        requested = cloudwatch.Metric(namespace="TradeOrder", metric_name="TradeOrderRequested",
                                      period=cdk.Duration.minutes(1), statistic="sum")
        filled = cloudwatch.Metric(namespace="TradeOrder", metric_name="TradeOrderFilled",
                                   period=cdk.Duration.minutes(1), statistic="sum")
        rejected = cloudwatch.Metric(namespace="TradeOrder", metric_name="TradeOrderRejected",
                                     period=cdk.Duration.minutes(1), statistic="sum")

        sla_percentage = cloudwatch.MathExpression(
            expression="requested / (filled + rejected)",
            using_metrics={
                "requested": requested,
                "filled": filled,
                "rejected": rejected
            }, period=cdk.Duration.minutes(1), label="TradeOrderSuccessRate")

        shutil.copy("trade_utils/trade_parameter_name.py", "order_api/trade_parameter_name.py")
        cdk.CfnOutput(self, "OrderAPI.ALB.DNSEndpoint", value=self.private_lb.alb.load_balancer_dns_name)
