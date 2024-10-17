#!/bin/python3

import functools
from flask import Flask, request, Response
from flask_api import status
import json
import logging
import boto3
import requests
import random
import os
import urllib.parse
from pythonjsonlogger import jsonlogger
from circuitbreaker import circuit
from circuitbreaker import CircuitBreakerMonitor
from retry.api import retry_call
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy import exc
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig
from data_objects import Customer, Activity, Symbol, TradeState, TransactionType
from trade_parameter_name import TradeParameterName


class ConfirmsUnavailableError(RuntimeError):
    pass


json_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(levelname)s %(lineno)d %(asctime)s %(task)-32s %(az)-10s - %(message)s')
json_handler.setFormatter(formatter)
logging.basicConfig(handlers=[json_handler], level=logging.INFO)
logger = logging.getLogger('orders')

meta_data_uri = os.environ.get('ECS_CONTAINER_METADATA_URI_V4')
tr = requests.get("{}/task".format(meta_data_uri), timeout=.05).json()
logger.info(tr)
availability_zone_ = tr['AvailabilityZone']
d = {'az': availability_zone_}

cw_client = boto3.client('cloudwatch')
ssm_client = boto3.client('ssm')
secret_id = ssm_client.get_parameter(Name=TradeParameterName.TRADE_ORDER_API_SECRET_ID.value)['Parameter']['Value']
confirms_endpoint = ssm_client.get_parameter(Name=TradeParameterName.TRADE_CONFIRMS_ENDPOINT.value)['Parameter'][
    'Value']
rds_proxy_endpoint = ssm_client.get_parameter(Name=TradeParameterName.TRADE_RDS_PROXY_ENDPOINT.value)['Parameter'][
    'Value']
rds_ro_proxy_endpoint = ssm_client.get_parameter(Name=TradeParameterName.TRADE_RDS_PROXY_READ_ONLY_ENDPOINT.value)[
    'Parameter']['Value']
secrets_cache = None
db_engine = None
ro_db_engine = None


def get_db_credentials_from_cache() -> str:
    """
    Uses AWS Secrets Manager and Secret Cache to retrieve database credentials with multi-user rotation strategy.
    Turns a hard dependency into a soft dependency by caching the credentials.
    """
    global secrets_cache, secret_id
    try:
        if secrets_cache is None:
            boto_session = boto3.session.Session()
            secrets_client = boto_session.client("secretsmanager")
            cache_config = SecretCacheConfig(max_cache_size=100, secret_refresh_interval=300)
            secrets_cache = SecretCache(config=cache_config, client=secrets_client)
    except ClientError as e:
        raise e
    return secrets_cache.get_secret_string(secret_id=secret_id)


def load_db_engine() -> None:
    """Load and cache read-write SQLAlchemy database connection. Refreshes credentials on each invocation."""
    global db_engine
    secret = json.loads(get_db_credentials_from_cache())
    host_ = secret['host']
    # host_ = rds_proxy_endpoint
    password = urllib.parse.quote_plus(secret['password'])
    db_conn_string = f"postgresql://{secret['username']}:{password}@{host_}:{secret['port']}/{secret['dbname']}?sslmode=require"
    # if you are having trouble recreating connection pool exhaustion,
    # try creating the db engine with the default timeout so slower connections don't timeout at 100ms
    #db_engine = create_engine(db_conn_string, pool_size=10)
    db_engine = create_engine(db_conn_string, pool_size=10, connect_args={"options": "-c statement_timeout=100"})


def load_ro_db_engine() -> None:
    """Load and cache read-only SQLAlchemy database connection. Refreshes credentials on each invocation."""
    global ro_db_engine
    secret = json.loads(get_db_credentials_from_cache())
    host_ = secret['host'].replace("stock.cluster", "stock.cluster-ro")
    # host_ = rds_ro_proxy_endpoint
    password = urllib.parse.quote_plus(secret['password'])
    db_conn_string = f"postgresql://{secret['username']}:{password}@{host_}:{secret['port']}/{secret['dbname']}?sslmode=require"
    ro_db_engine = create_engine(db_conn_string, pool_size=10)


def connection_aware(func):
    """
    A decorator to refresh database connections if failing to connect after rotation
    indicated by a sqlalchemy.exc.OperationalError wrapping a psycopg2.OperationalError.
    This decorator only retries once, and it does a full refresh of the database credentials and SQLAlchemy engine.
    Decorate any functions that make a database connection to gracefully handle failures due to password change
    or intermittent connectivity issues.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc.OperationalError as e:
            logger.exception("db credentials reloaded, retrying", e, extra=d)
            load_db_engine()
            load_ro_db_engine()
            return func(*args, **kwargs)

    return wrapper


def current_price(ticker: str, session: Session) -> Symbol:
    """
    Lookup current stock price from the database.
    In a real system, this database would be connected to the stock stream; it is static for this example.
    """
    logger.info("Checking Stock Price", extra=d)
    statement = select(Symbol).where(Symbol.ticker == ticker)
    symbol_record = session.scalars(statement).one()
    logger.info("Here's your symbol: {}".format(symbol_record.as_dict()), extra=d)
    return symbol_record


def get_customer(customer_id: str, session: Session) -> Customer:
    """
    Lookup customer from the database, add a semi-random cash balance.
    In a real system, a customer would have a cash balance or deposit accounts for purchasing with.
    """
    logger.info("Checking Customer Balance", extra=d)
    statement = select(Customer).where(Customer.id == customer_id)
    customer_record = session.scalars(statement).one()
    logger.info("Here's your customer: {}".format(customer_record.as_dict()), extra=d)
    return customer_record


def place_order(customer: Customer, symbol: Symbol, json_request, session: Session) -> Activity:
    """
    create a new trade record in the database making it ready to place with the exchange
    """
    logger.info("JSON request before insert: {}".format(json_request), extra=d)
    activity = Activity()
    activity.customer_id = customer.id
    activity.symbol_ticker = symbol.id
    activity.status = TradeState.submitted
    activity.type = TransactionType(json_request["transaction_type"])
    activity.share_count = json_request["share_count"]
    activity.current_price = json_request["current_price"]
    activity.request_id = json_request["request_id"]
    session.add(activity)
    return activity


def put_count_metric(metric_name: str):
    # Todo, this can be improved by using the EMF, https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html
    cw_client.put_metric_data(
        Namespace="TradeOrder",
        MetricData=[{
            "MetricName": metric_name,
            "Dimensions": [
                {
                    "Name": "AvailabilityZone",
                    "Value": availability_zone_
                }
            ],
            "Value": 1,
            "Unit": "Count"
        }]
    )


@circuit(failure_threshold=5, expected_exception=ConfirmsUnavailableError, recovery_timeout=60)
def execute_trade(activity: dict) -> Response:
    response = requests.post("http://{}/confirm-trade/".format(confirms_endpoint), json=activity, timeout=.3)
    logger.info(f"response: {response.status_code} for {response.reason}", extra=d)
    if "ConfirmsMaintenanceError" in response.reason:
        raise ConfirmsUnavailableError(response.json()) # triggers circuit breaker
    response.raise_for_status()  # triggers retries
    return response


app = Flask(__name__)
load_db_engine()
load_ro_db_engine()


@app.route("/trade/", methods=["POST"])
@connection_aware
def trade():
    put_count_metric("TradeOrderRequested")
    json_data = request.get_json()
    logger.debug("request to trade: {}".format(json_data), extra=d)

    try:
        with Session(ro_db_engine) as ro_session:
            symbol_record = current_price(json_data['ticker'], ro_session)
            logger.debug("symbol_record: {}".format(symbol_record.as_dict()), extra=d)
            customer = get_customer(json_data['customer_id'], ro_session)
            logger.debug("current_price: {}".format(json_data['current_price']), extra=d)

        with Session(db_engine) as session:
            session.expire_on_commit = False
            activity = place_order(customer=customer,
                                   symbol=symbol_record,
                                   json_request=json_data,
                                   session=session)
            session.commit()  # idempotent from here forward, db constraint on unique request id. Tested?
            balance = float(random.randrange(5000, 1000000))
            cost = symbol_record.close * float(json_data['share_count'])

            logger.debug("current balance: {}, trade cost: {}".format(balance, cost), extra=d)

            circuit_state = CircuitBreakerMonitor.get('execute_trade').state
            if circuit_state == "closed" \
                    and float(symbol_record.close) == float(json_data['current_price']) \
                    and balance > cost:
                activity.status = TradeState.pending
                session.commit()
                # result = retry_call(execute_trade, fargs=[activity.as_dict()], fkwargs={"info": "ip"}, tries=3, backoff=0.2, jitter=0.5)
                result = execute_trade(activity.as_dict())
                logger.info("exchange call result: {}".format(result), extra=d)

                activity.status = TradeState.filled
                session.commit()
                put_count_metric("TradeOrderFilled")
            elif circuit_state == "open":
                logger.info("Circuit open, aborted because orders cannot be filled.", extra=d)
                activity.status = TradeState.aborted
                session.commit()
                put_count_metric("TradeOrderAborted")
            else:
                logger.info("Not enough funds to execute trade or invalid price request, rejecting.", extra=d)
                activity.status = TradeState.rejected
                session.commit()
                put_count_metric("TradeOrderRejected")
    except Exception as e:
        logger.error(f"Processing failed for {activity}", extra=d)
        logger.error(e, extra=d)
        activity.status = TradeState.aborted
        session.commit()
        put_count_metric("TradeOrderAborted")
    return activity.as_dict()


@app.route("/", methods=["GET"])
def health():
    """
    A simple health check for the load balancers that indicates Flask application is up and running.
    """
    logger.info("Call to / it's OK", extra=d)
    state = CircuitBreakerMonitor.get('execute_trade').state
    if state == "open":
        put_count_metric(metric_name="ConfirmsCircuitOpen")
    elif state == "closed":
        put_count_metric(metric_name="ConfirmsCircuitClosed")
    else:
        put_count_metric(metric_name="ConfirmsCircuitUnknown")

    return "OK"


@app.route("/exchange-health/", methods=["GET"])
def deep_health():
    """
    A deep health check that confirms the order service can successfully connect to the trade confirms service.
    """
    logger.info("Call to /exchange-health/", extra=d)
    response = requests.get("http://{}/exchange-health/".format(confirms_endpoint))
    logger.info(response, extra=d)
    return Response(response.text, status=response.status_code, mimetype="text/plain")


@app.route("/db-health/", methods=["GET"])
# @connection_aware
def db_health():
    """
    A database health check that confirms the order service is successfully connecting to the database.
    """
    logger.info("Checking DB connection", extra=d)
    with Session(db_engine) as session:
        statement = select(Customer).where(Customer.first_name == "kevin")
        customer = session.scalars(statement).one()
    logger.info("Here's your customer: {}".format(customer.as_dict()), extra=d)
    return customer.as_dict()


@app.route("/db-stress/", methods=["GET"])
# @connection_aware
def db_stress():
    """
    issue long-running queries to the single writer instance to consume database connections, lead to exhaustion
    """
    logger.info("Stress consuming a DB connection", extra=d)
    for i in range(1, 25):
        with (Session(ro_db_engine) as session):
            result = session.execute(text("select pg_sleep(.1);"))
            logger.info(f"Stress Query result: {result}", extra=d)
    return {"result": "slow query complete"}


@app.route("/region-az/", methods=["GET"])
def region_az():
    return availability_zone_


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=80)
    logger.info("Started Order Flask app", extra=d)
