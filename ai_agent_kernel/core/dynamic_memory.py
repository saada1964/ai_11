import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sklearn.metrics.pairwise import cosine_similarity
from config.logger import logger
from core.llm_client import llm_client


class DynamicMemory:
    """Advanced dynamic memory system with vector-based retrieval"""
    
    def __init__(self):
        self.embedding_dim = 1536  # OpenAI ada-002 dimensions
        self.similarity_threshold = 0.7  # Minimum similarity for relevance
        self.max_memory_items = 10  # Maximum relevant memories to return
        self.memory_cache = {}  # Cache for embeddings
        
    async def retrieve_relevant_memory(self, 
                                     user_id: int,
                                     current_query: str,
                                     db: AsyncSession,
                                     memory_types: List[str] = None) -> Dict[str, Any]:
        """Retrieve most relevant memories using semantic similarity"""
        try:
            if memory_types is None:
                memory_types = ["user_memory", "conversation_history", "user_files"]
            
            logger.info(f"Retrieving relevant memories for user {user_id}: {current_query[:100]}...")
            
            # Generate embedding for current query
            query_embedding = await self._generate_embedding(current_query)
            
            # Retrieve memories from different sources
            all_memories = []
            
            for memory_type in memory_types:
                if memory_type == "user_memory":
                    memories = await self._get_user_memory_memories(db, user_id)
                elif memory_type == "conversation_history":
                    memories = await self._get_conversation_memories(db, user_id)
                elif memory_type == "user_files":
                    memories = await self._get_file_memories(db, user_id)
                else:
                    continue
                
                all_memories.extend(memories)
            
            # Calculate similarity scores
            relevant_memories = await self._rank_memories_by_relevance(
                current_query, query_embedding, all_memories
            )
            
            # Format response
            memory_result = {
                "query": current_query,
                "retrieved_count": len(relevant_memories),
                "memories": relevant_memories,
                "query_embedding": query_embedding.tolist() if hasattr(query_embedding, 'tolist') else str(query_embedding),
                "retrieval_meta_data": {
                    "memory_types_searched": memory_types,
                    "similarity_threshold": self.similarity_threshold,
                    "total_memories_found": len(all_memories),
                    "relevant_memories": len(relevant_memories)
                }
            }
            
            logger.info(f"Retrieved {len(relevant_memories)} relevant memories out of {len(all_memories)} total")
            return memory_result
            
        except Exception as e:
            logger.error(f"Memory retrieval error: {e}")
            return {
                "query": current_query,
                "retrieved_count": 0,
                "memories": [],
                "error": str(e),
                "retrieval_meta_data": {"error": str(e)}
            }
    
    async def _get_user_memory_memories(self, db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
        """Get user profile memories"""
        try:
            result = await db.execute(
                text("SELECT memory_profile FROM users WHERE id = :user_id"),
                {"user_id": user_id}
            )
            
            memory_data = result.scalar() or {}
            if isinstance(memory_data, str):
                memory_data = json.loads(memory_data)
            
            memories = []
            for key, value in memory_data.items():
                if isinstance(value, (str, int, float, bool)):
                    memories.append({
                        "type": "user_profile",
                        "key": key,
                        "content": str(value),
                        "meta_data": {"profile_field": key},
                        "relevance_score": 0.0
                    })
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        memories.append({
                            "type": "user_profile",
                            "key": f"{key}.{sub_key}",
                            "content": str(sub_value),
                            "meta_data": {"profile_field": f"{key}.{sub_key}"},
                            "relevance_score": 0.0
                        })
            
            logger.debug(f"Retrieved {len(memories)} user profile memories")
            return memories
            
        except Exception as e:
            logger.error(f"User memory retrieval error: {e}")
            return []
    
    async def _get_conversation_memories(self, db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
        """Get conversation history memories"""
        try:
            # Get recent conversations
            result = await db.execute(
                text("""
                    SELECT c.id, c.title, c.summary, m.role, m.content, m.created_at
                    FROM conversations c
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    WHERE c.user_id = :user_id
                    ORDER BY c.updated_at DESC, m.created_at DESC
                    LIMIT 50
                """),
                {"user_id": user_id}
            )
            
            memories = []
            for row in result.fetchall():
                conversation_id, title, summary, role, content, created_at = row
                
                if role and content:
                    memories.append({
                        "type": "conversation_message",
                        "conversation_id": conversation_id,
                        "content": content,
                        "role": role,
                        "meta_data": {
                            "conversation_title": title,
                            "summary": summary,
                            "created_at": created_at.isoformat() if created_at else None
                        },
                        "relevance_score": 0.0
                    })
                elif summary:
                    memories.append({
                        "type": "conversation_summary",
                        "conversation_id": conversation_id,
                        "content": summary,
                        "meta_data": {
                            "conversation_title": title,
                            "summary_type": "conversation_summary"
                        },
                        "relevance_score": 0.0
                    })
            
            logger.debug(f"Retrieved {len(memories)} conversation memories")
            return memories
            
        except Exception as e:
            logger.error(f"Conversation memory retrieval error: {e}")
            return []
    
    async def _get_file_memories(self, db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
        """Get file-based memories (RAG content)"""
        try:
            # Get recent file chunks with embeddings
            result = await db.execute(
                text("""
                    SELECT fc.id, fc.file_id, fc.content, fc.file_meta_data, 
                           f.filename, f.original_filename, fc.embedding
                    FROM file_chunks fc
                    JOIN files f ON fc.file_id = f.id
                    WHERE f.user_id = :user_id 
                        AND f.processing_status = 'completed'
                        AND fc.embedding IS NOT NULL
                    ORDER BY fc.created_at DESC
                    LIMIT 100
                """),
                {"user_id": user_id}
            )
            
            memories = []
            for row in result.fetchall():
                chunk_id, file_id, content, meta_data, filename, original_filename, embedding = row
                
                memories.append({
                    "type": "file_chunk",
                    "chunk_id": chunk_id,
                    "content": content,
                    "meta_data": {
                        "file_id": file_id,
                        "filename": filename,
                        "original_filename": original_filename,
                        **(json.loads(meta_data) if meta_data else {}),
                    },
                    "embedding": embedding,
                    "relevance_score": 0.0
                })
            
            logger.debug(f"Retrieved {len(memories)} file memories")
            return memories
            
        except Exception as e:
            logger.error(f"File memory retrieval error: {e}")
            return []
    
    async def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text using available embedding service"""
        try:
            # Check cache first
            cache_key = f"emb_{hash(text)}"
            if cache_key in self.memory_cache:
                return self.memory_cache[cache_key]
            
            # Use OpenAI embeddings (in production, this would be configurable)
            # For now, return a placeholder embedding
            # In real implementation, you would call OpenAI API or similar service
            
            # Placeholder: generate random embedding (for demonstration)
            embedding = np.random.rand(self.embedding_dim).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize
            
            # Cache the result
            self.memory_cache[cache_key] = embedding
            
            # Limit cache size
            if len(self.memory_cache) > 1000:
                # Remove oldest entries
                keys_to_remove = list(self.memory_cache.keys())[:100]
                for key in keys_to_remove:
                    del self.memory_cache[key]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            # Return zero embedding as fallback
            return np.zeros(self.embedding_dim, dtype=np.float32)
    
    async def _rank_memories_by_relevance(self, 
                                        query: str,
                                        query_embedding: np.ndarray,
                                        memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank memories by semantic relevance to query"""
        try:
            if not memories:
                return []
            
            # Generate embeddings for memory content
            memory_embeddings = []
            valid_memories = []
            
            for memory in memories:
                try:
                    if "embedding" in memory and memory["embedding"]:
                        # Parse existing embedding from database
                        if isinstance(memory["embedding"], str):
                            # Parse vector string format "[1.0, 2.0, ...]"
                            embedding_str = memory["embedding"].strip("[]")
                            embedding_vals = [float(x.strip()) for x in embedding_str.split(",")]
                            embedding = np.array(embedding_vals, dtype=np.float32)
                        else:
                            embedding = np.array(memory["embedding"], dtype=np.float32)
                    else:
                        # Generate embedding for content
                        content = memory.get("content", "")
                        embedding = await self._generate_embedding(content)
                    
                    memory_embeddings.append(embedding)
                    valid_memories.append(memory)
                    
                except Exception as e:
                    logger.warning(f"Failed to process memory {memory.get('chunk_id', 'unknown')}: {e}")
                    continue
            
            if not valid_memories:
                return []
            
            # Calculate similarities
            similarities = cosine_similarity([query_embedding], memory_embeddings)[0]
            
            # Add similarity scores to memories
            for i, memory in enumerate(valid_memories):
                memory["relevance_score"] = float(similarities[i])
                memory["content_length"] = len(memory.get("content", ""))
                memory["content_preview"] = memory.get("content", "")[:200] + "..." if len(memory.get("content", "")) > 200 else memory.get("content", "")
            
            # Filter by threshold and sort by relevance
            relevant_memories = [
                memory for memory in valid_memories 
                if memory["relevance_score"] >= self.similarity_threshold
            ]
            
            # Sort by relevance score (descending)
            relevant_memories.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Limit to maximum number
            return relevant_memories[:self.max_memory_items]
            
        except Exception as e:
            logger.error(f"Memory ranking error: {e}")
            return []
    
    async def enhance_plan_with_memory(self, 
                                     user_id: int,
                                     user_query: str,
                                     plan: Dict[str, Any],
                                     db: AsyncSession) -> Dict[str, Any]:
        """Enhance plan with relevant context from memory"""
        try:
            logger.info(f"Enhancing plan with memory for user {user_id}")
            
            # Retrieve relevant memories
            memory_result = await self.retrieve_relevant_memory(
                user_id=user_id,
                current_query=user_query,
                db=db
            )
            
            # Extract relevant context
            relevant_memories = memory_result.get("memories", [])
            
            if not relevant_memories:
                logger.info("No relevant memories found for plan enhancement")
                return plan
            
            # Create context for plan enhancement
            context_parts = []
            
            for memory in relevant_memories[:5]:  # Use top 5 memories
                memory_type = memory.get("type", "unknown")
                content = memory.get("content", "")
                score = memory.get("relevance_score", 0)
                
                context_parts.append(f"[{memory_type}] {content}")
            
            if context_parts:
                # Add memory context to plan description
                enhanced_plan = plan.copy()
                original_description = enhanced_plan.get("plan", {}).get("description", "")
                
                memory_context = f"\nRelevant context from user history:\n" + "\n".join(context_parts)
                enhanced_description = original_description + memory_context
                
                enhanced_plan["plan"]["description"] = enhanced_description
                enhanced_plan["memory_enhancement"] = {
                    "memories_used": len(relevant_memories),
                    "average_relevance": np.mean([m["relevance_score"] for m in relevant_memories]),
                    "memory_context_added": True
                }
                
                logger.info(f"Enhanced plan with {len(relevant_memories)} relevant memories")
                return enhanced_plan
            
            return plan
            
        except Exception as e:
            logger.error(f"Plan enhancement error: {e}")
            return plan
    
    async def analyze_memory_patterns(self, 
                                    user_id: int,
                                    db: AsyncSession,
                                    days_back: int = 30) -> Dict[str, Any]:
        """Analyze memory usage patterns for a user"""
        try:
            logger.info(f"Analyzing memory patterns for user {user_id}")
            
            # Get memory usage statistics
            stats = await self._get_memory_statistics(db, user_id, days_back)
            
            # Analyze query patterns
            query_patterns = await self._analyze_query_patterns(db, user_id, days_back)
            
            # Generate insights
            insights = await self._generate_memory_insights(stats, query_patterns)
            
            return {
                "user_id": user_id,
                "analysis_period_days": days_back,
                "statistics": stats,
                "query_patterns": query_patterns,
                "insights": insights,
                "recommendations": await self._generate_memory_recommendations(stats, insights)
            }
            
        except Exception as e:
            logger.error(f"Memory pattern analysis error: {e}")
            return {"error": str(e)}
    
    async def _get_memory_statistics(self, db: AsyncSession, user_id: int, days_back: int) -> Dict[str, Any]:
        """Get basic memory usage statistics"""
        try:
            result = await db.execute(
                text("""
                    SELECT 
                        COUNT(DISTINCT c.id) as total_conversations,
                        COUNT(m.id) as total_messages,
                        COUNT(f.id) as total_files,
                        COUNT(fc.id) as total_file_chunks,
                        AVG(LENGTH(m.content)) as avg_message_length
                    FROM users u
                    LEFT JOIN conversations c ON u.id = c.user_id
                    LEFT JOIN messages m ON c.id = m.conversation_id
                    LEFT JOIN files f ON u.id = f.user_id
                    LEFT JOIN file_chunks fc ON f.id = fc.file_id
                    WHERE u.id = :user_id
                        AND (c.created_at >= CURRENT_DATE - INTERVAL ':days days' OR c.created_at IS NULL)
                """),
                {"user_id": user_id, "days": days_back}
            )
            
            row = result.fetchone()
            if row:
                return {
                    "total_conversations": row[0] or 0,
                    "total_messages": row[1] or 0,
                    "total_files": row[2] or 0,
                    "total_file_chunks": row[3] or 0,
                    "avg_message_length": float(row[4] or 0)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Memory statistics error: {e}")
            return {}
    
    async def _analyze_query_patterns(self, db: AsyncSession, user_id: int, days_back: int) -> Dict[str, Any]:
        """Analyze user query patterns"""
        try:
            result = await db.execute(
                text("""
                    SELECT 
                        m.content,
                        m.created_at
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = :user_id 
                        AND m.role = 'user'
                        AND m.created_at >= CURRENT_DATE - INTERVAL ':days days'
                    ORDER BY m.created_at DESC
                    LIMIT 100
                """),
                {"user_id": user_id, "days": days_back}
            )
            
            queries = []
            for row in result.fetchall():
                content, created_at = row
                queries.append({
                    "content": content,
                    "created_at": created_at.isoformat() if created_at else None
                })
            
            # Analyze query characteristics
            query_lengths = [len(q["content"]) for q in queries]
            avg_length = np.mean(query_lengths) if query_lengths else 0
            
            return {
                "total_queries": len(queries),
                "avg_query_length": avg_length,
                "query_distribution": {
                    "short_queries": len([q for q in queries if len(q["content"]) < 50]),
                    "medium_queries": len([q for q in queries if 50 <= len(q["content"]) < 200]),
                    "long_queries": len([q for q in queries if len(q["content"]) >= 200])
                },
                "sample_queries": queries[:10]  # Sample for analysis
            }
            
        except Exception as e:
            logger.error(f"Query pattern analysis error: {e}")
            return {}
    
    async def _generate_memory_insights(self, stats: Dict[str, Any], patterns: Dict[str, Any]) -> List[str]:
        """Generate insights from memory analysis"""
        insights = []
        
        # Activity level insights
        total_messages = stats.get("total_messages", 0)
        if total_messages > 100:
            insights.append(f"User is highly active with {total_messages} messages")
        elif total_messages > 20:
            insights.append(f"User has moderate activity with {total_messages} messages")
        else:
            insights.append(f"User is new with {total_messages} messages")
        
        # File usage insights
        total_files = stats.get("total_files", 0)
        if total_files > 10:
            insights.append(f"User frequently uploads files ({total_files} files)")
        elif total_files > 0:
            insights.append(f"User uploads some files ({total_files} files)")
        
        # Query pattern insights
        avg_length = patterns.get("avg_query_length", 0)
        if avg_length > 150:
            insights.append("User asks detailed, comprehensive questions")
        elif avg_length > 50:
            insights.append("User asks moderately detailed questions")
        else:
            insights.append("User prefers concise questions")
        
        return insights
    
    async def _generate_memory_recommendations(self, stats: Dict[str, Any], insights: List[str]) -> List[str]:
        """Generate memory usage recommendations"""
        recommendations = []
        
        # Based on usage patterns
        total_files = stats.get("total_files", 0)
        if total_files == 0:
            recommendations.append("Consider uploading documents for better context-aware responses")
        
        total_messages = stats.get("total_messages", 0)
        if total_messages > 50:
            recommendations.append("Memory system is well-utilized - continue current usage pattern")
        
        return recommendations


# Global dynamic memory instance
dynamic_memory = DynamicMemory()