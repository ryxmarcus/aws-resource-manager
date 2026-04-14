# AWS Resource Manager

Tag-based EC2 and RDS scheduling automation via AWS Lambda and API Gateway.

## Architecture

- **API Gateway (HTTP API):** Provides path-based routing for `/resources/start` and `/resources/stop`.
- **Lambda Function:** Identifies resources based on tags and executes start/stop operations.
- **IAM:** Least-privilege role for EC2, RDS, and Tagging operations.

## Setup & Deployment

### Prerequisites
- AWS CLI configured with appropriate credentials.
- AWS SAM CLI installed.
- Python 3.12 installed.

### Build and Deploy
```bash
sam build
sam deploy --guided
```

## Usage

### Start Resources
Send a POST request to `/resources/start` with tag filters:
```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/resources/start \
     -H "Content-Type: application/json" \
     -d '{"tags": {"Environment": "dev", "Schedule": "true"}}'
```

### Stop Resources
Send a POST request to `/resources/stop` with tag filters:
```bash
curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/resources/stop \
     -H "Content-Type: application/json" \
     -d '{"tags": {"Environment": "dev"}}'
```

## Tagging Updates
After execution, the Lambda function updates the following tags on the target resources:
- `LastAction`: "Started" or "Stopped"
- `LastActionTime`: UTC timestamp of the operation.
