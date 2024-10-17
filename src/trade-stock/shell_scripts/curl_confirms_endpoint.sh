export CONFIRMS_ENDPOINT=$(aws ssm get-parameter \
  --name trade_confirms_endpoint --region us-east-1 | jq -r .Parameter.Value)
curl $CONFIRMS_ENDPOINT
