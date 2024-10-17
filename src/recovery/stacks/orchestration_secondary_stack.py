from aws_cdk import (
    Stack,
    Duration,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_ssm as ssm,
    aws_apigateway as apigateway,
    aws_sns as sns,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_iam as iam,
    aws_s3 as s3    
)
from constructs import Construct 
import os
import yaml

class OrchestrationSecondaryStack(Stack):
    def __init__(self, scope: Construct, id: str, domain_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)    

        ## Retrieve Secondary Clust ARN to use in SSM document
        secondary_cluster_arn = ssm.StringParameter.value_for_string_parameter(
            self, "trade_rds_secondary_cluster_arn"
        )  
        ## Create the bucket name     
        bucket_name = f"failover-bucket-{os.getenv('AWS_SECONDARY_REGION')}-{os.getenv('AWS_ACCOUNT_ID')}"

        # Retrieve bucket by name
        bucket = s3.Bucket.from_bucket_name(self, "S3FailoverBucket", bucket_name)        

        # IAM role for SSM Automation
        ssm_automation_role = iam.Role(
            self, "SSMAutomationRole",
            assumed_by=iam.ServicePrincipal("ssm.amazonaws.com"),
            description="Role to allow SSM Automation to run documents and access S3",
        )

        # Allow SSM Automation to execute the specified document
        ssm_automation_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:StartAutomationExecution"],
                resources=["*"],
            )
        )

        # Allow the SSM document to upload objects to the S3 bucket
        ssm_automation_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[
                    bucket.bucket_arn,  # Allow access to the bucket itself
                    f"{bucket.bucket_arn}/*"  # Allow access to all objects within the bucket
                ],
            )
        )        
        # Allow the SSM document to execute the failover automation
        ssm_automation_role.add_to_policy(
            iam.PolicyStatement(
                actions=["rds:SwitchoverGlobalCluster", "rds:FailoverGlobalCluster"],
                resources=["*"],
            )
        )
        # Allow the SSM document to execute the failover automation
        ssm_automation_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        yaml_doc = f""" # Use an f-string to interpolate the variable
        schemaVersion: '0.3'
        description: "Failover Document"
        assumeRole: "{ssm_automation_role.role_arn}"        
        mainSteps:
        - name: SwitchoverGlobalCluster
          action: aws:executeAwsApi
          nextStep: SToPFile
          inputs:
                Service: rds
                Api: SwitchoverGlobalCluster
                GlobalClusterIdentifier: global-trade-cluster
                TargetDbClusterIdentifier: {secondary_cluster_arn}                  
        - name: SToPFile
          action: aws:executeScript
          nextStep: PutMetricData
          inputs:
                Runtime: python3.10
                Handler: script_handler
                Script: |
                    def script_handler(event, context):
                        import boto3
                        # Create the text file
                        with open("failover.txt", "w") as f:
                            f.write("This is a test file for failover.")
                        # Upload the file to the S3 bucket                        
                        s3 = boto3.client('s3')
                        bucket_name = "{bucket_name}"  # Use the bucket name from the CDK variable
                        file_name = "failover.txt"
                        s3.upload_file(file_name, bucket_name, file_name)     
        - name: PutMetricData
          action: aws:executeAwsApi
          isEnd: true
          inputs:
                Service: cloudwatch
                Api: PutMetricData
                MetricData:
                    - MetricName: AvailableTradeFailoverMetric
                      Value: 3
                Namespace: AvailableTrade
        """
        # Create the AvailableTradeFailoverAutomation SSM Document
        ssm.CfnDocument(
            self, "AvailableTradeFailoverAutomation",
            content=yaml.safe_load(yaml_doc),
            document_type="Automation",
        )   

        ## Create an Alarm with a custom metric that will be used to signal a failover
        alarm = cloudwatch.Alarm(
            self,
            "AvailableTradeFailoverAlarm",
            metric=cloudwatch.Metric(
                namespace="AvailableTrade",
                metric_name="AvailableTradeFailoverMetric",
                dimensions_map={}, 
                statistic="Maximum",
                period=Duration.minutes(1),  
            ),
            alarm_name="AvailableTradeFailoverAlarm",
            threshold=2,
            evaluation_periods=1, 
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.IGNORE            
        )                                     

        # Create an SNS topic to be used with the CloudWatch Alarm
        alarm_topic = sns.Topic(self, "AvailableTradeFailoverAlarmTopic")
        alarm.add_alarm_action(cw_actions.SnsAction(alarm_topic))              

        # Create a certificate with multiple domain names (api-account and api-trade)
        hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=domain_name)        
        certificate = acm.Certificate(self, "Certificate",
                                    domain_name=domain_name,
                                    validation=acm.CertificateValidation.from_dns(hosted_zone),
                                    subject_alternative_names=[domain_name, f"api-account.{domain_name}", f"api-trade.{domain_name}"],
                                    )       
        ## Retrieve ssm parameter NewAccountAPIID
        account_api_id = ssm.StringParameter.value_for_string_parameter(
            self, "NewAccountAPIID"
        )

        ## Get a reference to the APIG
        account_api = apigateway.RestApi.from_rest_api_id(
            self, "NewAccountApi-Secondary",
            rest_api_id=account_api_id,
        )

        ## Create the custom domain name
        account_api.add_domain_name("NewAccountCustomDomain-Secondary",
            domain_name=f"api-account.{domain_name}",
            certificate=certificate,        
        )

        ## Retrieve ssm parameter names NewAccountAPIID
        trade_api_id = ssm.StringParameter.value_for_string_parameter(
            self, "TradeStockAPIID"
        )

        ## Get a reference to the APIG
        trade_api = apigateway.RestApi.from_rest_api_id(
            self, "TradeStockAPI-Secondary",
            rest_api_id=trade_api_id,
        )

        ## Create the custom domain name
        trade_api.add_domain_name("TradeStockCustomDomain-Secondary",
            domain_name=f"api-trade.{domain_name}",
            certificate=certificate,        
        )


