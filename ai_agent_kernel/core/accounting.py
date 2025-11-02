from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from config.logger import logger
from models.models import UsageLog, LLMModel, Tool


class AccountingService:
    """Handles cost calculation and usage tracking"""
    
    def __init__(self):
        # Cost calculation constants
        self.UNITS_PER_DOLLAR = 1000  # Convert dollars to units for user balance
        
    async def calculate_llm_cost(self, model_config: Dict[str, Any], 
                                input_tokens: int, output_tokens: int) -> Decimal:
        """Calculate cost for LLM usage"""
        try:
            price_per_million = Decimal(str(model_config["price_per_million_tokens"]))
            
            # Calculate cost in dollars
            total_tokens = input_tokens + output_tokens
            cost_dollars = (Decimal(total_tokens) / Decimal(1000000)) * price_per_million
            
            logger.debug(f"LLM cost calculation: {total_tokens} tokens × ${price_per_million}/M = ${cost_dollars}")
            return cost_dollars
            
        except Exception as e:
            logger.error(f"LLM cost calculation error: {e}")
            return Decimal("0.0")
    
    async def calculate_tool_cost(self, tool_config: Dict[str, Any]) -> Decimal:
        """Calculate cost for tool usage"""
        try:
            return Decimal(str(tool_config.get("price_usd", 0.0)))
        except Exception as e:
            logger.error(f"Tool cost calculation error: {e}")
            return Decimal("0.0")
    
    async def calculate_streaming_cost(self, duration_ms: int, cost_per_hour: Decimal = Decimal("0.01")) -> Decimal:
        """Calculate cost for streaming (very small cost)"""
        try:
            duration_hours = Decimal(duration_ms) / Decimal(3600000)  # Convert ms to hours
            return duration_hours * cost_per_hour
        except Exception as e:
            logger.error(f"Streaming cost calculation error: {e}")
            return Decimal("0.0")
    
    async def log_usage(self, db: AsyncSession, usage_data: Dict[str, Any]) -> Optional[int]:
        """Log usage to database"""
        try:
            usage_log = UsageLog(
                user_id=usage_data["user_id"],
                conversation_id=usage_data["conversation_id"],
                action_type=usage_data["action_type"],
                model_name=usage_data.get("model_name"),
                tool_name=usage_data.get("tool_name"),
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cost_usd=usage_data.get("cost_usd", 0.0),
                duration_ms=usage_data.get("duration_ms")
            )
            
            db.add(usage_log)
            await db.flush()  # Get the ID without committing
            
            logger.debug(f"Usage logged: {usage_data['action_type']} - ${usage_data.get('cost_usd', 0.0)}")
            return usage_log.id
            
        except Exception as e:
            logger.error(f"Usage logging error: {e}")
            return None
    
    async def check_user_balance(self, db: AsyncSession, user_id: int, estimated_cost_dollars: Decimal) -> bool:
        """Check if user has sufficient balance"""
        try:
            from models.models import User
            
            result = await db.execute(
                text("SELECT balance FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            
            user_balance_units = result.scalar()
            
            if user_balance_units is None:
                logger.warning(f"User {user_id} not found")
                return False
            
            # Convert estimated cost to units
            estimated_cost_units = int(estimated_cost_dollars * self.UNITS_PER_DOLLAR)
            
            logger.debug(f"Balance check: User {user_id} has {user_balance_units} units, needs {estimated_cost_units} units")
            
            return user_balance_units >= estimated_cost_units
            
        except Exception as e:
            logger.error(f"Balance check error: {e}")
            return True  # Allow operation if check fails
    
    async def deduct_balance(self, db: AsyncSession, user_id: int, cost_dollars: Decimal) -> bool:
        """Deduct cost from user balance"""
        try:
            cost_units = int(cost_dollars * self.UNITS_PER_DOLLAR)
            
            # Use atomic transaction to prevent race conditions
            result = await db.execute(
                text("""
                    UPDATE users 
                    SET balance = balance - :cost_units,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id AND balance >= :cost_units
                    RETURNING balance
                """),
                {
                    "user_id": user_id,
                    "cost_units": cost_units
                }
            )
            
            new_balance = result.scalar()
            
            if new_balance is not None:
                logger.info(f"Deducted {cost_units} units from user {user_id}, new balance: {new_balance}")
                return True
            else:
                logger.warning(f"Insufficient balance for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Balance deduction error: {e}")
            return False
    
    async def get_user_usage_stats(self, db: AsyncSession, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for a user"""
        try:
            result = await db.execute(
                text("""
                    SELECT 
                        action_type,
                        SUM(cost_usd) as total_cost,
                        COUNT(*) as usage_count,
                        SUM(input_tokens + output_tokens) as total_tokens
                    FROM usage_logs 
                    WHERE user_id = :user_id 
                        AND created_at >= CURRENT_DATE - INTERVAL ':days days'
                    GROUP BY action_type
                """),
                {"user_id": user_id, "days": days}
            )
            
            stats = {"user_id": user_id, "period_days": days, "by_action_type": {}}
            
            for row in result.fetchall():
                action_type = row[0]
                stats["by_action_type"][action_type] = {
                    "total_cost": float(row[1] or 0),
                    "usage_count": row[2] or 0,
                    "total_tokens": row[3] or 0
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Usage stats error: {e}")
            return {"error": str(e)}
    
    async def estimate_request_cost(self, model_config: Dict[str, Any], 
                                  tool_configs: list, estimated_tokens: int) -> Decimal:
        """Estimate total cost for a request before execution"""
        try:
            # LLM cost
            llm_cost = await self.calculate_llm_cost(
                model_config, 
                estimated_tokens // 2,  # Assume half input, half output
                estimated_tokens // 2
            )
            
            # Tool costs
            tool_cost = Decimal("0.0")
            for tool_config in tool_configs:
                tool_cost += await self.calculate_tool_cost(tool_config)
            
            total_cost = llm_cost + tool_cost
            
            logger.debug(f"Cost estimate: LLM ${llm_cost} + Tools ${tool_cost} = ${total_cost}")
            return total_cost
            
        except Exception as e:
            logger.error(f"Cost estimation error: {e}")
            return Decimal("0.0")
    
    async def format_cost_display(self, cost_dollars: Decimal) -> str:
        """Format cost for user display"""
        if cost_dollars < Decimal("0.01"):
            return f"${cost_dollars:.4f}"
        elif cost_dollars < Decimal("1.00"):
            return f"${cost_dollars:.2f}"
        else:
            return f"${cost_dollars:.2f}"
    
    async def format_balance_display(self, balance_units: int) -> Dict[str, str]:
        """Format balance for user display"""
        dollars = Decimal(balance_units) / self.UNITS_PER_DOLLAR
        
        return {
            "units": f"{balance_units:,}",
            "dollars": f"${dollars:.2f}",
            "formatted": f"{balance_units:,} units (${dollars:.2f})"
        }


# Global accounting service instance
accounting_service = AccountingService()