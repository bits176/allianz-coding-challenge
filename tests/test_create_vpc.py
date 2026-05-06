"""Tests for POST /vpcs — create_vpc Lambda."""

import json
import importlib
import pytest


@pytest.fixture(autouse=True)
def reload_module(aws):
    """Reload create_vpc module so it picks up mocked boto3."""
    import src.create.create_vpc as mod
    importlib.reload(mod)
    yield mod


def event(body):
    """Build a minimal API Gateway proxy event."""
    return {"body": json.dumps(body)}


class TestValidation:
    def test_missing_cidr(self, reload_module):
        result = reload_module.lambda_handler(event({"name": "test"}), None)
        assert result["statusCode"] == 400
        assert "cidr_block is required" in result["body"]

    def test_invalid_cidr(self, reload_module):
        result = reload_module.lambda_handler(event({"cidr_block": "not-a-cidr"}), None)
        assert result["statusCode"] == 400
        assert "Invalid CIDR" in result["body"]

    def test_no_subnets(self, reload_module):
        result = reload_module.lambda_handler(event({"cidr_block": "10.0.0.0/16", "subnets": []}), None)
        assert result["statusCode"] == 400
        assert "At least one subnet" in result["body"]

    def test_invalid_subnet_cidr(self, reload_module):
        body = {
            "cidr_block": "10.0.0.0/16",
            "subnets": [{"cidr_block": "garbage", "az": "eu-central-1a"}]
        }
        result = reload_module.lambda_handler(event(body), None)
        assert result["statusCode"] == 400
        assert "Invalid subnet CIDR" in result["body"]

    def test_invalid_json(self, reload_module):
        result = reload_module.lambda_handler({"body": "not{json"}, None)
        assert result["statusCode"] == 400
        assert "Invalid JSON" in result["body"]


class TestCreateVPC:
    def test_success(self, reload_module):
        body = {
            "name": "test-vpc",
            "cidr_block": "10.0.0.0/16",
            "subnets": [
                {"name": "sub-1a", "cidr_block": "10.0.1.0/24", "az": "eu-central-1a"}
            ]
        }
        result = reload_module.lambda_handler(event(body), None)
        assert result["statusCode"] == 201
        data = json.loads(result["body"])
        assert data["status"] == "ACTIVE"
        assert data["name"] == "test-vpc"
        assert data["vpc_id"].startswith("vpc-")
        assert len(data["subnets"]) == 1
        assert data["subnets"][0]["subnet_id"].startswith("subnet-")

    def test_idempotency_returns_existing(self, reload_module):
        body = {
            "name": "idem-vpc",
            "cidr_block": "10.1.0.0/16",
            "idempotency_key": "key-123",
            "subnets": [{"name": "s1", "cidr_block": "10.1.1.0/24", "az": "eu-central-1a"}]
        }
        r1 = reload_module.lambda_handler(event(body), None)
        assert r1["statusCode"] == 201

        # Same key → return existing, 200 not 201
        r2 = reload_module.lambda_handler(event(body), None)
        assert r2["statusCode"] == 200
        assert json.loads(r1["body"])["vpc_id"] == json.loads(r2["body"])["vpc_id"]
