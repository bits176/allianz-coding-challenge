"""POST /vpcs — Create a VPC with subnets in AWS and store the result in DynamoDB."""

import boto3
import json
import logging
import os
import ipaddress
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "vpcs")
PROJECT_TAG = "allianz-challenge"

ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    """Create a VPC with subnets in EC2 and save metadata to DynamoDB."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON"})

    cidr_block = body.get("cidr_block")
    name = body.get("name", "my-vpc")
    subnets_config = body.get("subnets", [])
    idempotency_key = body.get("idempotency_key")

    # --- Validation ---
    if not cidr_block:
        return response(400, {"error": "cidr_block is required"})

    if not validate_cidr(cidr_block):
        return response(400, {"error": f"Invalid CIDR block: {cidr_block}"})

    if not subnets_config:
        return response(400, {"error": "At least one subnet is required"})

    for i, s in enumerate(subnets_config):
        if not s.get("cidr_block") or not s.get("az"):
            return response(400, {"error": f"Subnet {i} needs cidr_block and az"})
        if not validate_cidr(s["cidr_block"]):
            return response(400, {"error": f"Invalid subnet CIDR: {s['cidr_block']}"})

    # --- Idempotency check ---
    if idempotency_key:
        existing = table.query(
            IndexName="idempotency-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("idempotency_key").eq(idempotency_key)
        )
        if existing.get("Items"):
            item = existing["Items"][0]
            if item.get("status") in ("ACTIVE", "CREATING"):
                return response(200, item)

    try:
        # Phase 1: Create VPC and immediately record intent in DynamoDB
        vpc_result = ec2.create_vpc(CidrBlock=cidr_block)
        vpc_id = vpc_result["Vpc"]["VpcId"]
        logger.info(f"Created VPC: {vpc_id}")

        created_at = datetime.now(timezone.utc).isoformat()
        item = {
            "vpc_id": vpc_id,
            "name": name,
            "cidr_block": cidr_block,
            "subnets": [],
            "status": "CREATING",
            "created_at": created_at,
        }
        if idempotency_key:
            item["idempotency_key"] = idempotency_key
        table.put_item(Item=item)
        logger.info(f"Recorded CREATING state for {vpc_id}")

        # Phase 2: Configure VPC and create subnets
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
        ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})

        ec2.create_tags(Resources=[vpc_id], Tags=[
            {"Key": "Name", "Value": name},
            {"Key": "Project", "Value": PROJECT_TAG},
            {"Key": "ManagedBy", "Value": "vpc-api"}
        ])

        created_subnets = []
        for subnet_config in subnets_config:
            subnet_result = ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=subnet_config["cidr_block"],
                AvailabilityZone=subnet_config["az"]
            )
            subnet_id = subnet_result["Subnet"]["SubnetId"]
            subnet_name = subnet_config.get("name", subnet_id)

            ec2.create_tags(Resources=[subnet_id], Tags=[
                {"Key": "Name", "Value": subnet_name},
                {"Key": "Project", "Value": PROJECT_TAG},
                {"Key": "ManagedBy", "Value": "vpc-api"}
            ])

            created_subnets.append({
                "subnet_id": subnet_id,
                "cidr_block": subnet_config["cidr_block"],
                "az": subnet_config["az"],
                "name": subnet_name
            })
            logger.info(f"Created subnet: {subnet_id}")

        # Phase 3: Mark as ACTIVE with full subnet info
        item["subnets"] = created_subnets
        item["status"] = "ACTIVE"
        table.put_item(Item=item)

        return response(201, item)

    except Exception as e:
        logger.error(f"Error creating VPC: {str(e)}")
        # If we have a vpc_id, update record to FAILED (if it was written)
        if "vpc_id" in dir():
            try:
                table.update_item(
                    Key={"vpc_id": vpc_id},
                    UpdateExpression="SET #s = :status",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":status": "FAILED"},
                )
            except Exception:
                pass
        return response(500, {"error": str(e)})


def validate_cidr(cidr):
    """Validate a CIDR block string."""
    try:
        ipaddress.ip_network(cidr, strict=False)
        return True
    except (ValueError, TypeError):
        return False


def response(status_code, body):
    """Build API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
