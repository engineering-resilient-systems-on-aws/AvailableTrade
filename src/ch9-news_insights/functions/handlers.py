import json
import boto3
import redis
from opensearchpy import OpenSearch
import os
from datetime import datetime

def DataReplicator_handler(event, context):
    """
    Data replication function using Redis Streams for CDC
    """
    redis_endpoint = os.environ['REDIS_ENDPOINT']
    opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
    # Connect to Redis
    redis_client = redis.Redis(host=redis_endpoint, port=6379, decode_responses=True)
    # Connect to OpenSearch
    opensearch_client = OpenSearch(
        hosts=[{'host': opensearch_endpoint, 'port': 443}],
        http_compress=True,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    # Process Redis stream events
    try:
        streams = redis_client.xread({'article_stream': '$'}, count=10, block=1000)
        for stream_name, messages in streams:
            for message_id, fields in messages:
                doc_id = fields.get('article_id')
                doc_body = {
                    'title': fields.get('title', ''),
                    'content': fields.get('content', ''),
                    'url': fields.get('url', ''),
                    'timestamp': fields.get('timestamp', ''),
                    'source': fields.get('source', '')
                }
                opensearch_client.index(
                    index='articles',
                    id=doc_id,
                    body=doc_body
                )
        return {
            'statusCode': 200,
            'body': json.dumps('Data replication completed successfully')
        }
    except Exception as e:
        print(f"Error in data replication: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def SearchAPI_handler(event, context):
    """
    Search API function for querying articles
    """
    opensearch_endpoint = os.environ['OPENSEARCH_ENDPOINT']
    opensearch_client = OpenSearch(
        hosts=[{'host': opensearch_endpoint, 'port': 443}],
        http_compress=True,
        use_ssl=True,
        verify_certs=True,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    try:
        query_params = event.get('queryStringParameters', {})
        search_query = query_params.get('q', '*')
        size = int(query_params.get('size', 10))
        search_body = {
            'query': {
                'multi_match': {
                    'query': search_query,
                    'fields': ['title^2', 'content']
                }
            },
            'size': size,
            'sort': [
                {'timestamp': {'order': 'desc'}}
            ]
        }
        response = opensearch_client.search(
            index='articles',
            body=search_body
        )
        results = []
        for hit in response['hits']['hits']:
            results.append({
                'id': hit['_id'],
                'title': hit['_source'].get('title', ''),
                'content': hit['_source'].get('content', '')[:200] + '...',
                'url': hit['_source'].get('url', ''),
                'timestamp': hit['_source'].get('timestamp', ''),
                'source': hit['_source'].get('source', ''),
                'score': hit['_score']
            })
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'total': response['hits']['total']['value'],
                'results': results
            })
        }
    except Exception as e:
        print(f"Error in search API: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }
