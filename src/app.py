import json
import boto3
import logging
import datetime
from typing import Dict, List, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clients
tagging_client = boto3.client('resourcegroupstaggingapi')
ec2_client = boto3.client('ec2')
rds_client = boto3.client('rds')

def get_tag_filters(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert JSON body tags into Resource Groups Tagging API filters."""
    tags = body.get('tags', {})
    filters = []
    for key, value in tags.items():
        filters.append({
            'Key': key,
            'Values': [value] if isinstance(value, str) else value
        })
    # Default filter to ensure we only touch managed resources if desired
    # For now, we trust the input filters
    return filters

def handle_ec2(instance_id: str, action: str):
    """Start or Stop EC2 instances."""
    try:
        if action == 'start':
            ec2_client.start_instances(InstanceIds=[instance_id])
            status = 'Started'
        else:
            ec2_client.stop_instances(InstanceIds=[instance_id])
            status = 'Stopped'
        
        # Update Tags
        ec2_client.create_tags(
            Resources=[instance_id],
            Tags=[
                {'Key': 'LastAction', 'Value': status},
                {'Key': 'LastActionTime', 'Value': datetime.datetime.utcnow().isoformat()}
            ]
        )
        return True, status
    except Exception as e:
        logger.error(f"Error handling EC2 {instance_id}: {str(e)}")
        return False, str(e)

def handle_rds(db_id: str, arn: str, action: str):
    """Start or Stop RDS instances."""
    try:
        if action == 'start':
            rds_client.start_db_instance(DBInstanceIdentifier=db_id)
            status = 'Started'
        else:
            rds_client.stop_db_instance(DBInstanceIdentifier=db_id)
            status = 'Stopped'
        
        # Update Tags
        rds_client.add_tags_to_resource(
            ResourceName=arn,
            Tags=[
                {'Key': 'LastAction', 'Value': status},
                {'Key': 'LastActionTime', 'Value': datetime.datetime.utcnow().isoformat()}
            ]
        )
        return True, status
    except Exception as e:
        logger.error(f"Error handling RDS {db_id}: {str(e)}")
        return False, str(e)

def lambda_handler(event, context):
    logger.info(f"Event: {json.dumps(event)}")
    
    path = event.get('rawPath', '')
    action = 'start' if '/start' in path else 'stop'
    
    body = {}
    if event.get('body'):
        try:
            body = json.loads(event['body'])
        except json.JSONDecodeError:
            pass

    tag_filters = get_tag_filters(body)
    
    results = {
        'action': action,
        'processed': [],
        'failed': []
    }

    try:
        # Find resources matching tags
        # We filter for EC2 instances and RDS instances specifically
        paginator = tagging_client.get_paginator('get_resources')
        page_iterator = paginator.paginate(
            TagFilters=tag_filters,
            ResourceTypeFilters=['ec2:instance', 'rds:db']
        )

        for page in page_iterator:
            for resource in page['ResourceTagMappingList']:
                arn = resource['ResourceARN']
                
                if ':ec2:' in arn:
                    instance_id = arn.split('/')[-1]
                    success, msg = handle_ec2(instance_id, action)
                elif ':rds:' in arn:
                    db_id = arn.split(':')[-1]
                    success, msg = handle_rds(db_id, arn, action)
                else:
                    logger.warning(f"Unsupported resource type: {arn}")
                    continue

                if success:
                    results['processed'].append({'arn': arn, 'status': msg})
                else:
                    results['failed'].append({'arn': arn, 'error': msg})

        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }
