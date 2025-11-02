from typing import Dict, List, Any, Optional
import asyncio
from config.logger import logger
from core.tools import tool_registry
from core.observability import observability_manager, observe_operation, TraceLevel
from database.database import AsyncSessionLocal


class Executor:
    """Executes plans by running tools in the correct order with dependency management"""
    
    def __init__(self):
        self.execution_cache = {}
    
    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete plan with all its steps and quality monitoring"""
        
        @observe_operation("executor.execute_plan", TraceLevel.HIGH)
        async def execute_with_observability():
            try:
                steps = plan.get("plan", {}).get("steps", [])
                
                # Record execution metrics
                observability_manager.record_metric(
                    "executor.plans_executed", 1,
                    observability_manager.metric_collector.metric_type.COUNTER,
                    {"step_count": str(len(steps))}
                )
                
                if not steps:
                    logger.info("No steps to execute")
                    observability_manager.record_metric(
                        "executor.empty_plans", 1,
                        observability_manager.metric_collector.metric_type.COUNTER
                    )
                    return {"status": "completed", "results": []}
                
                # Validate plan logic before execution
                async with observability_manager.trace_operation("validate_plan", level=TraceLevel.MEDIUM):
                    validation_result = await self._validate_execution_plan(plan)
                    
                if not validation_result["is_valid"]:
                    logger.warning(f"Plan validation failed: {validation_result['issues']}")
                    
                    observability_manager.record_metric(
                        "executor.validation_failures", 1,
                        observability_manager.metric_collector.metric_type.COUNTER
                    )
                    
                    return {
                        "status": "validation_failed",
                        "validation_errors": validation_result["issues"],
                        "results": []
                    }
                
                # Build dependency graph
                async with observability_manager.trace_operation("build_dependency_graph", level=TraceLevel.LOW):
                    dependency_graph = self._build_dependency_graph(steps)
                
                # Execute steps in dependency order
                async with observability_manager.trace_operation("topological_sort", level=TraceLevel.LOW):
                    execution_order = self._topological_sort(dependency_graph)
                
                logger.info(f"Executing {len(execution_order)} steps in order: {[step['id'] for step in execution_order]}")
                
                results = []
                step_outputs = {}  # Store outputs for dependency resolution
                quality_metrics = {
                    "steps_completed": 0,
                    "steps_failed": 0,
                    "total_execution_time": 0,
                    "quality_score": 0.0
                }
                
                # Execute steps with quality monitoring
                for i, step in enumerate(execution_order):
                    step_start_time = asyncio.get_event_loop().time()
                    
                    async with observability_manager.trace_operation(
                        f"execute_step_{step.get('id', f'index_{i}')}", 
                        level=TraceLevel.HIGH,
                        labels={"step_id": step.get('id', f'index_{i}'), "step_type": step.get('type', 'unknown')}
                        ):
                        step_result = await self._execute_step(step, step_outputs)
                        results.append(step_result)
                        
                        # Track quality metrics
                        execution_time = asyncio.get_event_loop().time() - step_start_time
                        quality_metrics["total_execution_time"] += execution_time
                        
                        if step_result.get("status") == "success":
                            quality_metrics["steps_completed"] += 1
                        
                        step_outputs[step["id"]] = step_result
                        
                        # Record step completion metrics
                        step_id = step.get("id", f"index_{i}")
                        observability_manager.record_metric(
                            "executor.steps", 1,
                            observability_manager.metric_collector.metric_type.COUNTER,
                            {"step_id": step_id, "status": step_result.get("status", "unknown")}
                        )
                else:
                    quality_metrics["steps_failed"] += 1
                    
                    # Log step completion
                    logger.info(f"Step {i+1}/{len(execution_order)} completed: {step['id']} "
                              f"({step_result.get('status', 'unknown')}, {execution_time:.2f}s)")
                
                # Calculate overall quality score
                quality_metrics["quality_score"] = self._calculate_quality_score(quality_metrics)
                
                # Log execution summary
                logger.info(f"Plan execution completed: {quality_metrics['steps_completed']} successful, "
                          f"{quality_metrics['steps_failed']} failed, "
                          f"quality score: {quality_metrics['quality_score']:.2f}/10")
                
                # Record execution summary metrics
                observability_manager.record_metric(
                    "executor.completion_time", quality_metrics["total_execution_time"],
                    observability_manager.metric_collector.metric_type.GAUGE
                )
                observability_manager.record_metric(
                    "executor.success_rate", quality_metrics["steps_completed"] / len(execution_order),
                    observability_manager.metric_collector.metric_type.GAUGE
                )
                
                return {
                    "status": "completed",
                    "results": results,
                    "step_count": len(execution_order),
                    "quality_metrics": quality_metrics,
                    "execution_summary": {
                        "success_rate": quality_metrics["steps_completed"] / len(execution_order),
                        "average_step_time": quality_metrics["total_execution_time"] / len(execution_order)
                    }
                }
                
            except Exception as e:
                logger.error(f"Plan execution error: {e}")
                
                # Record error metrics
                observability_manager.record_metric(
                    "executor.errors", 1,
                    observability_manager.metric_collector.metric_type.COUNTER,
                    {"error_type": type(e).__name__}
                )
                
                return {
                    "status": "error",
                    "error": str(e),
                    "results": results if 'results' in locals() else [],
                    "quality_metrics": quality_metrics if 'quality_metrics' in locals() else {}
                }
        
        return await execute_with_observability()
    
    async def _validate_execution_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plan before execution"""
        try:
            validation_result = {
                "is_valid": True,
                "issues": [],
                "warnings": []
            }
            
            steps = plan.get("plan", {}).get("steps", [])
            
            # Check for empty plan
            if not steps:
                validation_result["issues"].append({
                    "type": "empty_plan",
                    "description": "Plan contains no steps to execute",
                    "severity": "high"
                })
                validation_result["is_valid"] = False
                return validation_result
            
            # Validate step structure
            for i, step in enumerate(steps):
                step_id = step.get("id")
                step_type = step.get("type")
                
                if not step_id:
                    validation_result["issues"].append({
                        "type": "missing_step_id",
                        "description": f"Step {i} is missing an ID",
                        "severity": "high"
                    })
                    validation_result["is_valid"] = False
                
                if not step_type:
                    validation_result["issues"].append({
                        "type": "missing_step_type",
                        "description": f"Step {step_id} is missing a type",
                        "severity": "high"
                    })
                    validation_result["is_valid"] = False
                
                # Validate tool steps
                if step_type == "TOOL_CALL":
                    tool_name = step.get("tool")
                    if not tool_name:
                        validation_result["issues"].append({
                            "type": "missing_tool_name",
                            "description": f"Step {step_id} is missing tool name",
                            "severity": "high"
                        })
                        validation_result["is_valid"] = False
                    
                    # Check if tool exists in registry
                    tool_config = tool_registry.get_tool_config(tool_name)
                    if not tool_config:
                        validation_result["issues"].append({
                            "type": "tool_not_found",
                            "description": f"Tool '{tool_name}' not found in registry",
                            "severity": "high"
                        })
                        validation_result["is_valid"] = False
            
            # Check for circular dependencies
            if self._has_circular_dependency(steps):
                validation_result["issues"].append({
                    "type": "circular_dependency",
                    "description": "Circular dependency detected in plan",
                    "severity": "critical"
                })
                validation_result["is_valid"] = False
            
            # Add warnings for potential issues
            if len(steps) > 20:
                validation_result["warnings"].append({
                    "type": "complex_plan",
                    "description": f"Plan has {len(steps)} steps, may be complex to execute",
                    "priority": "medium"
                })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Plan validation error: {e}")
            return {
                "is_valid": False,
                "issues": [{"type": "validation_error", "description": str(e), "severity": "high"}],
                "warnings": []
            }
    
    def _has_circular_dependency(self, steps: List[Dict[str, Any]]) -> bool:
        """Check if plan has circular dependencies using DFS"""
        try:
            # Build dependency graph
            graph = {}
            for step in steps:
                step_id = step.get("id")
                dependencies = step.get("dependencies", [])
                graph[step_id] = dependencies
            
            # DFS to detect cycles
            visited = set()
            rec_stack = set()
            
            def has_cycle(node):
                if node in rec_stack:
                    return True
                if node in visited:
                    return False
                
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in graph.get(node, []):
                    if has_cycle(neighbor):
                        return True
                
                rec_stack.remove(node)
                return False
            
            for step_id in graph:
                if step_id not in visited:
                    if has_cycle(step_id):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Circular dependency check error: {e}")
            return False
    
    def _calculate_quality_score(self, quality_metrics: Dict[str, Any]) -> float:
        """Calculate overall quality score for execution"""
        try:
            steps_completed = quality_metrics.get("steps_completed", 0)
            steps_failed = quality_metrics.get("steps_failed", 0)
            total_steps = steps_completed + steps_failed
            
            if total_steps == 0:
                return 0.0
            
            # Base score from success rate
            success_rate = steps_completed / total_steps
            base_score = success_rate * 8.0
            
            # Bonus for efficient execution
            total_time = quality_metrics.get("total_execution_time", 0)
            avg_time = total_time / total_steps if total_steps > 0 else 0
            
            # Bonus for fast execution (penalize slow steps)
            if avg_time < 1.0:
                time_bonus = 2.0
            elif avg_time < 5.0:
                time_bonus = 1.0
            elif avg_time < 10.0:
                time_bonus = 0.5
            else:
                time_bonus = 0.0
            
            final_score = min(10.0, base_score + time_bonus)
            return final_score
            
        except Exception as e:
            logger.error(f"Quality score calculation error: {e}")
            return 5.0  # Default middle score
    
    def _build_dependency_graph(self, steps: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Build dependency graph from steps"""
        graph = {}
        step_map = {step["id"]: step for step in steps}
        
        for step in steps:
            step_id = step["id"]
            dependencies = step.get("dependencies", [])
            
            # Add reverse dependencies for topological sort
            graph[step_id] = []
            for dep_id in dependencies:
                if dep_id not in graph:
                    graph[dep_id] = []
                graph[dep_id].append(step_id)
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Perform topological sort to determine execution order"""
        # Get all step IDs
        all_steps = set(graph.keys())
        for dependencies in graph.values():
            all_steps.update(dependencies)
        
        # Kahn's algorithm for topological sort
        in_degree = {step_id: 0 for step_id in all_steps}
        for step_id, deps in graph.items():
            for dep_id in deps:
                in_degree[dep_id] += 1
        
        # Start with steps that have no dependencies
        queue = [step_id for step_id in in_degree if in_degree[step_id] == 0]
        result = []
        
        while queue:
            step_id = queue.pop(0)
            result.append(step_id)
            
            # Remove this step from dependencies of other steps
            for dep_step_id, deps in graph.items():
                if step_id in deps:
                    in_degree[dep_step_id] -= 1
                    if in_degree[dep_step_id] == 0:
                        queue.append(dep_step_id)
        
        # If we have a cycle, just return all steps
        if len(result) != len(all_steps):
            logger.warning("Dependency cycle detected, executing in original order")
            # Return all steps that exist in our original steps
            return list(graph.keys())
        
        return result
    
    async def _execute_step(self, step: Dict[str, Any], previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single step"""
        step_id = step["id"]
        step_type = step["type"]
        
        logger.info(f"Executing step: {step_id} ({step_type})")
        
        try:
            if step_type == "TOOL_CALL":
                return await self._execute_tool_step(step, previous_outputs)
            elif step_type == "DIRECT_ANSWER":
                return await self._execute_direct_answer_step(step)
            else:
                raise ValueError(f"Unknown step type: {step_type}")
                
        except Exception as e:
            logger.error(f"Step execution error ({step_id}): {e}")
            return {
                "step_id": step_id,
                "status": "error",
                "error": str(e),
                "step_type": step_type
            }
    
    async def _execute_tool_step(self, step: Dict[str, Any], previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call step"""
        step_id = step["id"]
        tool_name = step.get("tool")
        parameters = step.get("parameters", {})
        
        # Check if tool exists
        tool_config = tool_registry.get_tool_config(tool_name)
        if not tool_config:
            raise ValueError(f"Tool not found: {tool_name}")
        
        # Resolve dependencies in parameters
        resolved_parameters = self._resolve_parameter_dependencies(parameters, previous_outputs)
        
        logger.info(f"Calling tool {tool_name} with parameters: {resolved_parameters}")
        
        # Get the tool function
        tool_function_name = tool_config["function_name"]
        tool_function = tool_registry.functions.get(tool_function_name)
        
        if not tool_function:
            raise ValueError(f"Tool function not found: {tool_function_name}")
        
        # Execute the tool
        result = await tool_function(**resolved_parameters)
        
        return {
            "step_id": step_id,
            "status": result.get("status", "success"),
            "tool": tool_name,
            "parameters": resolved_parameters,
            "result": result,
            "output": result,  # For dependency resolution
            "step_type": "TOOL_CALL"
        }
    
    async def _execute_direct_answer_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a direct answer step"""
        step_id = step["id"]
        description = step.get("description", "")
        
        # For direct answer steps, the actual answer will be generated by the orchestrator
        # This step just indicates that a direct response should be provided
        
        return {
            "step_id": step_id,
            "status": "completed",
            "description": description,
            "result": {"message": "Direct answer step - response will be generated by orchestrator"},
            "step_type": "DIRECT_ANSWER"
        }
    
    def _resolve_parameter_dependencies(self, parameters: Dict[str, Any], 
                                     previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameter dependencies from previous step outputs"""
        resolved_params = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # This is a dependency reference
                step_id = value[2:-2]  # Remove {{ and }}
                if step_id in previous_outputs:
                    resolved_params[key] = previous_outputs[step_id]
                    logger.info(f"Resolved dependency {key} from step {step_id}")
                else:
                    logger.warning(f"Dependency {step_id} not found for parameter {key}")
                    resolved_params[key] = value  # Keep original value
            else:
                resolved_params[key] = value
        
        return resolved_params
    
    async def execute_single_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call (for simple invocations)"""
        tool_config = tool_registry.get_tool_config(tool_name)
        if not tool_config:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool_function_name = tool_config["function_name"]
        tool_function = tool_registry.functions.get(tool_function_name)
        
        if not tool_function:
            raise ValueError(f"Tool function not found: {tool_function_name}")
        
        logger.info(f"Executing single tool: {tool_name}")
        result = await tool_function(**parameters)
        
        return {
            "tool": tool_name,
            "status": result.get("status", "success"),
            "parameters": parameters,
            "result": result
        }