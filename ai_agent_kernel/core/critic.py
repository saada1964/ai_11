import json
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from config.logger import logger
from core.llm_client import llm_client
from models.models import Tool


class Critic:
    """Independent critique system for self-correction and quality improvement"""
    
    def __init__(self):
        self.critique_prompt = self._build_critique_prompt()
        self.improvement_suggestions = {
            "plan_optimization": [
                "Simplify complex steps",
                "Remove redundant operations", 
                "Improve step dependencies",
                "Use more efficient tool combinations"
            ],
            "tool_selection": [
                "Consider alternative tools that might be more suitable",
                "Check if there are more accurate or faster tools available",
                "Validate tool parameters and inputs",
                "Ensure tool compatibility with the use case"
            ],
            "logic_validation": [
                "Verify step sequence logic",
                "Check for logical inconsistencies",
                "Ensure dependencies are correctly ordered",
                "Validate business logic flow"
            ],
            "cost_optimization": [
                "Identify expensive operations",
                "Suggest cost-effective alternatives",
                "Balance accuracy vs cost trade-offs",
                "Prioritize essential vs nice-to-have steps"
            ]
        }
    
    def _build_critique_prompt(self) -> str:
        """Build the system prompt for critique generation"""
        return """You are an expert AI critique assistant. Your role is to analyze execution plans for potential issues and suggest improvements.

Your Response Format:
Return ONLY a valid JSON object with this exact structure:
{
    "overall_score": 1-10,
    "is_plan_valid": true/false,
    "confidence_level": 0.0-1.0,
    "issues_found": [
        {
            "category": "plan_optimization" | "tool_selection" | "logic_validation" | "cost_optimization",
            "severity": "low" | "medium" | "high" | "critical",
            "description": "Issue description",
            "step_id": "affected_step_id_or_null",
            "suggestion": "How to fix this issue"
        }
    ],
    "suggestions": [
        {
            "category": "improvement_area",
            "description": "Improvement description",
            "implementation_difficulty": "low" | "medium" | "high",
            "expected_benefit": "low" | "medium" | "high"
        }
    ],
    "improved_plan": {
        "description": "Improved plan description",
        "steps": [
            {
                "id": "step_id",
                "type": "TOOL_CALL" | "DIRECT_ANSWER", 
                "tool": "tool_name_if_applicable",
                "description": "Improved description",
                "parameters": {},
                "dependencies": [],
                "changes_made": "What was changed and why"
            }
        ],
        "memory_update": {
            "action": "save" | "none",
            "data": {}
        }
    },
    "summary": "Brief summary of findings and recommended changes"
}

Scoring Criteria:
- 10: Perfect plan, no issues found
- 8-9: Minor optimizations possible
- 6-7: Some improvements needed
- 4-5: Significant issues found
- 1-3: Plan has major problems

Available Tools Context:
{available_tools_context}

Current User Query: {user_query}
Current User Memory: {user_memory}
Generated Plan: {plan_to_review}

Now perform your critique:"""
    
    async def critique_plan(self, 
                          user_query: str,
                          user_memory: Dict[str, Any],
                          plan: Dict[str, Any], 
                          available_tools: List[Tool],
                          model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive critique of a generated plan"""
        try:
            logger.info(f"Starting plan critique for: {user_query[:100]}...")
            
            # Prepare tools context for critique
            tools_context = self._format_tools_context(available_tools)
            
            # Build critique prompt
            critique_prompt = self.critique_prompt.format(
                available_tools_context=tools_context,
                user_query=user_query,
                user_memory=json.dumps(user_memory, indent=2) if user_memory else "No memory available",
                plan_to_review=json.dumps(plan, indent=2)
            )
            
            messages = [
                {"role": "system", "content": critique_prompt},
                {"role": "user", "content": f"Critique this plan for {user_query}"}
            ]
            
            # Call critic model
            response = await llm_client.call_model(model_config, messages)
            
            try:
                critique_result = json.loads(response["content"])
                logger.info(f"Plan critique completed: Score {critique_result.get('overall_score', 'N/A')}/10")
                
                # Add meta_data
                critique_result.update({
                    "critique_token_usage": response.get("tokens_used", 0),
                    "critique_model": model_config.get("name"),
                    "critique_timestamp": self._get_timestamp(),
                    "original_plan_score": self._estimate_plan_quality(plan)
                })
                
                return critique_result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse critique response as JSON: {e}")
                return self._fallback_critique(plan, user_query)
                
        except Exception as e:
            logger.error(f"Plan critique error: {e}")
            return self._fallback_critique(plan, user_query)
    
    def _format_tools_context(self, tools: List[Tool]) -> str:
        """Format available tools for critique context"""
        context_lines = []
        
        for tool in tools:
            context_lines.append(f"- {tool.name}: {tool.description}")
            if tool.parameters:
                param_str = ", ".join([f"{k}: {v}" for k, v in tool.parameters.items()])
                context_lines.append(f"  Parameters: {param_str}")
            if tool.price_usd:
                context_lines.append(f"  Cost: ${tool.price_usd}")
            context_lines.append("")
        
        return "\n".join(context_lines)
    
    def _estimate_plan_quality(self, plan: Dict[str, Any]) -> float:
        """Quick heuristic estimate of plan quality"""
        quality_score = 5.0  # Base score
        
        # Check plan structure
        plan_data = plan.get("plan", {})
        steps = plan_data.get("steps", [])
        
        if not steps:
            return 3.0  # Empty plan is poor
        
        # Bonus for having clear description
        if plan_data.get("description"):
            quality_score += 1.0
        
        # Bonus for proper step structure
        has_valid_steps = all(
            step.get("id") and step.get("type") 
            for step in steps
        )
        if has_valid_steps:
            quality_score += 1.0
        
        # Penalty for circular dependencies
        step_ids = [step.get("id") for step in steps]
        if len(step_ids) != len(set(step_ids)):
            quality_score -= 2.0
        
        # Bonus for memory updates
        if plan.get("memory_update", {}).get("action") == "save":
            quality_score += 0.5
        
        return max(1.0, min(10.0, quality_score))
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _fallback_critique(self, plan: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Fallback critique when parsing fails"""
        return {
            "overall_score": 7.0,
            "is_plan_valid": True,
            "confidence_level": 0.5,
            "issues_found": [
                {
                    "category": "plan_optimization",
                    "severity": "low",
                    "description": "Plan critique could not be completed",
                    "step_id": None,
                    "suggestion": "Manual review recommended"
                }
            ],
            "suggestions": [
                {
                    "category": "plan_optimization", 
                    "description": "Manual validation of plan logic",
                    "implementation_difficulty": "medium",
                    "expected_benefit": "medium"
                }
            ],
            "improved_plan": plan,  # Keep original plan
            "summary": "Critique system encountered an error, using original plan",
            "critique_error": True
        }
    
    async def validate_tool_usage(self, tool_name: str, parameters: Dict[str, Any], 
                                available_tools: List[Tool]) -> Dict[str, Any]:
        """Validate specific tool usage before execution"""
        try:
            # Find the tool
            tool = next((t for t in available_tools if t.name == tool_name), None)
            if not tool:
                return {
                    "is_valid": False,
                    "issue_type": "tool_not_found",
                    "message": f"Tool '{tool_name}' is not available"
                }
            
            # Validate parameters
            expected_params = tool.parameters or {}
            validation_issues = []
            
            # Check required parameters
            for param_name, param_schema in expected_params.items():
                if param_schema.get("required", False) and param_name not in parameters:
                    validation_issues.append({
                        "parameter": param_name,
                        "issue": "required_parameter_missing",
                        "message": f"Required parameter '{param_name}' is missing"
                    })
            
            # Check parameter types
            for param_name, value in parameters.items():
                if param_name in expected_params:
                    expected_type = expected_params[param_name].get("type", "string")
                    if not self._validate_parameter_type(value, expected_type):
                        validation_issues.append({
                            "parameter": param_name,
                            "issue": "incorrect_type",
                            "message": f"Parameter '{param_name}' should be of type {expected_type}"
                        })
            
            return {
                "is_valid": len(validation_issues) == 0,
                "tool_name": tool_name,
                "validation_issues": validation_issues,
                "suggestions": self._get_tool_usage_suggestions(tool, parameters)
            }
            
        except Exception as e:
            logger.error(f"Tool validation error: {e}")
            return {
                "is_valid": True,  # Assume valid if validation fails
                "error": str(e)
            }
    
    def _validate_parameter_type(self, value: Any, expected_type: str) -> bool:
        """Validate parameter type"""
        type_checks = {
            "string": lambda x: isinstance(x, str),
            "integer": lambda x: isinstance(x, int),
            "number": lambda x: isinstance(x, (int, float)),
            "boolean": lambda x: isinstance(x, bool),
            "array": lambda x: isinstance(x, list),
            "object": lambda x: isinstance(x, dict)
        }
        
        check_func = type_checks.get(expected_type)
        return check_func(value) if check_func else True
    
    def _get_tool_usage_suggestions(self, tool: Tool, parameters: Dict[str, Any]) -> List[str]:
        """Get suggestions for better tool usage"""
        suggestions = []
        
        # Cost optimization suggestions
        if tool.price_usd and tool.price_usd > 0.01:
            suggestions.append("Consider if this tool is cost-effective for your use case")
        
        # Alternative tool suggestions
        if tool.name == "web_search_serper":
            suggestions.append("For simple queries, consider using wikipedia_search for faster results")
        elif tool.name == "wikipedia_search":
            suggestions.append("For real-time information, web_search_serper might be more current")
        
        # Parameter optimization
        if tool.name == "web_search_serper" and "query" in parameters:
            query = parameters["query"]
            if len(query) < 5:
                suggestions.append("Query is very short, consider adding more specific terms")
            elif len(query) > 100:
                suggestions.append("Query is very long, consider making it more concise")
        
        return suggestions
    
    async def generate_improvement_suggestions(self, 
                                             critique_result: Dict[str, Any],
                                             user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable improvement suggestions based on critique"""
        try:
            suggestions = []
            
            # Process issues found
            for issue in critique_result.get("issues_found", []):
                category = issue.get("category")
                severity = issue.get("severity")
                
                if category in self.improvement_suggestions:
                    for suggestion in self.improvement_suggestions[category]:
                        suggestions.append({
                            "issue_category": category,
                            "issue_description": issue.get("description"),
                            "suggestion": suggestion,
                            "severity": severity,
                            "actionable": True,
                            "estimated_effort": self._estimate_effort(category, suggestion),
                            "expected_impact": self._estimate_impact(category, suggestion)
                        })
            
            # Sort by severity and impact
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            suggestions.sort(
                key=lambda x: (severity_order.get(x["severity"], 0), x["expected_impact"]),
                reverse=True
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Improvement suggestions generation error: {e}")
            return []
    
    def _estimate_effort(self, category: str, suggestion: str) -> str:
        """Estimate implementation effort"""
        effort_keywords = {
            "low": ["simplify", "remove", "basic", "quick"],
            "medium": ["improve", "optimize", "enhance", "adjust"],
            "high": ["restructure", "rebuild", "complex", "major"]
        }
        
        for effort, keywords in effort_keywords.items():
            if any(keyword in suggestion.lower() for keyword in keywords):
                return effort
        
        return "medium"
    
    def _estimate_impact(self, category: str, suggestion: str) -> str:
        """Estimate expected impact"""
        impact_keywords = {
            "high": ["major", "critical", "essential", "significant"],
            "medium": ["improve", "enhance", "better", "optimize"],
            "low": ["minor", "nice-to-have", "optional", "simple"]
        }
        
        for impact, keywords in impact_keywords.items():
            if any(keyword in suggestion.lower() for keyword in keywords):
                return impact
        
        return "medium"


# Global critic instance
critic = Critic()