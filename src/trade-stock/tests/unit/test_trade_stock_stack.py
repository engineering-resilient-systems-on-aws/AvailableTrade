import aws_cdk as core
import aws_cdk.assertions as assertions

from trade_stock.trade_stock_stack import TradeStockStack


# example tests. To run these tests, uncomment this file along with the example
# resource in trade_stock/trade_stock_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = TradeStockStack(app, 'trade-stock')
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
