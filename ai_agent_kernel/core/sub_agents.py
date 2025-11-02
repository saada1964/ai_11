import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime
from config.logger import logger



class AgentType(Enum):
    """Types of sub-agents"""
    SPECIALIST = "specialist"      # Domain-specific agents
    COORDINATOR = "coordinator"    # Coordination agents
    EXECUTOR = "executor"          # Execution agents
    ANALYZER = "analyzer"          # Analysis agents
    SYNTHESIZER = "synthesizer"    # Synthesis agents


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    COMPLETED = "completed"
    FAILED = "failed"


class SubAgent(ABC):
    """Abstract base class for sub-agents"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, name: str, description: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.status = AgentStatus.IDLE
        self.capabilities = []
        self.sub_tools = []
        self.memory = {}
        self.execution_history = []
        
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        pass
    
    def update_status(self, status: AgentStatus):
        """Update agent status"""
        old_status = self.status
        self.status = status
        logger.info(f"Agent {self.name}: {old_status.value} -> {status.value}")
    
    def add_to_memory(self, key: str, value: Any):
        """Add information to agent memory"""
        self.memory[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "access_count": self.memory.get(key, {}).get("access_count", 0) + 1
        }
    
    def get_from_memory(self, key: str, default=None):
        """Get information from agent memory"""
        if key in self.memory:
            self.memory[key]["access_count"] += 1
            return self.memory[key]["value"]
        return default
    
    def record_execution(self, task: Dict[str, Any], result: Dict[str, Any]):
        """Record execution in history"""
        self.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "duration": result.get("execution_time", 0)
        })
        
        # Keep only last 10 executions
        if len(self.execution_history) > 10:
            self.execution_history = self.execution_history[-10:]


class SpecialistAgent(SubAgent):
    """Domain-specific specialist agent"""
    
    def __init__(self, agent_id: str, domain: str, name: str, description: str):
        super().__init__(agent_id, AgentType.SPECIALIST, name, description)
        self.domain = domain
        self.specialized_tools = []
        self.expertise_level = "intermediate"  # beginner, intermediate, advanced, expert
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute domain-specific task"""
        try:
            self.update_status(AgentStatus.BUSY)
            start_time = datetime.now()
            
            task_type = task.get("type")
            task_data = task.get("data", {})
            
            if task_type == "domain_analysis":
                result = await self._analyze_domain(task_data)
            elif task_type == "domain_synthesis":
                result = await self._synthesize_domain(task_data)
            elif task_type == "domain_validation":
                result = await self._validate_domain(task_data)
            else:
                result = await self._generic_domain_execution(task)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result.update({
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "execution_time": execution_time,
                "status": "completed"
            })
            
            self.update_status(AgentStatus.COMPLETED)
            self.record_execution(task, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
            self.update_status(AgentStatus.ERROR)
            self.record_execution(task, error_result)
            return error_result
    
    async def _analyze_domain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze domain-specific information"""
        return {
            "analysis_type": "domain_analysis",
            "domain": self.domain,
            "findings": f"Analysis of {self.domain} domain completed",
            "recommendations": [f"Consider {self.domain} best practices"]
        }
    
    async def _synthesize_domain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize domain-specific information"""
        return {
            "synthesis_type": "domain_synthesis",
            "domain": self.domain,
            "synthesis": f"Domain synthesis for {self.domain} completed",
            "confidence": 0.85
        }
    
    async def _validate_domain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate domain-specific information"""
        return {
            "validation_type": "domain_validation",
            "domain": self.domain,
            "is_valid": True,
            "validation_score": 0.9
        }
    
    async def _generic_domain_execution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generic domain execution"""
        return {
            "execution_type": "generic",
            "domain": self.domain,
            "message": f"Executed generic task in {self.domain} domain"
        }
    
    def get_capabilities(self) -> List[str]:
        """Return specialist agent capabilities"""
        return [
            f"{self.domain} analysis",
            f"{self.domain} synthesis", 
            f"{self.domain} validation",
            f"{self.domain} consultation"
        ]


class CoordinatorAgent(SubAgent):
    """Coordination agent for managing multiple sub-agents"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        super().__init__(agent_id, AgentType.COORDINATOR, name, description)
        self.managed_agents = []
        self.coordination_strategies = ["sequential", "parallel", "hierarchical"]
        self.load_balancing = True
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coordination task"""
        try:
            self.update_status(AgentStatus.BUSY)
            start_time = datetime.now()
            
            coordination_type = task.get("type")
            
            if coordination_type == "agent_coordination":
                result = await self._coordinate_agents(task)
            elif coordination_type == "load_balancing":
                result = await self._balance_load(task)
            elif coordination_type == "conflict_resolution":
                result = await self._resolve_conflicts(task)
            else:
                result = await self._generic_coordination(task)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result.update({
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "execution_time": execution_time,
                "managed_agents": len(self.managed_agents)
            })
            
            self.update_status(AgentStatus.COMPLETED)
            self.record_execution(task, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
            self.update_status(AgentStatus.ERROR)
            self.record_execution(task, error_result)
            return error_result
    
    async def _coordinate_agents(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multiple agents"""
        agents = task.get("agents", [])
        coordination_strategy = task.get("strategy", "sequential")
        
        results = []
        
        if coordination_strategy == "parallel":
            # Execute agents in parallel
            tasks = []
            for agent_config in agents:
                agent = self._get_agent_by_id(agent_config["id"])
                if agent:
                    tasks.append(agent.execute(agent_config["task"]))
            
            agent_results = await asyncio.gather(*tasks, return_exceptions=True)
            results = [r for r in agent_results if not isinstance(r, Exception)]
            
        elif coordination_strategy == "sequential":
            # Execute agents sequentially
            for agent_config in agents:
                agent = self._get_agent_by_id(agent_config["id"])
                if agent:
                    result = await agent.execute(agent_config["task"])
                    results.append(result)
        
        return {
            "coordination_type": "agent_coordination",
            "strategy": coordination_strategy,
            "coordinated_agents": len(agents),
            "results": results
        }
    
    async def _balance_load(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Balance workload among agents"""
        available_agents = [agent for agent in self.managed_agents if agent.status == AgentStatus.IDLE]
        
        return {
            "load_balancing": True,
            "available_agents": len(available_agents),
            "total_agents": len(self.managed_agents)
        }
    
    async def _resolve_conflicts(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflicts between agents"""
        conflicts = task.get("conflicts", [])
        
        return {
            "conflict_resolution": True,
            "conflicts_resolved": len(conflicts),
            "resolution_strategy": "priority_based"
        }
    
    async def _generic_coordination(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generic coordination task"""
        return {
            "coordination_type": "generic",
            "message": "Generic coordination task completed"
        }
    
    def register_agent(self, agent: SubAgent):
        """Register a sub-agent for coordination"""
        self.managed_agents.append(agent)
        logger.info(f"Registered agent {agent.name} with coordinator {self.name}")
    
    def _get_agent_by_id(self, agent_id: str) -> Optional[SubAgent]:
        """Get agent by ID"""
        for agent in self.managed_agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def get_capabilities(self) -> List[str]:
        """Return coordinator agent capabilities"""
        return [
            "multi-agent coordination",
            "load balancing",
            "conflict resolution",
            "task distribution",
            "agent management"
        ]


class ExecutorAgent(SubAgent):
    """Execution agent for running complex operations"""
    
    def __init__(self, agent_id: str, name: str, description: str):
        super().__init__(agent_id, AgentType.EXECUTOR, name, description)
        self.execution_strategies = ["direct", "tool_based", "iterative", "recursive"]
        self.max_iterations = 5
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complex task"""
        try:
            self.update_status(AgentStatus.BUSY)
            start_time = datetime.now()
            
            execution_type = task.get("type", "direct")
            
            if execution_type == "direct":
                result = await self._direct_execution(task)
            elif execution_type == "tool_based":
                result = await self._tool_based_execution(task)
            elif execution_type == "iterative":
                result = await self._iterative_execution(task)
            else:
                result = await self._generic_execution(task)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result.update({
                "agent_id": self.agent_id,
                "agent_type": self.agent_type.value,
                "execution_time": execution_time,
                "strategy": execution_type
            })
            
            self.update_status(AgentStatus.COMPLETED)
            self.record_execution(task, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "agent_id": self.agent_id,
                "execution_time": (datetime.now() - start_time).total_seconds()
            }
            self.update_status(AgentStatus.ERROR)
            self.record_execution(task, error_result)
            return error_result
    
    async def _direct_execution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Direct execution of task"""
        return {
            "execution_type": "direct",
            "result": "Task executed directly",
            "operations_count": 1
        }
    
    async def _tool_based_execution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Tool-based execution"""
        tools = task.get("tools", [])
        results = []
        from core.tools import tool_registry
        for tool_config in tools:
            tool_name = tool_config.get("name")
            tool_params = tool_config.get("parameters", {})
            
            try:
                # Execute tool
                tool_config_obj = tool_registry.get_tool_config(tool_name)
                if tool_config_obj:
                    tool_function = tool_registry.functions.get(tool_config_obj["function_name"])
                    if tool_function:
                        result = await tool_function(**tool_params)
                        results.append(result)
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                results.append({"error": str(e)})
        
        return {
            "execution_type": "tool_based",
            "tools_executed": len(tools),
            "results": results
        }
    
    async def _iterative_execution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Iterative execution with feedback loop"""
        iterations = 0
        current_state = task.get("initial_state", {})
        target_state = task.get("target_state", {})
        
        while iterations < self.max_iterations and current_state != target_state:
            iterations += 1
            # Simulate iteration
            current_state = {**current_state, f"iteration_{iterations}": True}
            
            if iterations % 2 == 0:
                logger.debug(f"Iteration {iterations}: state updated")
        
        return {
            "execution_type": "iterative",
            "iterations": iterations,
            "converged": current_state == target_state,
            "final_state": current_state
        }
    
    async def _generic_execution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generic execution"""
        return {
            "execution_type": "generic",
            "message": "Generic execution completed"
        }
    
    def get_capabilities(self) -> List[str]:
        """Return executor agent capabilities"""
        return [
            "direct execution",
            "tool-based execution", 
            "iterative processing",
            "complex task execution",
            "operation chaining"
        ]


class HierarchicalToolManager:
    """Manager for hierarchical tools and sub-agents"""
    
    def __init__(self):
        self.agents = {}
        self.agent_registry = {}
        self.tool_hierarchies = {}
        self.execution_graph = {}
        
    def register_agent(self, agent: SubAgent):
        """Register a sub-agent"""
        self.agents[agent.agent_id] = agent
        self.agent_registry[agent.agent_type.value] = agent.agent_id
        logger.info(f"Registered agent: {agent.name} ({agent.agent_type.value})")
    
    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[SubAgent]:
        """Get all agents of specific type"""
        return [agent for agent in self.agents.values() if agent.agent_type == agent_type]
    
    def create_tool_hierarchy(self, name: str, root_agent_id: str, child_agents: List[str]):
        """Create a hierarchical tool structure"""
        self.tool_hierarchies[name] = {
            "root_agent": root_agent_id,
            "child_agents": child_agents,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Created tool hierarchy: {name} with root {root_agent_id}")
    
    async def execute_hierarchical_task(self, hierarchy_name: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task through hierarchical tool structure"""
        try:
            if hierarchy_name not in self.tool_hierarchies:
                raise ValueError(f"Tool hierarchy '{hierarchy_name}' not found")
            
            hierarchy = self.tool_hierarchies[hierarchy_name]
            root_agent_id = hierarchy["root_agent"]
            child_agents = hierarchy["child_agents"]
            
            # Start with root agent
            root_agent = self.get_agent(root_agent_id)
            if not root_agent:
                raise ValueError(f"Root agent '{root_agent_id}' not found")
            
            # Execute root task
            root_result = await root_agent.execute(task)
            
            # Execute child tasks if needed
            child_results = []
            for child_id in child_agents:
                child_agent = self.get_agent(child_id)
                if child_agent:
                    child_task = {
                        "type": "subordinate_task",
                        "parent_result": root_result,
                        "data": task.get("data", {})
                    }
                    child_result = await child_agent.execute(child_task)
                    child_results.append(child_result)
            
            return {
                "hierarchy": hierarchy_name,
                "root_result": root_result,
                "child_results": child_results,
                "execution_time": root_result.get("execution_time", 0) + sum(r.get("execution_time", 0) for r in child_results)
            }
            
        except Exception as e:
            logger.error(f"Hierarchical task execution error: {e}")
            return {"error": str(e), "hierarchy": hierarchy_name}
    
    async def optimize_execution_graph(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize execution order based on dependencies"""
        # Simple dependency analysis
        dependency_graph = {}
        task_map = {task.get("id"): task for task in tasks}
        
        for task in tasks:
            task_id = task.get("id")
            dependencies = task.get("dependencies", [])
            dependency_graph[task_id] = dependencies
        
        # Find execution order using topological sort
        execution_order = self._topological_sort(dependency_graph)
        
        return {
            "optimized_order": execution_order,
            "total_tasks": len(tasks),
            "dependency_analysis": dependency_graph
        }
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Topological sort for task ordering"""
        # Simple implementation
        in_degree = {node: 0 for node in graph}
        for node, deps in graph.items():
            for dep in deps:
                in_degree[dep] = in_degree.get(dep, 0) + 1
        
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor, deps in graph.items():
                if node in deps:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of the entire sub-agent system"""
        status_by_type = {}
        for agent_type in AgentType:
            agents = self.get_agents_by_type(agent_type)
            status_by_type[agent_type.value] = {
                "count": len(agents),
                "active": len([a for a in agents if a.status == AgentStatus.BUSY]),
                "idle": len([a for a in agents if a.status == AgentStatus.IDLE]),
                "error": len([a for a in agents if a.status == AgentStatus.ERROR])
            }
        
        return {
            "total_agents": len(self.agents),
            "hierarchies": len(self.tool_hierarchies),
            "status_by_type": status_by_type,
            "system_health": "healthy" if len([a for a in self.agents.values() if a.status == AgentStatus.ERROR]) == 0 else "degraded"
        }


def initialize_default_agents():
    """Initialize default sub-agents"""
    # Create specialist agents
    research_agent = SpecialistAgent("research_001", "research", "Research Specialist", "Specializes in research and data analysis")
    web_agent = SpecialistAgent("web_001", "web", "Web Specialist", "Specializes in web operations and APIs")
    data_agent = SpecialistAgent("data_001", "data", "Data Specialist", "Specializes in data processing and analysis")
    
    # Create coordinator agent
    coordinator = CoordinatorAgent("coord_001", "Task Coordinator", "Coordinates multiple sub-agents")
    
    # Create executor agent
    executor = ExecutorAgent("exec_001", "Task Executor", "Executes complex multi-step operations")
    # Global hierarchical tool manager
    

    # Register agents
    for agent in [research_agent, web_agent, data_agent, coordinator, executor]:
        hierarchical_tool_manager.register_agent(agent)
    
    # Create tool hierarchy
    hierarchical_tool_manager.create_tool_hierarchy(
        "research_workflow", 
        "coord_001", 
        ["research_001", "web_001", "data_001", "exec_001"]
    )
    
    logger.info("Initialized default sub-agent hierarchy")


# Initialize default agents on import
hierarchical_tool_manager = HierarchicalToolManager()
initialize_default_agents()