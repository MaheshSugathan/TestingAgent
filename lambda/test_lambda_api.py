#!/usr/bin/env python3
"""
Test script for Lambda API with Cognito authentication.
Usage: python test_lambda_api.py
"""

import boto3
import requests
import json
import sys
import os
from typing import Optional

# Configuration - Update these values from Terraform outputs
USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")
API_URL = os.getenv("API_GATEWAY_URL", "")
USERNAME = os.getenv("COGNITO_USERNAME", "testuser")
PASSWORD = os.getenv("COGNITO_PASSWORD", "")


def authenticate(username: str, password: str) -> Optional[str]:
    """Authenticate with Cognito and return ID token."""
    try:
        cognito = boto3.client('cognito-idp')
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        return response['AuthenticationResult']['IdToken']
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None


def invoke_agent_core(id_token: str, input_text: str, session_id: str = None) -> dict:
    """Invoke the Agent Core API via Lambda."""
    headers = {
        'Authorization': f'Bearer {id_token}',
        'Content-Type': 'application/json'
    }

    payload = {
        'inputText': input_text
    }
    
    if session_id:
        payload['sessionId'] = session_id

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return {}


def main():
    """Main test function."""
    # Validate configuration
    if not all([USER_POOL_ID, CLIENT_ID, API_URL]):
        print("Error: Missing required environment variables:")
        print("  - COGNITO_USER_POOL_ID")
        print("  - COGNITO_CLIENT_ID")
        print("  - API_GATEWAY_URL")
        print("\nSet these from Terraform outputs:")
        print("  export COGNITO_USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)")
        print("  export COGNITO_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id)")
        print("  export API_GATEWAY_URL=$(terraform output -raw api_gateway_url)")
        sys.exit(1)

    if not PASSWORD:
        print("Error: COGNITO_PASSWORD environment variable not set")
        print("  export COGNITO_PASSWORD='YourSecurePass123!'")
        sys.exit(1)

    print("🔐 Authenticating with Cognito...")
    id_token = authenticate(USERNAME, PASSWORD)
    
    if not id_token:
        print("❌ Authentication failed")
        sys.exit(1)
    
    print("✅ Authentication successful")
    print(f"\n📡 Invoking Agent Core API: {API_URL}")
    
    # Test query
    test_query = "What is RAG evaluation?"
    session_id = "test-session-python"
    
    print(f"Query: {test_query}")
    print(f"Session ID: {session_id}\n")
    
    result = invoke_agent_core(id_token, test_query, session_id)
    
    if result:
        print("✅ Response received:")
        print(json.dumps(result, indent=2))
    else:
        print("❌ No response received")
        sys.exit(1)


if __name__ == "__main__":
    main()

