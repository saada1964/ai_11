#!/usr/bin/env python3
"""
Comprehensive testing script for hierarchical tools and sub-agents system
"""
import asyncio
import json
from typing import Dict, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.sub_agents import (
    SubAgent, SpecialistAgent, CoordinatorAgent, ExecutorAgent,
    AgentType, AgentStatus, hierarchical_tool_manager
)
from core.tools import tool_registry
from core.planner import Planner
from config.logger import logger


class HierarchicalToolsTestSuite:
    """Test suite for hierarchical tools and sub-agents"""
    
    def __init__(self):
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    async def run_all_tests(self):
        """Run all hierarchical tools tests"""
        logger.info("Starting Hierarchical Tools Test Suite...")
        
        # Test Sub-Agent System
        await self.test_sub_agent_system()
        
        # Test Agent Registration and Management
        await self.test_agent_management()
        
        # Test Hierarchical Tool Registration
        await self.test_hierarchical_tool_registration()
        
        # Test Agent Execution
        await self.test_agent_execution()
        
        # Test Tool Optimization
        await self.test_tool_optimization()
        
        # Test Hierarchical Task Execution
        await self.test_hierarchical_execution()
        
        # Test System Status and Monitoring
        await self.test_system_monitoring()
        
        # Test Edge Cases
        await self.test_edge_cases()
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    async def test_sub_agent_system(self):
        """Test sub-agent system core functionality"""
        test_name = "Sub-Agent System Core"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Create specialist agent
            specialist = SpecialistAgent("test_spec_001", "test_domain", "Test Specialist", "Test specialist agent")
            assert specialist.agent_id == "test_spec_001", "Agent ID should be set correctly"
            assert specialist.agent_type == AgentType.SPECIALIST, "Agent type should be specialist"
            assert specialist.domain == "test_domain", "Domain should be set correctly"
            await self._record_test_result(test_name, "Specialist Agent Creation", True, "Specialist agent created successfully")
            
            # Test 2: Create coordinator agent
            coordinator = CoordinatorAgent("test_coord_001", "Test Coordinator", "Test coordination agent")
            assert coordinator.agent_type == AgentType.COORDINATOR, "Agent type should be coordinator"
            await self._record_test_result(test_name, "Coordinator Agent Creation", True, "Coordinator agent created successfully")
            
            # Test 3: Create executor agent
            executor = ExecutorAgent("test_exec_001", "Test Executor", "Test execution agent")
            assert executor.agent_type == AgentType.EXECUTOR, "Agent type should be executor"
            await self._record_test_result(test_name, "Executor Agent Creation", True, "Executor agent created successfully")
            
            # Test 4: Agent status management
            specialist.update_status(AgentStatus.BUSY)
            assert specialist.status == AgentStatus.BUSY, "Agent status should be updated"
            specialist.update_status(AgentStatus.COMPLETED)
            assert specialist.status == AgentStatus.COMPLETED, "Agent status should be completed"
            await self._record_test_result(test_name, "Agent Status Management", True, "Status transitions work correctly")
            
            # Test 5: Agent memory system
            specialist.add_to_memory("test_key", "test_value")
            memory_value = specialist.get_from_memory("test_key")
            assert memory_value == "test_value", "Memory should be stored and retrieved correctly"
            await self._record_test_result(test_name, "Agent Memory System", True, "Memory operations work correctly")
            
            # Test 6: Execution history
            test_task = {"type": "test", "data": {}}
            test_result = {"status": "success", "execution_time": 1.0}
            specialist.record_execution(test_task, test_result)
            assert len(specialist.execution_history) == 1, "Execution should be recorded"
            await self._record_test_result(test_name, "Execution History", True, "History tracking works correctly")
            
        except Exception as e:
            await self._record_test_result(test_name, "System Core Tests", False, str(e))
    
    async def test_agent_management(self):
        """Test agent registration and management"""
        test_name = "Agent Management"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Agent registration
            

            test_agent = SpecialistAgent("test_agent_001", "test", "Test Agent", "Test agent")
            hierarchical_tool_manager.register_agent(test_agent)
            
            registered_agent = hierarchical_tool_manager.get_agent("test_agent_001")
            assert registered_agent is not None, "Agent should be registered"
            assert registered_agent.agent_id == "test_agent_001", "Registered agent ID should match"
            await self._record_test_result(test_name, "Agent Registration", True, "Agent registered successfully")
            
            # Test 2: Get agents by type
            specialist_agents = hierarchical_tool_manager.get_agents_by_type(AgentType.SPECIALIST)
            assert len(specialist_agents) > 0, "Should have specialist agents"
            await self._record_test_result(test_name, "Get Agents by Type", True, 
                                        f"Found {len(specialist_agents)} specialist agents")
            
            # Test 3: Tool hierarchy creation
            hierarchical_tool_manager.create_tool_hierarchy(
                "test_hierarchy", 
                "coord_001", 
                ["research_001", "web_001", "data_001"]
            )
            
            assert "test_hierarchy" in hierarchical_tool_manager.tool_hierarchies, "Hierarchy should be created"
            await self._record_test_result(test_name, "Tool Hierarchy Creation", True, "Hierarchy created successfully")
            
            # Test 4: System status
            status = hierarchical_tool_manager.get_system_status()
            assert "total_agents" in status, "Status should contain agent count"
            assert status["total_agents"] > 0, "Should have at least one agent"
            await self._record_test_result(test_name, "System Status", True, 
                                        f"System status: {status['total_agents']} agents, {status['system_health']}")
            
        except Exception as e:
            await self._record_test_result(test_name, "Management Tests", False, str(e))
    
    async def test_hierarchical_tool_registration(self):
        """Test hierarchical tool registration"""
        test_name = "Hierarchical Tool Registration"
        logger.info(f"Running {test_name}...")
        
        try:
            

            # Test 1: Register hierarchical tool
            test_agent = hierarchical_tool_manager.get_agent("research_001")
            if test_agent:
                tool_config = {
                    "name": "test_hierarchical_tool",
                    "description": "Test hierarchical tool",
                    "function_name": "test_function",
                    "price_usd": 0.001
                }
                
                tool_registry.register_hierarchical_tool(tool_config, test_agent)
                
                assert "test_hierarchical_tool" in tool_registry.agent_powered_tools, "Tool should be registered"
                registered_agent = tool_registry.agent_powered_tools["test_hierarchical_tool"]
                assert registered_agent.agent_id == test_agent.agent_id, "Agent should be linked correctly"
                
                await self._record_test_result(test_name, "Hierarchical Tool Registration", True, "Tool registered successfully")
            
            # Test 2: Tool capabilities
            capabilities = tool_registry.get_tool_capabilities("test_hierarchical_tool")
            assert isinstance(capabilities, list), "Capabilities should be a list"
            await self._record_test_result(test_name, "Tool Capabilities", True, 
                                        f"Capabilities: {capabilities}")
            
            # Test 3: Default hierarchical tools
            default_hierarchical_tools = ["research_workflow", "web_analysis", "data_processing", "complex_executor"]
            for tool_name in default_hierarchical_tools:
                if tool_name in tool_registry.agent_powered_tools:
                    await self._record_test_result(test_name, f"Default Tool {tool_name}", True, 
                                                "Default hierarchical tool available")
            
        except Exception as e:
            await self._record_test_result(test_name, "Registration Tests", False, str(e))
    
    async def test_agent_execution(self):
        """Test agent execution functionality"""
        test_name = "Agent Execution"
        logger.info(f"Running {test_name}...")
        
        try:
            

            # Test 1: Specialist agent execution
            test_agent = SpecialistAgent("exec_test_001", "test", "Execution Test Agent", "Test execution")
            hierarchical_tool_manager.register_agent(test_agent)
            
            test_task = {
                "type": "domain_analysis",
                "data": {"input": "test data"}
            }
            
            result = await test_agent.execute(test_task)
            
            assert result.get("status") == "completed", "Task should complete successfully"
            assert result.get("agent_id") == test_agent.agent_id, "Agent ID should be in result"
            assert "execution_time" in result, "Execution time should be recorded"
            
            await self._record_test_result(test_name, "Specialist Agent Execution", True, 
                                        f"Executed in {result.get('execution_time', 0):.3f}s")
            
            # Test 2: Coordinator agent execution
            coord_agent = hierarchical_tool_manager.get_agent("coord_001")
            if coord_agent:
                coord_task = {
                    "type": "load_balancing",
                    "data": {}
                }
                
                coord_result = await coord_agent.execute(coord_task)
                assert coord_result.get("load_balancing") == True, "Load balancing should be performed"
                
                await self._record_test_result(test_name, "Coordinator Agent Execution", True, 
                                            "Coordinator executed task successfully")
            
            # Test 3: Executor agent execution
            exec_agent = hierarchical_tool_manager.get_agent("exec_001")
            if exec_agent:
                exec_task = {
                    "type": "direct",
                    "data": {"operation": "test"}
                }
                
                exec_result = await exec_agent.execute(exec_task)
                assert exec_result.get("execution_type") == "direct", "Direct execution type should be set"
                
                await self._record_test_result(test_name, "Executor Agent Execution", True, 
                                            "Executor executed task successfully")
            
        except Exception as e:
            await self._record_test_result(test_name, "Execution Tests", False, str(e))
    
    async def test_tool_optimization(self):
        """Test tool optimization functionality"""
        test_name = "Tool Optimization"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Tool selection optimization
            task_description = "Research Python tutorials and analyze web content"
            available_tools = ["web_search_serper", "research_workflow", "web_analysis", "advanced_calculator"]
            
            optimization_result = await tool_registry.optimize_tool_selection(
                task_description=task_description,
                available_tools=available_tools
            )
            
            assert "recommended_tools" in optimization_result, "Should have recommended tools"
            recommended = optimization_result["recommended_tools"]
            assert len(recommended) > 0, "Should recommend at least one tool"
            
            await self._record_test_result(test_name, "Tool Selection Optimization", True, 
                                        f"Recommended: {recommended}")
            
            # Test 2: Tool capabilities checking
            capabilities = tool_registry.get_tool_capabilities("research_workflow")
            assert isinstance(capabilities, list), "Capabilities should be a list"
            assert len(capabilities) > 0, "Should have capabilities"
            
            await self._record_test_result(test_name, "Tool Capabilities Check", True, 
                                        f"Capabilities: {len(capabilities)} found")
            
        except Exception as e:
            await self._record_test_result(test_name, "Optimization Tests", False, str(e))
    
    async def test_hierarchical_execution(self):
        """Test hierarchical task execution"""
        test_name = "Hierarchical Execution"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Execute through hierarchical tool
            if "research_workflow" in tool_registry.agent_powered_tools:
                result = await tool_registry.execute_hierarchical_tool("research_workflow", {
                    "task_type": "domain_analysis",
                    "query": "machine learning trends"
                })
                
                assert result.get("status") == "success", "Hierarchical execution should succeed"
                assert "agent" in result, "Result should contain agent info"
                assert "result" in result, "Result should contain execution result"
                
                await self._record_test_result(test_name, "Hierarchical Tool Execution", True, 
                                            f"Executed via {result.get('agent', 'unknown')} agent")
            

            # Test 2: Execute through tool hierarchy
            if "research_workflow" in hierarchical_tool_manager.tool_hierarchies:
                hierarchy_result = await hierarchical_tool_manager.execute_hierarchical_task(
                    "research_workflow",
                    {"type": "analysis", "data": {"topic": "AI research"}}
                )
                
                assert "hierarchy" in hierarchy_result, "Should contain hierarchy info"
                assert "root_result" in hierarchy_result, "Should contain root result"
                
                await self._record_test_result(test_name, "Hierarchy Execution", True, 
                                            "Hierarchy task executed successfully")
            
        except Exception as e:
            await self._record_test_result(test_name, "Hierarchical Tests", False, str(e))
    
    async def test_system_monitoring(self):
        """Test system monitoring and status reporting"""
        test_name = "System Monitoring"
        logger.info(f"Running {test_name}...")
        
        try:
            

            # Test 1: Get system status
            status = hierarchical_tool_manager.get_system_status()
            
            assert isinstance(status, dict), "Status should be a dictionary"
            assert "total_agents" in status, "Status should contain agent count"
            assert "hierarchies" in status, "Status should contain hierarchy count"
            assert "status_by_type" in status, "Status should contain type breakdown"
            assert "system_health" in status, "Status should contain health indicator"
            
            await self._record_test_result(test_name, "System Status Report", True, 
                                        f"Health: {status['system_health']}, Agents: {status['total_agents']}")
            
            # Test 2: Agent status distribution
            status_by_type = status["status_by_type"]
            total_agents_by_type = sum(type_info["count"] for type_info in status_by_type.values())
            
            assert total_agents_by_type == status["total_agents"], "Agent counts should match"
            
            await self._record_test_result(test_name, "Agent Status Distribution", True, 
                                        "Agent distribution calculated correctly")
            
            # Test 3: Execution graph optimization
            sample_tasks = [
                {"id": "task1", "dependencies": []},
                {"id": "task2", "dependencies": ["task1"]},
                {"id": "task3", "dependencies": ["task1", "task2"]}
            ]
            
            optimization = await hierarchical_tool_manager.optimize_execution_graph(sample_tasks)
            
            assert "optimized_order" in optimization, "Should contain optimized order"
            assert "total_tasks" in optimization, "Should contain task count"
            
            await self._record_test_result(test_name, "Execution Graph Optimization", True, 
                                        f"Optimized order: {optimization['optimized_order']}")
            
        except Exception as e:
            await self._record_test_result(test_name, "Monitoring Tests", False, str(e))
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        test_name = "Edge Cases"
        logger.info(f"Running {test_name}...")
        
        try:
            

            # Test 1: Non-existent agent
            non_existent_agent = hierarchical_tool_manager.get_agent("non_existent_agent")
            assert non_existent_agent is None, "Should return None for non-existent agent"
            
            await self._record_test_result(test_name, "Non-existent Agent Handling", True, "Handled correctly")
            
            # Test 2: Tool optimization with no available tools
            empty_optimization = await tool_registry.optimize_tool_selection(
                task_description="test",
                available_tools=[]
            )
            
            assert "recommended_tools" in empty_optimization, "Should handle empty tool list"
            assert len(empty_optimization["recommended_tools"]) == 0, "Should return empty recommendations"
            
            await self._record_test_result(test_name, "Empty Tool List Optimization", True, "Handled empty list correctly")
            
            # Test 3: Hierarchical tool execution with non-existent tool
            non_existent_result = await tool_registry.execute_hierarchical_tool("non_existent_tool", {})
            assert non_existent_result.get("status") == "error", "Should return error for non-existent tool"
            
            await self._record_test_result(test_name, "Non-existent Tool Execution", True, "Handled correctly")
            
            # Test 4: Invalid agent task execution
            test_agent = SpecialistAgent("edge_test_001", "test", "Edge Test Agent", "Test edge cases")
            test_agent.update_status(AgentStatus.ERROR)
            
            invalid_task = {"type": "invalid_task_type", "data": {}}
            result = await test_agent.execute(invalid_task)
            
            assert result.get("status") == "error", "Should handle invalid task type"
            
            await self._record_test_result(test_name, "Invalid Task Handling", True, "Handled invalid tasks correctly")
            
        except Exception as e:
            await self._record_test_result(test_name, "Edge Case Tests", False, str(e))
    
    async def _record_test_result(self, test_category: str, test_name: str, 
                                passed: bool, details: str = ""):
        """Record test result"""
        self.test_results["total_tests"] += 1
        if passed:
            self.test_results["passed"] += 1
            logger.info(f"✅ PASSED: {test_category} - {test_name}")
        else:
            self.test_results["failed"] += 1
            logger.error(f"❌ FAILED: {test_category} - {test_name}: {details}")
        
        self.test_results["tests"].append({
            "category": test_category,
            "test_name": test_name,
            "passed": passed,
            "details": details
        })
    
    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("HIERARCHICAL TOOLS TEST SUITE SUMMARY")
        print("="*60)
        
        print(f"Total Tests: {self.test_results['total_tests']}")
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"Success Rate: {(self.test_results['passed'] / self.test_results['total_tests'] * 100):.1f}%")
        
        if self.test_results["failed"] > 0:
            print(f"\nFAILED TESTS:")
            for test in self.test_results["tests"]:
                if not test["passed"]:
                    print(f"  • {test['category']} - {test['test_name']}: {test['details']}")
        
        print("\n" + "="*60)
        
        # Overall status
        if self.test_results["failed"] == 0:
            print("🎉 ALL TESTS PASSED - Hierarchical tools system is working correctly!")
        else:
            print(f"⚠️ {self.test_results['failed']} tests failed - Review and fix issues")
        print("="*60 + "\n")


async def main():
    """Main test function"""
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Initialize test suite
    test_suite = HierarchicalToolsTestSuite()
    
    try:
        # Run all tests
        results = await test_suite.run_all_tests()
        
        # Return exit code based on results
        return 0 if results["failed"] == 0 else 1
        
    except Exception as e:
        logger.error(f"Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)