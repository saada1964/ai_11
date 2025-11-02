#!/usr/bin/env python3
"""
Simple test script for AI Agent Kernel
Simple usage example
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import orchestrator
from core.tools import tool_registry
from core.llm_client import llm_client
from database.database import init_db, close_db, AsyncSessionLocal
from models.models import User
from schemas.schemas import AgentRequest


async def test_system():
    """Test the AI Agent Kernel system"""
    print("🤖 Testing AI Agent Kernel...")
    print("=" * 50)
    
    try:
        # Initialize database
        print("📦 Initializing database...")
        await init_db()
        
        # Load default tools
        print("🔧 Loading tools...")
        default_tools = [
            {
                "name": "web_search_serper",
                "description": "Fast web search using Serper.dev",
                "function_name": "web_search_serper",
                "price_usd": 0.001,
                "api_key_name": "SERPER_API_KEY",
                "is_active": True,
                "parameters": {"query": "search query string"}
            },
            {
                "name": "wikipedia_search", 
                "description": "Search Wikipedia articles",
                "function_name": "wikipedia_search",
                "price_usd": 0.0001,
                "api_key_name": None,
                "is_active": True,
                "parameters": {"query": "search query", "language": "en"}
            },
            {
                "name": "advanced_calculator",
                "description": "Safe mathematical calculator",
                "function_name": "advanced_calculator", 
                "price_usd": 0.00001,
                "api_key_name": None,
                "is_active": True,
                "parameters": {"expression": "mathematical expression"}
            }
        ]
        tool_registry.load_tools_from_db(default_tools)
        print(f"✅ Loaded {len(default_tools)} tools")
        
        # Test tools directly
        print("\n🧪 Testing tools directly...")
        
        # Test calculator
        print("Testing calculator...")
        calc_result = await tool_registry.functions["advanced_calculator"](expression="2+2")
        print(f"Calculator result: {calc_result}")
        
        # Test Wikipedia
        print("Testing Wikipedia search...")
        wiki_result = await tool_registry.functions["wikipedia_search"](query="Python programming")
        print(f"Wikipedia result status: {wiki_result['status']}")
        if wiki_result['status'] == 'success':
            print(f"Found {wiki_result['total_results']} results")
        
        # Test planner with a simple request
        print("\n🧠 Testing planner...")
        from core.planner import Planner
        
        planner = Planner()
        plan = await planner.create_plan(
            user_query="What is the weather today?",
            user_memory={},
            available_tools=["advanced_calculator", "wikipedia_search"],
            model_config={
                "name": "llama-3.1-8b-instant",
                "api_standard": "openai",
                "max_tokens": 1000,
                "temperature": 0.3
            }
        )
        print(f"Plan intent: {plan['intent']}")
        print(f"Plan description: {plan.get('plan', {}).get('description', 'N/A')}")
        
        # Test executor
        print("\n⚡ Testing executor...")
        from core.executor import Executor
        
        executor = Executor()
        
        if plan['intent'] == 'execute_plan':
            execution_result = await executor.execute_plan(plan)
            print(f"Execution status: {execution_result['status']}")
            print(f"Steps executed: {execution_result.get('step_count', 0)}")
        
        # Test complete request flow
        print("\n🌊 Testing complete request flow...")
        
        # Create a test request
        request = AgentRequest(
            query="Calculate 5*3 and search for information about artificial intelligence",
            user_id=1
        )
        
        # Process the request
        async with AsyncSessionLocal() as db:
            result = await orchestrator.process_request(db, request)
            
            print("✅ Request processed successfully!")
            print(f"Intent: {result['intent']}")
            print(f"Conversation ID: {result['conversation_id']}")
            print(f"Response length: {len(result['response'])} characters")
            print("\nResponse preview:")
            print("-" * 40)
            print(result['response'][:300] + "..." if len(result['response']) > 300 else result['response'])
            print("-" * 40)
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        await close_db()
        print("\n🧹 Cleanup completed")


async def test_simple_calculator():
    """Test just the calculator functionality"""
    print("🧮 Testing Calculator Tool")
    print("=" * 30)
    
    try:
        # Load calculator tool
        tool_registry.load_tools_from_db([
            {
                "name": "advanced_calculator",
                "description": "Safe mathematical calculator",
                "function_name": "advanced_calculator", 
                "price_usd": 0.00001,
                "api_key_name": None,
                "is_active": True,
                "parameters": {"expression": "mathematical expression"}
            }
        ])
        
        # Test various calculations
        test_expressions = [
            "2+2",
            "10*5",
            "100/4",
            "(5+3)*2",
            "2**3"  # exponentiation
        ]
        
        for expr in test_expressions:
            result = await tool_registry.functions["advanced_calculator"](expression=expr)
            print(f"{expr} = {result.get('formatted_result', 'ERROR')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Calculator test failed: {e}")
        return False


async def main():
    """Main test function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        await test_simple_calculator()
    else:
        await test_system()


if __name__ == "__main__":
    print("AI Agent Kernel Test Suite")
    print("Usage: python test_system.py [--simple]")
    print("")
    
    # Run the tests
    success = asyncio.run(main())
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)