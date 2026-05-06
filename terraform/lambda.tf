# ---------- Package Lambda Code ----------
data "archive_file" "create_vpc" {
  type        = "zip"
  source_dir  = "${path.module}/../src/create"
  output_path = "${path.module}/.build/create_vpc.zip"
}

data "archive_file" "get_vpcs" {
  type        = "zip"
  source_dir  = "${path.module}/../src/get"
  output_path = "${path.module}/.build/get_vpcs.zip"
}

data "archive_file" "delete_vpc" {
  type        = "zip"
  source_dir  = "${path.module}/../src/delete"
  output_path = "${path.module}/.build/delete_vpc.zip"
}

# ---------- Lambda Functions ----------
resource "aws_lambda_function" "create_vpc" {
  function_name    = "${var.project_name}-create-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "create_vpc.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  filename         = data.archive_file.create_vpc.output_path
  source_code_hash = data.archive_file.create_vpc.output_base64sha256

  environment {
    variables = {
      TABLE_NAME  = aws_dynamodb_table.vpcs.name
      ENVIRONMENT = var.environment
    }
  }
}

resource "aws_lambda_function" "get_vpcs" {
  function_name    = "${var.project_name}-get-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "get_vpcs.lambda_handler"
  runtime          = "python3.12"
  timeout          = 10
  memory_size      = 128
  filename         = data.archive_file.get_vpcs.output_path
  source_code_hash = data.archive_file.get_vpcs.output_base64sha256

  environment {
    variables = {
      TABLE_NAME  = aws_dynamodb_table.vpcs.name
      ENVIRONMENT = var.environment
    }
  }
}

resource "aws_lambda_function" "delete_vpc" {
  function_name    = "${var.project_name}-delete-${var.environment}"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "delete_vpc.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  filename         = data.archive_file.delete_vpc.output_path
  source_code_hash = data.archive_file.delete_vpc.output_base64sha256

  environment {
    variables = {
      TABLE_NAME  = aws_dynamodb_table.vpcs.name
      ENVIRONMENT = var.environment
    }
  }
}
