import json
import numpy as np
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from config.logger import logger
from core.llm_client import llm_client
from core.critic import critic
from core.dynamic_memory import dynamic_memory

from core.tools import tool_registry
from core.observability import observability_manager, observe_operation, TraceLevel
from database.database import AsyncSessionLocal


class Planner:
    """Core planning component that converts natural language requests into actionable plans with self-correction"""
    
    def __init__(self):
        self.planning_prompt = self._build_planning_prompt()
        self.enable_self_correction = True  # Enable self-correction by default
        self.max_critique_iterations = 2    # Maximum critique iterations
        self.critique_threshold = 7.0       # Minimum score to accept plan
        
        # Dynamic Memory Settings
        self.enable_dynamic_memory = True   # Enable dynamic memory retrieval
        self.memory_enhancement_threshold = 0.5  # Minimum memory relevance to use
        self.max_memory_context_items = 5   # Maximum memory items to include
        
        # Hierarchical Tools Settings
        self.enable_hierarchical_tools = True  # Enable hierarchical tool selection
        self.agent_coordination_enabled = True  # Enable sub-agent coordination
        self.tool_optimization_enabled = True   # Enable automatic tool optimization
    
    def _build_planning_prompt(self) -> str:
        """Build the system prompt for the planning model"""
        return """You are an AI planning assistant. Your job is to analyze user requests and create detailed execution plans.

Available Tools:
{available_tools}

Your Response Format:
Return ONLY a valid JSON object with this exact structure:
{{
    "intent": "direct_answer" | "execute_plan",
    "plan": {{
        "description": "Brief description of what needs to be done",
        "steps": [
            {{
                "id": "step_1",
                "type": "TOOL_CALL" | "DIRECT_ANSWER",
                "tool": "tool_name_if_applicable",
                "description": "What this step does",
                "parameters": {{}},
                "dependencies": []
            }}
        ]
    }},
    "memory_update": {{
        "action": "save" | "none",
        "data": {{}}
    }}
}}

Intent Types:
- "direct_answer": Simple question that can be answered without tools
- "execute_plan": Complex task requiring tool usage

Step Types:
- "TOOL_CALL": Execute a specific tool
- "DIRECT_ANSWER": Provide direct response without tools

Guidelines:
1. Analyze the request complexity first
2. For simple questions, use "direct_answer"
3. For tasks requiring information or computation, use "execute_plan"
4. Order steps logically with proper dependencies
5. Use memory updates sparingly - only when important context should be saved
6. Be specific in tool parameters and descriptions
7. Handle dependencies correctly (e.g., tool output as input to next step)

Examples:
Simple Question: "What's the weather today?"
Response:
{{
    "intent": "direct_answer",
    "plan": {{
        "description": "Answer weather question",
        "steps": []
    }},
    "memory_update": {{"action": "none", "data": {{}}}}
}}

Complex Task: "Search for Python tutorials and calculate 2+2"
Response:
{{
    "intent": "execute_plan",
    "plan": {{
        "description": "Search for Python tutorials and perform calculation",
        "steps": [
            {{
                "id": "search_tutorials",
                "type": "TOOL_CALL",
                "tool": "web_search_serper",
                "description": "Search for Python learning resources",
                "parameters": {{"query": "Python tutorials for beginners"}},
                "dependencies": []
            }},
            {{
                "id": "calculate",
                "type": "TOOL_CALL",
                "tool": "advanced_calculator",
                "description": "Calculate 2+2",
                "parameters": {{"expression": "2+2"}},
                "dependencies": []
            }}
        ]
    }},
    "memory_update": {{"action": "none", "data": {{}}}}
}}

Now analyze the following request:"""
    
    async def create_plan(self, user_query: str, user_memory: Dict[str, Any], 
                         available_tools: List[str], model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan for handling the user request (backward compatibility)"""
        # For backward compatibility, create plan without dynamic memory
        # This will be enhanced by orchestrator that has user context
        
        try:
            # Step 1: Generate initial plan
            initial_plan = await self._generate_initial_plan(user_query, user_memory, available_tools, model_config)
            
            # Step 2: Apply self-correction if enabled
            if self.enable_self_correction and initial_plan.get("intent") == "execute_plan":
                final_plan = await self._apply_self_correction(
                    user_query, user_memory, initial_plan, available_tools, model_config
                )
                return final_plan
            else:
                # Return initial plan without self-correction
                initial_plan["self_correction_applied"] = False
                initial_plan["critique_iterations"] = 0
                return initial_plan
                
        except Exception as e:
            logger.error(f"Planning error: {e}")
            # Return a fallback plan
            return {
                "intent": "direct_answer",
                "plan": {
                    "description": "Error in planning, using fallback",
                    "steps": []
                },
                "memory_update": {"action": "none", "data": {}},
                "fallback": True,
                "error": str(e)
            }
    
    async def create_plan_with_context(self, user_query: str, user_memory: Dict[str, Any], 
                                     available_tools: List[str], model_config: Dict[str, Any],
                                     user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Create plan with full context including user ID and database session"""
        
        @observe_operation("planner.create_plan", TraceLevel.HIGH)
        async def plan_with_context():
            try:
                # Record plan creation metrics
                observability_manager.record_metric(
                    "planner.plans_created", 1, 
                    observability_manager.metric_collector.metric_type.COUNTER,
                    {"user_id": str(user_id), "query_length": str(len(user_query))}
                )
                
                # Step 1: Generate initial plan
                async with observability_manager.trace_operation("generate_initial_plan", level=TraceLevel.MEDIUM):
                    initial_plan = await self._generate_initial_plan(user_query, user_memory, available_tools, model_config)
                
                # Step 2: Apply dynamic memory enhancement if enabled
                enhanced_plan = initial_plan
                if self.enable_dynamic_memory:
                    async with observability_manager.trace_operation("apply_dynamic_memory", level=TraceLevel.MEDIUM):
                        enhanced_plan = await self._apply_dynamic_memory_enhancement(
                            user_id=user_id,
                            user_query=user_query,
                            user_memory=user_memory,
                            plan=initial_plan,
                            db_session=db
                        )
                    
                    # Record memory enhancement metrics
                    memory_items_used = enhanced_plan.get("memory_items_used", 0)
                    observability_manager.record_metric(
                        "memory.enhancements_applied", 1,
                        observability_manager.metric_collector.metric_type.COUNTER,
                        {"user_id": str(user_id), "items_used": str(memory_items_used)}
                    )
                
                # Step 3: Apply self-correction if enabled
                if self.enable_self_correction and enhanced_plan.get("intent") == "execute_plan":
                    async with observability_manager.trace_operation("apply_self_correction", level=TraceLevel.MEDIUM):
                        final_plan = await self._apply_self_correction(
                            user_query, user_memory, enhanced_plan, available_tools, model_config
                        )
                    
                    # Record self-correction metrics
                    critique_iterations = final_plan.get("critique_iterations", 0)
                    final_score = final_plan.get("final_score", 0)
                    observability_manager.record_metric(
                        "self_correction.iterations", critique_iterations,
                        observability_manager.metric_collector.metric_type.GAUGE,
                        {"user_id": str(user_id)}
                    )
                    observability_manager.record_metric(
                        "self_correction.final_score", final_score,
                        observability_manager.metric_collector.metric_type.GAUGE,
                        {"user_id": str(user_id)}
                    )
                    
                    return final_plan
                else:
                    # Return enhanced plan without self-correction
                    enhanced_plan["self_correction_applied"] = False
                    enhanced_plan["critique_iterations"] = 0
                    
                    observability_manager.record_metric(
                        "self_correction.skipped", 1,
                        observability_manager.metric_collector.metric_type.COUNTER,
                        {"user_id": str(user_id)}
                    )
                    
                    return enhanced_plan
                
            except Exception as e:
                logger.error(f"Planning error: {e}")
                
                # Record error metric
                observability_manager.record_metric(
                    "planner.errors", 1,
                    observability_manager.metric_collector.metric_type.COUNTER,
                    {"user_id": str(user_id), "error_type": type(e).__name__}
                )
                
                # Return a fallback plan
                return {
                    "intent": "direct_answer",
                    "plan": {
                        "description": "Error in planning, using fallback",
                        "steps": []
                    },
                    "memory_update": {"action": "none", "data": {}},
                    "fallback": True,
                    "error": str(e)
                }
        
        return await plan_with_context()
    
    async def _generate_initial_plan(self, user_query: str, user_memory: Dict[str, Any], 
                                   available_tools: List[str], model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the initial plan without self-correction"""
        try:
            # Prepare the prompt with available tools
            tools_list = "\n".join([f"- {tool}" for tool in available_tools])
            full_prompt = self.planning_prompt.format(available_tools=tools_list)
            
            # Add user memory context if available
            if user_memory:
                memory_context = f"\n\nUser Context:\n{json.dumps(user_memory, indent=2)}"
                full_prompt += memory_context
            
            # Add the user query
            full_prompt += f"\n\nUser Request: {user_query}"
            
            messages = [
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": user_query}
            ]
            
            logger.info(f"Generating initial plan for query: {user_query[:100]}...")
            
            # Call the LLM to create the plan
            response = await llm_client.call_model(model_config, messages)
            
            # Parse the JSON response
            try:
                plan_data = json.loads(response["content"])
                logger.info(f"Initial plan created successfully: {plan_data.get('intent', 'unknown')}")
                
                # Add meta_data
                plan_data.update({
                    "initial_plan": True,
                    "generation_model": model_config.get("name"),
                    "generation_timestamp": self._get_timestamp()
                })
                
                return plan_data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse planning response as JSON: {e}")
                logger.error(f"Response content: {response['content']}")
                
                # Fallback to direct answer if parsing fails
                return {
                    "intent": "direct_answer",
                    "plan": {
                        "description": "Fallback direct answer due to planning error",
                        "steps": []
                    },
                    "memory_update": {"action": "none", "data": {}},
                    "fallback": True,
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Initial plan generation error: {e}")
            raise
    
    async def _apply_self_correction(self, user_query: str, user_memory: Dict[str, Any], 
                                   plan: Dict[str, Any], available_tools: List[str], 
                                   model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply self-correction to improve plan quality"""
        try:
            logger.info("Starting self-correction process...")
            
            # Use a separate critic model for critique (could be different from planner model)
            critic_model_config = await self._get_critic_model_config(model_config)
            
            current_plan = plan.copy()
            iteration = 0
            critique_history = []
            
            while iteration < self.max_critique_iterations:
                iteration += 1
                logger.info(f"Critique iteration {iteration}")
                
                # Get critique for current plan
                critique_result = await critic.critique_plan(
                    user_query=user_query,
                    user_memory=user_memory,
                    plan=current_plan,
                    available_tools=[],  # We'll populate this differently
                    model_config=critic_model_config
                )
                
                critique_history.append(critique_result)
                
                # Check if plan quality is acceptable
                overall_score = critique_result.get("overall_score", 0)
                if overall_score >= self.critique_threshold:
                    logger.info(f"Plan quality acceptable (score: {overall_score}), stopping self-correction")
                    break
                
                # Apply improvements if available
                improved_plan = critique_result.get("improved_plan")
                if improved_plan and improved_plan != current_plan:
                    logger.info(f"Applying plan improvements from critique")
                    current_plan = improved_plan
                else:
                    logger.info("No improvements found, stopping self-correction")
                    break
            
            # Add self-correction meta_data
            current_plan.update({
                "self_correction_applied": True,
                "critique_iterations": iteration,
                "final_score": critique_result.get("overall_score", 0) if critique_result else 0,
                "critique_history": critique_history,
                "self_correction_enabled": self.enable_self_correction
            })
            
            logger.info(f"Self-correction completed: {iteration} iterations, final score: {current_plan.get('final_score', 0)}")
            return current_plan
            
        except Exception as e:
            logger.error(f"Self-correction error: {e}")
            # Return original plan with error meta_data
            plan["self_correction_error"] = str(e)
            plan["self_correction_applied"] = False
            return plan
    
    async def _get_critic_model_config(self, planner_model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get model configuration for critique (use a more capable model if available)"""
        # For now, use the same model as planner
        # In production, you might want to use a more capable model for critique
        return {
            **planner_model_config,
            "temperature": 0.1,  # Lower temperature for more consistent critique
            "max_tokens": planner_model_config.get("max_tokens", 4000) + 1000  # More tokens for detailed critique
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def _apply_dynamic_memory_enhancement(self, 
                                              user_id: int,
                                              user_query: str,
                                              user_memory: Dict[str, Any],
                                              plan: Dict[str, Any],
                                              db_session) -> Dict[str, Any]:
        """Apply dynamic memory enhancement to improve plan context awareness"""
        try:
            if not db_session:
                logger.warning("No database session available for memory enhancement")
                return plan
            
            logger.info(f"Applying dynamic memory enhancement for user {user_id}")
            
            # Get relevant memories
            memory_result = await dynamic_memory.retrieve_relevant_memory(
                user_id=user_id,
                current_query=user_query,
                db=db_session
            )
            
            # Check if memories are relevant enough
            relevant_memories = memory_result.get("memories", [])
            if not relevant_memories:
                logger.info("No relevant memories found for enhancement")
                plan["dynamic_memory_applied"] = False
                plan["memory_enhancement"] = {"reason": "no_relevant_memories"}
                return plan
            
            # Filter memories by relevance threshold
            filtered_memories = [
                memory for memory in relevant_memories
                if memory.get("relevance_score", 0) >= self.memory_enhancement_threshold
            ]
            
            if not filtered_memories:
                logger.info("No memories meet relevance threshold")
                plan["dynamic_memory_applied"] = False
                plan["memory_enhancement"] = {"reason": "below_threshold", "max_relevance": max([m.get("relevance_score", 0) for m in relevant_memories])}
                return plan
            
            # Limit memory items
            final_memories = filtered_memories[:self.max_memory_context_items]
            
            # Enhance plan with memory context
            enhanced_plan = plan.copy()
            plan_data = enhanced_plan.get("plan", {})
            
            # Add memory context to plan description
            original_description = plan_data.get("description", "")
            memory_context = self._format_memory_context(final_memories)
            
            enhanced_description = f"{original_description}\n\nMemory Context:\n{memory_context}"
            enhanced_plan["plan"]["description"] = enhanced_description
            
            # Add memory enhancement meta_data
            enhanced_plan["dynamic_memory_applied"] = True
            enhanced_plan["memory_enhancement"] = {
                "memories_used": len(final_memories),
                "average_relevance": np.mean([m["relevance_score"] for m in final_memories]),
                "max_relevance": max([m["relevance_score"] for m in final_memories]),
                "memory_types": list(set([m["type"] for m in final_memories])),
                "enhancement_timestamp": self._get_timestamp()
            }
            
            logger.info(f"Enhanced plan with {len(final_memories)} relevant memories "
                       f"(avg relevance: {enhanced_plan['memory_enhancement']['average_relevance']:.3f})")
            
            return enhanced_plan
            
        except Exception as e:
            logger.error(f"Dynamic memory enhancement error: {e}")
            plan["dynamic_memory_error"] = str(e)
            plan["dynamic_memory_applied"] = False
            return plan
    
    async def _apply_hierarchical_tool_optimization(self, 
                                                  user_query: str,
                                                  plan: Dict[str, Any],
                                                  available_tools: List[str]) -> Dict[str, Any]:
        """Apply hierarchical tool optimization to improve plan execution"""
        try:
            if not self.enable_hierarchical_tools:
                return plan
            
            logger.info("Applying hierarchical tool optimization")
            
            # Optimize tool selection
            optimization_result = await tool_registry.optimize_tool_selection(
                task_description=user_query,
                available_tools=available_tools
            )
            
            if "error" in optimization_result:
                logger.warning(f"Tool optimization failed: {optimization_result['error']}")
                plan["hierarchical_optimization"] = {"applied": False, "reason": "optimization_failed"}
                return plan
            
            recommended_tools = optimization_result.get("recommended_tools", [])
            
            if not recommended_tools:
                logger.info("No optimized tools found")
                plan["hierarchical_optimization"] = {"applied": False, "reason": "no_recommendations"}
                return plan
            
            # Enhance plan with optimized tools
            enhanced_plan = plan.copy()
            plan_data = enhanced_plan.get("plan", {})
            steps = plan_data.get("steps", [])
            
            # Update step tool selections with optimized recommendations
            updated_steps = []
            for step in steps:
                if step.get("type") == "TOOL_CALL":
                    current_tool = step.get("tool")
                    if current_tool in recommended_tools:
                        step["optimization_applied"] = True
                        step["optimization_reason"] = "recommended_by_analysis"
                    else:
                        # Check if there's a better hierarchical alternative
                        better_alternative = self._find_better_tool_alternative(current_tool, recommended_tools)
                        if better_alternative:
                            step["original_tool"] = current_tool
                            step["tool"] = better_alternative
                            step["optimization_applied"] = True
                            step["optimization_reason"] = "hierarchical_upgrade"
                
                updated_steps.append(step)
            
            enhanced_plan["plan"]["steps"] = updated_steps
            
            # Add optimization meta_data
            enhanced_plan["hierarchical_optimization"] = {
                "applied": True,
                "recommended_tools": recommended_tools,
                "optimized_steps": len([s for s in updated_steps if s.get("optimization_applied")]),
                "tool_scores": optimization_result.get("tool_scores", {}),
                "optimization_timestamp": self._get_timestamp()
            }
            
            logger.info(f"Applied hierarchical optimization: {len(recommended_tools)} recommended tools, "
                       f"{enhanced_plan['hierarchical_optimization']['optimized_steps']} steps optimized")
            
            return enhanced_plan
            
        except Exception as e:
            logger.error(f"Hierarchical tool optimization error: {e}")
            plan["hierarchical_optimization_error"] = str(e)
            plan["hierarchical_optimization"] = {"applied": False, "reason": "error"}
            return plan
    
    def _find_better_tool_alternative(self, current_tool: str, recommended_tools: List[str]) -> Optional[str]:
        """Find a better hierarchical alternative for a tool"""
        # Mapping of basic tools to their hierarchical equivalents
        hierarchical_mapping = {
            "web_search_serper": "web_analysis",
            "wikipedia_search": "web_analysis", 
            "advanced_calculator": "data_processing",
            "search_user_documents": "research_workflow"
        }
        
        # Check if current tool has a hierarchical equivalent in recommendations
        hierarchical_equivalent = hierarchical_mapping.get(current_tool)
        if hierarchical_equivalent and hierarchical_equivalent in recommended_tools:
            return hierarchical_equivalent
        
        return None
    
    def _format_memory_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format memory context for inclusion in plan description"""
        context_lines = []
        
        for i, memory in enumerate(memories, 1):
            memory_type = memory.get("type", "unknown")
            content = memory.get("content", "")
            relevance = memory.get("relevance_score", 0)
            
            # Truncate long content
            if len(content) > 300:
                content = content[:300] + "..."
            
            context_lines.append(f"{i}. [{memory_type}] (relevance: {relevance:.3f}) {content}")
        
        return "\n".join(context_lines)
    
    async def get_memory_update_plan(self, conversation_history: List[Dict[str, str]], 
                                   current_memory: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Determine if memory should be updated based on conversation"""
        try:
            # Check if there's significant new information
            recent_messages = conversation_history[-10:]  # Last 10 messages
            
            memory_prompt = f"""Analyze this conversation and determine if important new information 
should be saved to user memory. Current memory: {json.dumps(current_memory)}

Conversation:
{chr(10).join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])}

Respond with JSON:
{{
    "should_update": true/false,
    "new_information": {{}},
    "reasoning": "explanation"
}}"""
            
            messages = [
                {"role": "system", "content": "You are a memory analysis assistant. Determine what information should be saved."},
                {"role": "user", "content": memory_prompt}
            ]
            
            # Use a simple model for memory analysis
            model_config = {
                "name": "llama-3.1-8b-instant",
                "api_standard": "openai",
                "max_tokens": 1000,
                "temperature": 0.1
            }
            
            response = await llm_client.call_model(model_config, messages)
            
            try:
                memory_analysis = json.loads(response["content"])
                if memory_analysis.get("should_update", False):
                    return {
                        "action": "save",
                        "data": memory_analysis.get("new_information", {})
                    }
            except json.JSONDecodeError:
                pass
                
        except Exception as e:
            logger.error(f"Memory update analysis error: {e}")
            
        return {"action": "none", "data": {}}
    
    async def validate_plan_logic(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate plan logic and dependencies"""
        try:
            validation_result = {
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            steps = plan.get("plan", {}).get("steps", [])
            step_ids = [step.get("id") for step in steps]
            
            # Check for duplicate step IDs
            if len(step_ids) != len(set(step_ids)):
                validation_result["issues"].append({
                    "type": "duplicate_step_ids",
                    "description": "Found duplicate step IDs",
                    "severity": "high"
                })
                validation_result["is_valid"] = False
            
            # Check dependency validity
            for step in steps:
                step_id = step.get("id")
                dependencies = step.get("dependencies", [])
                
                for dep in dependencies:
                    if dep not in step_ids:
                        validation_result["issues"].append({
                            "type": "invalid_dependency",
                            "description": f"Step {step_id} depends on non-existent step {dep}",
                            "step_id": step_id,
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
            
            # Add recommendations for improvement
            if len(steps) > 10:
                validation_result["recommendations"].append({
                    "type": "complex_plan",
                    "description": "Plan has many steps, consider breaking into smaller tasks",
                    "priority": "medium"
                })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Plan validation error: {e}")
            return {
                "is_valid": False,
                "issues": [{"type": "validation_error", "description": str(e), "severity": "high"}],
                "warnings": [],
                "recommendations": []
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
    
    async def optimize_plan_efficiency(self, plan: Dict[str, Any], 
                                     available_tools: List[str]) -> Dict[str, Any]:
        """Optimize plan for efficiency and cost"""
        try:
            optimized_plan = plan.copy()
            steps = optimized_plan.get("plan", {}).get("steps", [])
            
            # Group similar consecutive operations
            grouped_steps = self._group_similar_steps(steps)
            
            # Identify potential optimizations
            optimizations_applied = []
            
            # Check for redundant steps
            original_count = len(steps)
            optimized_count = len(grouped_steps)
            
            if optimized_count < original_count:
                optimizations_applied.append({
                    "type": "step_grouping",
                    "description": f"Grouped {original_count} steps into {optimized_count} logical groups",
                    "impact": "medium"
                })
                optimized_plan["plan"]["steps"] = grouped_steps
            
            # Add optimization meta_data
            optimized_plan["optimizations_applied"] = optimizations_applied
            optimized_plan["original_step_count"] = original_count
            optimized_plan["optimized_step_count"] = optimized_count
            
            return optimized_plan
            
        except Exception as e:
            logger.error(f"Plan optimization error: {e}")
            return plan
    
    def _group_similar_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group similar consecutive steps to improve efficiency"""
        if len(steps) < 2:
            return steps
        
        grouped_steps = []
        current_group = []
        
        for step in steps:
            if not current_group:
                current_group = [step]
            else:
                # Check if step is similar to current group
                last_step = current_group[-1]
                
                if (step.get("type") == last_step.get("type") and 
                    step.get("tool") == last_step.get("tool")):
                    # Add to current group
                    current_group.append(step)
                else:
                    # Start new group
                    if len(current_group) > 1:
                        # Merge group steps
                        merged_step = self._merge_similar_steps(current_group)
                        grouped_steps.append(merged_step)
                    else:
                        grouped_steps.extend(current_group)
                    current_group = [step]
        
        # Add remaining group
        if len(current_group) > 1:
            merged_step = self._merge_similar_steps(current_group)
            grouped_steps.append(merged_step)
        else:
            grouped_steps.extend(current_group)
        
        return grouped_steps
    
    def _merge_similar_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple similar steps into a single optimized step"""
        if len(steps) == 1:
            return steps[0]
        
        # Take the first step as base
        merged_step = steps[0].copy()
        
        # Update description to reflect grouping
        original_description = merged_step.get("description", "")
        merged_step["description"] = f"Grouped operation: {original_description} (+ {len(steps)-1} similar steps)"
        
        # Merge parameters if they exist
        all_parameters = {}
        for step in steps:
            params = step.get("parameters", {})
            if isinstance(params, dict):
                all_parameters.update(params)
        
        if all_parameters:
            merged_step["parameters"] = all_parameters
        
        # Add grouping meta_data
        merged_step["is_grouped"] = True
        merged_step["grouped_steps"] = [step.get("id") for step in steps]
        
        return merged_step