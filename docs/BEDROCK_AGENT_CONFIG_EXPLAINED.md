# 📄 Purpose of `bedrock-agent-simple.json`

## 🎯 Overview

`bedrock-agent-simple.json` is the **configuration file** that defines your Bedrock agent when it was initially created. It contains the essential settings for your agent.

---

## 📋 Current Configuration

```json
{
  "agentName": "rag-evaluation-agent",
  "agentResourceRoleArn": "arn:aws:iam::890742586186:role/BedrockAgentRole",
  "foundationModel": "anthropic.claude-v2",
  "description": "RAG evaluation agent for testing agents using Bedrock",
  "instruction": "You are an AI agent that evaluates RAG..."
}
```

---

## 🔍 What Each Field Means

### **1. agentName**
- **Value**: `"rag-evaluation-agent"`
- **Purpose**: The name of your agent in AWS Bedrock
- **Use**: Identifier for your agent

### **2. agentResourceRoleArn**
- **Value**: `"arn:aws:iam::890742586186:role/BedrockAgentRole"`
- **Purpose**: IAM role that the agent uses to access AWS resources
- **Use**: Gives the agent permissions to:
  - Read from S3
  - Write to CloudWatch
  - Invoke Bedrock models

### **3. foundationModel**
- **Value**: `"anthropic.claude-v2"`
- **Purpose**: The underlying LLM model the agent uses
- **Use**: Claude v2 for text generation and reasoning

### **4. description**
- **Value**: `"RAG evaluation agent for testing agents using Bedrock"`
- **Purpose**: Human-readable description
- **Use**: Helps identify the agent's purpose

### **5. instruction**
- **Value**: The system prompt for the agent
- **Purpose**: Defines the agent's behavior and capabilities
- **Use**: Tells the agent what it should do

---

## 💡 How It Was Used

This file was used when **creating** your Bedrock agent with:

```bash
aws bedrock-agent create-agent \
    --cli-input-json file://bedrock-agent-simple.json \
    --region us-east-1
```

This created your agent with ID `DBW5ST5EOA`.

---

## 🔧 When to Use This File

### **1. Initial Agent Creation** ✅
Used when first deploying your agent to Bedrock.

### **2. Reference Documentation** ✅
Shows what configuration was used to create the agent.

### **3. Updating Agent (Manual)** ⚠️
If you need to update the agent configuration, you could modify this file and run update commands (though the agent is already created).

---

## ⚠️ Important Notes

### **This File is NOT Currently Used**

After the agent was created, this file is primarily:
- ✅ **Documentation** - Shows the original configuration
- ✅ **Reference** - Helps understand agent settings
- ⚠️ **Not actively used** - The agent is already deployed

### **To Update Your Agent**

Since the agent is already deployed:
1. The agent has additional prompt overrides configured
2. The Docker image is what actually runs
3. Changes would need to be made through AWS Console or CLI
4. This file serves as a historical record

---

## 🚀 Current Agent Status

- **Agent ID**: `DBW5ST5EOA`
- **Status**: PREPARED
- **Configuration**: This file was used during creation
- **Current Active Config**: Managed in AWS Bedrock Console

---

## 📝 Summary

**Purpose:**
- ✅ Configuration file used to create your Bedrock agent
- ✅ Documents the initial setup
- ✅ Reference for understanding agent configuration

**Current Status:**
- ⚠️ Agent already created
- ⚠️ This file is now primarily documentation
- ✅ Can be used as reference for creating similar agents

**Key Fields:**
- `agentName`: Identifier for your agent
- `agentResourceRoleArn`: IAM permissions
- `foundationModel`: Claude v2 model
- `instruction`: System prompt defining agent behavior

---

## 🎯 Takeaway

This file is your **agent configuration template** that was used during initial deployment. It's now kept for reference and documentation purposes to understand how your agent was originally configured.

