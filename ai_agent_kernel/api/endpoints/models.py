from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database.database import get_db
from schemas.schemas import LLMModel, LLMModelCreate
from config.logger import logger

router = APIRouter()


@router.get("/", response_model=list[LLMModel])
async def get_models(db: AsyncSession = Depends(get_db)):
    """Get all available models"""
    try:
        result = await db.execute(
            text("SELECT * FROM llm_models ORDER BY provider, price_per_million_tokens")
        )
        
        models = []
        for row in result.fetchall():
            models.append({
                "id": row[0],
                "name": row[1],
                "provider": row[2],
                "api_endpoint": row[3],
                "api_standard": row[4],
                "price_per_million_tokens": float(row[5]),
                "role": row[6],
                "max_tokens": row[7],
                "temperature": float(row[8]) if row[8] else 0.7,
                "is_active": row[9],
                "created_at": row[10].isoformat() if row[10] else None,
                "updated_at": row[11].isoformat() if row[11] else None
            })
        
        return models
        
    except Exception as e:
        logger.error(f"Get models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_models(db: AsyncSession = Depends(get_db)):
    """Get only active models by role"""
    try:
        result = await db.execute(
            text("""
                SELECT role, name, provider, price_per_million_tokens
                FROM llm_models 
                WHERE is_active = true 
                ORDER BY role, price_per_million_tokens
            """)
        )
        
        models_by_role = {}
        for row in result.fetchall():
            role = row[0]
            if role not in models_by_role:
                models_by_role[role] = []
            
            models_by_role[role].append({
                "name": row[1],
                "provider": row[2],
                "price_per_million_tokens": float(row[3])
            })
        
        return {
            "models_by_role": models_by_role,
            "available_roles": list(models_by_role.keys())
        }
        
    except Exception as e:
        logger.error(f"Get active models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=LLMModel)
async def create_model(model: LLMModelCreate, db: AsyncSession = Depends(get_db)):
    """Create a new model configuration"""
    try:
        # Check if model name already exists
        existing = await db.execute(
            text("SELECT id FROM llm_models WHERE name = :name"),
            {"name": model.name}
        )
        
        if existing.fetchone():
            raise HTTPException(status_code=400, detail="Model name already exists")
        
        # Insert new model
        result = await db.execute(
            text("""
                INSERT INTO llm_models 
                (name, provider, api_endpoint, api_standard, price_per_million_tokens, 
                 role, max_tokens, temperature, is_active)
                VALUES (:name, :provider, :api_endpoint, :api_standard, 
                        :price_per_million_tokens, :role, :max_tokens, :temperature, :is_active)
                RETURNING *
            """),
            {
                "name": model.name,
                "provider": model.provider,
                "api_endpoint": model.api_endpoint,
                "api_standard": model.api_standard,
                "price_per_million_tokens": model.price_per_million_tokens,
                "role": model.role,
                "max_tokens": model.max_tokens or 4000,
                "temperature": model.temperature or 0.7,
                "is_active": model.is_active
            }
        )
        
        row = result.fetchone()
        
        return {
            "id": row[0],
            "name": row[1],
            "provider": row[2],
            "api_endpoint": row[3],
            "api_standard": row[4],
            "price_per_million_tokens": float(row[5]),
            "role": row[6],
            "max_tokens": row[7],
            "temperature": float(row[8]) if row[8] else 0.7,
            "is_active": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "updated_at": row[11].isoformat() if row[11] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}", response_model=LLMModel)
async def get_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific model"""
    try:
        result = await db.execute(
            text("SELECT * FROM llm_models WHERE id = :model_id"),
            {"model_id": model_id}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return {
            "id": row[0],
            "name": row[1],
            "provider": row[2],
            "api_endpoint": row[3],
            "api_standard": row[4],
            "price_per_million_tokens": float(row[5]),
            "role": row[6],
            "max_tokens": row[7],
            "temperature": float(row[8]) if row[8] else 0.7,
            "is_active": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "updated_at": row[11].isoformat() if row[11] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{model_id}", response_model=LLMModel)
async def update_model(model_id: int, model_update: dict, db: AsyncSession = Depends(get_db)):
    """Update a model configuration"""
    try:
        # Check if model exists
        existing = await db.execute(
            text("SELECT id FROM llm_models WHERE id = :model_id"),
            {"model_id": model_id}
        )
        
        if not existing.fetchone():
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Build update query dynamically
        update_fields = []
        params = {"model_id": model_id}
        
        for field, value in model_update.items():
            if field in ["name", "provider", "api_endpoint", "api_standard", "role"]:
                update_fields.append(f"{field} = :{field}")
                params[field] = value
            elif field in ["price_per_million_tokens", "max_tokens", "temperature"]:
                update_fields.append(f"{field} = :{field}")
                params[field] = value
            elif field == "is_active":
                update_fields.append("is_active = :is_active")
                params["is_active"] = value
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE llm_models 
            SET {', '.join(update_fields)}
            WHERE id = :model_id
            RETURNING *
        """
        
        result = await db.execute(text(query), params)
        row = result.fetchone()
        
        return {
            "id": row[0],
            "name": row[1],
            "provider": row[2],
            "api_endpoint": row[3],
            "api_standard": row[4],
            "price_per_million_tokens": float(row[5]),
            "role": row[6],
            "max_tokens": row[7],
            "temperature": float(row[8]) if row[8] else 0.7,
            "is_active": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "updated_at": row[11].isoformat() if row[11] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{model_id}")
async def delete_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a model (soft delete by setting is_active to false)"""
    try:
        result = await db.execute(
            text("""
                UPDATE llm_models 
                SET is_active = false, updated_at = CURRENT_TIMESTAMP
                WHERE id = :model_id AND is_active = true
                RETURNING id
            """),
            {"model_id": model_id}
        )
        
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Model not found or already deleted")
        
        return {"message": "Model deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))