from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb
)
import aws_cdk as cdk
from constructs import Construct


class DatasourceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, secondary_region: str,
                 idempotency_table: str, accounts_table: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.idempotency_table = dynamodb.TableV2(
            self, 'GlobalIdempotency', table_name=idempotency_table,
            partition_key={'name': 'id', 'type': dynamodb.AttributeType.STRING},
            deletion_protection=True,
            replicas=[dynamodb.ReplicaTableProps(region=secondary_region)],
            contributor_insights=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            time_to_live_attribute="expiration",
            point_in_time_recovery=True)

        self.new_account_table = dynamodb.TableV2(
            self, 'GlobalBrokerageAccounts', table_name=accounts_table,
            partition_key={'name': 'user_id',
                           'type': dynamodb.AttributeType.STRING},
            sort_key={'name': 'account_id',
                      'type': dynamodb.AttributeType.STRING},
            deletion_protection=True,
            replicas=[dynamodb.ReplicaTableProps(region=secondary_region)],
            contributor_insights=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            point_in_time_recovery=True,)

        self.new_account_table.add_global_secondary_index(
            partition_key=dynamodb.Attribute(name='user_id', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name='request_token', type=dynamodb.AttributeType.STRING),
            index_name='user_request'
        )
