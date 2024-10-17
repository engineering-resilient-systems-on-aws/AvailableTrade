from aws_cdk import (
    Stack,
    aws_synthetics as synthetics,
    aws_iam as iam,
    aws_s3 as s3,
    Duration,
    RemovalPolicy    
)
from aws_cdk.aws_cloudwatch import (
    Alarm,
    ComparisonOperator,
    Statistic,
)
from constructs import Construct
import os

class FrontEndCanaryStack(Stack):


    def __init__(self, scope: Construct, id: str, endpoint_url: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        assets_bucket = s3.Bucket(self, 'CanaryAssetsBucket',
            # bucket_name='canary-assets-bucket',
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        canary_role = iam.Role(self, f"canary-{self.account}-{self.region}-role",
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            description='Canary IAM Role'
        )

        canary_role.add_to_policy(iam.PolicyStatement(
            resources=['*'],
            actions=['s3:ListAllMyBuckets'],
            effect=iam.Effect.ALLOW
        ))    

        canary_role.add_to_policy(iam.PolicyStatement(
            resources=[f"{assets_bucket.bucket_arn}/*"],
            actions=["kms:GenerateDataKey"],
            effect=iam.Effect.ALLOW
        ))      

        canary_role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"{assets_bucket.bucket_arn}",
                    f"{assets_bucket.bucket_arn}/*"
                ],
                actions=['s3:*'],
                effect=iam.Effect.ALLOW,
            )
        )

        canary_role.add_to_policy(
            iam.PolicyStatement(
                resources=['*'],
                actions=['cloudwatch:PutMetricData'],
                effect=iam.Effect.ALLOW,
                conditions={
                    "StringEquals": {
                        "cloudwatch:namespace": "CloudWatchSynthetics",
                    },
                },
            )
        )
        with open('python/index.py', 'r') as file:
            code_as_string = file.read()
        canary = synthetics.Canary(self, 'FrontEndCanary',
                          canary_name=f"canary-web-{self.region}",
                          role=canary_role,
                          schedule=synthetics.Schedule.rate(Duration.minutes(5)),
                          artifacts_bucket_location={'bucket': assets_bucket},
                          environment_variables={'ENDPOINT_URL': f"https://{endpoint_url}"},
                          runtime = synthetics.Runtime.SYNTHETICS_PYTHON_SELENIUM_3_0,
                          test=synthetics.Test.custom(
                              code=synthetics.Code.from_inline(code_as_string),
                              handler='index.handler'
                          )
        )

        # Get the metric for successful canary runs
        success_metric = canary.metric_success_percent()

        # Set up CloudWatch Alarm for success rate
        Alarm(
            self,
            "CanarySuccessAlarm",
            alarm_name=f"Synthetics-Alarm-canary-web-{self.region}",            
            metric=success_metric,
            evaluation_periods=2,  # Evaluate over 2 periods
            threshold=90,  # Threshold for success rate (90%)
            comparison_operator=ComparisonOperator.LESS_THAN_THRESHOLD,            
            alarm_description="Canary successful run rate fell below 90%",
        )



