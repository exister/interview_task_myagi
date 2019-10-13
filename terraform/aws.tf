provider "aws" {
  version = "~> 2.32"
}

resource "aws_iam_role" "iam_for_lambda" {
  name = "iam_for_lambda"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

variable "lambda_zip_path" {
  type = "string"
  default = "../tickers/dist/2019-10-13-161125-TickerService.zip"
}

resource "aws_lambda_function" "ticker" {
  filename = var.lambda_zip_path
  function_name = "TickerService"
  role = aws_iam_role.iam_for_lambda.arn
  handler = "service.handler"
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout = 600
  runtime = "python3.6"
}


resource "aws_api_gateway_rest_api" "ticker" {
  name = "TickerServiceAPI"
  description = "TickerService API"
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_lambda_permission" "apigw" {
  statement_id = "AllowAPIGatewayInvoke"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ticker.function_name
  principal = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.ticker.execution_arn}/*/*"
}

resource "aws_api_gateway_resource" "company" {
  rest_api_id = aws_api_gateway_rest_api.ticker.id
  parent_id = aws_api_gateway_rest_api.ticker.root_resource_id
  path_part = "company"
}

resource "aws_api_gateway_method" "tickers_list" {
  rest_api_id = aws_api_gateway_rest_api.ticker.id
  resource_id = aws_api_gateway_resource.company.id
  http_method = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "tickers_list" {
  rest_api_id = aws_api_gateway_rest_api.ticker.id
  resource_id = aws_api_gateway_method.tickers_list.resource_id
  http_method = aws_api_gateway_method.tickers_list.http_method

  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri = aws_lambda_function.ticker.invoke_arn
}

resource "aws_api_gateway_resource" "company_details" {
  rest_api_id = aws_api_gateway_rest_api.ticker.id
  parent_id = aws_api_gateway_resource.company.id
  path_part = "{ticker}"
}

resource "aws_api_gateway_method" "ticker_details" {
  rest_api_id = aws_api_gateway_rest_api.ticker.id
  resource_id = aws_api_gateway_resource.company_details.id
  http_method = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "ticker_details" {
  rest_api_id = aws_api_gateway_rest_api.ticker.id
  resource_id = aws_api_gateway_method.ticker_details.resource_id
  http_method = aws_api_gateway_method.ticker_details.http_method

  integration_http_method = "POST"
  type = "AWS_PROXY"
  uri = aws_lambda_function.ticker.invoke_arn
}

resource "aws_api_gateway_deployment" "ticker" {
  depends_on = [
    "aws_api_gateway_integration.tickers_list",
    "aws_api_gateway_integration.ticker_details",
  ]

  rest_api_id = aws_api_gateway_rest_api.ticker.id
  stage_name = "test"
}

output "base_url" {
  value = aws_api_gateway_deployment.ticker.invoke_url
}