"""Tests for GET /vpcs — get_vpcs Lambda."""

import json
import importlib
import pytest


@pytest.fixture(autouse=True)
def reload_module(aws):
    """Reload get_vpcs module so it picks up mocked boto3."""
    import src.get.get_vpcs as mod
    importlib.reload(mod)
    yield mod


def _seed_vpc(aws, vpc_id, status="ACTIVE", name="test-vpc"):
    aws["dynamodb"].Table("vpcs").put_item(Item={
        "vpc_id": vpc_id,
        "name": name,
        "cidr_block": "10.0.0.0/16",
        "subnets": [],
        "status": status,
        "created_at": "2024-01-01T00:00:00+00:00"
    })


class TestListVPCs:
    def test_empty(self, reload_module, aws):
        result = reload_module.lambda_handler({"pathParameters": None}, None)
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["vpcs"] == []

    def test_only_active_returned(self, reload_module, aws):
        _seed_vpc(aws, "vpc-1", "ACTIVE")
        _seed_vpc(aws, "vpc-2", "DELETED")
        _seed_vpc(aws, "vpc-3", "FAILED")
        _seed_vpc(aws, "vpc-4", "ACTIVE")

        result = reload_module.lambda_handler({"pathParameters": None}, None)
        data = json.loads(result["body"])
        ids = [v["vpc_id"] for v in data["vpcs"]]
        assert sorted(ids) == ["vpc-1", "vpc-4"]


class TestGetSingle:
    def test_found(self, reload_module, aws):
        _seed_vpc(aws, "vpc-123", "ACTIVE", "my-vpc")

        result = reload_module.lambda_handler(
            {"pathParameters": {"vpc_id": "vpc-123"}}, None
        )
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["name"] == "my-vpc"

    def test_returns_any_status(self, reload_module, aws):
        """GET /vpcs/{id} returns the record regardless of status."""
        _seed_vpc(aws, "vpc-del", "DELETED")

        result = reload_module.lambda_handler(
            {"pathParameters": {"vpc_id": "vpc-del"}}, None
        )
        assert result["statusCode"] == 200

    def test_not_found(self, reload_module):
        result = reload_module.lambda_handler(
            {"pathParameters": {"vpc_id": "vpc-nope"}}, None
        )
        assert result["statusCode"] == 404
        assert "not found" in json.loads(result["body"])["error"]
