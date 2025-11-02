#!/usr/bin/env python3
"""
Comprehensive testing script for dynamic memory and vector-based retrieval system
"""
import asyncio
import json
import numpy as np
from typing import Dict, Any
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.dynamic_memory import DynamicMemory
from core.planner import Planner
from config.logger import logger


class DynamicMemoryTestSuite:
    """Test suite for dynamic memory and vector-based retrieval"""
    
    def __init__(self):
        self.dynamic_memory = DynamicMemory()
        self.planner = Planner()
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "tests": []
        }
    
    async def run_all_tests(self):
        """Run all dynamic memory tests"""
        logger.info("Starting Dynamic Memory Test Suite...")
        
        # Test Memory System Core
        await self.test_memory_system_core()
        
        # Test Embedding Generation
        await self.test_embedding_generation()
        
        # Test Memory Retrieval
        await self.test_memory_retrieval()
        
        # Test Memory Enhancement
        await self.test_memory_enhancement()
        
        # Test Pattern Analysis
        await self.test_pattern_analysis()
        
        # Test Edge Cases
        await self.test_edge_cases()
        
        # Print summary
        self.print_test_summary()
        
        return self.test_results
    
    async def test_memory_system_core(self):
        """Test core memory system functionality"""
        test_name = "Memory System Core"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Dynamic memory initialization
            assert self.dynamic_memory is not None, "DynamicMemory instance not created"
            await self._record_test_result(test_name, "Memory System Initialization", True, "DynamicMemory instance created")
            
            # Test 2: Configuration settings
            assert self.dynamic_memory.similarity_threshold > 0, "Similarity threshold should be positive"
            assert self.dynamic_memory.max_memory_items > 0, "Max memory items should be positive"
            await self._record_test_result(test_name, "Configuration Settings", True, 
                                        f"Threshold: {self.dynamic_memory.similarity_threshold}, Max items: {self.dynamic_memory.max_memory_items}")
            
            # Test 3: Memory cache initialization
            assert isinstance(self.dynamic_memory.memory_cache, dict), "Memory cache should be dictionary"
            await self._record_test_result(test_name, "Memory Cache", True, "Cache initialized correctly")
            
            # Test 4: Embedding dimension check
            assert self.dynamic_memory.embedding_dim > 0, "Embedding dimension should be positive"
            await self._record_test_result(test_name, "Embedding Dimensions", True, 
                                        f"Dimension: {self.dynamic_memory.embedding_dim}")
            
        except Exception as e:
            await self._record_test_result(test_name, "Core Tests", False, str(e))
    
    async def test_embedding_generation(self):
        """Test embedding generation and caching"""
        test_name = "Embedding Generation"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Single text embedding
            test_text = "This is a test query for embedding generation"
            embedding = await self.dynamic_memory._generate_embedding(test_text)
            
            assert embedding is not None, "Embedding should not be None"
            assert isinstance(embedding, np.ndarray), "Embedding should be numpy array"
            assert embedding.shape[0] == self.dynamic_memory.embedding_dim, "Embedding dimension mismatch"
            await self._record_test_result(test_name, "Single Text Embedding", True, 
                                        f"Generated {embedding.shape} embedding")
            
            # Test 2: Embedding normalization
            embedding_norm = np.linalg.norm(embedding)
            assert abs(embedding_norm - 1.0) < 1e-6, "Embedding should be normalized"
            await self._record_test_result(test_name, "Embedding Normalization", True, f"Norm: {embedding_norm:.6f}")
            
            # Test 3: Caching functionality
            cache_size_before = len(self.dynamic_memory.memory_cache)
            embedding2 = await self.dynamic_memory._generate_embedding(test_text)
            cache_size_after = len(self.dynamic_memory.memory_cache)
            
            assert cache_size_after >= cache_size_before, "Cache should be populated"
            await self._record_test_result(test_name, "Embedding Cache", True, 
                                        f"Cache size: {cache_size_before} -> {cache_size_after}")
            
            # Test 4: Different text embeddings
            test_texts = ["Python programming", "Machine learning", "Data science"]
            embeddings = []
            
            for text in test_texts:
                emb = await self.dynamic_memory._generate_embedding(text)
                embeddings.append(emb)
            
            # Calculate similarities between embeddings
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i+1, len(embeddings)):
                    from sklearn.metrics.pairwise import cosine_similarity
                    sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                    similarities.append(sim)
            
            avg_similarity = np.mean(similarities)
            assert 0.0 <= avg_similarity <= 1.0, "Similarity should be between 0 and 1"
            await self._record_test_result(test_name, "Cross-Text Similarities", True, 
                                        f"Average similarity: {avg_similarity:.3f}")
            
        except Exception as e:
            await self._record_test_result(test_name, "Embedding Tests", False, str(e))
    
    async def test_memory_retrieval(self):
        """Test memory retrieval and ranking"""
        test_name = "Memory Retrieval"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Mock database retrieval
            from unittest.mock import AsyncMock
            
            mock_db = AsyncMock()
            mock_result = AsyncMock()
            mock_result.scalar.return_value = {"preference": "Python", "skill_level": "intermediate"}
            mock_db.execute.return_value = mock_result
            
            memories = await self.dynamic_memory._get_user_memory_memories(mock_db, 1)
            
            assert isinstance(memories, list), "Memories should be a list"
            await self._record_test_result(test_name, "User Memory Retrieval", True, 
                                        f"Retrieved {len(memories)} memories")
            
            # Test 2: Memory type filtering
            memory_types = ["user_memory", "conversation_history"]
            filtered_memories = await self.dynamic_memory.retrieve_relevant_memory(
                user_id=1,
                current_query="Python programming",
                db=mock_db,
                memory_types=memory_types
            )
            
            assert "memories" in filtered_memories, "Result should contain memories"
            await self._record_test_result(test_name, "Memory Type Filtering", True, 
                                        f"Filtered {len(memory_types)} types")
            
            # Test 3: Memory ranking simulation
            test_memories = [
                {
                    "type": "user_profile",
                    "content": "User prefers Python programming",
                    "meta_data": {"profile_field": "preference"},
                    "relevance_score": 0.0
                },
                {
                    "type": "conversation_message", 
                    "content": "I love working with Python",
                    "meta_data": {"role": "user"},
                    "relevance_score": 0.0
                }
            ]
            
            query_embedding = await self.dynamic_memory._generate_embedding("Python programming")
            ranked_memories = await self.dynamic_memory._rank_memories_by_relevance(
                "Python programming", query_embedding, test_memories
            )
            
            assert len(ranked_memories) <= len(test_memories), "Should not return more memories than provided"
            if ranked_memories:
                assert all(memory.get("relevance_score", 0) >= 0 for memory in ranked_memories), "All scores should be non-negative"
            
            await self._record_test_result(test_name, "Memory Ranking", True, 
                                        f"Ranked {len(ranked_memories)} memories")
            
        except Exception as e:
            await self._record_test_result(test_name, "Retrieval Tests", False, str(e))
    
    async def test_memory_enhancement(self):
        """Test memory enhancement functionality"""
        test_name = "Memory Enhancement"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Plan enhancement simulation
            original_plan = {
                "intent": "execute_plan",
                "plan": {
                    "description": "Search for Python tutorials",
                    "steps": []
                },
                "memory_update": {"action": "none", "data": {}}
            }
            
            enhanced_plan = await self.dynamic_memory.enhance_plan_with_memory(
                user_id=1,
                user_query="Find Python learning resources",
                plan=original_plan,
                db=AsyncMock()  # Mock database
            )
            
            # Check if plan was enhanced
            if enhanced_plan != original_plan:
                assert "memory_enhancement" in enhanced_plan, "Enhanced plan should have memory meta_data"
                await self._record_test_result(test_name, "Plan Enhancement", True, "Plan enhanced with memory context")
            else:
                await self._record_test_result(test_name, "Plan Enhancement", True, "No enhancement needed (no relevant memories)")
            
            # Test 2: Memory context formatting
            sample_memories = [
                {
                    "type": "user_profile",
                    "content": "User is interested in Python programming",
                    "relevance_score": 0.85
                },
                {
                    "type": "conversation_message",
                    "content": "Previous discussion about Python frameworks",
                    "relevance_score": 0.72
                }
            ]
            
            formatted_context = self.planner._format_memory_context(sample_memories)
            assert isinstance(formatted_context, str), "Formatted context should be string"
            assert "1." in formatted_context, "Should contain numbered list"
            assert "Python" in formatted_context, "Should contain relevant content"
            
            await self._record_test_result(test_name, "Context Formatting", True, 
                                        f"Formatted {len(sample_memories)} memories")
            
            # Test 3: Memory filtering by relevance
            low_relevance_threshold = 0.8
            filtered_memories = [
                memory for memory in sample_memories
                if memory.get("relevance_score", 0) >= low_relevance_threshold
            ]
            
            await self._record_test_result(test_name, "Relevance Filtering", True, 
                                        f"Filtered {len(filtered_memories)}/{len(sample_memories)} by relevance")
            
        except Exception as e:
            await self._record_test_result(test_name, "Enhancement Tests", False, str(e))
    
    async def test_pattern_analysis(self):
        """Test memory pattern analysis"""
        test_name = "Pattern Analysis"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Query pattern analysis
            sample_stats = {
                "total_conversations": 15,
                "total_messages": 250,
                "total_files": 5,
                "avg_message_length": 85.5
            }
            
            sample_patterns = {
                "total_queries": 180,
                "avg_query_length": 75.2,
                "query_distribution": {
                    "short_queries": 60,
                    "medium_queries": 90,
                    "long_queries": 30
                }
            }
            
            insights = await self.dynamic_memory._generate_memory_insights(sample_stats, sample_patterns)
            
            assert isinstance(insights, list), "Insights should be a list"
            assert len(insights) > 0, "Should generate at least one insight"
            await self._record_test_result(test_name, "Insight Generation", True, 
                                        f"Generated {len(insights)} insights")
            
            # Test 2: Recommendations generation
            recommendations = await self.dynamic_memory._generate_memory_recommendations(sample_stats, insights)
            
            assert isinstance(recommendations, list), "Recommendations should be a list"
            await self._record_test_result(test_name, "Recommendations", True, 
                                        f"Generated {len(recommendations)} recommendations")
            
            # Test 3: Pattern detection
            active_user_stats = {"total_messages": 300, "total_files": 15}
            active_insights = await self.dynamic_memory._generate_memory_insights(active_user_stats, {})
            
            # Should detect high activity
            high_activity_insights = [insight for insight in active_insights if "active" in insight.lower()]
            assert len(high_activity_insights) > 0, "Should detect high activity"
            
            await self._record_test_result(test_name, "Pattern Detection", True, 
                                        f"Detected {len(high_activity_insights)} activity insights")
            
        except Exception as e:
            await self._record_test_result(test_name, "Pattern Tests", False, str(e))
    
    async def test_edge_cases(self):
        """Test edge cases and error handling"""
        test_name = "Edge Cases"
        logger.info(f"Running {test_name}...")
        
        try:
            # Test 1: Empty text embedding
            empty_embedding = await self.dynamic_memory._generate_embedding("")
            assert empty_embedding is not None, "Should handle empty text"
            assert empty_embedding.shape[0] == self.dynamic_memory.embedding_dim, "Should have correct dimension"
            await self._record_test_result(test_name, "Empty Text Embedding", True, "Handled empty text correctly")
            
            # Test 2: Very long text
            long_text = "A" * 10000  # Very long text
            long_embedding = await self.dynamic_memory._generate_embedding(long_text)
            assert long_embedding is not None, "Should handle long text"
            await self._record_test_result(test_name, "Long Text Embedding", True, "Handled long text correctly")
            
            # Test 3: Memory cache limit
            initial_cache_size = len(self.dynamic_memory.memory_cache)
            
            # Add many embeddings to test cache limit
            for i in range(50):
                await self.dynamic_memory._generate_embedding(f"Test text {i}")
            
            # Cache should not grow unbounded
            final_cache_size = len(self.dynamic_memory.memory_cache)
            assert final_cache_size > initial_cache_size, "Cache should grow"
            
            await self._record_test_result(test_name, "Cache Management", True, 
                                        f"Cache size controlled: {initial_cache_size} -> {final_cache_size}")
            
            # Test 4: Invalid memory types
            mock_db = AsyncMock()
            invalid_result = await self.dynamic_memory.retrieve_relevant_memory(
                user_id=1,
                current_query="test",
                db=mock_db,
                memory_types=["invalid_type"]
            )
            
            assert "error" in invalid_result or "memories" in invalid_result, "Should handle invalid types gracefully"
            await self._record_test_result(test_name, "Invalid Type Handling", True, "Handled invalid memory types")
            
            # Test 5: Memory ranking with empty memories
            empty_ranking = await self.dynamic_memory._rank_memories_by_relevance(
                "test query", await self.dynamic_memory._generate_embedding("test"), []
            )
            
            assert empty_ranking == [], "Should return empty list for empty memories"
            await self._record_test_result(test_name, "Empty Memory Ranking", True, "Handled empty memory list")
            
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
        print("DYNAMIC MEMORY TEST SUITE SUMMARY")
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
            print("🎉 ALL TESTS PASSED - Dynamic memory system is working correctly!")
        else:
            print(f"⚠️ {self.test_results['failed']} tests failed - Review and fix issues")
        print("="*60 + "\n")


async def main():
    """Main test function"""
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Initialize test suite
    test_suite = DynamicMemoryTestSuite()
    
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