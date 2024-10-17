from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
)
import aws_cdk as cdk
from constructs import Construct


class FrontEndSecondaryBucketStack(cdk.Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        website_bucket = s3.Bucket(self, 'SecondaryS3Bucket',
                                   bucket_name=f'website-{self.account}-{self.region}',
                                   versioned=True,
                                   removal_policy=cdk.RemovalPolicy.DESTROY,
                                   auto_delete_objects=True,
                                   enforce_ssl=True,
                                   server_access_logs_bucket=s3.Bucket(self,f"ServerAccessLogsBucket-{self.account}-{self.region}")
                                   )

        website_bucket.add_to_resource_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            principals=[iam.ServicePrincipal('cloudfront.amazonaws.com')],
            actions=["s3:GetObject"],
            resources=[website_bucket.arn_for_objects("*")]
        ))
