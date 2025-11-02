import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
import httpx
import wikipedia
import numexpr
from serpapi import GoogleSearch as serp_search
from config.settings import settings
from config.logger import logger
from core.sub_agents import SubAgent, AgentType



class ToolRegistry:
    """Dynamic registry for AI tools"""
    
    def __init__(self):
        self.tools = {}
        self.functions = {}
        self.agent_powered_tools = {}  # Tools powered by sub-agents
        
    def register_tool(self, tool_config: Dict[str, Any], function: Callable):
        """Register a tool in the registry"""
        self.tools[tool_config["name"]] = tool_config
        self.functions[tool_config["function_name"]] = function
        logger.info(f"Registered tool: {tool_config['name']}")
    
    def load_tools_from_db(self, tools_data: List[Dict[str, Any]]):
        """Load tools from database configuration"""
        for tool_config in tools_data:
            if tool_config["is_active"]:
                function = self._get_function_by_name(tool_config["function_name"])
                if function:
                    self.register_tool(tool_config, function)
                else:
                    logger.warning(f"Function {tool_config['function_name']} not found for tool {tool_config['name']}")
    
    def _get_function_by_name(self, function_name: str) -> Optional[Callable]:
        """Get function by name from predefined functions"""
        return self.functions.get(function_name)
    
    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get tool configuration"""
        return self.tools.get(tool_name)
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())
    
    def register_hierarchical_tool(self, tool_config: Dict[str, Any], agent: SubAgent):
        """Register a hierarchical tool powered by a sub-agent"""
        self.tools[tool_config["name"]] = tool_config
        self.agent_powered_tools[tool_config["name"]] = agent
        logger.info(f"Registered hierarchical tool: {tool_config['name']} powered by agent {agent.name}")
    
    async def execute_hierarchical_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a hierarchical tool using sub-agent"""
        try:
            if tool_name not in self.agent_powered_tools:
                raise ValueError(f"Hierarchical tool '{tool_name}' not found")
            
            agent = self.agent_powered_tools[tool_name]
            
            # Create task for agent
            task = {
                "type": parameters.get("task_type", "general"),
                "data": parameters,
                "id": f"tool_{tool_name}_{int(asyncio.get_event_loop().time())}"
            }
            
            # Execute through agent
            result = await agent.execute(task)
            
            return {
                "status": "success",
                "tool": tool_name,
                "agent": agent.name,
                "result": result,
                "execution_time": result.get("execution_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Hierarchical tool execution error: {e}")
            return {
                "status": "error",
                "tool": tool_name,
                "error": str(e)
            }
    
    def get_tool_capabilities(self, tool_name: str) -> List[str]:
        """Get capabilities of a specific tool"""
        if tool_name in self.agent_powered_tools:
            agent = self.agent_powered_tools[tool_name]
            return agent.get_capabilities()
        elif tool_name in self.tools:
            # Return basic tool capabilities for regular tools
            return ["basic_execution"]
        else:
            return []
    
    async def optimize_tool_selection(self, task_description: str, available_tools: List[str]) -> Dict[str, Any]:
        """Optimize tool selection based on task requirements"""
        try:
            # Analyze task description to determine best tools
            task_keywords = task_description.lower().split()
            
            tool_scores = {}
            
            for tool_name in available_tools:
                score = 0
                capabilities = self.get_tool_capabilities(tool_name)
                
                # Score based on capabilities matching task keywords
                for capability in capabilities:
                    for keyword in task_keywords:
                        if keyword in capability.lower():
                            score += 1
                
                # Bonus for hierarchical tools
                if tool_name in self.agent_powered_tools:
                    score += 2
                
                tool_scores[tool_name] = score
            
            # Sort tools by score
            sorted_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "task_description": task_description,
                "tool_scores": tool_scores,
                "recommended_tools": [tool for tool, score in sorted_tools[:3] if score > 0],
                "optimization_method": "capability_matching"
            }
            
        except Exception as e:
            logger.error(f"Tool optimization error: {e}")
            return {"error": str(e)}


# Tool Functions - These will be called by name from database
async def web_search_serper(query: str, **kwargs) -> Dict[str, Any]:
    """Perform web search using Serper.dev API"""
    try:
        search_results = serp_search(q=query, api_key=settings.serper_api_key)
        
        formatted_results = []
        for result in search_results.get("organic", [])[:5]:  # Top 5 results
            formatted_results.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("link", ""),
                "displayLink": result.get("displayLink", "")
            })
        
        return {
            "status": "success",
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }


async def wikipedia_search(query: str, language: str = "en", **kwargs) -> Dict[str, Any]:
    """Smart Wikipedia search with language detection"""
    try:
        # Set language
        wikipedia.set_lang(language)
        
        # Search for pages
        search_results = wikipedia.search(query, results=3)
        
        formatted_results = []
        for page_title in search_results:
            try:
                page = wikipedia.page(page_title)
                formatted_results.append({
                    "title": page.title,
                    "summary": page.summary[:500] + "..." if len(page.summary) > 500 else page.summary,
                    "url": page.url,
                    "categories": page.categories[:5]  # Top 5 categories
                })
            except wikipedia.exceptions.DisambiguationError:
                # Handle disambiguation pages
                page = wikipedia.page(page_title, auto_suggest=True)
                formatted_results.append({
                    "title": page.title,
                    "summary": page.summary[:500] + "..." if len(page.summary) > 500 else page.summary,
                    "url": page.url,
                    "note": "Auto-selected from disambiguation"
                })
            except Exception as e:
                logger.warning(f"Error fetching Wikipedia page {page_title}: {e}")
                continue
        
        return {
            "status": "success",
            "query": query,
            "language": language,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Wikipedia search error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "query": query
        }


async def advanced_calculator(expression: str, **kwargs) -> Dict[str, Any]:
    """Safe mathematical expression evaluator using numexpr"""
    try:
        # Validate expression - only allow mathematical operations
        allowed_chars = set('0123456789+-*/()., ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Expression contains invalid characters")
        
        # Evaluate expression safely
        result = numexpr.evaluate(expression)
        
        return {
            "status": "success",
            "expression": expression,
            "result": float(result),
            "formatted_result": str(result)
        }
        
    except Exception as e:
        logger.error(f"Calculator error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "expression": expression
        }


async def search_user_documents(query: str, user_id: int, **kwargs) -> Dict[str, Any]:
    """Search through user uploaded documents using RAG"""
    # Placeholder for RAG functionality
    # This will be implemented later with vector search
    return {
        "status": "not_implemented",
        "message": "RAG functionality will be implemented in a future version",
        "query": query,
        "user_id": user_id
    }


# Hierarchical tools powered by sub-agents
async def research_workflow_tool(task_type: str, query: str, **kwargs) -> Dict[str, Any]:
    """Hierarchical research tool powered by research specialist agent"""
    return await tool_registry.execute_hierarchical_tool("research_workflow", {
        "task_type": task_type,
        "query": query,
        "parameters": kwargs
    })

async def web_analysis_tool(url: str, analysis_type: str = "comprehensive", **kwargs) -> Dict[str, Any]:
    """Hierarchical web analysis tool powered by web specialist agent"""
    return await tool_registry.execute_hierarchical_tool("web_analysis", {
        "task_type": analysis_type,
        "url": url,
        "parameters": kwargs
    })

async def data_processing_tool(data: Any, operation: str, **kwargs) -> Dict[str, Any]:
    """Hierarchical data processing tool powered by data specialist agent"""
    return await tool_registry.execute_hierarchical_tool("data_processing", {
        "task_type": operation,
        "data": data,
        "parameters": kwargs
    })

async def complex_task_executor(task_description: str, strategy: str = "auto", **kwargs) -> Dict[str, Any]:
    """Hierarchical complex task executor"""
    return await tool_registry.execute_hierarchical_tool("complex_executor", {
        "task_type": "complex_execution",
        "description": task_description,
        "strategy": strategy,
        "parameters": kwargs
    })


# Global tool registry instance
tool_registry = ToolRegistry()

# Register default tool functions
tool_registry.functions = {
    "web_search_serper": web_search_serper,
    "wikipedia_search": wikipedia_search,
    "advanced_calculator": advanced_calculator,
    "search_user_documents": search_user_documents,
    "research_workflow_tool": research_workflow_tool,
    "web_analysis_tool": web_analysis_tool,
    "data_processing_tool": data_processing_tool,
    "complex_task_executor": complex_task_executor
}

# Register hierarchical tools with sub-agents
hierarchical_tool_configs = [
    {
        "name": "research_workflow",
        "description": "Comprehensive research workflow using specialist agents",
        "function_name": "research_workflow_tool",
        "price_usd": 0.005,
        "is_hierarchical": True,
        "capabilities": ["research", "analysis", "synthesis", "validation"]
    },
    {
        "name": "web_analysis", 
        "description": "Advanced web content analysis and processing",
        "function_name": "web_analysis_tool",
        "price_usd": 0.003,
        "is_hierarchical": True,
        "capabilities": ["web_scraping", "content_analysis", "data_extraction"]
    },
    {
        "name": "data_processing",
        "description": "Complex data processing and analysis pipeline",
        "function_name": "data_processing_tool", 
        "price_usd": 0.004,
        "is_hierarchical": True,
        "capabilities": ["data_cleaning", "statistical_analysis", "visualization"]
    },
    {
        "name": "complex_executor",
        "description": "Multi-step complex task execution coordinator",
        "function_name": "complex_task_executor",
        "price_usd": 0.006,
        "is_hierarchical": True,
        "capabilities": ["task_coordination", "multi_agent_execution", "workflow_optimization"]
    }
]
def register_hierarchical_tools():
    from core.sub_agents import hierarchical_tool_manager
    for config in hierarchical_tool_configs:
        # Find appropriate agent for this tool
        if "research" in config["name"]:
            agent = hierarchical_tool_manager.get_agent("research_001")
        elif "web" in config["name"]:
            agent = hierarchical_tool_manager.get_agent("web_001")
        elif "data" in config["name"]:
            agent = hierarchical_tool_manager.get_agent("data_001") 
        else:
            agent = hierarchical_tool_manager.get_agent("coord_001")
        
        if agent:
            tool_registry.register_hierarchical_tool(config, agent)
register_hierarchical_tools()
logger.info("Default tool functions and hierarchical tools registered")