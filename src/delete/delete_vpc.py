"""DELETE /vpcs/{vpc_id} — Delete a VPC and its subnets, then soft-delete in DynamoDB."""

import boto3
import json
import logging
import os
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "vpcs")

ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """Delete subnets + VPC from EC2, then soft-delete the record in DynamoDB."""
    vpc_id = event.get("pathParameters", {}).get("vpc_id")
    if not vpc_id:
        return response(400, {"error": "vpc_id is required"})

    try:
        # Get VPC record from DynamoDB
        result = table.get_item(Key={"vpc_id": vpc_id})
        item = result.get("Item")
        if not item:
            return response(404, {"error": f"VPC {vpc_id} not found"})

        if item.get("status") == "DELETED":
            return response(400, {"error": f"VPC {vpc_id} is already deleted"})

        # Delete subnets first (AWS requires this before deleting VPC)
        for subnet in item.get("subnets", []):
            try:
                ec2.delete_subnet(SubnetId=subnet["subnet_id"])
                logger.info(f"Deleted subnet: {subnet['subnet_id']}")
            except ec2.exceptions.ClientError as e:
                logger.warning(f"Could not delete subnet {subnet['subnet_id']}: {e}")

        # Delete VPC
        ec2.delete_vpc(VpcId=vpc_id)
        logger.info(f"Deleted VPC: {vpc_id}")

        # Soft delete — mark as DELETED, keep the record for audit trail
        # "status" is a DynamoDB reserved word, so we alias it with #s
        table.update_item(
            Key={"vpc_id": vpc_id},
            UpdateExpression="SET #s = :status, deleted_at = :deleted_at",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":status": "DELETED",
                ":deleted_at": datetime.utcnow().isoformat() + "Z"
            }
        )

        return response(200, {"message": f"VPC {vpc_id} deleted", "status": "DELETED"})

    except Exception as e:
        logger.error(f"Error deleting VPC: {str(e)}")
        return response(500, {"error": str(e)})


def response(status_code, body):
    """Build API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body) if body else ""
    }
