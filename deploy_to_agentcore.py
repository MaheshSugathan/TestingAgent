#!/usr/bin/env python3
"""
Deploy RAG evaluation agents to AgentCore
This script helps deploy and manage agents in your AgentCore service
"""

import os
import json
import requests
import yaml
import time
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentCoreDeployer:
    """Deploy and manage agents in AgentCore."""
    
    def __init__(self, agentcore_base_url: str = "http://localhost:8000"):
        """Initialize AgentCore deployer.
        
        Args:
            agentcore_base_url: Base URL of AgentCore service
        """
        self.base_url = agentcore_base_url.rstrip('/')
        self.agents_dir = "agentcore_agents"
        
    def deploy_agent(self, agent_name: str, agent_config: Dict[str, Any]) -> bool:
        """Deploy an agent to AgentCore.
        
        Args:
            agent_name: Name of the agent
            agent_config: Agent configuration
            
        Returns:
            True if deployment successful, False otherwise
        """
        try:
            logger.info(f"Deploying agent: {agent_name}")
            
            # Prepare deployment payload
            deployment_payload = {
                "name": agent_name,
                "config": agent_config,
                "deploy": True
            }
            
            # Deploy agent
            response = requests.post(
                f"{self.base_url}/agents/{agent_name}/deploy",
                json=deployment_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully deployed agent: {agent_name}")
                return True
            else:
                logger.error(f"❌ Failed to deploy agent {agent_name}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error deploying agent {agent_name}: {e}")
            return False
    
    def check_agent_health(self, agent_name: str) -> bool:
        """Check if an agent is healthy.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/agents/{agent_name}/health",
                timeout=10
            )
            
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ Agent {agent_name} is healthy: {health_data.get('status')}")
                return True
            else:
                logger.warning(f"⚠️ Agent {agent_name} health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking agent {agent_name} health: {e}")
            return False
    
    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Get agent information.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent information dictionary
        """
        try:
            response = requests.get(
                f"{self.base_url}/agents/{agent_name}/info",
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get info for agent {agent_name}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting info for agent {agent_name}: {e}")
            return {}
    
    def list_agents(self) -> List[str]:
        """List all deployed agents.
        
        Returns:
            List of agent names
        """
        try:
            response = requests.get(f"{self.base_url}/agents", timeout=10)
            
            if response.status_code == 200:
                agents_data = response.json()
                return [agent.get('name') for agent in agents_data.get('agents', [])]
            else:
                logger.error(f"Failed to list agents: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
            return []
    
    def test_agent(self, agent_name: str, test_query: str = "What is machine learning?") -> Dict[str, Any]:
        """Test an agent with a sample query.
        
        Args:
            agent_name: Name of the agent
            test_query: Test query to send
            
        Returns:
            Test response dictionary
        """
        try:
            payload = {
                "query": test_query,
                "session_id": f"test-{int(time.time())}",
                "metadata": {"test": True}
            }
            
            response = requests.post(
                f"{self.base_url}/agents/{agent_name}/invoke",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Agent test failed: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error testing agent {agent_name}: {e}")
            return {"error": str(e)}
    
    def deploy_all_agents(self) -> Dict[str, bool]:
        """Deploy all RAG evaluation agents.
        
        Returns:
            Dictionary of deployment results
        """
        results = {}
        
        # Agent configurations
        agents_config = {
            "retrieval-agent": {
                "entry_point": "retrieval_agent.py",
                "dependencies": ["boto3", "botocore"],
                "environment": {
                    "AWS_REGION": "us-east-1",
                    "S3_BUCKET_NAME": "rag-evaluation-documents"
                },
                "config": {
                    "max_documents": 5,
                    "timeout": 30
                }
            },
            "evaluator-agent": {
                "entry_point": "evaluator_agent.py",
                "dependencies": ["pydantic", "requests"],
                "environment": {
                    "EVALUATION_TYPE": "llm_judge"
                },
                "config": {
                    "evaluation_type": "llm_judge",
                    "timeout": 45
                }
            },
            "dev-agent": {
                "entry_point": "dev_agent.py",
                "dependencies": ["requests", "pydantic"],
                "environment": {
                    "AGENTCORE_BASE_URL": "http://localhost:8000",
                    "BILL_AGENT_NAME": "bill"
                },
                "config": {
                    "timeout": 60,
                    "max_retries": 3
                }
            }
        }
        
        for agent_name, config in agents_config.items():
            logger.info(f"\n🚀 Deploying {agent_name}...")
            results[agent_name] = self.deploy_agent(agent_name, config)
            
            if results[agent_name]:
                # Wait a bit for deployment to complete
                time.sleep(2)
                
                # Check health
                if self.check_agent_health(agent_name):
                    logger.info(f"✅ {agent_name} deployed and healthy")
                else:
                    logger.warning(f"⚠️ {agent_name} deployed but health check failed")
            else:
                logger.error(f"❌ {agent_name} deployment failed")
        
        return results
    
    def run_deployment_tests(self) -> Dict[str, Any]:
        """Run tests on all deployed agents.
        
        Returns:
            Test results dictionary
        """
        test_results = {}
        agents = self.list_agents()
        
        logger.info(f"\n🧪 Running deployment tests on {len(agents)} agents...")
        
        for agent_name in agents:
            logger.info(f"\nTesting {agent_name}...")
            
            # Get agent info
            info = self.get_agent_info(agent_name)
            
            # Test agent
            test_response = self.test_agent(agent_name)
            
            test_results[agent_name] = {
                "info": info,
                "test_response": test_response,
                "healthy": self.check_agent_health(agent_name)
            }
            
            if test_response.get("error"):
                logger.error(f"❌ {agent_name} test failed: {test_response['error']}")
            else:
                logger.info(f"✅ {agent_name} test passed")
        
        return test_results

def main():
    """Main deployment function."""
    print("🚀 AgentCore Deployment Tool")
    print("=" * 50)
    
    # Initialize deployer
    deployer = AgentCoreDeployer()
    
    # Check AgentCore connectivity
    try:
        response = requests.get(f"{deployer.base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ AgentCore service is accessible")
        else:
            print(f"⚠️ AgentCore service returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to AgentCore service: {e}")
        print("💡 Make sure AgentCore is running on the specified URL")
        return
    
    # Deploy all agents
    print("\n📦 Deploying RAG evaluation agents...")
    deployment_results = deployer.deploy_all_agents()
    
    # Show deployment summary
    print("\n📊 Deployment Summary:")
    for agent_name, success in deployment_results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"  {agent_name}: {status}")
    
    # Run tests
    print("\n🧪 Running deployment tests...")
    test_results = deployer.run_deployment_tests()
    
    # Show test summary
    print("\n📋 Test Results:")
    for agent_name, results in test_results.items():
        healthy = "✅ Healthy" if results["healthy"] else "❌ Unhealthy"
        test_status = "✅ Passed" if not results["test_response"].get("error") else "❌ Failed"
        print(f"  {agent_name}: Health={healthy}, Test={test_status}")
    
    # Save results
    results_file = "agentcore_deployment_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "deployment_results": deployment_results,
            "test_results": test_results,
            "timestamp": time.time()
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("\n🎉 Deployment process completed!")

if __name__ == "__main__":
    main()
