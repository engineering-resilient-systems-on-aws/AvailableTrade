import logging

import circuitbreaker
from circuitbreaker import circuit
import retry
import requests
from pythonjsonlogger import jsonlogger


# decorate with circuit breaker, it will see the failures. Once there are enough failures the circuit will close
@circuit(failure_threshold=5, expected_exception=RuntimeError)
def do_stuff() -> requests.Response:
    print("trying to get stock")
    response = requests.get("https://ipinfo.io/shit")
    if response.status_code != 200:
        raise RuntimeError("took a shit")
    return response


print(circuitbreaker.CircuitBreakerMonitor.get_circuits())
print(circuitbreaker.CircuitBreakerMonitor.get_closed())
print(circuitbreaker.CircuitBreakerMonitor.get_open())
# monitor the circuits, if it's open, don't even bother.
try:
    print("trying")
    response = retry.api.retry_call(do_stuff, backoff=0, jitter=0.1, tries=2)
    print(response)
except:
    pass

try:
    print("trying")
    response = retry.api.retry_call(do_stuff, backoff=0, jitter=0.1, tries=2)
    print(response)
except:
    pass

try:
    print("trying")
    response = retry.api.retry_call(do_stuff, backoff=0, jitter=0.1, tries=2)
    print(response)
except:
    pass


try:
    print("trying")
    response = retry.api.retry_call(do_stuff, backoff=0, jitter=0.1, tries=2)
    print(response)
except:
    pass

print(circuitbreaker.CircuitBreakerMonitor.get('do_stuff').open_until)


@circuit(failure_threshold=2, expected_exception=RuntimeError)
def is_registered():
    print("make it stop")


print(circuitbreaker.CircuitBreakerMonitor.get('is_registered').state)



d = {'task': 'foo', 'az': 'us-east-1'}


json_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(levelname)s %(lineno)d %(asctime)s %(task)-32s %(az)-10s - %(message)s')
json_handler.setFormatter(formatter)
logging.basicConfig(handlers=[json_handler], level=logging.INFO)
logger = logging.getLogger('orders')
logger.info("logs in json format", extra=d)