variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "vpc-api"
}

variable "allowed_cidr" {
  description = "CIDR allowed to call the API. Use 0.0.0.0/0 for public access."
  type        = string
  default     = "0.0.0.0/0"
}
