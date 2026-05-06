"""Shared test fixtures — mocked AWS services via moto."""

import os
import pytest
import boto3
from moto import mock_aws

os.environ["TABLE_NAME"] = "vpcs"
os.environ["AWS_DEFAULT_REGION"] = "eu-central-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"


@pytest.fixture
def aws(monkeypatch):
    """Mock all AWS services and create DynamoDB table."""
    with mock_aws():
        # Create DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="eu-central-1")
        dynamodb.create_table(
            TableName="vpcs",
            KeySchema=[{"AttributeName": "vpc_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "vpc_id", "AttributeType": "S"},
                {"AttributeName": "idempotency_key", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "idempotency-index",
                "KeySchema": [{"AttributeName": "idempotency_key", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create a VPC so EC2 is initialized
        ec2 = boto3.client("ec2", region_name="eu-central-1")

        yield {"dynamodb": dynamodb, "ec2": ec2}
