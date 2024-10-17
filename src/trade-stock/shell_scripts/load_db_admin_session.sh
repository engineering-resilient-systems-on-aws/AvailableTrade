export ADMIN_SECRET_ID=$(aws ssm get-parameter --name trade_db_secret_id \
 --region us-east-1 | jq -r .Parameter.Value)
export ADMIN_SECRET=`aws secretsmanager get-secret-value \
 --secret-id $ADMIN_SECRET_ID --region us-east-1 | jq -r '.SecretString'`
export PGUSER="`echo $ADMIN_SECRET | jq -r '.username'`"
export PGPASSWORD="`echo $ADMIN_SECRET | jq -r '.password'`"
export PGHOST="`echo $ADMIN_SECRET | jq -r '.host'`"
export PGDATABASE="`echo $ADMIN_SECRET | jq -r '.dbname'`"
export PGPORT="`echo $ADMIN_SECRET | jq -r '.port'`"
psql -c "select version(),AURORA_VERSION();"
