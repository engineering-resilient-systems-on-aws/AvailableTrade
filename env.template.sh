# run `source env.sh` to set these before doing any CDK deployment actions

export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
export AWS_PRIMARY_REGION=us-east-1
export AWS_SECONDARY_REGION=us-west-2

export PYTHONPATH=$PYTHONPATH:`pwd`:`pwd`/src/trade-stock:`pwd`/src/account_open:`pwd`/src/front_end

export AWS_DOMAIN_NAME= # update with your cloudfront URL (after deploying front end) or your custom AWS hosted domain

export JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1