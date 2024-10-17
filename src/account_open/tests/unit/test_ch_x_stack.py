import aws_cdk as core
import aws_cdk.assertions as assertions

from ch_x.ch_x_stack import ChXStack


# example tests. To run these tests, uncomment this file along with the example
# resource in stacks/process_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ChXStack(app, "ch-x")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
