import os
import random
from dataclasses import dataclass, field
from uuid import uuid4
from aws_lambda_powertools import Logger
import json
import boto3
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    IdempotencyConfig,
    idempotent_function
)
from aws_lambda_powertools import Tracer
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import event_source, SQSEvent
from aws_lambda_powertools.utilities.idempotency.serialization.dataclass import DataclassSerializer
from boto3.dynamodb.conditions import Key


logger = Logger()
metrics = Metrics()
tracer = Tracer()
accounts_table = os.getenv("ACCOUNTS_TABLE")
idempotency_table = os.getenv("IDEMPOTENCY_TABLE")
recovery_region = os.getenv("RECOVERY_REGION") == "True"
persistence_store = DynamoDBPersistenceLayer(table_name=idempotency_table)
config = IdempotencyConfig(event_key_jmespath="request_token",
                           raise_on_no_idempotency_key=True,
                           expires_after_seconds=60 * 60 * 3)
ddb_client = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
failover_bucket = os.getenv("FAILOVER_BUCKET")


@tracer.capture_lambda_handler
@metrics.log_metrics
@event_source(data_class=SQSEvent)
def handler(event: SQSEvent, context: LambdaContext):
    config.register_lambda_context(context)
    recovery_mode = in_recovery_mode()
    logger.info(f'recovery_mode: {recovery_mode}')
    batch_item_failures = []
    sqs_batch_response = {}
    active_in_recovery = recovery_region and not in_recovery_mode()
    passive_in_primary = not recovery_region and in_recovery_mode()
    for record in event.records:
        logger.debug(f'record: {record}')
        body = json.loads(record["body"])
        message = json.loads(body['Message'])
        green_test = "greentest_" in message["user_id"]
        if (active_in_recovery or passive_in_primary) and not green_test:
            logger.info("nothing to do, message must be processed in active region")
            table = ddb_client.Table(accounts_table)
            logger.debug(f'finding record {message}')
            try:
                logger.debug('query dynamo')  # must throw an error if not found
                user_id = message['user_id']
                request_token = message['request_token']
                response = table.query(
                    IndexName='user_request',
                    KeyConditionExpression=Key('user_id').eq(user_id) & Key('request_token').eq(
                        request_token), ProjectionExpression='account_id')
                if len(response['Items']) < 1:
                    raise Exception("account record not found")
                logger.debug(
                    f'safe to purge message, found {response}')
            except Exception as e:
                logger.error('failed to process', e)
                batch_item_failures.append({"itemIdentifier": record.message_id})
        else:  # current region is the active region, process messages
            logger.info("active region, attempting to create new account")
            try:
                # raise Exception("kaboom!!!")  # forced failure
                logger.debug(f'body: {body}')
                account: Account = create_brokerage_account(account_event=message)
            except Exception as exc:
                logger.error('failed to create account', exc)
                batch_item_failures.append({"itemIdentifier": record.message_id})
                metrics.add_metric(name="NewAccountFailure", unit=MetricUnit.Count, value=1)

    sqs_batch_response["batchItemFailures"] = batch_item_failures
    return sqs_batch_response


def in_recovery_mode():
    # ToDo: list has paging, so want to change this to just get the object. it will throw error, so need clean try/except flow
    objects = s3_client.list_objects_v2(Bucket=failover_bucket)
    for obj in objects.get('Contents', []):
        if 'failover.txt' in obj['Key']:
            return True
    return False


@dataclass
class Beneficiary:
    name: str
    percent: int


@dataclass
class Suitability:
    liquidity: str
    time_horizon: str
    risk_tolerance: str


@dataclass
class Instructions:
    dividends: str


@dataclass
class Account:
    customer_first_name: str
    customer_last_name: str
    account_type: str
    comment: str
    beneficiaries: list[Beneficiary]
    suitability: Suitability
    instructions: Instructions
    request_token: str
    user_id: str
    account_id: str = field(default_factory=lambda: f"{uuid4()}")


@idempotent_function(data_keyword_argument='account_event', config=config, persistence_store=persistence_store,
                     output_serializer=DataclassSerializer)
def create_brokerage_account(account_event: dict) -> Account:
    account: Account = Account(**account_event)
    account_serialized = DataclassSerializer(Account).to_dict(data=account)
    logger.debug(f'serialized account {account_serialized}')
    table = ddb_client.Table(accounts_table)
    result = table.put_item(Item=account_serialized)
    logger.debug(f'ddb put result{result}')
    metrics.add_metric(name="NewAccountOpened", unit=MetricUnit.Count, value=1)
    tracer.put_annotation("account_id", account.account_id)
    return account
