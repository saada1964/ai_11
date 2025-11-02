from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.database import get_db
from schemas.schemas import Tool
from config.logger import logger

router = APIRouter()


@router.get("/", response_model=list[Tool])
async def get_tools(db: AsyncSession = Depends(get_db)):
    """Get all available tools"""
    try:
        result = await db.execute(
            text("SELECT * FROM tools ORDER BY name")
        )
        
        tools = []
        for row in result.fetchall():
            tools.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "function_name": row[3],
                "price_usd": float(row[4]) if row[4] else 0.0,
                "api_key_name": row[5],
                "is_active": row[6],
                "parameters": row[7] if row[7] else {},
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None
            })
        
        return tools
        
    except Exception as e:
        logger.error(f"Get tools error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_tools(db: AsyncSession = Depends(get_db)):
    """Get only active tools"""
    try:
        result = await db.execute(
            text("""
                SELECT name, description, function_name, price_usd, parameters
                FROM tools 
                WHERE is_active = true 
                ORDER BY name
            """)
        )
        
        tools = []
        for row in result.fetchall():
            tools.append({
                "name": row[0],
                "description": row[1],
                "function_name": row[2],
                "price_usd": float(row[3]) if row[3] else 0.0,
                "parameters": row[4] if row[4] else {}
            })
        
        return {
            "active_tools": tools,
            "count": len(tools)
        }
        
    except Exception as e:
        logger.error(f"Get active tools error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Tool)
async def create_tool(tool_data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new tool configuration"""
    try:
        # Check if tool name already exists
        existing = await db.execute(
            text("SELECT id FROM tools WHERE name = :name"),
            {"name": tool_data["name"]}
        )
        
        if existing.fetchone():
            raise HTTPException(status_code=400, detail="Tool name already exists")
        
        # Insert new tool
        result = await db.execute(
            text("""
                INSERT INTO tools 
                (name, description, function_name, price_usd, api_key_name, is_active, parameters)
                VALUES (:name, :description, :function_name, :price_usd, :api_key_name, :is_active, :parameters)
                RETURNING *
            """),
            {
                "name": tool_data["name"],
                "description": tool_data["description"],
                "function_name": tool_data["function_name"],
                "price_usd": tool_data.get("price_usd", 0.0),
                "api_key_name": tool_data.get("api_key_name"),
                "is_active": tool_data.get("is_active", True),
                "parameters": tool_data.get("parameters", {})
            }
        )
        
        row = result.fetchone()
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "function_name": row[3],
            "price_usd": float(row[4]) if row[4] else 0.0,
            "api_key_name": row[5],
            "is_active": row[6],
            "parameters": row[7] if row[7] else {},
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tool_id}", response_model=Tool)
async def get_tool(tool_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific tool"""
    try:
        result = await db.execute(
            text("SELECT * FROM tools WHERE id = :tool_id"),
            {"tool_id": tool_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "function_name": row[3],
            "price_usd": float(row[4]) if row[4] else 0.0,
            "api_key_name": row[5],
            "is_active": row[6],
            "parameters": row[7] if row[7] else {},
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(tool_id: int, tool_update: dict, db: AsyncSession = Depends(get_db)):
    """Update a tool configuration"""
    try:
        # Check if tool exists
        existing = await db.execute(
            text("SELECT id FROM tools WHERE id = :tool_id"),
            {"tool_id": tool_id}
        )
        
        if not existing.fetchone():
            raise HTTPException(status_code=404, detail="Tool not found")
        
        # Build update query dynamically
        update_fields = []
        params = {"tool_id": tool_id}
        
        for field, value in tool_update.items():
            if field in ["name", "description", "function_name", "api_key_name"]:
                update_fields.append(f"{field} = :{field}")
                params[field] = value
            elif field == "price_usd":
                update_fields.append("price_usd = :price_usd")
                params["price_usd"] = value
            elif field == "is_active":
                update_fields.append("is_active = :is_active")
                params["is_active"] = value
            elif field == "parameters":
                update_fields.append("parameters = :parameters")
                params["parameters"] = value
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE tools 
            SET {', '.join(update_fields)}
            WHERE id = :tool_id
            RETURNING *
        """
        
        result = await db.execute(text(query), params)
        row = result.fetchone()
        
        return {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "function_name": row[3],
            "price_usd": float(row[4]) if row[4] else 0.0,
            "api_key_name": row[5],
            "is_active": row[6],
            "parameters": row[7] if row[7] else {},
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tool_id}")
async def delete_tool(tool_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a tool (soft delete by setting is_active to false)"""
    try:
        result = await db.execute(
            text("""
                UPDATE tools 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = :tool_id AND is_active = true
                RETURNING id
            """),
            {"tool_id": tool_id}
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Tool not found or already deleted")
        
        return {"message": "Tool deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tool_id}/test")
async def test_tool(tool_id: int, test_params: dict, db: AsyncSession = Depends(get_db)):
    """Test a tool with given parameters"""
    try:
        from core.executor import Executor
        from core.tools import tool_registry
        
        # Get tool configuration
        result = await db.execute(
            text("SELECT name, function_name, parameters FROM tools WHERE id = :tool_id AND is_active = true"),
            {"tool_id": tool_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Tool not found or inactive")
        
        tool_name = row[0]
        function_name = row[1]
        expected_params = row[2] or {}
        
        # Load tool into registry if not already loaded
        if function_name not in tool_registry.functions:
            await db.execute(text("SELECT 1"))  # Ensure connection is active
            
            # Try to get full tool config and load it
            tool_result = await db.execute(
                text("SELECT name, description, function_name, price_usd, api_key_name FROM tools WHERE id = :tool_id"),
                {"tool_id": tool_id}
            )
            
            tool_config_row = tool_result.fetchone()
            if tool_config_row:
                tool_config = {
                    "name": tool_config_row[0],
                    "description": tool_config_row[1],
                    "function_name": tool_config_row[2],
                    "price_usd": float(tool_config_row[3]) if tool_config_row[3] else 0.0,
                    "api_key_name": tool_config_row[4],
                    "is_active": True,
                    "parameters": expected_params
                }
                
                tool_function = tool_registry.functions.get(function_name)
                if tool_function:
                    tool_registry.register_tool(tool_config, tool_function)
        
        # Get the tool function and execute it
        tool_function = tool_registry.functions.get(function_name)
        if not tool_function:
            raise HTTPException(status_code=400, detail=f"Tool function '{function_name}' not found")
        
        # Execute the tool
        executor = Executor()
        result = await executor.execute_single_tool(tool_name, test_params)
        
        return {
            "tool_name": tool_name,
            "function_name": function_name,
            "parameters_used": test_params,
            "expected_parameters": expected_params,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test tool error: {e}")
        raise HTTPException(status_code=500, detail=str(e))