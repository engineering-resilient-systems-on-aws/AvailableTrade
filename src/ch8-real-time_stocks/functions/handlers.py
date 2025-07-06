

import json
import boto3
import base64
from datetime import datetime

firehose = boto3.client('firehose')

def StockDataProcessor_handler(event, context):
    '''
    Process stock data from MSK and send to Firehose
    '''
    records = []
    
    for record in event.get('records', []):
        # Decode Kafka message
        payload = base64.b64decode(record['value']).decode('utf-8')
        stock_data = json.loads(payload)
        
        # Enrich with timestamp
        enriched_data = {
            **stock_data,
            'processed_timestamp': datetime.utcnow().isoformat(),
            'partition_key': stock_data.get('symbol', 'unknown')
        }
        
        records.append({
            'Data': json.dumps(enriched_data) + '\\n'
        })
    
    # Send to Firehose
    if records:
        firehose.put_record_batch(
            DeliveryStreamName='realtime-stocks-firehose',
            Records=records
        )
    
    return {
        'statusCode': 200,
        'body': json.dumps(f'Processed {len(records)} records')
    }


def StockAPIHandler_handler(event, context):
    '''
    Handle API requests for stock data enrichment
    '''
    
    symbol = event.get('pathParameters', {}).get('symbol', 'UNKNOWN')
    
    # Mock enrichment data
    enrichment_data = {
        'symbol': symbol,
        'company_name': f'{symbol} Corporation',
        'sector': 'Technology',
        'market_cap': '1B+',
        'enriched_at': datetime.utcnow().isoformat()
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(enrichment_data)
    }