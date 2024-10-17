export ORDER_ENDPOINT=$(aws ssm get-parameter --name trade_order_endpoint \
 --region us-east-1 | jq -r .Parameter.Value)
curl $ORDER_ENDPOINT/db-health/
