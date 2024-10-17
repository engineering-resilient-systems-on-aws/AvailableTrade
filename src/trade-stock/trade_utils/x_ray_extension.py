import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    aws_ecs as ecs,
    aws_iam as iam,
    Stack
)
from cdk_ecs_service_extensions import (
    Service,
    ServiceExtension,
)


class XRayExtension(ServiceExtension):
    def __init__(self, image_id: str, requests_per_target=None):
        super().__init__("xray-sidecar")
        self.requests_per_target = requests_per_target
        self.image_id = image_id

    def prehook(self, service: Service, scope: Construct) -> None:
        self._parent_service = service
        self._scope = scope

# docker pull amazon/aws-xray-daemon
# aws ecr get-login-password --region $AWS_PRIMARY_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_PRIMARY_REGION.amazonaws.com
# aws ecr create-repository --repository-name amazon/aws-xray-daemon
# docker tag amazon/aws-xray-daemon $AWS_ACCOUNT_ID.dkr.ecr.$AWS_PRIMARY_REGION.amazonaws.com/amazon/aws-xray-daemon:latest
# docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_PRIMARY_REGION.amazonaws.com/amazon/aws-xray-daemon:latest

    def use_task_definition(self, task_definition: ecs.TaskDefinition) -> None:
        self.container = task_definition.add_container('xray',
                                                       image=ecs.ContainerImage.from_registry(self.image_id),
                                                       essential=True,
                                                       memory_reservation_mib=256,
                                                       environment={
                                                           'AWS_REGION': Stack.of(self._parent_service).region},
                                                       health_check=ecs.HealthCheck(
                                                           command=[
                                                               'CMD-SHELL',
                                                               'curl -s http://localhost:2000'
                                                           ],
                                                           start_period=cdk.Duration.seconds(10),
                                                           interval=cdk.Duration.seconds(5),
                                                           timeout=cdk.Duration.seconds(2),
                                                           retries=3
                                                       ),
                                                       logging=ecs.AwsLogDriver(stream_prefix='xray'),
                                                       user='1337')
        task_definition.task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AWSXRayDaemonWriteAccess'))
        # need to add permissions for the ECR for xray image right here. delete stack and do a clean try.
        # image is trying to start like mac silicon, need to build it for linux, like with the other one.
        # what a pain, maybe test it from cloudshell.
        # jesus christ - exec /xray: exec format error

    def resolve_container_dependencies(self) -> None:
        if not self.container:
            raise Exception('The container dependency hook was called before the container was created')
