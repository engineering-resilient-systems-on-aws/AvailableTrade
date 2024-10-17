#!/usr/bin/env python3
import os
import aws_cdk as cdk
from aws_cdk import (
    aws_rds as rds,
)
from trade_stock.vpc_stack import VpcStack
from trade_stock.trade_order_stack import TradeOrderStack
from trade_stock.trade_confirms_stack import TradeConfirmsStack
from trade_stock.public_api_stack import PublicApiStack
from trade_stock.trade_database import TradeDatabaseStack
from trade_stock.trade_database_secondary_stack import TradeDatabaseSecondaryStack

app = cdk.App()
account = os.getenv('AWS_ACCOUNT_ID')
primary_region = os.getenv('AWS_PRIMARY_REGION')
secondary_region = os.getenv('AWS_SECONDARY_REGION')

primary_env = cdk.Environment(account=account, region=primary_region)
primary_vpc_stack = VpcStack(app, "TradeVpcStackPrimary", env=primary_env)
primary_database = TradeDatabaseStack(app, "TradeDatabaseStackPrimary", env=primary_env,
                                      vpc=primary_vpc_stack.vpc, secondary_region=secondary_region)
primary_order_api_stack = TradeOrderStack(app, "TradeOrderStackPrimary", env=primary_env,
                                          vpc=primary_vpc_stack.vpc,
                                          task_role=primary_database.task_role)
primary_confirms_api_stack = TradeConfirmsStack(app, "TradeConfirmsStackPrimary", env=primary_env,
                                                vpc=primary_vpc_stack.vpc)
primary_api = PublicApiStack(app, "TradeStockApiGatewayStackPrimary", env=primary_env,
                             private_lb=primary_order_api_stack.private_lb,
                             resource_name="trade")

secondary_env = cdk.Environment(account=account, region=secondary_region)
secondary_vpc_stack = VpcStack(app, "TradeVpcStackSecondary", env=secondary_env)
secondary_database = TradeDatabaseSecondaryStack(app, "TradeDatabaseStackSecondary", env=secondary_env,
                                                 vpc=secondary_vpc_stack.vpc)

secondary_confirms_api_stack = TradeConfirmsStack(app, "TradeConfirmsStackSecondary", env=secondary_env,
                                                  vpc=secondary_vpc_stack.vpc)
secondary_order_api_stack = TradeOrderStack(app, "TradeOrderStackSecondary", env=secondary_env,
                                            vpc=secondary_vpc_stack.vpc,
                                            task_role=secondary_database.task_role)
secondary_api = PublicApiStack(app, "TradeStockApiGatewayStackSecondary", env=secondary_env,
                               private_lb=secondary_order_api_stack.private_lb,
                               resource_name="trade")

app.synth()
