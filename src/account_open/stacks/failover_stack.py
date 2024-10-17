from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam
)
import aws_cdk as cdk
from constructs import Construct


class FailoverStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.failover_bucket = s3.Bucket(self, "failover_bucket",
                                         bucket_name=f'failover-bucket-{self.region}-{self.account}')

        self.failover_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                principals=[
                    iam.ServicePrincipal("lambda.amazonaws.com"),
                    iam.ServicePrincipal("ssm.amazonaws.com")
                ],
                actions=["s3:PutObject"],
                resources=[self.failover_bucket.arn_for_objects("*")],
            )
        )

        cdk.CfnOutput(self, "Failover Bucket", value=self.failover_bucket.bucket_name)
