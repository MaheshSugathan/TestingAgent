# Terraform Infrastructure for Bedrock Agent Core

This Terraform configuration creates the necessary AWS infrastructure for deploying your RAG evaluation agent to AWS Bedrock Agent Core.

## 📋 Prerequisites

1. **Terraform installed** (>= 1.0)
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. **AWS CLI configured** with appropriate credentials
   ```bash
   aws configure
   ```

3. **AWS Account** with permissions for:
   - ECR (Elastic Container Registry)
   - IAM (roles and policies)
   - S3 (for CodeBuild sources)
   - CloudWatch (logs)
   - Bedrock Agent Core

## 🚀 Quick Start

### 1. Initialize Terraform

```bash
cd terraform
terraform init
```

### 2. Configure Variables

Copy the example variables file and customize:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

### 3. Review the Plan

```bash
terraform plan
```

### 4. Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted to create the resources.

### 5. Get Output Values

After deployment, Terraform will output important values:

```bash
terraform output
```

Save these values - you'll need them for the agentcore configuration.

### 6. Update agentcore Configuration

After Terraform creates the resources, update your `.bedrock_agentcore.yaml`:

```yaml
agents:
  rag_evaluation_agent:
    aws:
      execution_role: <runtime_execution_role_arn from terraform output>
      ecr_repository: <ecr_repository_url from terraform output>
      ecr_auto_create: false
      execution_role_auto_create: false
```

### 7. Deploy Your Agent

```bash
cd ..
agentcore launch
```

## 🧹 Cleanup (Destroy Infrastructure)

**⚠️ IMPORTANT: This will delete ALL resources created by Terraform!**

To remove all infrastructure and stop incurring costs:

```bash
cd terraform
terraform destroy
```

Type `yes` when prompted. This will:
- Delete the ECR repository (and all images)
- Delete IAM roles and policies
- Delete S3 bucket (and all contents)
- Delete CloudWatch log groups

**Note:** The Bedrock Agent Core runtime itself needs to be deleted separately:

```bash
cd ..
agentcore delete --agent-name rag_evaluation_agent
```

## 📊 What Gets Created

### Resources Created:

1. **ECR Repository**
   - Stores your Docker container images
   - Name: `bedrock-agentcore-rag_evaluation_agent`

2. **IAM Roles**
   - `AmazonBedrockAgentCoreSDKRuntime-*` - For running the agent
   - `AmazonBedrockAgentCoreSDKCodeBuild-*` - For building containers

3. **S3 Bucket**
   - Stores CodeBuild source code
   - Name: `bedrock-agentcore-codebuild-sources-{account}-{region}`
   - Lifecycle policy: Deletes objects after 7 days

4. **CloudWatch Log Group**
   - Stores agent runtime logs
   - Retention: 7 days

## 💰 Cost Optimization

- **S3 Lifecycle Policy**: Automatically deletes old CodeBuild sources after 7 days
- **CloudWatch Log Retention**: Logs are retained for only 7 days
- **Easy Cleanup**: Run `terraform destroy` when done testing

## 🔧 Customization

Edit `terraform.tfvars` to customize:
- AWS region
- Agent name
- Resource tags
- Retention periods

## 📝 Notes

- The Bedrock Agent Core runtime itself is created by the `agentcore` CLI tool, not Terraform
- After running `terraform apply`, you still need to deploy your agent using `agentcore launch`
- Always run `terraform destroy` after testing to avoid unnecessary costs

