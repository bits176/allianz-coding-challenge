# ---------- API Gateway (REST) ----------
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-${var.environment}"
  description = "VPC Management API"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = "*"
      Action    = "execute-api:Invoke"
      Resource  = "arn:aws:execute-api:${var.aws_region}:*:*/*/*/*"
      Condition = {
        IpAddress = {
          "aws:SourceIp" = [var.allowed_cidr]
        }
      }
    }]
  })
}

# /vpcs resource
resource "aws_api_gateway_resource" "vpcs" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "vpcs"
}

# /vpcs/{vpc_id} resource
resource "aws_api_gateway_resource" "vpc_by_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.vpcs.id
  path_part   = "{vpc_id}"
}

# ---------- Cognito Authorizer ----------
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "cognito-auth"
  rest_api_id     = aws_api_gateway_rest_api.main.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [aws_cognito_user_pool.main.arn]
  identity_source = "method.request.header.Authorization"
}

# ---------- POST /vpcs ----------
resource "aws_api_gateway_method" "create_vpc" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.vpcs.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "create_vpc" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.vpcs.id
  http_method             = aws_api_gateway_method.create_vpc.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.create_vpc.invoke_arn
}

# ---------- GET /vpcs ----------
resource "aws_api_gateway_method" "list_vpcs" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.vpcs.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "list_vpcs" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.vpcs.id
  http_method             = aws_api_gateway_method.list_vpcs.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.get_vpcs.invoke_arn
}

# ---------- GET /vpcs/{vpc_id} ----------
resource "aws_api_gateway_method" "get_vpc" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.vpc_by_id.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_vpc" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.vpc_by_id.id
  http_method             = aws_api_gateway_method.get_vpc.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.get_vpcs.invoke_arn
}

# ---------- DELETE /vpcs/{vpc_id} ----------
resource "aws_api_gateway_method" "delete_vpc" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.vpc_by_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "delete_vpc" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.vpc_by_id.id
  http_method             = aws_api_gateway_method.delete_vpc.http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.delete_vpc.invoke_arn
}

# ---------- Deployment ----------
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  # Redeploy when any method/integration/policy changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_rest_api.main.policy,
      aws_api_gateway_method.create_vpc,
      aws_api_gateway_integration.create_vpc,
      aws_api_gateway_method.list_vpcs,
      aws_api_gateway_integration.list_vpcs,
      aws_api_gateway_method.get_vpc,
      aws_api_gateway_integration.get_vpc,
      aws_api_gateway_method.delete_vpc,
      aws_api_gateway_integration.delete_vpc,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  deployment_id = aws_api_gateway_deployment.main.id
  stage_name    = var.environment
}

# ---------- Lambda Permissions (allow API GW to invoke) ----------
resource "aws_lambda_permission" "create_vpc" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_vpc.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "get_vpcs" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_vpcs.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "delete_vpc" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_vpc.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}
