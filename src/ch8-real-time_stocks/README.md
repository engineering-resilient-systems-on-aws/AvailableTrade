# Real-Time Stock Analytics CDK Stack

## Requirements

### requirements.txt
```txt
aws-cdk-lib==2.203.1
constructs>=10.0.0
```

### Prerequisites
- Python 3.9+
- Node.js 18+ (for CDK CLI)
- AWS CLI configured

## Deployment

```bash
# Install CDK CLI
npm install -g aws-cdk@2.203.1

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install aws-cdk-lib==2.203.1 constructs>=10.0.0

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy the stack
cdk deploy RealtimeStocksStack
```

## Architecture

The stack deploys:
- **Amazon MSK** - Kafka cluster for data ingestion
- **AWS Lambda** - Stream processing functions
- **Kinesis Data Firehose** - Data delivery to S3
- **Amazon S3** - Data storage
- **Amazon Athena** - Data analytics
- **API Gateway** - Data enrichment endpoints

## Usage

After deployment, you'll get:
- **API Gateway URL** - Test with `/stocks/AAPL`
- **MSK Bootstrap Servers** - Connect your producers/consumers

## Testing

```bash
# Test the API
curl [APIGatewayURL]/stocks/AAPL

# Connect to MSK using the bootstrap servers
# Send messages to the "stock-prices" topic
```

## Cleanup

```bash
cdk destroy RealtimeStocksStack
```

## 📋 Requirements

### requirements.txt
```txt
aws-cdk-lib==2.203.1
constructs>=10.0.0
```

### System Requirements
- Python 3.9+
- Node.js 18+ (for CDK CLI)
- AWS CLI configured

## 🚀 Quick Start

### 1. Installation
```bash
# Install CDK CLI
npm install -g aws-cdk@2.203.1

# Create project directory
mkdir realtime-stocks-learning
cd realtime-stocks-learning

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install aws-cdk-lib==2.203.1 constructs>=10.0.0

# Initialize CDK (first time only)
cdk bootstrap
```

### 2. Deploy the Stack
```bash
# Deploy the learning stack
cdk deploy RealtimeStocksLearningStack

# Grab coffee ☕ - takes about 10-15 minutes
```

### 3. Test Your Pipeline

#### Generate Sample Data
```bash
# Use the sample data generator function
aws lambda invoke --function-name [SampleDataGeneratorFunction] response.json
cat response.json
```

#### Test API Enrichment
```bash
# Test the enrichment API
curl [APIGatewayURL]/stocks/AAPL

# Example response:
{
  "symbol": "AAPL",
  "company_name": "Apple Inc.",
  "sector": "Technology",
  "market_cap": "3.0T",
  "analyst_rating": "Buy",
  "risk_level": "Low",
  "volatility": 0.25,
  "enriched_at": "2025-07-03T10:30:00Z"
}
```

#### Query Data with Athena
```sql
-- Use the Athena workgroup to query your data
SELECT symbol, 
       avg(price) as avg_price,
       count(*) as trade_count
FROM realtime_stocks_learning_db.stock_data
WHERE year = '2025' AND month = '07'
GROUP BY symbol
ORDER BY avg_price DESC;
```

## 🎯 Learning Objectives

This stack teaches you:

1. **Event-Driven Architecture**: MSK Serverless → Lambda → Firehose → S3
2. **Stream Processing**: Real-time data transformation and enrichment
3. **Data Lake Architecture**: Partitioned storage in S3 with Glue catalog
4. **Serverless Analytics**: Query streaming data with Athena
5. **API Integration**: RESTful APIs for data enrichment
6. **Cost Optimization**: Pay-per-use serverless services

## 🔧 What's Different from Traditional Architectures

### Old Way (Expensive)
- **MSK Provisioned**: 2+ brokers running 24/7 = $200+/month
- **Fixed Costs**: Pay even when not using
- **Complex Management**: Broker sizing, scaling, monitoring

### New Way (Learning-Optimized)
- **MSK Serverless**: Pay only for messages processed
- **Variable Costs**: ~$2-10/month for typical learning
- **Fully Managed**: No broker management needed

## 📊 Corrected Cost Breakdown (Monthly Estimates)

### **MSK Provisioned (This Stack)**
| Service | Learning Usage | Cost |
|---------|---------------|------|
| MSK Cluster | 2 × t3.small brokers | $48 |
| MSK Storage | 20GB EBS | $2 |
| Lambda | 1,000 invocations | $0.20 |
| Firehose | 1GB data | $0.30 |
| S3 Storage | 10GB | $0.25 |
| Athena | 10GB scanned | $0.50 |
| **Total** | | **$90-120/month** |

### **MSK Serverless (AVOID for learning!)**
| Service | Minimal Usage | Cost |
|---------|---------------|------|
| Cluster (always on) | 720 hours | $540 |
| Partitions | 10 partitions | $11 |
| Data In/Out | 1GB | $0.15 |
| Storage | 1GB | $0.10 |
| **Total** | | **$550+/month** |

### **Local Docker (FREE)**
| Service | Learning Usage | Cost |
|---------|---------------|------|
| Kafka + Zookeeper | Local containers | $0 |
| Local development | Full feature set | $0 |
| **Total** | | **FREE** |

## 🛡️ Built-in Cost Controls

- **Smallest instances**: t3.small brokers (cheapest option)
- **Minimal storage**: 10GB EBS volumes
- **Auto-cleanup**: Data expires after 7 days
- **Small batches**: Minimal processing overhead  
- **Query limits**: 1GB scan limit in Athena
- **Short retention**: 1-week log retention

## ⚠️ **Cost Warning & Alternatives**

### **If Budget is Under $100/month:**
**Use Local Docker Development:**
```bash
# Clone and run local Kafka
git clone https://github.com/confluentinc/cp-all-in-one
cd cp-all-in-one/cp-all-in-one
docker-compose up -d

# Access Kafka at localhost:9092
# Access Control Center at http://localhost:9021
```

### **If Budget is $100-200/month:**
**Use this MSK Provisioned stack** - Real AWS experience with reasonable costs

### **If Budget is $500+/month:**
**Consider MSK Serverless** - But you're paying premium for convenience

## 💡 **Learning Recommendations by Budget:**

### **$0 Budget (Students):**
1. **Docker Compose locally** - Learn Kafka fundamentals
2. **AWS Free Tier** - Use other services (Lambda, S3, Athena)
3. **Confluent Cloud Free Tier** - 400 hours/month free

### **$50-100 Budget (Learners):**
1. **This CDK Stack** - Real AWS experience
2. **Monitor costs daily** - Set up billing alerts
3. **Clean up regularly** - Use auto-cleanup features

### **$200+ Budget (Professionals):**
1. **MSK Provisioned with larger instances** - Production-like experience
2. **Add monitoring and alerting** - CloudWatch, Grafana
3. **Multi-region setup** - Learn disaster recovery

## 🧪 Learning Experiments

### Experiment 1: Basic Data Flow
1. Generate sample data using the Lambda function
2. Watch data flow through the pipeline
3. Query results in Athena

### Experiment 2: API Enrichment
1. Test different stock symbols via API
2. Observe how enrichment data is added
3. Analyze enriched data patterns

### Experiment 3: Real-Time Processing
1. Send continuous data streams
2. Monitor Lambda processing logs
3. Analyze processing latency and throughput

### Experiment 4: Cost Monitoring
1. Enable AWS Cost Explorer
2. Track daily spending by service
3. Optimize based on usage patterns

## 📱 Monitoring and Debugging

### CloudWatch Logs
```bash
# View Lambda processing logs
aws logs tail /aws/lambda/RealtimeStocksLearningStack-StockDataProcessor --follow

# View API Gateway logs
aws logs tail /aws/apigateway/RealtimeStocksLearningStack-StockDataAPI --follow
```

### S3 Data Verification
```bash
# Check if data is being stored
aws s3 ls s3://[DataBucketName]/ --recursive

# Download sample data file
aws s3 cp s3://[DataBucketName]/year=2025/month=07/day=03/hour=10/sample.gz ./
```

### MSK Serverless Monitoring
```bash
# Check cluster status
aws kafka describe-cluster-v2 --cluster-arn [MSKServerlessClusterArn]

# List topics
aws kafka list-topics --cluster-arn [MSKServerlessClusterArn]
```

## 🔍 Troubleshooting Guide

### Common Issues

#### 1. Lambda Function Timeouts
**Problem**: Lambda function timing out processing messages
**Solution**: 
- Check CloudWatch logs for errors
- Increase timeout if needed (but watch costs)
- Reduce batch size in event source mapping

#### 2. No Data in S3
**Problem**: Data not appearing in S3 bucket
**Solution**:
- Verify Firehose delivery stream is active
- Check Lambda function is processing messages
- Ensure IAM permissions are correct

#### 3. Athena Query Errors
**Problem**: Athena queries failing or returning no results
**Solution**:
- Verify Glue table schema matches data
- Check S3 partitioning structure
- Ensure data format is correct (JSON lines)

#### 4. API Gateway 500 Errors
**Problem**: API returning internal server errors
**Solution**:
- Check Lambda function logs
- Verify API Gateway integration
- Test Lambda function directly

### Cost Alerts Setup
```bash
# Set up billing alert (optional)
aws budgets create-budget \
    --account-id [YOUR-ACCOUNT-ID] \
    --budget '{
        "BudgetName": "RealtimeStocksLearning",
        "BudgetLimit": {
            "Amount": "20",
            "Unit": "USD"
        },
        "TimeUnit": "MONTHLY",
        "BudgetType": "COST"
    }'
```

## 📚 Learning Resources

### AWS Documentation
- [MSK Serverless Getting Started](https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html)
- [Lambda Event Source Mappings](https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html)
- [Athena Getting Started](https://docs.aws.amazon.com/athena/latest/ug/getting-started.html)

### Sample Queries for Learning

#### Basic Analytics
```sql
-- Daily trading volume by symbol
SELECT 
    symbol,
    DATE(from_iso8601_timestamp(timestamp)) as trade_date,
    SUM(volume) as total_volume,
    AVG(price) as avg_price,
    COUNT(*) as trade_count
FROM realtime_stocks_learning_db.stock_data
WHERE year = '2025' AND month = '07'
GROUP BY symbol, DATE(from_iso8601_timestamp(timestamp))
ORDER BY trade_date DESC, total_volume DESC;
```

#### Enrichment Analysis
```sql
-- Compare sectors and risk levels
SELECT 
    sector,
    risk_level,
    COUNT(*) as stock_count,
    AVG(volatility) as avg_volatility,
    AVG(price) as avg_price
FROM realtime_stocks_learning_db.stock_data
WHERE sector != 'Unknown'
GROUP BY sector, risk_level
ORDER BY avg_volatility DESC;
```

#### Performance Monitoring
```sql
-- Processing latency analysis
SELECT 
    DATE_DIFF('second', 
              from_iso8601_timestamp(timestamp), 
              from_iso8601_timestamp(processed_timestamp)) as processing_latency_seconds,
    processing_region,
    COUNT(*) as record_count
FROM realtime_stocks_learning_db.stock_data
WHERE year = '2025' AND month = '07'
GROUP BY processing_region, processing_latency_seconds
ORDER BY processing_latency_seconds DESC;
```

## 🚀 Next Steps & Advanced Learning

### 1. Add Real Data Sources
- Connect to real stock APIs (Alpha Vantage, Yahoo Finance)
- Implement API rate limiting and error handling
- Add data validation and cleansing

### 2. Enhanced Analytics
- Add Amazon QuickSight for dashboards
- Implement machine learning with SageMaker
- Create real-time alerting with SNS

### 3. Production Readiness
- Add monitoring with CloudWatch alarms
- Implement proper error handling and dead letter queues
- Add security scanning and compliance checks

### 4. Cost Optimization
- Implement S3 Intelligent Tiering
- Add Lambda reserved concurrency
- Use Spot instances for batch processing

## 🗑️ Cleanup Instructions

**Important**: Remember to clean up to avoid ongoing charges!

```bash
# Delete the stack and all resources
cdk destroy RealtimeStocksLearningStack

# Verify S3 buckets are empty (should be auto-deleted)
aws s3 ls

# Check for any remaining resources
aws resourcegroupstaggingapi get-resources \
    --tag-filters Key=Project,Values=RealtimeStocksLearning
```

## 📞 Support & Community

### Getting Help
1. **AWS Documentation**: Official guides and tutorials
2. **Stack Overflow**: Community support with `aws-cdk` and `aws-msk` tags
3. **AWS Forums**: Official AWS community forums
4. **GitHub Issues**: CDK-specific issues and feature requests

### Contributing
If you improve this learning stack:
1. Fork the repository
2. Make your improvements
3. Submit a pull request with detailed description
4. Share your learning experiences!

---

## 🎓 Learning Checklist

- [ ] Successfully deployed the stack
- [ ] Generated sample data using Lambda function
- [ ] Tested API Gateway enrichment endpoints
- [ ] Queried data using Athena
- [ ] Monitored costs in AWS console
- [ ] Analyzed processing logs in CloudWatch
- [ ] Experimented with different data patterns
- [ ] Cleaned up resources after learning

**Congratulations! You've built a production-ready streaming analytics pipeline optimized for learning! 🎉**
