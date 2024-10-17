import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_rum as rum,
    aws_cognito as cognito,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch
)
from constructs import Construct


class FrontEndRumStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, domain_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rum_identity_pool = cognito.CfnIdentityPool(self, 'FrontEndRumPool', allow_unauthenticated_identities=True)
        rum_federated_role = iam.Role(self, "RumRole",
                                      assumed_by=iam.FederatedPrincipal("cognito-identity.amazonaws.com", {
                                          'StringEquals': {
                                              "cognito-identity.amazonaws.com:aud": rum_identity_pool.ref
                                          },
                                          "ForAnyValue:StringLike": {
                                              "cognito-identity.amazonaws.com:amr": "unauthenticated"
                                          }
                                      }, assume_role_action="sts:AssumeRoleWithWebIdentity"))

        local_application_monitor_name = "local_resilient_front_end"
        deployed_application_monitor_name = "deployed_resilient_front_end"
        rum_federated_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW, actions=['rum:PutRumEvents'],
            resources=[f'arn:aws:rum:{self.region}:{self.account}:appmonitor/{local_application_monitor_name}',
                       f'arn:aws:rum:{self.region}:{self.account}:appmonitor/{deployed_application_monitor_name}'])
        )

        cognito.CfnIdentityPoolRoleAttachment(self, 'FrontEndRumRole', identity_pool_id=rum_identity_pool.ref,
                                              roles={
                                                  "unauthenticated": rum_federated_role.role_arn
                                              }
                                              )

        local = rum.CfnAppMonitor(self, "FrontEndRumMonitorLocal", domain='localhost',
                                  name=local_application_monitor_name,
                                  app_monitor_configuration=rum.CfnAppMonitor.AppMonitorConfigurationProperty(
                                      allow_cookies=True,
                                      enable_x_ray=True,
                                      session_sample_rate=1,
                                      telemetries=['errors', 'performance', 'http'],
                                      identity_pool_id=rum_identity_pool.ref,
                                      guest_role_arn=rum_federated_role.role_arn
                                  ),
                                  cw_log_enabled=True)
        cdk.CfnOutput(self, "LocalRum-AppMonitorId", value=local.attr_id)

        local_js_error_metric = cloudwatch.Metric(metric_name="JsErrorCount", namespace="AWS/RUM",
                                                  dimensions_map={"application_name": local.name})
        cloudwatch.Alarm(self, "LocalRumJavascriptErrorsAlarm", metric=local_js_error_metric,
                         threshold=5,
                         evaluation_periods=3,
                         datapoints_to_alarm=1)      

        hosted_domain = False          
        
        if len(domain_name) > 1 and "cloudfront" not in domain_name:
            hosted_domain = True

        if hosted_domain:            
            deployed = rum.CfnAppMonitor(self, "FrontEndRumMonitor", domain=domain_name,
                                     name=deployed_application_monitor_name,
                                     app_monitor_configuration=rum.CfnAppMonitor.AppMonitorConfigurationProperty(
                                         allow_cookies=True,
                                         enable_x_ray=True,
                                         session_sample_rate=1,
                                         telemetries=['errors', 'performance', 'http'],
                                         identity_pool_id=rum_identity_pool.ref,
                                         guest_role_arn=rum_federated_role.role_arn
                                     ),
                                     cw_log_enabled=True)
            cdk.CfnOutput(self, "DeployedRum-AppMonitorId", value=deployed.attr_id)   
            prod_js_error_metric = cloudwatch.Metric(metric_name="JsErrorCount", namespace="AWS/RUM",
                                                 dimensions_map={"application_name": deployed.name})
            cloudwatch.Alarm(self, "ProdRumJavascriptErrorsAlarm", metric=prod_js_error_metric,
                         threshold=5,
                         evaluation_periods=3,
                         datapoints_to_alarm=1)                 

