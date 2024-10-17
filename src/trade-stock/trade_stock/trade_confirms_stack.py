from aws_cdk import (
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr,
    aws_ssm as ssm,
    aws_iam as iam
)
import os
import shutil
import aws_cdk as cdk
from aws_cdk import Stack
from cdk_ecs_service_extensions import (
    Container,
    Environment,
    Service,
    ServiceDescription,
    EnvironmentCapacityType,
    AutoScalingOptions
)
from trade_utils.private_lb_extension import PrivateAlbExtension
from trade_utils.trade_parameter_name import TradeParameterName
from trade_utils.x_ray_extension import XRayExtension
from constructs import Construct


class TradeConfirmsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ToDO is it possible to use a single image, cross region, address this
        # make a decision, push to both regions, or use replication.
        # if using replication, you need to pull the image from ECR by tag
        # to learn how to do this, you should also write the code to pull down the x-ray image from
        # dockerhub and push it to your repo, then enable X-Ray by using your customer sidecar, parameterize the image
        # or standardize on the image name and put a copy in each region.
        # you have to read up a bit more on ECR and learn best practices for mult-region

        # ToDO turn on scan on push
        confirms_api_image = ecr.DockerImageAsset(self, 'confirms_api_image',
                                                  directory=os.path.join(os.path.dirname('.'), 'confirms_api'))
        cluster = ecs.Cluster(self, "TradeConfirmsCluster", container_insights=True, vpc=vpc)
        service = ServiceDescription()
        container = Container(cpu=256, memory_mib=512, traffic_port=80,
                              image=ecs.ContainerImage.from_docker_image_asset(asset=confirms_api_image)
                              )



        service.add(container)
        self.private_lb = PrivateAlbExtension()
        service.add(self.private_lb)
        #service.add(XRayExtension()) # copy Xray image into ECR

        environment = Environment(self, "TradeConfirmsDev", vpc=vpc, cluster=cluster,
                                  capacity_type=EnvironmentCapacityType.FARGATE)

        task_role = iam.Role(self, "TradeConfirmsTaskRole",
                             assumed_by=iam.ServicePrincipal('ecs-tasks.amazonaws.com'))
        task_role.add_to_policy(iam.PolicyStatement(resources=["*"], actions=["ssm:GetParameter"]))

        self.service = Service(self, "ConfirmsApi", environment=environment,
                               service_description=service,
                               desired_count=len(vpc.availability_zones) * 2,
                               auto_scale_task_count=AutoScalingOptions(
                                   min_task_count=len(vpc.availability_zones),
                                   max_task_count=len(vpc.availability_zones) * 5,
                                   target_cpu_utilization=70,
                                   target_memory_utilization=50),
                               task_role=task_role)

        ssm.StringParameter(self, "ConfirmsApiDNSEndpoint",
                            description="Confirms API DNS endpoint",
                            parameter_name=TradeParameterName.TRADE_CONFIRMS_ENDPOINT.value,
                            string_value=self.private_lb.alb.load_balancer_dns_name)

        ssm.StringParameter(self, "ConfirmsExchangeStatus",
                            description="Indicates if the confirms exchange is available to accept trade requests",
                            parameter_name=TradeParameterName.TRADE_CONFIRMS_EXCHANGE_STATUS.value,
                            string_value="AVAILABLE")

        ssm.StringParameter(self, "ConfirmsGlitchFactor",
                            description="Indicates how often the confirms api is glitching",
                            parameter_name=TradeParameterName.TRADE_CONFIRMS_GLITCH_FACTOR.value,
                            string_value="OFF")

        shutil.copy("trade_utils/trade_parameter_name.py", "confirms_api/trade_parameter_name.py")

        cdk.CfnOutput(self, "ConfirmsAPI.ALB.DNSEndpoint", value=self.private_lb.alb.load_balancer_dns_name)
