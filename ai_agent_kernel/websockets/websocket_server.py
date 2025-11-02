"""
WebSocket server for real-time communication
"""

import json
import asyncio
from typing import Dict, List, Set, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import get_db
from services.auth_service import AuthService
from models.models import User, ActiveSession
from utils.security import JWTManager
from config.logger import logger
from config.settings import settings


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # User ID -> Set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # WebSocket -> User info
        self.connection_users: Dict[WebSocket, dict] = {}
        # Room/Channel connections
        self.rooms: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int, session_id: int):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Add to user connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        
        # Store user info for this connection
        self.connection_users[websocket] = {
            "user_id": user_id,
            "session_id": session_id,
            "connected_at": datetime.now(timezone.utc)
        }
        
        logger.info(f"WebSocket connected: User {user_id}, Session {session_id}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        user_info = self.connection_users.get(websocket)
        if user_info:
            user_id = user_info["user_id"]
            
            # Remove from user connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove from all rooms
            for room_connections in self.rooms.values():
                room_connections.discard(websocket)
            
            # Remove user info
            del self.connection_users[websocket]
            
            logger.info(f"WebSocket disconnected: User {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Send message to all connections of a specific user"""
        if user_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected:
                self.disconnect(websocket)
    
    async def send_message_to_connection(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send message to websocket: {e}")
            self.disconnect(websocket)
    
    async def join_room(self, websocket: WebSocket, room_id: str):
        """Add connection to a room"""
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)
        
        user_info = self.connection_users.get(websocket)
        if user_info:
            logger.info(f"User {user_info['user_id']} joined room {room_id}")
    
    async def leave_room(self, websocket: WebSocket, room_id: str):
        """Remove connection from a room"""
        if room_id in self.rooms:
            self.rooms[room_id].discard(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
        
        user_info = self.connection_users.get(websocket)
        if user_info:
            logger.info(f"User {user_info['user_id']} left room {room_id}")
    
    async def broadcast_to_room(self, message: dict, room_id: str):
        """Broadcast message to all connections in a room"""
        if room_id in self.rooms:
            disconnected = set()
            for websocket in self.rooms[room_id]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to broadcast to room {room_id}: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            for websocket in disconnected:
                self.disconnect(websocket)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_online_users(self) -> List[int]:
        """Get list of online user IDs"""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()


class WebSocketAuth:
    """WebSocket authentication helper"""
    
    @staticmethod
    async def authenticate_websocket(
        token: str,
        db: AsyncSession
    ) -> tuple[User, ActiveSession]:
        """Authenticate WebSocket connection using token"""
        try:
            auth_service = AuthService(db)
            user, session = await auth_service.verify_session(token)
            return user, session
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )


class WebSocketHandler:
    """WebSocket message handler"""
    
    def __init__(self, websocket: WebSocket, user: User, session: ActiveSession, db: AsyncSession):
        self.websocket = websocket
        self.user = user
        self.session = session
        self.db = db
    
    async def handle_message(self, message: dict):
        """Handle incoming WebSocket message"""
        try:
            message_type = message.get("type")
            
            if message_type == "ping":
                await self.handle_ping()
            elif message_type == "join_room":
                await self.handle_join_room(message.get("room_id"))
            elif message_type == "leave_room":
                await self.handle_leave_room(message.get("room_id"))
            elif message_type == "chat_message":
                await self.handle_chat_message(message)
            elif message_type == "typing":
                await self.handle_typing(message)
            elif message_type == "agent_invoke":
                await self.handle_agent_invoke(message)
            else:
                await self.send_error("Unknown message type")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self.send_error("Message handling failed")
    
    async def handle_ping(self):
        """Handle ping message"""
        await manager.send_message_to_connection({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, self.websocket)
    
    async def handle_join_room(self, room_id: str):
        """Handle join room request"""
        if not room_id:
            await self.send_error("Room ID required")
            return
        
        await manager.join_room(self.websocket, room_id)
        await manager.send_message_to_connection({
            "type": "room_joined",
            "room_id": room_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, self.websocket)
    
    async def handle_leave_room(self, room_id: str):
        """Handle leave room request"""
        if not room_id:
            await self.send_error("Room ID required")
            return
        
        await manager.leave_room(self.websocket, room_id)
        await manager.send_message_to_connection({
            "type": "room_left",
            "room_id": room_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, self.websocket)
    
    async def handle_chat_message(self, message: dict):
        """Handle chat message"""
        room_id = message.get("room_id")
        content = message.get("content")
        
        if not room_id or not content:
            await self.send_error("Room ID and content required")
            return
        
        # Broadcast message to room
        await manager.broadcast_to_room({
            "type": "chat_message",
            "room_id": room_id,
            "user_id": self.user.id,
            "username": self.user.username,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, room_id)
    
    async def handle_typing(self, message: dict):
        """Handle typing indicator"""
        room_id = message.get("room_id")
        is_typing = message.get("is_typing", False)
        
        if not room_id:
            await self.send_error("Room ID required")
            return
        
        # Broadcast typing status to room (except sender)
        typing_message = {
            "type": "typing",
            "room_id": room_id,
            "user_id": self.user.id,
            "username": self.user.username,
            "is_typing": is_typing,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to all connections in room except the sender
        if room_id in manager.rooms:
            for websocket in manager.rooms[room_id]:
                if websocket != self.websocket:
                    await manager.send_message_to_connection(typing_message, websocket)
    
    async def handle_agent_invoke(self, message: dict):
        """Handle agent invocation request"""
        # This would integrate with your existing agent system
        # For now, just send an acknowledgment
        await manager.send_message_to_connection({
            "type": "agent_response",
            "status": "processing",
            "message": "Agent request received and processing",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, self.websocket)
    
    async def send_error(self, error_message: str):
        """Send error message"""
        await manager.send_message_to_connection({
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, self.websocket)


async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token"),
    db: AsyncSession = Depends(get_db)
):
    """
    WebSocket endpoint for real-time communication
    
    Query Parameters:
    - token: JWT access token for authentication
    
    Supported message types:
    - ping: Keep-alive ping
    - join_room: Join a chat room
    - leave_room: Leave a chat room  
    - chat_message: Send chat message
    - typing: Typing indicator
    - agent_invoke: Invoke AI agent
    """
    try:
        # Authenticate WebSocket connection
        user, session = await WebSocketAuth.authenticate_websocket(token, db)
        
        # Connect to manager
        await manager.connect(websocket, user.id, session.id)
        
        # Send welcome message
        await manager.send_message_to_connection({
            "type": "connected",
            "user_id": user.id,
            "username": user.username,
            "session_id": session.id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, websocket)
        
        # Create message handler
        handler = WebSocketHandler(websocket, user, session, db)
        
        # Message loop
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle message
                await handler.handle_message(message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await handler.send_error("Invalid JSON format")
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                await handler.send_error("Message processing failed")
                
    except HTTPException as e:
        # Authentication failed
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Connection failed")
    finally:
        # Cleanup
        manager.disconnect(websocket)


async def send_notification_to_user(user_id: int, notification: dict):
    """
    Send notification to all connections of a specific user
    
    This function can be called from other parts of the application
    to send real-time notifications to users.
    """
    notification_message = {
        "type": "notification",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **notification
    }
    
    await manager.send_personal_message(notification_message, user_id)


async def broadcast_system_message(message: str, level: str = "info"):
    """
    Broadcast system message to all connected users
    """
    system_message = {
        "type": "system_message",
        "level": level,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Send to all users
    for user_id in manager.get_online_users():
        await manager.send_personal_message(system_message, user_id)


def get_websocket_stats() -> dict:
    """Get WebSocket connection statistics"""
    return {
        "total_connections": manager.get_total_connections(),
        "online_users": len(manager.get_online_users()),
        "active_rooms": len(manager.rooms),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }