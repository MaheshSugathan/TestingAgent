# Terraform Infrastructure Guide

This guide shows you how to use Terraform to manage your AWS infrastructure for the Bedrock Agent Core deployment, making it easy to create and destroy resources to minimize costs.

## 📋 Quick Start

### 1. Deploy Infrastructure

```bash
cd terraform
./deploy.sh
```

This will:
- Create ECR repository
- Create IAM roles
- Create S3 bucket for CodeBuild
- Create CloudWatch log groups

### 2. Deploy Your Agent

After infrastructure is created, deploy your agent:

```bash
cd ..
agentcore launch
```

### 3. Test Your Agent

```bash
agentcore invoke '{"prompt": "What is RAG?"}'
```

### 4. Clean Up Everything (Stop All Costs)

When you're done testing, destroy everything:

```bash
cd terraform
./cleanup-all.sh
```

This removes:
- ✅ Terraform infrastructure (ECR, IAM, S3, CloudWatch)
- ✅ Bedrock Agent Core runtime

## 🔧 Manual Steps

### Deploy Infrastructure Manually

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Destroy Infrastructure Manually

```bash
cd terraform
terraform destroy
```

### Delete Agent Core Runtime Manually

```bash
agentcore delete --agent-name rag_evaluation_agent
```

## 📊 Cost Savings

By using Terraform:

- **Easy cleanup**: One command removes everything
- **No orphaned resources**: Terraform tracks all resources
- **S3 lifecycle**: Automatically deletes old files after 7 days
- **CloudWatch retention**: Logs retained for only 7 days

## ⚠️ Important Notes

1. **Always destroy after testing** to avoid ongoing costs
2. **The Agent Core runtime** is created by `agentcore launch`, not Terraform
3. **Use `cleanup-all.sh`** to remove both Terraform resources AND the runtime
4. **ECR images are deleted** when you destroy - make sure you have backups if needed

## 🛠️ Troubleshooting

### Terraform state locked

If you see a lock error:
```bash
terraform force-unlock <lock-id>
```

### Resources already exist

If resources already exist from previous deployments:
1. Import them into Terraform state, OR
2. Delete them manually first, then run `terraform apply`

### Agent Core runtime won't delete

If `agentcore delete` fails:
```bash
# Check status first
agentcore status

# Try deleting with force
agentcore delete --agent-name rag_evaluation_agent --force
```

## 📝 Configuration

Edit `terraform/terraform.tfvars` to customize:
- AWS region
- Agent name
- Resource tags
- Retention periods

## 💡 Best Practices

1. **Always review `terraform plan`** before applying
2. **Use tags** to track resources
3. **Set up billing alerts** in AWS Console
4. **Destroy immediately** after testing
5. **Keep terraform state** in version control (or use remote state)

