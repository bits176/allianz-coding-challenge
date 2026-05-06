"""GET /vpcs — List all active VPCs or retrieve a single VPC by ID."""

import boto3
import json
import logging
import os
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "vpcs")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def lambda_handler(event, context):
    """List active VPCs or get a single VPC by ID from DynamoDB."""
    path_params = event.get("pathParameters") or {}
    vpc_id = path_params.get("vpc_id")

    try:
        if vpc_id:
            # GET /vpcs/{vpc_id}
            result = table.get_item(Key={"vpc_id": vpc_id})
            item = result.get("Item")
            if not item:
                return response(404, {"error": f"VPC {vpc_id} not found"})
            return response(200, item)
        else:
            # GET /vpcs — only return ACTIVE VPCs
            result = table.scan(
                FilterExpression="#s = :active",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":active": "ACTIVE"}
            )
            return response(200, {"vpcs": result.get("Items", [])})

    except Exception as e:
        logger.error(f"Error fetching VPCs: {str(e)}")
        return response(500, {"error": str(e)})


def response(status_code, body):
    """Build API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, cls=DecimalEncoder)
    }
