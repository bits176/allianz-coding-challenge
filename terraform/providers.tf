terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  # Remote state — requires terraform/state-backend/ to be applied first
  backend "s3" {
    bucket       = "vpc-api-terraform-state"
    key          = "vpc-api/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "vpc-api"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
