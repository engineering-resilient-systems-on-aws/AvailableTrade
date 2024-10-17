import aws_cdk as core
import aws_cdk.assertions as assertions

from front_end.front_end_stack import FrontEndStack

# example tests. To run these tests, uncomment this file along with the example
# resource in front_end/front_end_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = FrontEndStack(app, "front-end")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
