#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.process_stack import ProcessStack
from stacks.datasource_stack import DatasourceStack
from stacks.failover_stack import FailoverStack

app = cdk.App()
account = os.getenv('AWS_ACCOUNT_ID')
primary_region = os.getenv('AWS_PRIMARY_REGION')
secondary_region = os.getenv('AWS_SECONDARY_REGION')
idempotency_table = 'idempotency'
accounts_table = 'brokerage_accounts'

failover = FailoverStack(app, "FailoverStack", env=cdk.Environment(account=account, region=secondary_region))

multi_region = DatasourceStack(app, "DatasourceStack",
                               env=cdk.Environment(account=account, region=primary_region),
                               secondary_region=secondary_region,
                               idempotency_table=idempotency_table,
                               accounts_table=accounts_table)

primary = ProcessStack(app, "ProcessStack-primary",
                       env=cdk.Environment(account=account, region=primary_region),
                       recovery_region=False,
                       idempotency_table=idempotency_table,
                       accounts_table=accounts_table, failover_bucket=failover.failover_bucket.bucket_name)

secondary = ProcessStack(app, "ProcessStack-secondary",
                         env=cdk.Environment(account=account, region=secondary_region),
                         recovery_region=True,
                         idempotency_table=idempotency_table,
                         accounts_table=accounts_table, failover_bucket=failover.failover_bucket.bucket_name)

primary.topic.add_subscription(cdk.aws_sns_subscriptions.SqsSubscription(primary.queue))
primary.topic.add_subscription(cdk.aws_sns_subscriptions.SqsSubscription(secondary.queue))

#secondary.topic.add_subscription(cdk.aws_sns_subscriptions.SqsSubscription(primary.queue))
# add the subscription post deploy if desired, cyclic reference for CDK so can't do it here
secondary.topic.add_subscription(cdk.aws_sns_subscriptions.SqsSubscription(secondary.queue))

multi_region.idempotency_table.grant_read_write_data(primary.new_account_function)
multi_region.new_account_table.grant_read_write_data(primary.new_account_function)

multi_region.idempotency_table.replica(secondary_region).grant_read_write_data(secondary.new_account_function)
multi_region.new_account_table.replica(secondary_region).grant_read_write_data(secondary.new_account_function)

failover.failover_bucket.grant_read(primary.new_account_function)
failover.failover_bucket.grant_read(secondary.new_account_function)

app.synth()
