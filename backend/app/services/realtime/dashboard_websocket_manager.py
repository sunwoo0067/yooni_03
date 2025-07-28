"""
Dashboard-specific WebSocket Manager
Handles real-time dashboard updates
"""
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket
import asyncio
import json
from datetime import datetime

from app.services.realtime.websocket_manager import connection_manager
from app.core.logging import logger

class DashboardWebSocketManager:
    def __init__(self):
        self.manager = connection_manager
        self.update_tasks: Dict[str, asyncio.Task] = {}
        
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect dashboard client"""
        connection_id = f"dashboard_{user_id}_{datetime.utcnow().timestamp()}"
        await self.manager.connect(websocket, user_id, connection_id)
        
        # Subscribe to dashboard channels
        await self.manager.subscribe(connection_id, [
            f"dashboard:{user_id}",
            f"alerts:{user_id}",
            f"metrics:{user_id}"
        ])
        
        # Start periodic updates for this connection
        self.update_tasks[connection_id] = asyncio.create_task(
            self._periodic_updates(connection_id, user_id)
        )
        
        return connection_id
        
    async def disconnect(self, connection_id: str):
        """Disconnect dashboard client"""
        # Cancel update task
        if connection_id in self.update_tasks:
            self.update_tasks[connection_id].cancel()
            del self.update_tasks[connection_id]
            
        await self.manager.disconnect(connection_id)
        
    async def send_dashboard_update(self, user_id: int, data: Dict[str, Any]):
        """Send dashboard update to user"""
        await self.manager.broadcast_dashboard_update(user_id, "metrics", data)
        
    async def send_alert(self, user_id: int, alert: Dict[str, Any]):
        """Send alert to user"""
        await self.manager.send_notification(user_id, {
            "type": "alert",
            "alert": alert
        })
        
    async def broadcast_system_status(self, status: Dict[str, Any]):
        """Broadcast system status to all dashboard users"""
        # This would broadcast to all dashboard channels
        for user_id in self._get_active_dashboard_users():
            await self.send_dashboard_update(user_id, {
                "type": "system_status",
                "data": status
            })
            
    async def _periodic_updates(self, connection_id: str, user_id: int):
        """Send periodic updates to dashboard"""
        try:
            while connection_id in self.manager.connection_info:
                # Send heartbeat
                await self.manager.send_personal_message(
                    {"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()},
                    self.manager.active_connections.get(user_id, {}).get(connection_id)
                )
                
                await asyncio.sleep(30)  # Every 30 seconds
                
        except asyncio.CancelledError:
            logger.info(f"Periodic updates cancelled for {connection_id}")
        except Exception as e:
            logger.error(f"Error in periodic updates: {str(e)}")
            
    def _get_active_dashboard_users(self) -> List[int]:
        """Get list of users with active dashboard connections"""
        users = []
        for user_id, connections in self.manager.active_connections.items():
            for connection_id in connections:
                if connection_id.startswith("dashboard_"):
                    users.append(user_id)
                    break
        return users
        
    async def subscribe_to_metrics(self, connection_id: str, metrics: List[str]):
        """Subscribe to specific metrics"""
        channels = [f"metric:{m}" for m in metrics]
        await self.manager.subscribe(connection_id, channels)
        
    async def unsubscribe_from_metrics(self, connection_id: str, metrics: List[str]):
        """Unsubscribe from specific metrics"""
        channels = [f"metric:{m}" for m in metrics]
        await self.manager.unsubscribe(connection_id, channels)

# Global instance
dashboard_ws_manager = DashboardWebSocketManager()