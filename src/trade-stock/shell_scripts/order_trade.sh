bash
cd ~
export ORDER_ENDPOINT=$(aws ssm get-parameter --name trade_order_endpoint \
 --region us-east-1 | jq -r .Parameter.Value)

cat <<'EOF' > trade.sh
curl \
--request POST \
--header "Content-Type: application/json" \
--data '{"request_id": "'$(uuidgen)'", "customer_id": "4", "ticker": "IPAY",
 "transaction_type": "buy", "current_price": 40.06,
 "share_count": '$RANDOM'}' \
$ORDER_ENDPOINT/trade/
EOF

chmod u+x trade.sh
watch -d -n 1 ./trade.sh
