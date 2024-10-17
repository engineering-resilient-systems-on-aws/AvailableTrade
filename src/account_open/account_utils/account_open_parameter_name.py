from enum import Enum


class AccountOpenParameterName(Enum):
    ACCOUNT_OPEN_REGIONAL_ENDPOINT = 'AccountOpenRegionalEndpoint_'  # to use this append region name
    ACCOUNT_OPEN_GLOBAL_ENDPOINT = 'AccountOpenGlobalEndpoint'  # to use this, you need a domain and hosted zone
