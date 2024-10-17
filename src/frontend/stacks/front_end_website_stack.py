from aws_cdk import (
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_cloudfront as cloudfront,
    aws_certificatemanager as acm,
    aws_wafv2 as waf,
    aws_iam as iam,
    aws_cloudwatch as cw,
    aws_ssm as ssm,
)
import aws_cdk as cdk
from constructs import Construct
from aws_solutions_constructs.aws_cloudfront_s3 import CloudFrontToS3
from aws_solutions_constructs.aws_wafwebacl_cloudfront import WafwebaclToCloudFront
import os


class FrontEndWebsiteStack(cdk.Stack):

    def __init__(self, scope: Construct, id: str, domain_name: str, secondary_region: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
    
        distribution = None        
        hosted_domain = False

        website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            versioned=True,
            bucket_name=f'website-{self.account}-{self.region}',
            removal_policy=cdk.RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True,
            server_access_logs_bucket=s3.Bucket(self,f"ServerAccessLogsBucket-{self.account}-{self.region}", enforce_ssl=True)
        )

        js_rewrite_function = '''
        function handler(event) {
            var request = event.request;
            var uri = request.uri;        
            if (!uri.includes('.')) {
                request.uri = '/';
            }        
            return request;
        }
        '''            

        if len(domain_name) > 1 and "cloudfront" not in domain_name:
            hosted_domain = True

        if hosted_domain:
            hosted_zone = route53.HostedZone.from_lookup(self, "HostedZone", domain_name=domain_name)
            api_account_name = "api-account." + domain_name
            api_trade_name = "api-trade." + domain_name

            certificate = acm.Certificate(self, "Certificate",
                                        domain_name=domain_name,
                                        validation=acm.CertificateValidation.from_dns(hosted_zone),
                                        subject_alternative_names=[domain_name, api_account_name, api_trade_name],
                                        )

            # Write the certificate arn to a ssm parameter named CertificateARN
            ssm.StringParameter(self, "CertificateARN",
                                                       parameter_name="CertificateARN",
                                                       string_value=certificate.certificate_arn,
                                                       )
            content_security_policy_content = f"default-src 'self'; object-src data: w3.org/svg/2000 https://{domain_name}; img-src data: w3.org/svg/2000 https://{domain_name}; style-src-elem https://cdn.jsdelivr.net https://{domain_name}; script-src-elem https://code.jquery.com https://cdn.jsdelivr.net https://{domain_name}; font-src https://cdn.jsdelivr.net; connect-src https://api-account.{domain_name} https://api-trade.{domain_name} https://cognito-identity.us-east-1.amazonaws.com https://dataplane.rum.us-east-1.amazonaws.com;"
            distribution = CloudFrontToS3(self, 'CloudFrontToS3',
                                        existing_bucket_obj=website_bucket,
                                        cloud_front_distribution_props={
                                            "default_behavior": {
                                                "viewer_protocol_policy": cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                                                "compress": True,
                                                "allowed_methods": cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                                                "cached_methods": cloudfront.CachedMethods.CACHE_GET_HEAD,
                                                "cache_policy": cloudfront.CachePolicy.CACHING_OPTIMIZED,
                                                # for whatever reason this isn't working,
                                                # function creates but not associates, so manual step
                                                "function_associations": [cloudfront.FunctionAssociation(
                                                    event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                                                    function=cloudfront.Function(self, "JsRefreshHandler",
                                                                                code=cloudfront.FunctionCode.from_inline(js_rewrite_function),
                                                                                runtime=cloudfront.FunctionRuntime.JS_2_0)
                                                )]
                                            },
                                            "domainNames": [domain_name, api_account_name, api_trade_name],
                                            "certificate": certificate,
                                        },
                                        insert_http_security_headers=False,
                                        response_headers_policy_props={
                                            "security_headers_behavior": {
                                                "content_security_policy": cloudfront.ResponseHeadersContentSecurityPolicy(
                                                    override=True,
                                                    content_security_policy=content_security_policy_content),
                                                "strict_transport_security": cloudfront.ResponseHeadersStrictTransportSecurity(
                                                    access_control_max_age=cdk.Duration.seconds(600),
                                                    include_subdomains=True, override=True
                                                ),
                                                "frame_options": cloudfront.ResponseHeadersFrameOptions(
                                                    frame_option=cloudfront.HeadersFrameOption.DENY, override=True),
                                                "xss_protection": cloudfront.ResponseHeadersXSSProtection(protection=True,
                                                                                                            mode_block=True,
                                                                                                            override=True)
                                            }

                                        })            
        else:
            # TODO: need to account for primary region API gateway endpoints
            ## content_security_policy_content = f"default-src 'self'; object-src data: w3.org/svg/2000 https://{domain_name}; img-src data: w3.org/svg/2000 https://{domain_name}; style-src-elem https://cdn.jsdelivr.net https://{domain_name}; script-src-elem https://code.jquery.com https://cdn.jsdelivr.net https://{domain_name}; font-src https://cdn.jsdelivr.net; connect-src API_GATEWAY_REGIONAL_ACCOUNTOPEN API_GATEWAY_REGIONAL_TRADESTOCK https://cognito-identity.us-east-1.amazonaws.com https://dataplane.rum.us-east-1.amazonaws.com;"
            content_security_policy_content = f"default-src 'self'; object-src data: w3.org/svg/2000 https://{domain_name}; img-src data: w3.org/svg/2000 https://{domain_name}; style-src-elem https://cdn.jsdelivr.net https://{domain_name}; script-src-elem https://code.jquery.com https://cdn.jsdelivr.net https://{domain_name}; font-src https://cdn.jsdelivr.net; connect-src API_GATEWAY_REGIONAL_ACCOUNTOPEN API_GATEWAY_REGIONAL_TRADESTOCK https://cognito-identity.us-east-1.amazonaws.com https://dataplane.rum.us-east-1.amazonaws.com;"
            distribution = CloudFrontToS3(self, 'CloudFrontToS3',
                                        existing_bucket_obj=website_bucket,
                                        cloud_front_distribution_props={
                                            "default_behavior": {
                                                "viewer_protocol_policy": cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                                                "compress": True,
                                                "allowed_methods": cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                                                "cached_methods": cloudfront.CachedMethods.CACHE_GET_HEAD,
                                                "cache_policy": cloudfront.CachePolicy.CACHING_OPTIMIZED,
                                                # for whatever reason this isn't working,
                                                # function creates but not associates, so manual step
                                                "function_associations": [cloudfront.FunctionAssociation(
                                                    event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                                                    function=cloudfront.Function(self, "JsRefreshHandler",
                                                                                code=cloudfront.FunctionCode.from_inline(js_rewrite_function),
                                                                                runtime=cloudfront.FunctionRuntime.JS_2_0)
                                                )]
                                            },
                                        },
                                        insert_http_security_headers=False,
                                        response_headers_policy_props={
                                            "security_headers_behavior": {
                                                "content_security_policy": cloudfront.ResponseHeadersContentSecurityPolicy(
                                                    override=True,
                                                    content_security_policy=content_security_policy_content),
                                                "strict_transport_security": cloudfront.ResponseHeadersStrictTransportSecurity(
                                                    access_control_max_age=cdk.Duration.seconds(600),
                                                    include_subdomains=True, override=True
                                                ),
                                                "frame_options": cloudfront.ResponseHeadersFrameOptions(
                                                    frame_option=cloudfront.HeadersFrameOption.DENY, override=True),
                                                "xss_protection": cloudfront.ResponseHeadersXSSProtection(protection=True,
                                                                                                            mode_block=True,
                                                                                                            override=True)
                                            }

                                        })

        replication_role = iam.Role(
            self,
            "ReplicationRole",
            assumed_by=iam.ServicePrincipal("s3.amazonaws.com"),
            path="/service-role/",

        )

        replication_role.add_to_policy(
            iam.PolicyStatement(
                resources=[website_bucket.bucket_arn],
                actions=["s3:GetReplicationConfiguration", "s3:ListBucket"],
            )
        )

        replication_role.add_to_policy(
            iam.PolicyStatement(
                resources=[website_bucket.arn_for_objects("*")],
                actions=[
                    "s3:GetObjectVersion",
                    "s3:GetObjectVersionAcl",
                    "s3:GetObjectVersionForReplication",
                    "s3:GetObjectLegalHold",
                    "s3:GetObjectVersionTagging",
                    "s3:GetObjectRetention",
                ],
            )
        )

        replication_role.add_to_policy(
            iam.PolicyStatement(
                resources=[f"arn:aws:s3:::website-{self.account}-{secondary_region}/*"],
                actions=[
                    "s3:ReplicateObject",
                    "s3:ReplicateDelete",
                    "s3:ReplicateTags",
                    "s3:GetObjectVersionTagging",
                    "s3:ObjectOwnerOverrideToBucketOwner",
                ],
            )
        )

        website_bucket.node.default_child.replication_configuration = s3.CfnBucket.ReplicationConfigurationProperty(
            role=replication_role.role_arn,
            rules=[
                s3.CfnBucket.ReplicationRuleProperty(
                    destination=s3.CfnBucket.ReplicationDestinationProperty(
                        bucket=f"arn:aws:s3:::website-{self.account}-{secondary_region}",
                    ),
                    status="Enabled"
                )
            ],
        )

        waf_rules = []
        aws_managed_rules = waf.CfnWebACL.RuleProperty(
            name="AWS-AWSManagedRulesCommonRuleSet",
            priority=1,
            override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    vendor_name="AWS",
                    excluded_rules=[
                        waf.CfnWebACL.ExcludedRuleProperty(name="SizeRestrictions_BODY")
                    ],
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="aws_common_rules",
                sampled_requests_enabled=True,
            ),
        )
        waf_rules.append(aws_managed_rules)

        aws_anon_ip_list = waf.CfnWebACL.RuleProperty(
            name="AWS-AWSManagedRulesAnonymousIpList",
            priority=2,
            override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name="AWSManagedRulesAnonymousIpList",
                    vendor_name="AWS",
                    excluded_rules=[],
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="aws_anonymous",
                sampled_requests_enabled=True,
            ),
        )
        waf_rules.append(aws_anon_ip_list)

        aws_ip_rep_list = waf.CfnWebACL.RuleProperty(
            name="AWS-AWSManagedRulesAmazonIpReputationList",
            priority=3,
            override_action=waf.CfnWebACL.OverrideActionProperty(none={}),
            statement=waf.CfnWebACL.StatementProperty(
                managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                    name="AWSManagedRulesAmazonIpReputationList",
                    vendor_name="AWS",
                    excluded_rules=[],
                )
            ),
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="aws_reputation",
                sampled_requests_enabled=True,
            ),
        )
        waf_rules.append(aws_ip_rep_list)

        # Create a new global WAF rule group
        rule_group = waf.CfnRuleGroup(
             self,
             "RuleGroup",
             capacity=10,
             name="RateLimitRuleGroup",
             description="Rate Limit Rule Group",
             scope="CLOUDFRONT",
             rules=[waf.CfnRuleGroup.RuleProperty(
                    name="RateLimitRule",
                    priority=4,
                    statement=waf.CfnRuleGroup.StatementProperty(
                        rate_based_statement=waf.CfnRuleGroup.RateBasedStatementProperty(
                            limit=100,
                            evaluation_window_sec=60,
                            aggregate_key_type="IP",
                            scope_down_statement=None
                        )
                    ),
                    action=waf.CfnRuleGroup.RuleActionProperty(
                        block={}
                    ),
                    visibility_config=waf.CfnRuleGroup.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitMetric",
                    ),
                ) 
             ],
             visibility_config=waf.CfnRuleGroup.VisibilityConfigProperty(
                  cloud_watch_metrics_enabled=True,
                  metric_name="RateLimitMetric",
                  sampled_requests_enabled=True,
                  ),
        )   

        web_acl = waf.CfnWebACL(
            self,
            "CfnWebACL",
            default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
            scope='CLOUDFRONT',
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="web_acl",
                sampled_requests_enabled=True,
            ),
            rules=waf_rules,
        )   

        # Create a CloudWatch alarm for the rate limiting rule
        cw.CfnAlarm(
            self, "WAFRateLimitAlarm",
            alarm_description="Alarm for rate limiting rule",
            metric_name="BlockedRequests",        
            namespace="AWS/WAFV2",
            period=10,
            evaluation_periods=1,
            statistic="Average",
            threshold=100,
            comparison_operator="GreaterThanThreshold",
            dimensions=[
                cw.CfnAlarm.DimensionProperty(
                    name="Rule",
                    value="RateLimitMetric",
                ),
                cw.CfnAlarm.DimensionProperty(
                    name="RuleGroup",
                    value="RateLimitRuleGroup",
                ),
            ],
            alarm_actions=[],
            ok_actions=[],
        )        

        WafwebaclToCloudFront(self, "WafToDistributiuon",
                              existing_cloud_front_web_distribution=distribution.cloud_front_web_distribution,
                              existing_webacl_obj=web_acl)

        source_dir = os.path.join(os.path.dirname("."), "website/dist")
        s3deploy.BucketDeployment(self, "BucketDeployment",
                                  sources=[s3deploy.Source.asset(source_dir)],
                                  destination_bucket=website_bucket)
        if hosted_domain:
            route53.ARecord(self, "ARecord",
                            zone=hosted_zone,
                            target=route53.RecordTarget.from_alias(
                                targets.CloudFrontTarget(distribution.cloud_front_web_distribution)),
                            )

        cdk.CfnOutput(self, "WebsiteURL", value=f"https://{domain_name}")
        cdk.CfnOutput(self, "CloudFrontDomainName", value=distribution.cloud_front_web_distribution.domain_name)
        cdk.CfnOutput(self, "CloudFrontDistributionID", value=distribution.cloud_front_web_distribution.distribution_id)        
