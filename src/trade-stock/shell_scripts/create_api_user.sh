export API_SECRET_ID=$(aws ssm get-parameter --name trade_order_api_secret_id \
 --region us-east-1 | jq -r .Parameter.Value)
export API_SECRET=`aws secretsmanager get-secret-value \
 --secret-id $API_SECRET_ID --region us-east-1 | jq -r '.SecretString'`
export API_PASSWORD="`echo $API_SECRET | jq -r '.password'`"
export API_USER="`echo $API_SECRET | jq -r '.username'`"
psql -c "create user $API_USER with password '$API_PASSWORD';"
psql -c \
"grant select,insert,update,delete on all tables in schema public to $API_USER;"
psql -c \
"grant usage,select on all sequences in schema public to $API_USER;"
