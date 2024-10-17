# NOTE: you can't use this, it requires IAM permissions that Cloud9 managed credentials don't support

TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
INSTANCEID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" -v http://169.254.169.254/latest/meta-data/instance-id 2> /dev/null)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" -v http://169.254.169.254/latest/meta-data/placement/region 2> /dev/null)
aws iam create-role --role-name cloud9-instance-profile-role \
  --assume-role-policy-document file://home/ec2-user/environment/instance-profile-role-trust.json
aws iam attach-role-policy --role-name cloud9-instance-profile-role \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam create-instance-profile --instance-profile-name cloud9-instance-profile
aws iam add-role-to-instance-profile --role-name cloud9-instance-profile-role \
  --instance-profile-name cloud9-instance-profile
aws ec2 associate-iam-instance-profile \
  --iam-instance-profile Name=cloud9-instance-profile \
  --region $REGION --instance-id $INSTANCEID