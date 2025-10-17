#!/usr/bin/env python3
"""
Test AgentCore deployed agents
This script tests the deployed RAG evaluation agents in AgentCore
"""

import requests
import json
import time
import asyncio
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentCoreTester:
    """Test deployed agents in AgentCore."""
    
    def __init__(self, agentcore_base_url: str = "http://localhost:8000"):
        """Initialize AgentCore tester.
        
        Args:
            agentcore_base_url: Base URL of AgentCore service
        """
        self.base_url = agentcore_base_url.rstrip('/')
        self.session_id = f"test-session-{int(time.time())}"
    
    def test_agent_health(self, agent_name: str) -> bool:
        """Test agent health.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/agents/{agent_name}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"✅ {agent_name} health: {health_data.get('status')}")
                return True
            else:
                logger.error(f"❌ {agent_name} health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ {agent_name} health check error: {e}")
            return False
    
    def test_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Test agent info endpoint.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent info dictionary
        """
        try:
            response = requests.get(f"{self.base_url}/agents/{agent_name}/info", timeout=5)
            if response.status_code == 200:
                info = response.json()
                logger.info(f"✅ {agent_name} info: {info.get('name')} v{info.get('version')}")
                return info
            else:
                logger.error(f"❌ {agent_name} info failed: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"❌ {agent_name} info error: {e}")
            return {}
    
    def test_retrieval_agent(self) -> Dict[str, Any]:
        """Test retrieval agent.
        
        Returns:
            Test results dictionary
        """
        logger.info("\n🔍 Testing Retrieval Agent...")
        
        payload = {
            "query": "What is machine learning?",
            "session_id": self.session_id,
            "max_documents": 3,
            "metadata": {"test": True}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/agents/retrieval-agent/invoke",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Retrieved {len(result.get('documents', []))} documents")
                logger.info(f"   Retrieval time: {result.get('retrieval_time', 0):.3f}s")
                return {"success": True, "data": result}
            else:
                logger.error(f"❌ Retrieval agent failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Retrieval agent error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_dev_agent(self) -> Dict[str, Any]:
        """Test dev agent.
        
        Returns:
            Test results dictionary
        """
        logger.info("\n🤖 Testing Dev Agent...")
        
        payload = {
            "query": "What is machine learning?",
            "context": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            "session_id": self.session_id,
            "metadata": {"test": True}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/agents/dev-agent/invoke",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Generated response: {result.get('response', '')[:50]}...")
                logger.info(f"   Confidence: {result.get('confidence', 'N/A')}")
                logger.info(f"   Execution time: {result.get('execution_time', 0):.3f}s")
                return {"success": True, "data": result}
            else:
                logger.error(f"❌ Dev agent failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Dev agent error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_evaluator_agent(self) -> Dict[str, Any]:
        """Test evaluator agent.
        
        Returns:
            Test results dictionary
        """
        logger.info("\n📊 Testing Evaluator Agent...")
        
        payload = {
            "query": "What is machine learning?",
            "context": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            "response": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
            "session_id": self.session_id,
            "evaluation_type": "llm_judge",
            "metadata": {"test": True}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/agents/evaluator-agent/invoke",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                scores = result.get('scores', {})
                logger.info(f"✅ Evaluation completed")
                logger.info(f"   Scores: {scores}")
                logger.info(f"   Evaluation time: {result.get('evaluation_time', 0):.3f}s")
                return {"success": True, "data": result}
            else:
                logger.error(f"❌ Evaluator agent failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Evaluator agent error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_full_rag_pipeline(self) -> Dict[str, Any]:
        """Test full RAG pipeline with all agents.
        
        Returns:
            Pipeline test results
        """
        logger.info("\n🔄 Testing Full RAG Pipeline...")
        
        pipeline_results = {
            "session_id": self.session_id,
            "start_time": time.time(),
            "steps": {}
        }
        
        # Step 1: Retrieval
        retrieval_result = self.test_retrieval_agent()
        pipeline_results["steps"]["retrieval"] = retrieval_result
        
        if not retrieval_result["success"]:
            pipeline_results["error"] = "Retrieval step failed"
            return pipeline_results
        
        # Extract context from retrieval
        documents = retrieval_result["data"].get("documents", [])
        context = "\n\n".join([doc.get("content", "") for doc in documents])
        
        # Step 2: Dev Agent (Response Generation)
        dev_payload = {
            "query": "What is machine learning?",
            "context": context,
            "session_id": self.session_id,
            "metadata": {"test": True, "pipeline": True}
        }
        
        try:
            dev_response = requests.post(
                f"{self.base_url}/agents/dev-agent/invoke",
                json=dev_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if dev_response.status_code == 200:
                dev_result = dev_response.json()
                pipeline_results["steps"]["dev"] = {"success": True, "data": dev_result}
            else:
                pipeline_results["steps"]["dev"] = {"success": False, "error": f"HTTP {dev_response.status_code}"}
                
        except Exception as e:
            pipeline_results["steps"]["dev"] = {"success": False, "error": str(e)}
        
        # Step 3: Evaluation
        if pipeline_results["steps"]["dev"]["success"]:
            eval_payload = {
                "query": "What is machine learning?",
                "context": context,
                "response": pipeline_results["steps"]["dev"]["data"].get("response", ""),
                "session_id": self.session_id,
                "evaluation_type": "llm_judge",
                "metadata": {"test": True, "pipeline": True}
            }
            
            try:
                eval_response = requests.post(
                    f"{self.base_url}/agents/evaluator-agent/invoke",
                    json=eval_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if eval_response.status_code == 200:
                    eval_result = eval_response.json()
                    pipeline_results["steps"]["evaluation"] = {"success": True, "data": eval_result}
                else:
                    pipeline_results["steps"]["evaluation"] = {"success": False, "error": f"HTTP {eval_response.status_code}"}
                    
            except Exception as e:
                pipeline_results["steps"]["evaluation"] = {"success": False, "error": str(e)}
        
        pipeline_results["end_time"] = time.time()
        pipeline_results["total_time"] = pipeline_results["end_time"] - pipeline_results["start_time"]
        
        # Calculate success rate
        successful_steps = sum(1 for step in pipeline_results["steps"].values() if step.get("success", False))
        total_steps = len(pipeline_results["steps"])
        pipeline_results["success_rate"] = (successful_steps / total_steps) * 100 if total_steps > 0 else 0
        
        logger.info(f"✅ Pipeline completed: {successful_steps}/{total_steps} steps successful ({pipeline_results['success_rate']:.1f}%)")
        logger.info(f"   Total time: {pipeline_results['total_time']:.3f}s")
        
        return pipeline_results
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all agent tests.
        
        Returns:
            Complete test results
        """
        logger.info("🧪 Starting AgentCore Deployment Tests")
        logger.info("=" * 50)
        
        # Test agent health and info
        agents = ["retrieval-agent", "dev-agent", "evaluator-agent"]
        health_results = {}
        info_results = {}
        
        for agent in agents:
            health_results[agent] = self.test_agent_health(agent)
            info_results[agent] = self.test_agent_info(agent)
        
        # Test individual agents
        individual_results = {
            "retrieval": self.test_retrieval_agent(),
            "dev": self.test_dev_agent(),
            "evaluator": self.test_evaluator_agent()
        }
        
        # Test full pipeline
        pipeline_results = self.test_full_rag_pipeline()
        
        # Compile results
        all_results = {
            "timestamp": time.time(),
            "session_id": self.session_id,
            "health_results": health_results,
            "info_results": info_results,
            "individual_results": individual_results,
            "pipeline_results": pipeline_results,
            "summary": {
                "total_agents": len(agents),
                "healthy_agents": sum(health_results.values()),
                "successful_individual_tests": sum(1 for result in individual_results.values() if result["success"]),
                "pipeline_success_rate": pipeline_results.get("success_rate", 0)
            }
        }
        
        return all_results

def main():
    """Main test function."""
    print("🧪 AgentCore Deployment Tester")
    print("=" * 50)
    
    # Initialize tester
    tester = AgentCoreTester()
    
    # Check AgentCore connectivity
    try:
        response = requests.get(f"{tester.base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ AgentCore service is accessible")
        else:
            print(f"⚠️ AgentCore service returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to AgentCore service: {e}")
        print("💡 Make sure AgentCore is running and agents are deployed")
        return
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Print summary
    print("\n📊 Test Summary:")
    print(f"   Healthy Agents: {results['summary']['healthy_agents']}/{results['summary']['total_agents']}")
    print(f"   Individual Tests: {results['summary']['successful_individual_tests']}/3")
    print(f"   Pipeline Success Rate: {results['summary']['pipeline_success_rate']:.1f}%")
    
    # Save results
    results_file = "agentcore_test_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    main()
