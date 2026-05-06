"""Tests for DELETE /vpcs/{vpc_id} — delete_vpc Lambda."""

import json
import importlib
import pytest


@pytest.fixture(autouse=True)
def reload_module(aws):
    """Reload delete_vpc module so it picks up mocked boto3."""
    import src.delete.delete_vpc as mod
    importlib.reload(mod)
    yield mod


def _seed_vpc_with_resources(aws):
    """Create a real mocked VPC + subnets in EC2 and store in DynamoDB."""
    ec2 = aws["ec2"]
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]
    subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
    subnet_id = subnet["Subnet"]["SubnetId"]

    tbl = aws["dynamodb"].Table("vpcs")
    tbl.put_item(Item={
        "vpc_id": vpc_id,
        "name": "delete-me",
        "cidr_block": "10.0.0.0/16",
        "status": "ACTIVE",
        "subnets": [{"subnet_id": subnet_id, "cidr_block": "10.0.1.0/24", "az": "eu-central-1a"}],
        "created_at": "2024-01-01T00:00:00+00:00"
    })
    return vpc_id


class TestDeleteVPC:
    def test_success(self, reload_module, aws):
        vpc_id = _seed_vpc_with_resources(aws)
        result = reload_module.lambda_handler(
            {"pathParameters": {"vpc_id": vpc_id}}, None
        )
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "DELETED"

        # Verify DynamoDB record is soft-deleted
        tbl = aws["dynamodb"].Table("vpcs")
        item = tbl.get_item(Key={"vpc_id": vpc_id})["Item"]
        assert item["status"] == "DELETED"
        assert "deleted_at" in item

    def test_not_found(self, reload_module):
        result = reload_module.lambda_handler(
            {"pathParameters": {"vpc_id": "vpc-nonexist"}}, None
        )
        assert result["statusCode"] == 404

    def test_already_deleted(self, reload_module, aws):
        tbl = aws["dynamodb"].Table("vpcs")
        tbl.put_item(Item={
            "vpc_id": "vpc-gone",
            "name": "gone",
            "cidr_block": "10.0.0.0/16",
            "status": "DELETED",
            "subnets": [],
            "deleted_at": "2024-01-01T00:00:00+00:00"
        })
        result = reload_module.lambda_handler(
            {"pathParameters": {"vpc_id": "vpc-gone"}}, None
        )
        assert result["statusCode"] == 400
        assert "already deleted" in json.loads(result["body"])["error"]

    def test_missing_vpc_id(self, reload_module):
        result = reload_module.lambda_handler({"pathParameters": {}}, None)
        assert result["statusCode"] == 400
