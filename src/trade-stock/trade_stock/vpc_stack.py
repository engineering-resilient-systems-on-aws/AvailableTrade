import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2
)
from aws_cdk import Stack
from constructs import Construct

# ToDo: consider making this a dict, and adding a policy statement for each: ec2.PolicyStatement(), be secure
interface_endpoints = ['ecr.dkr', 'ecr.api', 'xray', 'logs', 'ssm', 'ssmmessages', 'ec2messages', 'secretsmanager',
                       'elasticloadbalancing','monitoring'] # guardduty-data
# TODO: watch out for this if you have gaurd duty turned on with your private VPC 
# 1. aws-guardduty-agent-fargate container was attempting to and failing to download.
# I had to disable Guard Duty to successfully deploy.
# CannotPullContainerError: pull image manifest has been retried 1 time(s):
# failed to resolve ref 593207742271.dkr.ecr.us-east-1.amazonaws.com/aws-guardduty-agent-fargate:v1.0.1-Fg_x86_64:
# pulling from host 593207742271.dkr.ecr.us-east-1.amazonaws.com failed



class VpcStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc: ec2.IVpc = ec2.Vpc(self, "VPC", max_azs=3, subnet_configuration=[
            ec2.SubnetConfiguration(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, name="Service", cidr_mask=24),
        ])
        self.vpc.add_flow_log("TradeStockVpcFlow")
        vpc_peer = ec2.Peer.ipv4(self.vpc.vpc_cidr_block)
        endpoint_sg = ec2.SecurityGroup(self, "endpoint_sg", security_group_name="InterfaceEndpointsSG",
                                        description="allow access VPC Endpoints", vpc=self.vpc,
                                        allow_all_outbound=True)
        cdk.Tags.of(endpoint_sg).add("Name", "InterfaceEndpoints")
        endpoint_sg.add_ingress_rule(vpc_peer, ec2.Port.tcp(443))
        endpoint_sg.add_ingress_rule(vpc_peer, ec2.Port.tcp(80))

        # ToDo: endpoint policies should be in place before you go to production.

        for endpoint in interface_endpoints:
            self.vpc.add_interface_endpoint(
                endpoint,
                service=ec2.InterfaceVpcEndpointAwsService(endpoint, port=443),
                private_dns_enabled=True,
                security_groups=[endpoint_sg])
            # interface_endpoint.add_to_policy(iam.PolicyStatement())
            # support here https://docs.aws.amazon.com/vpc/latest/privatelink/aws-services-privatelink-support.html

        self.vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)
        # ToDo: gateway_endpoint.add_to_policy(iam.PolicyStatement()) -- allow for ECR and Amazon Linux policies
