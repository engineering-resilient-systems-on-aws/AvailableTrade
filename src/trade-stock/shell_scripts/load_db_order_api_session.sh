export API_SECRET_ID=$(aws ssm get-parameter --name trade_order_api_secret_id \
 --region us-east-1 | jq -r .Parameter.Value)
export API_SECRET=`aws secretsmanager get-secret-value \
 --secret-id $API_SECRET_ID --region us-east-1 | jq -r '.SecretString'`
export PGUSER="`echo $API_SECRET | jq -r '.username'`"
export PGPASSWORD="`echo $API_SECRET | jq -r '.password'`"
export PGHOST="`echo $API_SECRET | jq -r '.host'`"
export PGDATABASE="`echo $API_SECRET | jq -r '.dbname'`"
export PGPORT="`echo $API_SECRET | jq -r '.port'`"
psql -c "select version(),AURORA_VERSION();"
psql -c "select current_role;"
