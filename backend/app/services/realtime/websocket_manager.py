"""
WebSocket 연결 관리자
실시간 대시보드 데이터 푸시 관리
"""
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import json
import asyncio
from collections import defaultdict

from app.core.logging import logger
from app.services.cache_service import CacheService


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # 활성 연결: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = defaultdict(dict)
        # 구독 정보: {channel: {user_id: Set[connection_id]}}
        self.subscriptions: Dict[str, Dict[int, Set[str]]] = defaultdict(lambda: defaultdict(set))
        # 연결별 정보: {connection_id: {"user_id": int, "channels": Set[str]}}
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        self.cache = CacheService()
        
    async def connect(
        self,
        websocket: WebSocket,
        user_id: int,
        connection_id: str
    ) -> None:
        """WebSocket 연결 수락"""
        try:
            await websocket.accept()
            
            # 연결 저장
            self.active_connections[user_id][connection_id] = websocket
            self.connection_info[connection_id] = {
                "user_id": user_id,
                "channels": set(),
                "connected_at": datetime.now()
            }
            
            # 환영 메시지 전송
            await self.send_personal_message(
                {
                    "type": "connection",
                    "status": "connected",
                    "connection_id": connection_id,
                    "timestamp": datetime.now().isoformat()
                },
                websocket
            )
            
            logger.info(f"WebSocket 연결 성공: user_id={user_id}, connection_id={connection_id}")
            
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {str(e)}")
            raise
            
    async def disconnect(self, connection_id: str) -> None:
        """WebSocket 연결 해제"""
        try:
            if connection_id not in self.connection_info:
                return
                
            info = self.connection_info[connection_id]
            user_id = info["user_id"]
            
            # 연결 제거
            if user_id in self.active_connections:
                self.active_connections[user_id].pop(connection_id, None)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    
            # 구독 정보 제거
            for channel in info["channels"]:
                if channel in self.subscriptions and user_id in self.subscriptions[channel]:
                    self.subscriptions[channel][user_id].discard(connection_id)
                    if not self.subscriptions[channel][user_id]:
                        del self.subscriptions[channel][user_id]
                        
            # 연결 정보 제거
            del self.connection_info[connection_id]
            
            logger.info(f"WebSocket 연결 해제: connection_id={connection_id}")
            
        except Exception as e:
            logger.error(f"WebSocket 연결 해제 실패: {str(e)}")
            
    async def subscribe(
        self,
        connection_id: str,
        channels: List[str]
    ) -> None:
        """채널 구독"""
        try:
            if connection_id not in self.connection_info:
                return
                
            info = self.connection_info[connection_id]
            user_id = info["user_id"]
            
            for channel in channels:
                self.subscriptions[channel][user_id].add(connection_id)
                info["channels"].add(channel)
                
            # 구독 확인 메시지
            websocket = self.active_connections.get(user_id, {}).get(connection_id)
            if websocket:
                await self.send_personal_message(
                    {
                        "type": "subscription",
                        "status": "subscribed",
                        "channels": channels,
                        "timestamp": datetime.now().isoformat()
                    },
                    websocket
                )
                
            logger.info(f"채널 구독: connection_id={connection_id}, channels={channels}")
            
        except Exception as e:
            logger.error(f"채널 구독 실패: {str(e)}")
            
    async def unsubscribe(
        self,
        connection_id: str,
        channels: List[str]
    ) -> None:
        """채널 구독 해제"""
        try:
            if connection_id not in self.connection_info:
                return
                
            info = self.connection_info[connection_id]
            user_id = info["user_id"]
            
            for channel in channels:
                if channel in self.subscriptions and user_id in self.subscriptions[channel]:
                    self.subscriptions[channel][user_id].discard(connection_id)
                    if not self.subscriptions[channel][user_id]:
                        del self.subscriptions[channel][user_id]
                info["channels"].discard(channel)
                
            # 구독 해제 확인 메시지
            websocket = self.active_connections.get(user_id, {}).get(connection_id)
            if websocket:
                await self.send_personal_message(
                    {
                        "type": "subscription",
                        "status": "unsubscribed",
                        "channels": channels,
                        "timestamp": datetime.now().isoformat()
                    },
                    websocket
                )
                
            logger.info(f"채널 구독 해제: connection_id={connection_id}, channels={channels}")
            
        except Exception as e:
            logger.error(f"채널 구독 해제 실패: {str(e)}")
            
    async def send_personal_message(
        self,
        message: Dict[str, Any],
        websocket: WebSocket
    ) -> None:
        """개인 메시지 전송"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"메시지 전송 실패: {str(e)}")
            
    async def send_user_message(
        self,
        message: Dict[str, Any],
        user_id: int
    ) -> None:
        """특정 사용자의 모든 연결에 메시지 전송"""
        try:
            if user_id in self.active_connections:
                disconnected = []
                
                for connection_id, websocket in self.active_connections[user_id].items():
                    try:
                        await websocket.send_json(message)
                    except Exception:
                        disconnected.append(connection_id)
                        
                # 실패한 연결 제거
                for connection_id in disconnected:
                    await self.disconnect(connection_id)
                    
        except Exception as e:
            logger.error(f"사용자 메시지 전송 실패: {str(e)}")
            
    async def broadcast_to_channel(
        self,
        channel: str,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None
    ) -> None:
        """채널 구독자에게 브로드캐스트"""
        try:
            if channel not in self.subscriptions:
                return
                
            message["channel"] = channel
            message["timestamp"] = datetime.now().isoformat()
            
            for user_id, connection_ids in self.subscriptions[channel].items():
                if user_id not in self.active_connections:
                    continue
                    
                disconnected = []
                
                for connection_id in connection_ids:
                    if connection_id == exclude_connection:
                        continue
                        
                    websocket = self.active_connections[user_id].get(connection_id)
                    if websocket:
                        try:
                            await websocket.send_json(message)
                        except Exception:
                            disconnected.append(connection_id)
                            
                # 실패한 연결 제거
                for connection_id in disconnected:
                    await self.disconnect(connection_id)
                    
        except Exception as e:
            logger.error(f"채널 브로드캐스트 실패: {str(e)}")
            
    async def handle_message(
        self,
        websocket: WebSocket,
        connection_id: str
    ) -> None:
        """WebSocket 메시지 처리"""
        try:
            while True:
                data = await websocket.receive_json()
                
                message_type = data.get("type")
                
                if message_type == "ping":
                    # 핑 응답
                    await self.send_personal_message(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket
                    )
                    
                elif message_type == "subscribe":
                    # 채널 구독
                    channels = data.get("channels", [])
                    await self.subscribe(connection_id, channels)
                    
                elif message_type == "unsubscribe":
                    # 채널 구독 해제
                    channels = data.get("channels", [])
                    await self.unsubscribe(connection_id, channels)
                    
                elif message_type == "refresh":
                    # 데이터 새로고침 요청
                    channels = data.get("channels", [])
                    await self._handle_refresh_request(connection_id, channels)
                    
                else:
                    # 알 수 없는 메시지 타입
                    await self.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )
                    
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"메시지 처리 실패: {str(e)}")
            await self.disconnect(connection_id)
            
    async def _handle_refresh_request(
        self,
        connection_id: str,
        channels: List[str]
    ) -> None:
        """새로고침 요청 처리"""
        try:
            if connection_id not in self.connection_info:
                return
                
            info = self.connection_info[connection_id]
            user_id = info["user_id"]
            websocket = self.active_connections.get(user_id, {}).get(connection_id)
            
            if not websocket:
                return
                
            # 요청된 채널의 최신 데이터 전송
            for channel in channels:
                if channel not in info["channels"]:
                    continue
                    
                # 캐시에서 최신 데이터 조회
                cache_key = f"realtime:{channel}:{user_id}"
                cached_data = await self.cache.get(cache_key)
                
                if cached_data:
                    await self.send_personal_message(
                        {
                            "type": "data",
                            "channel": channel,
                            "data": cached_data,
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )
                    
        except Exception as e:
            logger.error(f"새로고침 요청 처리 실패: {str(e)}")
            
    def get_connection_count(self, user_id: Optional[int] = None) -> int:
        """연결 수 조회"""
        if user_id is not None:
            return len(self.active_connections.get(user_id, {}))
        return sum(len(connections) for connections in self.active_connections.values())
        
    def get_channel_subscribers(self, channel: str) -> int:
        """채널 구독자 수 조회"""
        if channel not in self.subscriptions:
            return 0
        return sum(len(connections) for connections in self.subscriptions[channel].values())
        
    async def broadcast_dashboard_update(
        self,
        user_id: int,
        update_type: str,
        data: Dict[str, Any]
    ) -> None:
        """대시보드 업데이트 브로드캐스트"""
        try:
            message = {
                "type": "dashboard_update",
                "update_type": update_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            # 사용자의 대시보드 채널로 전송
            channel = f"dashboard:{user_id}"
            await self.broadcast_to_channel(channel, message)
            
            # 캐시 업데이트
            cache_key = f"realtime:dashboard:{user_id}"
            await self.cache.set(cache_key, data, ttl=60)
            
        except Exception as e:
            logger.error(f"대시보드 업데이트 브로드캐스트 실패: {str(e)}")
            
    async def send_notification(
        self,
        user_id: int,
        notification: Dict[str, Any]
    ) -> None:
        """실시간 알림 전송"""
        try:
            message = {
                "type": "notification",
                "notification": notification,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.send_user_message(message, user_id)
            
        except Exception as e:
            logger.error(f"알림 전송 실패: {str(e)}")


# 전역 연결 관리자 인스턴스
connection_manager = ConnectionManager()