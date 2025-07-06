# News Insights CDK Stack

## Requirements

### requirements.txt
```txt
aws-cdk-lib==2.203.1
constructs>=10.0.0
opensearch-py==2.4.2
redis==5.0.1
requests==2.31.0
beautifulsoup4==4.12.2
boto3==1.34.84
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

# Install dependencies (includes all modules for OpenSearch, Redis, web scraping)
pip install aws-cdk-lib==2.203.1 constructs>=10.0.0 opensearch-py==2.4.2 redis==5.0.1 requests==2.31.0 beautifulsoup4==4.12.2 boto3==1.34.84

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy the stack
cdk deploy NewsInsightsStack
```

## Architecture

The stack deploys three main components:

### 1. Article Downloader
- **ECS Fargate Service** - Orchestrated download of news articles
- **EventBridge Scheduler** - Triggers downloads every hour
- **S3 Storage** - Stores downloaded articles

### 2. Data Replicator
- **Lambda Function** - CDC process using Redis Streams
- **Redis Cluster** - Message streaming and caching
- **EventBridge Rule** - Triggers replication every 5 minutes

### 3. Search API
- **OpenSearch Domain** - Search index for articles
- **Lambda Function** - Search query processing
- **API Gateway** - RESTful search interface

## Usage

After deployment, you'll get:
- **Search API URL** - Query articles with `/search?q=keyword`
- **OpenSearch Endpoint** - Direct access to search cluster

### Search Examples

```bash
# Search for articles containing "technology"
curl "[SearchAPIURL]/search?q=technology"

# Search with size limit
curl "[SearchAPIURL]/search?q=news&size=5"

# Search all articles
curl "[SearchAPIURL]/search?q=*"
```

## Components

### Article Downloader (ECS)
- Runs on Fargate with minimal resource allocation
- Scheduled to run every hour via EventBridge
- Stores articles in S3 and sends metadata to Redis

### Data Replicator (Lambda)
- Processes Redis Stream events
- Replicates article metadata to OpenSearch
- Ensures search index stays synchronized

### Search API (Lambda + API Gateway)
- Provides RESTful search interface
- Decouples clients from OpenSearch cluster
- Supports full-text search across articles

## Cleanup

```bash
cdk destroy NewsInsightsStack
```

## Development

The stack includes:
- Redis cluster for message streaming
- OpenSearch for full-text search
- ECS for scalable article processing
- Lambda for serverless data processing
- API Gateway for secure API access