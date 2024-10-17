#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.orchestration_primary_stack import OrchestrationPrimaryStack
from stacks.orchestration_secondary_stack import OrchestrationSecondaryStack  
from stacks.orchestration_route53_stack import OrchestrationRoute53Stack 
app = cdk.App()

account = os.getenv('AWS_ACCOUNT_ID')
primary_region = os.getenv('AWS_PRIMARY_REGION')
secondary_region = os.getenv('AWS_SECONDARY_REGION')
website_domain_name = os.getenv('AWS_DOMAIN_NAME')

primary_environment = cdk.Environment(account=account, region=primary_region)
secondary_environment = cdk.Environment(account=account, region=secondary_region)

OrchestrationSecondaryStack(app, "Orchestration-Secondary-Stack", env=secondary_environment, domain_name=website_domain_name)
OrchestrationPrimaryStack(app, "Orchestration-Primary-Stack", env=primary_environment, domain_name=website_domain_name)
OrchestrationRoute53Stack(app, "Orchestration-Route53-Primary-Stack", env=primary_environment, domain_name=website_domain_name, is_primary=True)
OrchestrationRoute53Stack(app, "Orchestration-Route53-Secondary-Stack", env=secondary_environment, domain_name=website_domain_name, is_primary=False)

app.synth()
