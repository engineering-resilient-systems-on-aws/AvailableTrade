export ORDER_ENDPOINT=$(aws ssm get-parameter --name trade_order_endpoint \
--region us-east-1 | jq -r .Parameter.Value)
for i in {1..100}; do   time curl $ORDER_ENDPOINT/db-health/; done
