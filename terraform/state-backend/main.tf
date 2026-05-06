# Bootstrap — run this ONCE to create the remote state infrastructure.
# This itself uses local state (stored in this directory).

# ─── TERRAFORM SETTINGS ───────────────────────────────────────────────────────
# This block configures Terraform itself (not AWS).
terraform {
  # Minimum Terraform CLI version needed to run this code.
  # If someone has an older version, they'll get a clear error.
  required_version = ">= 1.5"

  # Plugins Terraform needs to download.
  # Providers are how Terraform knows how to talk to AWS, GCP, Azure, etc.
  required_providers {
    aws = {
      source  = "hashicorp/aws"   # Download from HashiCorp's registry
      version = "~> 5.0"          # Any 5.x (not 6.0) — prevents breaking changes
    }
  }
}

# ─── PROVIDER ─────────────────────────────────────────────────────────────────
# "I want to talk to AWS, in this region."
# Terraform uses your local AWS credentials (from `aws configure` or env vars).
provider "aws" {
  region = var.aws_region   # References the variable below
}

# ─── VARIABLES ────────────────────────────────────────────────────────────────
# Variables are inputs. Like function parameters.
# If no value is passed at runtime, the `default` is used.

variable "aws_region" {
  default = "eu-central-1"   # Frankfurt. Change this to deploy elsewhere.
}

variable "project_name" {
  default = "vpc-api"   # Used to build resource names like "vpc-api-terraform-state"
}

# ─── RESOURCE: S3 BUCKET ─────────────────────────────────────────────────────
# This is the actual S3 bucket where Terraform stores its state file.
# Format: resource "<provider_type>" "<local_name>" { ... }
#   - "aws_s3_bucket" = the type (from the AWS provider plugin)
#   - "state"         = our local name (used to reference it: aws_s3_bucket.state.id)
resource "aws_s3_bucket" "state" {
  # The real bucket name in AWS. Must be globally unique across ALL AWS accounts.
  bucket = "${var.project_name}-terraform-state"   # → "vpc-api-terraform-state"

  # lifecycle = special Terraform meta-block (not an AWS setting).
  # prevent_destroy = if someone runs `terraform destroy`, refuse to delete this.
  # Safety net: losing the state bucket = losing track of all infrastructure.
  lifecycle {
    prevent_destroy = true
  }
}

# ─── RESOURCE: VERSIONING ────────────────────────────────────────────────────
# Keeps every version of every file in the bucket.
# Why? If state gets corrupted, you can roll back to a previous version.
resource "aws_s3_bucket_versioning" "state" {
  # References the bucket above. Terraform knows to create the bucket FIRST.
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ─── RESOURCE: ENCRYPTION ────────────────────────────────────────────────────
# Encrypts all objects at rest. The state file contains resource IDs, ARNs,
# and sometimes sensitive outputs — it should never be stored in plaintext.
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"   # AWS-managed key. Free. No setup needed.
    }
  }
}

# ─── RESOURCE: PUBLIC ACCESS BLOCK ───────────────────────────────────────────
# Locks down the bucket so nothing can ever be made public.
# All 4 settings = true means: no public ACLs, no public policies, period.
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true   # Reject any PUT that sets a public ACL
  block_public_policy     = true   # Reject any bucket policy that grants public access
  ignore_public_acls      = true   # Even if public ACLs exist, ignore them
  restrict_public_buckets = true   # Restrict access to only AWS-authorized principals
}

# ─── OUTPUT ──────────────────────────────────────────────────────────────────
# Outputs are values printed after `terraform apply`.
# Like a function's return value. Other Terraform configs can read these too.
output "state_bucket" {
  value = aws_s3_bucket.state.id   # Prints: "vpc-api-terraform-state"
}
