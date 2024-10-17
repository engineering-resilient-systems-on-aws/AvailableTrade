import builtins
import typing
import aws_cdk as cdk
from aws_cdk import (
    Duration,
    aws_elasticloadbalancingv2 as elb,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2_targets as targets,
)
from cdk_ecs_service_extensions import (
    HttpLoadBalancerProps,
    Service,
    ServiceExtension,
    ServiceBuild
)
from constructs import Construct


class PrivateAlbExtension(ServiceExtension):
    def __init__(self, requests_per_target=None):
        super().__init__("load-balancer")
        self.alb_listener = None
        self.alb = None
        self.nlb = None
        self.nlb_listener = None
        self.requests_per_target = requests_per_target
        self.props = HttpLoadBalancerProps(requests_per_target=self.requests_per_target)

    def prehook(self, parent: Service, scope: Construct) -> None:
        self._parent_service = parent
        self._scope = scope
        self.alb = elb.ApplicationLoadBalancer(
            scope,
            "{}-private-alb".format(self._parent_service.id),
            vpc=self._parent_service.vpc,
            internet_facing=False,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            cross_zone_enabled=True
        )

        self.alb_listener = self.alb.add_listener(
            "{}-alb-listener".format(self._parent_service.id), port=80, open=True
        )

        self.nlb = elb.NetworkLoadBalancer(
            scope,
            "{}-private-nlb".format(self._parent_service.id),
            vpc=self._parent_service.vpc,
            internet_facing=False,
            cross_zone_enabled=True,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED  # TODO - for sidecar docker images
            ),
        )

        target_group = elb.NetworkTargetGroup(
            scope,
            "{}-alb-target_group".format(self._parent_service.id),
            port=80,
            target_type=elb.TargetType.ALB,
            protocol=elb.Protocol.TCP,
            health_check=elb.HealthCheck(enabled=True),
            vpc=self._parent_service.vpc,
            targets=[targets.AlbTarget(self.alb, 80)],
        )

        self.nlb_listener = self.nlb.add_listener(
            "{}-nlb-listener".format(self._parent_service.id),
            port=80,
            default_action=elb.NetworkListenerAction.forward([target_group]),
        )

        cdk.CfnOutput(
            scope,
            "{}-nlb-dns-output".format(self._parent_service.id),
            value=self.nlb.load_balancer_dns_name,
        )

    def use_service(
            self, service: typing.Union[ecs.Ec2Service, ecs.FargateService]
    ) -> None:

        target_group = self.alb_listener.add_targets(
            self._parent_service.id,
            deregistration_delay=Duration.seconds(10),
            port=80,
            targets=[service]
            # health_check=elb.HealthCheck(path='/health/')  # customize health check here if desired
        )
        target_group.set_attribute("load_balancing.cross_zone.enabled", "true")

        if self.requests_per_target:
            if not self._parent_service.scalable_task_count:
                raise Exception(
                    "Auto scaling target for the service {} hasn't been configured. Please use Service construct to configure 'minTaskCount' and 'maxTaskCount'.".format(
                        self._parent_service.id
                    )
                )
            self._parent_service.scalable_task_count.scale_on_request_count(
                "{}-target-request-count-{}".format(
                    self._parent_service.id, self.requests_per_target
                ),
                requests_per_target=self.requests_per_target,
                target_group=target_group,
            )
            self._parent_service.enable_auto_scaling_policy()
            self._parent_service.ecs_service.enable_deployment_alarms()

    def modify_service_props(
            self,
            *,
            cluster: ecs.ICluster,
            task_definition: ecs.TaskDefinition,
            assign_public_ip: typing.Optional[builtins.bool] = None,
            cloud_map_options: typing.Optional[ecs.CloudMapOptions] = None,
            desired_count: int = None,
            health_check_grace_period: typing.Optional[Duration] = None,
            max_healthy_percent: int = None,
            min_healthy_percent: int = None
    ) -> ServiceBuild:
        build = ServiceBuild(
            cluster=cluster,
            task_definition=task_definition,
            assign_public_ip=False,  # override
            cloud_map_options=cloud_map_options,
            desired_count=desired_count,
            health_check_grace_period=Duration.minutes(1),
            max_healthy_percent=max_healthy_percent,
            min_healthy_percent=min_healthy_percent,
        )
        return build
