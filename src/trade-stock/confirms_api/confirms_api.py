#!/bin/python3
from flask import Flask, Response
from flask_api import status
from trade_parameter_name import TradeParameterName
import boto3
import logging
from pythonjsonlogger import jsonlogger
import time
import requests
import os


class ConfirmsMaintenanceError(RuntimeError):
    pass


class ConfirmsProcessingException(RuntimeError):
    pass


app = Flask(__name__)
count: int = 0

json_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(levelname)s %(lineno)d %(asctime)s %(task)-32s %(az)-10s - %(message)s')
json_handler.setFormatter(formatter)
logging.basicConfig(handlers=[json_handler], level=logging.INFO)
logger = logging.getLogger('confirms')

meta_data_uri = os.environ.get('ECS_CONTAINER_METADATA_URI_V4')
tr = requests.get("{}/task".format(meta_data_uri)).json()
availability_zone_ = tr['AvailabilityZone']
d = {'az': availability_zone_}


def get_exchange_status(request_count: int, force: bool = False) -> str:
    """
    Get exchange status is a fault injection for the simulated 3rd party off-platform confirms service.
    When the exchange status is not OPEN, the service will hard fail.
    Test full outages with circuit breakers and graceful degradation.
    """
    global exchange_status
    if force or request_count % 10 == 0:
        ssm_client = boto3.client('ssm')
        exchange_status = ssm_client.get_parameter(
            Name=TradeParameterName.TRADE_CONFIRMS_EXCHANGE_STATUS.value)['Parameter']['Value']
    return exchange_status


def get_exchange_glitch_factor(request_count: int, force: bool = False) -> str:
    """
    Get glitch_factor is a fault injection for the simulated third-party off-platform confirms service.
    When the glitch_factor is greater than 0, the service will return intermittent errors, or gray failures.
    Test non-deterministic/intermittent error behavior like network issues, impaired instances, and resource exhaustion.
    """
    global glitch_factor
    if force or request_count % 10 == 0:
        ssm_client = boto3.client('ssm')
        glitch_factor = ssm_client.get_parameter(
            Name=TradeParameterName.TRADE_CONFIRMS_GLITCH_FACTOR.value)['Parameter']['Value']
    return glitch_factor


exchange_status = get_exchange_status(0, True)
glitch_factor = get_exchange_glitch_factor(0, True)


@app.route("/")
def health():
    """
    A simple health check for the load balancers that indicates Flask application is up and running.
    """
    logger.info("Call to / it's OK", extra=d)
    return Response(response="OK", status=status.HTTP_200_OK)


@app.route("/exchange-health/")
def exchange_health():
    """
    A deep health check indicates if the exchange is open for trading running and running normally.
    """
    response_message = "Exchange is {} and glitch factor is {}.".format(exchange_status, glitch_factor)
    available = exchange_status == "AVAILABLE" or glitch_factor == "OFF"
    response_status = status.HTTP_200_OK if available else status.HTTP_503_SERVICE_UNAVAILABLE
    logger.info("Call to /exchange_health/ response is {}".format(response_message), extra=d)
    return Response(response_message, status=response_status, mimetype="text/plain")


@app.route("/confirm-trade/", methods=["POST", "GET", "PUT"])
def confirm_trade():
    """
    Simulated placing a trade order with a third-party off-platform exchange.
    Demonstrates glitches and outages for resilience chaos testing.
    """
    global count
    count += 1
    try:
        if get_exchange_status(count) != "AVAILABLE":
            raise ConfirmsMaintenanceError("ConfirmsMaintenanceError: Exchange is not available, come back later!")
        if get_exchange_glitch_factor(count) == "ON" and count % 3 == 0:
            raise ConfirmsProcessingException("ConfirmsProcessingException: Processing error, please try again...")
    except ConfirmsMaintenanceError as e:
        logger.error("ConfirmsMaintenanceError:  Exchange status: {}".format(exchange_status), extra=d)
        return Response(e.__str__(), status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except ConfirmsProcessingException as e:
        logger.error("ConfirmsProcessingException: glitch_factor is: {}".format(glitch_factor), extra=d)
        return Response(e.__str__(), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    time.sleep(.1)  # delay to simulate doing some work

    return Response("Trade Confirmed", status=status.HTTP_200_OK)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=80)
    logger.info("Started Confirms Flask app", extra=d)
