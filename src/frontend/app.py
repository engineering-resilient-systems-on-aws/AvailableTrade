#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.front_end_canary_stack import FrontEndCanaryStack
from stacks.front_end_website_stack import FrontEndWebsiteStack
from stacks.front_end_secondary_bucket_stack import FrontEndSecondaryBucketStack
from stacks.front_end_rum_stack import FrontEndRumStack

account = os.getenv('AWS_ACCOUNT_ID')
primary_region = os.getenv('AWS_PRIMARY_REGION')
secondary_region = os.getenv('AWS_SECONDARY_REGION')
website_domain_name = os.getenv('AWS_DOMAIN_NAME')
primary_environment = cdk.Environment(account=account, region=primary_region)
secondary_environment = cdk.Environment(account=account, region=secondary_region)

app = cdk.App()

FrontEndSecondaryBucketStack(app, "FrontEnd-BucketStack-Secondary", env=secondary_environment)
FrontEndWebsiteStack(app, "FrontEnd-WebsiteStack", env=primary_environment, domain_name=website_domain_name, secondary_region=secondary_region)
FrontEndCanaryStack(app, "FrontEnd-CanaryStack-Primary", env=primary_environment, endpoint_url=website_domain_name)
FrontEndCanaryStack(app, "FrontEnd-CanaryStack-Secondary", env=secondary_environment, endpoint_url=website_domain_name)
FrontEndRumStack(app, "FrontEnd-RumStack", env=primary_environment, domain_name=website_domain_name)

app.synth()
