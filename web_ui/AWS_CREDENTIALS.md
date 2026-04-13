# AWS Credentials Configuration for Web UI

## How the Web App Connects to AWS

The web app backend uses **boto3** to connect to AWS Bedrock Agent Core. Boto3 follows the **AWS credential chain** to automatically find and use your AWS credentials.

## Current Configuration

Typical local setup (replace with your own values from `aws sts get-caller-identity` and `aws configure list`):

**Credential Source**: `~/.aws/credentials` (shared-credentials-file)  
**AWS profile**: `default` (or the profile you set in `AWS_PROFILE`)  
**Account**: *(run `aws sts get-caller-identity --query Account --output text`)*  
**Region**: `us-east-1` (from `~/.aws/config` or `AWS_REGION`)

## How It Works

In `backend/main.py`, the code creates a boto3 client:

```python
def get_bedrock_client():
    """Get or create Bedrock Agent Core client."""
    global bedrock_client
    if bedrock_client is None:
        region = os.getenv("AWS_REGION", "us-east-1")
        bedrock_client = boto3.client('bedrock-agentcore', region_name=region)
    return bedrock_client
```

When `boto3.client()` is called **without explicit credentials**, it automatically searches for credentials in this order:

## AWS Credential Chain (Priority Order)

### 1. Environment Variables (Highest Priority)
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_SESSION_TOKEN=your_session_token  # For temporary credentials
export AWS_REGION=us-east-1
```

### 2. AWS Credentials File (`~/.aws/credentials`)
```ini
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

### 3. AWS Config File (`~/.aws/config`)
```ini
[default]
region = us-east-1
```

### 4. IAM Role (if running on EC2/ECS/Lambda)
- Automatically assumed if running on AWS infrastructure
- No credentials needed in code

### 5. AWS SSO (if configured)
- Uses AWS SSO credentials after login

## Current Setup

Example local setup:
- **Source**: `~/.aws/credentials` file
- **Profile**: `default`
- **Identity**: *(IAM user or role from `aws sts get-caller-identity`)*
- **Region**: `us-east-1`

## Required IAM Permissions

Your AWS user needs these permissions to invoke Agent Core Runtime:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:*:*:runtime/*"
            ]
        }
    ]
}
```

## Verifying Your Credentials

Check which credentials are being used:

```bash
# Check current AWS identity
aws sts get-caller-identity

# Check credential configuration
aws configure list

# Test Agent Core access
aws bedrock-agentcore list-runtimes --region us-east-1
```

## Changing Credentials

### Option 1: Use Different AWS Profile

```bash
# Set profile in environment
export AWS_PROFILE=my-profile

# Or modify backend code to use profile:
bedrock_client = boto3.Session(profile_name='my-profile').client('bedrock-agentcore', region_name=region)
```

### Option 2: Use Environment Variables

```bash
export AWS_ACCESS_KEY_ID=your_new_key
export AWS_SECRET_ACCESS_KEY=your_new_secret
export AWS_REGION=us-east-1

# Restart backend
```

### Option 3: Use Temporary Credentials (STS)

```bash
# Assume role
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/MyRole \
  --role-session-name web-ui-session

# Export temporary credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

## Security Best Practices

1. **Never commit credentials to code**
   - ✅ Use `~/.aws/credentials` (already in `.gitignore`)
   - ✅ Use environment variables
   - ❌ Don't hardcode in Python files

2. **Use IAM roles when possible**
   - If deploying to EC2/ECS, use IAM roles instead of access keys

3. **Rotate credentials regularly**
   - Update credentials in `~/.aws/credentials`
   - Restart backend after updating

4. **Use least privilege**
   - Only grant `bedrock-agentcore:InvokeAgentRuntime` permission
   - Don't use admin credentials

## Troubleshooting

### Error: "Unable to locate credentials"

**Solution**: Ensure credentials are configured:
```bash
aws configure
# Or set environment variables
```

### Error: "Access Denied"

**Solution**: Check IAM permissions:
```bash
# Verify permissions
aws iam get-user-policy --user-name YOUR_IAM_USER --policy-name YourPolicy

# Test access
aws bedrock-agentcore list-runtimes --region us-east-1
```

### Error: "Invalid region"

**Solution**: Set correct region:
```bash
export AWS_REGION=us-east-1
# Or update ~/.aws/config
```

## Code Location

The credential handling is in:
- **File**: `web_ui/backend/main.py`
- **Function**: `get_bedrock_client()` (line 26-32)
- **Client creation**: `boto3.client('bedrock-agentcore', region_name=region)`

No explicit credentials are passed, so boto3 uses the credential chain automatically.

