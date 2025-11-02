#!/usr/bin/env python3
"""
Comprehensive testing script for self-correction and quality assurance features
"""
import asyncio
import json
from typing import Dict, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.critic import critic
from core.planner import Planner
from core.executor import Executor
from core.llm_client import llm_client
from config.settings import settings
from config.logger import logger


class SelfCorrectionTestSuite:
    """Test suite for self-correction and quality assurance"""
    
    def __init__(self):
        self.critic = critic
        self.planner = Planner()
        self.executor = Executor()
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    async def run_all_tests(self):
        """Run all self-correction tests"""
        logger.info("Starting Self-Correction Test Suite...")
        
        # Test Critic Component
        await self.test_critic_component()
        
        # Test Plan Quality Assessment
        await self.test_plan_quality_assessment()
        
        # Test Self-Correction Integration
        await self.test_self_correction_integration()
        
        # Test Quality Monitoring
        await self.test_quality_monitoring()
        
        # Test Edge Cases
        await self.test_edge_cases()
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    async def test_critic_component(self):
        """Test the critic component functionality"""
        test_name = "Critic Component Tests"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Critic initialization
            assert critic is not None, "Critic instance not created"
            await self._record_test_result(test_name, "Critic Initialization", True, "Critic instance created successfully")
            
            # Test 2: Critique prompt building
            critic_prompt = critic.critique_prompt
            assert critic_prompt is not None, "Critique prompt not built"
            assert "overall_score" in critic_prompt, "Critique prompt missing required elements"
            await self._record_test_result(test_name, "Critique Prompt Building", True, "Prompt contains required elements")
            
            # Test 3: Improvement suggestions
            assert len(critic.improvement_suggestions) > 0, "No improvement suggestions available"
            await self._record_test_result(test_name, "Improvement Suggestions", True, f"Found {len(critic.improvement_suggestions)} suggestion categories")
            
            # Test 4: Fallback critique
            sample_plan = {
                "intent": "execute_plan",
                "plan": {"description": "Test plan", "steps": []}
            }
            fallback_result = critic._fallback_critique(sample_plan, "test query")
            assert fallback_result.get("is_plan_valid") == True, "Fallback critique should be valid"
            await self._record_test_result(test_name, "Fallback Critique", True, "Fallback critique works correctly")
            
        except Exception as e:
            await self._record_test_result(test_name, "General Tests", False, str(e))
    
    async def test_plan_quality_assessment(self):
        """Test plan quality assessment functionality"""
        test_name = "Plan Quality Assessment"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Plan with good structure
            good_plan = {
                "intent": "execute_plan",
                "plan": {
                    "description": "Search for Python tutorials and calculate result",
                    "steps": [
                        {
                            "id": "search_tutorials",
                            "type": "TOOL_CALL",
                            "tool": "web_search_serper",
                            "description": "Search for Python learning resources",
                            "parameters": {"query": "Python tutorials for beginners"},
                            "dependencies": []
                        },
                        {
                            "id": "calculate",
                            "type": "TOOL_CALL", 
                            "tool": "advanced_calculator",
                            "description": "Calculate 2+2",
                            "parameters": {"expression": "2+2"},
                            "dependencies": []
                        }
                    ]
                },
                "memory_update": {"action": "none", "data": {}}
            }
            
            quality_score = self.planner._estimate_plan_quality(good_plan)
            assert quality_score >= 6.0, f"Good plan should score above 6.0, got {quality_score}"
            await self._record_test_result(test_name, "Good Plan Quality", True, f"Score: {quality_score}/10")
            
            # Test 2: Plan with poor structure
            poor_plan = {
                "intent": "execute_plan", 
                "plan": {
                    "description": "",
                    "steps": [
                        {"id": "", "type": "", "tool": "", "parameters": {}, "dependencies": []}
                    ]
                }
            }
            
            poor_score = self.planner._estimate_plan_quality(poor_plan)
            assert poor_score < 6.0, f"Poor plan should score below 6.0, got {poor_score}"
            await self._record_test_result(test_name, "Poor Plan Quality", True, f"Score: {poor_score}/10")
            
            # Test 3: Empty plan
            empty_plan = {"intent": "direct_answer", "plan": {"description": "Direct answer", "steps": []}}
            empty_score = self.planner._estimate_plan_quality(empty_plan)
            assert empty_score == 3.0, f"Empty plan should score 3.0, got {empty_score}"
            await self._record_test_result(test_name, "Empty Plan Quality", True, f"Score: {empty_score}/10")
            
        except Exception as e:
            await self._record_test_result(test_name, "Quality Assessment", False, str(e))
    
    async def test_self_correction_integration(self):
        """Test self-correction integration with planner"""
        test_name = "Self-Correction Integration"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Planner with self-correction enabled
            original_setting = self.planner.enable_self_correction
            self.planner.enable_self_correction = True
            
            # Mock user query and context
            user_query = "Search for weather information and calculate temperature in Celsius"
            user_memory = {}
            available_tools = ["web_search_serper", "wikipedia_search", "advanced_calculator"]
            
            # Mock model config
            model_config = {
                "name": "llama-3.1-8b-instant",
                "provider": "Groq",
                "api_endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "api_standard": "openai",
                "price_per_million_tokens": 0.06,
                "max_tokens": 4000,
                "temperature": 0.3
            }
            
            # Generate plan with self-correction
            plan = await self.planner.create_plan(
                user_query=user_query,
                user_memory=user_memory,
                available_tools=available_tools,
                model_config=model_config
            )
            
            # Verify plan structure
            assert plan.get("intent") in ["execute_plan", "direct_answer"], "Plan should have valid intent"
            assert "plan" in plan, "Plan should contain plan data"
            
            # Check self-correction meta_data
            if plan.get("intent") == "execute_plan":
                assert "self_correction_applied" in plan, "Plan should have self-correction meta_data"
                assert "critique_iterations" in plan, "Plan should have critique iteration count"
                
                if plan.get("self_correction_applied"):
                    assert plan.get("final_score") > 0, "Self-corrected plan should have quality score"
                    await self._record_test_result(test_name, "Self-Correction Applied", True, 
                                                f"Iterations: {plan.get('critique_iterations')}, Score: {plan.get('final_score')}")
                else:
                    await self._record_test_result(test_name, "Self-Correction Bypassed", True, 
                                                "Plan bypassed self-correction (may be direct answer)")
            else:
                await self._record_test_result(test_name, "Direct Answer Plan", True, 
                                            "Plan generated direct answer (no self-correction needed)")
            
            # Restore original setting
            self.planner.enable_self_correction = original_setting
            
        except Exception as e:
            await self._record_test_result(test_name, "Self-Correction Integration", False, str(e))
    
    async def test_quality_monitoring(self):
        """Test quality monitoring in executor"""
        test_name = "Quality Monitoring"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Quality metrics calculation
            sample_metrics = {
                "steps_completed": 8,
                "steps_failed": 2,
                "total_execution_time": 15.5
            }
            
            quality_score = self.executor._calculate_quality_score(sample_metrics)
            assert 0.0 <= quality_score <= 10.0, f"Quality score should be between 0-10, got {quality_score}"
            await self._record_test_result(test_name, "Quality Score Calculation", True, f"Score: {quality_score}/10")
            
            # Test 2: Plan validation
            valid_plan = {
                "intent": "execute_plan",
                "plan": {
                    "description": "Test execution plan",
                    "steps": [
                        {
                            "id": "step1",
                            "type": "DIRECT_ANSWER",
                            "description": "Simple step",
                            "parameters": {},
                            "dependencies": []
                        }
                    ]
                }
            }
            
            validation_result = await self.executor._validate_execution_plan(valid_plan)
            assert validation_result.get("is_valid") == True, "Valid plan should pass validation"
            await self._record_test_result(test_name, "Valid Plan Validation", True, "Plan validation passed")
            
            # Test 3: Invalid plan detection
            invalid_plan = {
                "intent": "execute_plan",
                "plan": {
                    "description": "",
                    "steps": [
                        {
                            "id": "",  # Missing ID
                            "type": "",  # Missing type
                            "description": "",
                            "parameters": {},
                            "dependencies": []
                        }
                    ]
                }
            }
            
            invalid_validation = await self.executor._validate_execution_plan(invalid_plan)
            assert invalid_validation.get("is_valid") == False, "Invalid plan should fail validation"
            await self._record_test_result(test_name, "Invalid Plan Detection", True, "Invalid plan correctly detected")
            
        except Exception as e:
            await self._record_test_result(test_name, "Quality Monitoring", False, str(e))
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        test_name = "Edge Cases"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Circular dependency detection
            circular_plan = {
                "plan": {
                    "steps": [
                        {
                            "id": "step1",
                            "dependencies": ["step2"]
                        },
                        {
                            "id": "step2", 
                            "dependencies": ["step1"]
                        }
                    ]
                }
            }
            
            has_circular = self.executor._has_circular_dependency(circular_plan["plan"]["steps"])
            assert has_circular == True, "Should detect circular dependency"
            await self._record_test_result(test_name, "Circular Dependency Detection", True, "Circular dependency detected")
            
            # Test 2: Plan optimization
            redundant_plan = {
                "plan": {
                    "description": "Test optimization",
                    "steps": [
                        {
                            "id": "calc1",
                            "type": "TOOL_CALL",
                            "tool": "advanced_calculator",
                            "description": "Calculate 2+2",
                            "parameters": {"expression": "2+2"},
                            "dependencies": []
                        },
                        {
                            "id": "calc2", 
                            "type": "TOOL_CALL",
                            "tool": "advanced_calculator",
                            "description": "Calculate 3+3", 
                            "parameters": {"expression": "3+3"},
                            "dependencies": []
                        }
                    ]
                }
            }
            
            # Test plan optimization without actual tools (just structure)
            optimized = self.planner._group_similar_steps(redundant_plan["plan"]["steps"])
            assert len(optimized) == 2, "Should group similar steps appropriately"
            await self._record_test_result(test_name, "Plan Optimization", True, f"Optimized {len(redundant_plan['plan']['steps'])} steps to {len(optimized)}")
            
            # Test 3: Empty plan handling
            empty_plan = {"intent": "direct_answer", "plan": {"description": "", "steps": []}}
            quality_score = self.planner._estimate_plan_quality(empty_plan)
            assert quality_score == 3.0, "Empty plan should have score of 3.0"
            await self._record_test_result(test_name, "Empty Plan Handling", True, "Empty plan handled correctly")
            
        except Exception as e:
            await self._record_test_result(test_name, "Edge Cases", False, str(e))
    
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
        print("SELF-CORRECTION TEST SUITE SUMMARY")
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
            print("🎉 ALL TESTS PASSED - Self-correction system is working correctly!")
        else:
            print(f"⚠️ {self.test_results['failed']} tests failed - Review and fix issues")
        print("="*60 + "\n")


async def main():
    """Main test function"""
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Initialize test suite
    test_suite = SelfCorrectionTestSuite()
    
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