import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import HTTPException
from config.logger import logger
from core.planner import Planner
from core.executor import Executor
from core.tools import tool_registry
from core.accounting import accounting_service
from core.dynamic_memory import dynamic_memory

from core.ui_components import ui_component_manager, create_enhanced_response
from core.observability import observability_manager, observe_operation, TraceLevel
from models.models import User, LLMModel, Tool, Conversation, Message
from schemas.schemas import AgentRequest


class Orchestrator:
    """Main orchestrator that manages the complete request lifecycle"""
    
    def __init__(self):
        self.planner = Planner()
        self.executor = Executor()
        
    async def process_request(self, db: AsyncSession, request: AgentRequest) -> Dict[str, Any]:
        """Process a complete agent request"""
        async with observability_manager.trace_operation(
            "orchestrator.process_request",
            {"user_id": str(request.user_id), "query_length": str(len(request.query))},
            TraceLevel.HIGH
        ):
            try:
                logger.info(f"Processing request from user {request.user_id}: {request.query[:100]}...")
                
                # Record request metric
                observability_manager.record_metric(
                    "requests.total", 1, observability_manager.metric_collector.metric_type.COUNTER,
                    {"user_id": str(request.user_id)}
                )
            
                # 1. Get user context and memory
                async with observability_manager.trace_operation("get_user_memory", level=TraceLevel.MEDIUM):
                    user_memory = await self._get_user_memory(db, request.user_id)
                
                # 2. Get conversation context
                async with observability_manager.trace_operation("get_conversation_context", level=TraceLevel.MEDIUM):
                    conversation_id, conversation_context = await self._get_conversation_context(
                        db, request.user_id, request.conversation_id
                    )
                
                # 3. Load available models and tools
                async with observability_manager.trace_operation("load_configurations", level=TraceLevel.MEDIUM):
                    model_config = await self._get_model_config(db, role="planner")
                    available_tools = await self._get_available_tools(db)
                    await self._load_tools_to_registry(db)
                
                # 4. Create plan with self-correction and dynamic memory
                async with observability_manager.trace_operation("create_plan", level=TraceLevel.HIGH):
                    plan = await self.planner.create_plan_with_context(
                        user_query=request.query,
                        user_memory=user_memory,
                        available_tools=available_tools,
                        model_config=model_config,
                        user_id=request.user_id,
                        db=db
                    )
                    
                    # Log plan creation metrics
                    memory_applied = plan.get("dynamic_memory_applied", False)
                    self_correction_applied = plan.get("self_correction_applied", False)
                    hierarchical_optimization = plan.get("hierarchical_optimization", {}).get("applied", False)
                    
                    logger.info(f"Plan created: memory={memory_applied}, self_correction={self_correction_applied}, "
                               f"hierarchical={hierarchical_optimization}")
                
                # Log hierarchical system status periodically
                if hasattr(self, '_last_status_log') and (datetime.now() - self._last_status_log).seconds > 300:
                    from core.sub_agents import hierarchical_tool_manager
                    system_status = hierarchical_tool_manager.get_system_status()
                    logger.info(f"Hierarchical system status: {system_status['system_health']}, "
                               f"agents: {system_status['total_agents']}, hierarchies: {system_status['hierarchies']}")
                    self._last_status_log = datetime.now()
                else:
                    self._last_status_log = datetime.now()
                
                # 5. Execute plan
                async with observability_manager.trace_operation("execute_plan", level=TraceLevel.HIGH):
                    execution_result = await self._execute_plan(db, request, plan, conversation_id)
                
                # 6. Prepare enhanced response with UI components
                async with observability_manager.trace_operation("prepare_response", level=TraceLevel.MEDIUM):
                    final_response = await self._prepare_enhanced_response(
                        db, request, plan, execution_result, conversation_id
                    )
                
                # Log plan quality metrics
                if plan.get("self_correction_applied"):
                    logger.info(f"Applied self-correction: {plan.get('critique_iterations', 0)} iterations, "
                              f"score: {plan.get('final_score', 0)}/10")
                else:
                    logger.info("Plan created without self-correction")
                
                # 7. Update memory if needed
                if plan.get("memory_update", {}).get("action") == "save":
                    await self._update_user_memory(db, request.user_id, plan["memory_update"]["data"])
                
                # 8. Save messages
                await self._save_messages(db, request, final_response, conversation_id)
                
                # 9. Log final accounting
                await self._log_final_usage(db, request, final_response, conversation_id)
                
                # Record success metric
                observability_manager.record_metric(
                    "requests.success", 1, observability_manager.metric_collector.metric_type.COUNTER,
                    {"user_id": str(request.user_id)}
                )
                
                return final_response
                
            except Exception as e:
                logger.error(f"Request processing error: {e}")
                
                # Record error metric
                observability_manager.record_metric(
                    "requests.error", 1, observability_manager.metric_collector.metric_type.COUNTER,
                    {"user_id": str(request.user_id), "error_type": type(e).__name__}
                )
                
                raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    async def _prepare_enhanced_response(self, db: AsyncSession, request: AgentRequest,
                                       plan: Dict[str, Any], execution_result: Dict[str, Any],
                                       conversation_id: int) -> Dict[str, Any]:
        """Prepare enhanced response with UI components"""
        try:
            # Get basic response first
            basic_response = await self._prepare_final_response(
                db, request, plan, execution_result, conversation_id
            )
            
            # Create enhanced response with UI components
            enhanced_response = create_enhanced_response(
                result=basic_response,
                user_id=request.user_id,
                query=request.query
            )
            
            # Add original meta_data
            enhanced_response.update({
                "original_response": basic_response,
                "enhancement_applied": True,
                "ui_components_enabled": True,
                "response_id": f"resp_{int(datetime.now().timestamp())}"
            })
            
            logger.info(f"Created enhanced response with {enhanced_response.get('component_count', 0)} UI components")
            return enhanced_response
            
        except Exception as e:
            logger.error(f"Enhanced response preparation error: {e}")
            # Fallback to basic response
            return await self._prepare_final_response(
                db, request, plan, execution_result, conversation_id
            )
    
    async def _get_user_memory(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get user's long-term memory"""
        try:
            result = await db.execute(
                text("SELECT memory_profile FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            
            memory = result.scalar() or {}
            return memory if isinstance(memory, dict) else {}
            
        except Exception as e:
            logger.error(f"Error getting user memory: {e}")
            return {}
    
    async def _get_conversation_context(self, db: AsyncSession, user_id: int, 
                                      conversation_id: Optional[int]) -> tuple[int, List[Dict[str, str]]]:
        """Get or create conversation and its recent messages"""
        if not conversation_id:
            # Create new conversation
            conversation_id = await self._create_conversation(db, user_id)
            conversation_context = []
        else:
            # Get existing conversation
            conversation_context = await self._get_recent_messages(db, conversation_id, limit=5)
        
        return conversation_id, conversation_context
    
    async def _create_conversation(self, db: AsyncSession, user_id: int) -> int:
        """Create a new conversation"""
        try:
            conversation = Conversation(
                user_id=user_id,
                title="New Conversation"
            )
            
            db.add(conversation)
            await db.flush()
            
            logger.info(f"Created new conversation {conversation.id} for user {user_id}")
            return conversation.id
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            raise
    
    async def _get_recent_messages(self, db: AsyncSession, conversation_id: int, 
                                 limit: int = 5) -> List[Dict[str, str]]:
        """Get recent messages from conversation"""
        try:
            result = await db.execute(
                text("""
                    SELECT role, content 
                    FROM messages 
                    WHERE conversation_id = :conversation_id 
                    ORDER BY created_at DESC 
                    LIMIT :limit
                """),
                {"conversation_id": conversation_id, "limit": limit}
            )
            
            messages = []
            for row in result.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1]
                })
            
            # Reverse to get chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return []
    
    async def _get_model_config(self, db: AsyncSession, role: str) -> Dict[str, Any]:
        """Get model configuration from database"""
        try:
            result = await db.execute(
                text("""
                    SELECT name, provider, api_endpoint, api_standard, 
                           price_per_million_tokens, max_tokens, temperature
                    FROM llm_models 
                    WHERE role = :role AND is_active = true 
                    ORDER BY price_per_million_tokens ASC 
                    LIMIT 1
                """),
                {"role": role}
            )
            
            row = result.fetchone()
            if not row:
                raise ValueError(f"No active model found for role: {role}")
            
            return {
                "name": row[0],
                "provider": row[1],
                "api_endpoint": row[2],
                "api_standard": row[3],
                "price_per_million_tokens": float(row[4]),
                "max_tokens": row[5],
                "temperature": float(row[6])
            }
            
        except Exception as e:
            logger.error(f"Error getting model config: {e}")
            # Fallback to default
            return {
                "name": "llama-3.1-8b-instant",
                "provider": "Groq",
                "api_endpoint": "https://api.groq.com/openai/v1/chat/completions",
                "api_standard": "openai",
                "price_per_million_tokens": 0.06,
                "max_tokens": 4000,
                "temperature": 0.3
            }
    
    async def _get_available_tools(self, db: AsyncSession) -> List[str]:
        """Get list of available tools"""
        try:
            result = await db.execute(
                text("SELECT name FROM tools WHERE is_active = true ORDER BY name")
            )
            
            tools = [row[0] for row in result.fetchall()]
            return tools
            
        except Exception as e:
            logger.error(f"Error getting available tools: {e}")
            return []
    
    async def _load_tools_to_registry(self, db: AsyncSession):
        """Load tools from database into registry"""
        try:
            result = await db.execute(
                text("SELECT name, description, function_name, price_usd, api_key_name, parameters, is_active FROM tools WHERE is_active = true")
            )
            
            tools_data = []
            for row in result.fetchall():
                tools_data.append({
                    "name": row[0],
                    "description": row[1],
                    "function_name": row[2],
                    "price_usd": float(row[3]) if row[3] else 0.0,
                    "api_key_name": row[4],
                    "parameters": row[5] or {},
                    "is_active": bool(row[6])
                })
            
            tool_registry.load_tools_from_db(tools_data)
            logger.info(f"Loaded {len(tools_data)} tools into registry")
            
        except Exception as e:
            logger.error(f"Error loading tools to registry: {e}")
    
    async def _execute_plan(self, db: AsyncSession, request: AgentRequest, 
                          plan: Dict[str, Any], conversation_id: int) -> Dict[str, Any]:
        """Execute the generated plan"""
        intent = plan.get("intent")
        
        if intent == "direct_answer":
            # Simple direct answer - no tool execution needed
            return {
                "intent": "direct_answer",
                "status": "completed",
                "message": "Direct answer - will be generated by orchestrator"
            }
        elif intent == "execute_plan":
            # Execute the plan steps
            execution_result = await self.executor.execute_plan(plan)
            return execution_result
        else:
            raise ValueError(f"Unknown intent: {intent}")
    
    async def _prepare_final_response(self, db: AsyncSession, request: AgentRequest,
                                    plan: Dict[str, Any], execution_result: Dict[str, Any],
                                    conversation_id: int) -> Dict[str, Any]:
        """Prepare the final response for the user"""
        intent = plan.get("intent")
        
        if intent == "direct_answer":
            # Generate direct answer using a summarizer model
            final_response = await self._generate_direct_answer(db, request.query)
        else:
            # For execute_plan, compile results from tool executions
            final_response = await self._compile_execution_results(execution_result, plan)
        
        return {
            "response": final_response,
            "conversation_id": conversation_id,
            "intent": intent,
            "plan_description": plan.get("plan", {}).get("description", ""),
            "tokens_used": execution_result.get("tokens_used", 0),
            "cost_usd": execution_result.get("cost_usd", 0.0)
        }
    
    async def _generate_direct_answer(self, db: AsyncSession, query: str) -> str:
        """Generate a direct answer using a summarizer model"""
        try:
            model_config = await self._get_model_config(db, role="summarizer")
            
            messages = [
                {"role": "system", "content": "You are a helpful AI assistant. Provide direct, accurate answers to user questions."},
                {"role": "user", "content": query}
            ]
            
            from core.llm_client import llm_client
            response = await llm_client.call_model(model_config, messages)
            return response["content"]
            
        except Exception as e:
            logger.error(f"Error generating direct answer: {e}")
            return "I'm sorry, I couldn't generate an answer at this time."
    
    async def _compile_execution_results(self, execution_result: Dict[str, Any], 
                                       plan: Dict[str, Any]) -> str:
        """Compile results from tool executions into a final response"""
        try:
            if execution_result.get("status") != "completed":
                return "I encountered an error while processing your request."
            
            results = execution_result.get("results", [])
            if not results:
                return "No results were generated."
            
            # Compile results from successful tool executions
            compiled_response = []
            compiled_response.append("I've completed the following tasks:")
            compiled_response.append("")
            
            for result in results:
                if result.get("status") == "success":
                    step_id = result.get("step_id", "Unknown")
                    step_type = result.get("step_type", "Unknown")
                    
                    if step_type == "TOOL_CALL":
                        tool_name = result.get("tool", "Unknown Tool")
                        tool_result = result.get("result", {})
                        
                        compiled_response.append(f"**{step_id}** ({tool_name}):")
                        
                        if tool_result.get("status") == "success":
                            # Format based on tool type
                            if tool_name == "web_search_serper":
                                search_results = tool_result.get("results", [])
                                if search_results:
                                    compiled_response.append("Here are the search results:")
                                    for i, search_result in enumerate(search_results, 1):
                                        compiled_response.append(
                                            f"{i}. **{search_result.get('title', 'No title')}**\n"
                                            f"   {search_result.get('snippet', 'No snippet')}\n"
                                            f"   Source: {search_result.get('displayLink', 'Unknown')}"
                                        )
                            elif tool_name == "wikipedia_search":
                                wiki_results = tool_result.get("results", [])
                                if wiki_results:
                                    compiled_response.append("Here's what I found:")
                                    for wiki_result in wiki_results:
                                        compiled_response.append(
                                            f"**{wiki_result.get('title', 'No title')}**\n"
                                            f"{wiki_result.get('summary', 'No summary')}"
                                        )
                            elif tool_name == "advanced_calculator":
                                expression = tool_result.get("expression", "")
                                result_val = tool_result.get("formatted_result", "")
                                compiled_response.append(f"Calculation: {expression} = {result_val}")
                            else:
                                # Generic tool result display
                                compiled_response.append(str(tool_result))
                        else:
                            compiled_response.append(f"Error: {tool_result.get('error', 'Unknown error')}")
                    
                    compiled_response.append("")  # Add blank line between steps
            
            return "\n".join(compiled_response)
            
        except Exception as e:
            logger.error(f"Error compiling execution results: {e}")
            return "I completed the tasks but encountered an error while formatting the results."
    
    async def _update_user_memory(self, db: AsyncSession, user_id: int, new_memory: Dict[str, Any]):
        """Update user's long-term memory"""
        try:
            # Merge new memory with existing memory
            result = await db.execute(
                text("SELECT memory_profile FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            
            current_memory = result.scalar() or {}
            if isinstance(current_memory, str):
                current_memory = json.loads(current_memory)
            
            # Merge memories (new takes precedence)
            updated_memory = {**current_memory, **new_memory}
            
            # Save updated memory
            await db.execute(
                text("""
                    UPDATE users 
                    SET memory_profile = :memory_profile,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """),
                {
                    "user_id": user_id,
                    "memory_profile": json.dumps(updated_memory)
                }
            )
            
            logger.info(f"Updated memory for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user memory: {e}")
    
    async def _save_messages(self, db: AsyncSession, request: AgentRequest,
                           final_response: Dict[str, Any], conversation_id: int):
        """Save user message and assistant response"""
        try:
            # Save user message
            user_message = Message(
                conversation_id=conversation_id,
                user_id=request.user_id,
                role="user",
                content=request.query,
                tokens_used=0,  # Will be calculated if needed
                cost_usd=0.0
            )
            
            db.add(user_message)
            await db.flush()  # Get user message ID
            
            # Save assistant response
            assistant_message = Message(
                conversation_id=conversation_id,
                user_id=request.user_id,
                role="assistant",
                content=final_response["response"],
                tokens_used=final_response.get("tokens_used", 0),
                cost_usd=final_response.get("cost_usd", 0.0)
            )
            
            db.add(assistant_message)
            
            # Update conversation message count
            await db.execute(
                text("""
                    UPDATE conversations 
                    SET total_messages = total_messages + 2,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :conversation_id
                """),
                {"conversation_id": conversation_id}
            )
            
            logger.info(f"Saved messages for conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error saving messages: {e}")
    
    async def _log_final_usage(self, db: AsyncSession, request: AgentRequest,
                              final_response: Dict[str, Any], conversation_id: int):
        """Log final usage for accounting"""
        try:
            usage_data = {
                "user_id": request.user_id,
                "conversation_id": conversation_id,
                "action_type": "complete_request",
                "model_name": final_response.get("model_used"),
                "input_tokens": final_response.get("tokens_used", 0) // 2,
                "output_tokens": final_response.get("tokens_used", 0) // 2,
                "cost_usd": final_response.get("cost_usd", 0.0)
            }
            
            await accounting_service.log_usage(db, usage_data)
            
        except Exception as e:
            logger.error(f"Error logging final usage: {e}")


# Global orchestrator instance
orchestrator = Orchestrator()