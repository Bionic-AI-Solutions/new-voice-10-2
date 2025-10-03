"""
WebSocket connection manager for real-time communication.
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time communication."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
        self.connection_users: Dict[str, str] = {}  # connection_id -> user_id
    
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Connect a WebSocket and return connection ID."""
        connection_id = f"{user_id}_{asyncio.get_event_loop().time()}"
        
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        self.connection_users[connection_id] = user_id
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
        return connection_id
    
    async def disconnect(self, user_id: str, connection_id: Optional[str] = None):
        """Disconnect WebSocket(s) for a user."""
        if connection_id:
            # Disconnect specific connection
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                if connection_id in self.connection_users:
                    del self.connection_users[connection_id]
                logger.info(f"WebSocket disconnected: {connection_id}")
        else:
            # Disconnect all connections for user
            if user_id in self.user_connections:
                for conn_id in list(self.user_connections[user_id]):
                    if conn_id in self.active_connections:
                        del self.active_connections[conn_id]
                    if conn_id in self.connection_users:
                        del self.connection_users[conn_id]
                del self.user_connections[user_id]
                logger.info(f"All WebSockets disconnected for user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to all connections of a specific user."""
        if user_id in self.user_connections:
            for connection_id in list(self.user_connections[user_id]):
                await self.send_message_to_connection(message, connection_id)
    
    async def send_message_to_connection(self, message: dict, connection_id: str):
        """Send message to a specific connection."""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                # Remove failed connection
                await self._remove_connection(connection_id)
    
    async def broadcast_message(self, message: dict):
        """Broadcast message to all active connections."""
        for connection_id in list(self.active_connections.keys()):
            await self.send_message_to_connection(message, connection_id)
    
    async def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.active_connections)
    
    async def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a specific user."""
        return len(self.user_connections.get(user_id, set()))
    
    async def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs."""
        return list(self.user_connections.keys())
    
    async def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has any active connections."""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    async def _remove_connection(self, connection_id: str):
        """Remove a connection from all tracking structures."""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.connection_users:
            user_id = self.connection_users[connection_id]
            del self.connection_users[connection_id]
            
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        logger.info(f"Removed connection: {connection_id}")
