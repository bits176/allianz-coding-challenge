output "api_url" {
  description = "API Gateway base URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/vpcs"
}

output "user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "user_pool_client_id" {
  description = "Cognito App Client ID"
  value       = aws_cognito_user_pool_client.main.id
}

output "dynamodb_table" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.vpcs.name
}
