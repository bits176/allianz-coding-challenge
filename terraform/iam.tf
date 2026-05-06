# ---------- IAM Role for Lambda ----------
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project_name}-lambda-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# CloudWatch Logs — all functions need this
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Least-privilege: DynamoDB access scoped to our table only
resource "aws_iam_policy" "dynamodb_access" {
  name = "${var.project_name}-dynamodb-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
      ]
      Resource = [
        aws_dynamodb_table.vpcs.arn,
        "${aws_dynamodb_table.vpcs.arn}/index/*",
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "dynamodb" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

# Least-privilege: EC2 VPC/Subnet actions only
resource "aws_iam_policy" "ec2_vpc_access" {
  name = "${var.project_name}-ec2-vpc-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:CreateVpc",
        "ec2:DeleteVpc",
        "ec2:ModifyVpcAttribute",
        "ec2:CreateSubnet",
        "ec2:DeleteSubnet",
        "ec2:CreateTags",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
      ]
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ec2_vpc" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = aws_iam_policy.ec2_vpc_access.arn
}
