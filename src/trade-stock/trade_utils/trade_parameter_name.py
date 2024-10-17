from enum import Enum


class TradeParameterName(Enum):
    TRADE_CONFIRMS_ENDPOINT = 'trade_confirms_endpoint'
    TRADE_CONFIRMS_EXCHANGE_STATUS = 'trade_confirms_exchange_status'
    TRADE_CONFIRMS_GLITCH_FACTOR = 'trade_confirms_glitch_factor'
    TRADE_ORDER_ENDPOINT = 'trade_order_endpoint'
    TRADE_ORDER_API_ENDPOINT = 'trade_order_global_endpoint'
    TRADE_RDS_PROXY_ENDPOINT = 'trade_rds_proxy_endpoint'
    TRADE_RDS_PROXY_READ_ONLY_ENDPOINT = 'trade_rds_proxy_read_only_endpoint'
    TRADE_DATABASE_SECRET_ID = 'trade_db_secret_id'
    TRADE_ORDER_API_SECRET_ID = 'trade_order_api_secret_id'
    TRADE_RDS_SECONDARY_CLUSTER_ARN = 'trade_rds_secondary_cluster_arn'
