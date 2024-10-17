import os
import aws_cdk as cdk
from stacks.hello_resilience_stack import HelloResilienceStack

account = os.getenv('AWS_ACCOUNT_ID')
primary_region = os.getenv('AWS_PRIMARY_REGION')

app = cdk.App()
HelloResilienceStack(
    app, "HelloResilienceStack",
    env=cdk.Environment(account=account, region=primary_region))
app.synth()
