"""
WebSocket 연결 관리자
실시간 대시보드 데이터 푸시 관리
강화된 기능: 하트비트, 메시지 큐잉, 연결 상태 모니터링
"""
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta
import json
import asyncio
from collections import defaultdict, deque
from enum import Enum

from app.core.logging import logger
from app.services.cache_service import CacheService


class ConnectionState(Enum):
    """연결 상태"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    SUSPENDED = "suspended"


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # 활성 연결: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = defaultdict(dict)
        # 구독 정보: {channel: {user_id: Set[connection_id]}}
        self.subscriptions: Dict[str, Dict[int, Set[str]]] = defaultdict(lambda: defaultdict(set))
        # 연결별 정보: {connection_id: {"user_id": int, "channels": Set[str], ...}}
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        # 메시지 큐: {user_id: deque[message]}
        self.message_queues: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        # 하트비트 태스크: {connection_id: asyncio.Task}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        # 연결 상태: {connection_id: ConnectionState}
        self.connection_states: Dict[str, ConnectionState] = {}
        self.cache = CacheService()
        self.heartbeat_interval = 30  # 30초
        self.heartbeat_timeout = 60  # 60초
        
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
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "last_activity": datetime.now()
            }
            self.connection_states[connection_id] = ConnectionState.CONNECTED
            
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
            
            # 큐에 있던 메시지 전송
            await self._send_queued_messages(user_id, websocket)
            
            # 하트비트 시작
            self.heartbeat_tasks[connection_id] = asyncio.create_task(
                self._heartbeat_loop(connection_id, websocket)
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
            
            # 하트비트 태스크 취소
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]
                
            # 연결 상태 업데이트
            self.connection_states[connection_id] = ConnectionState.DISCONNECTED
            
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
                    # 하트비트 시간 업데이트
                    if connection_id in self.connection_info:
                        self.connection_info[connection_id]["last_heartbeat"] = datetime.now()
                    
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
            
    async def _heartbeat_loop(
        self,
        connection_id: str,
        websocket: WebSocket
    ) -> None:
        """하트비트 루프"""
        try:
            while connection_id in self.connection_info:
                await asyncio.sleep(self.heartbeat_interval)
                
                # 하트비트 전송
                try:
                    await self.send_personal_message(
                        {
                            "type": "heartbeat",
                            "timestamp": datetime.now().isoformat()
                        },
                        websocket
                    )
                    
                    # 타임아웃 체크
                    if connection_id in self.connection_info:
                        last_heartbeat = self.connection_info[connection_id]["last_heartbeat"]
                        if datetime.now() - last_heartbeat > timedelta(seconds=self.heartbeat_timeout):
                            logger.warning(f"하트비트 타임아웃: connection_id={connection_id}")
                            await self.disconnect(connection_id)
                            break
                            
                except Exception as e:
                    logger.error(f"하트비트 전송 실패: {str(e)}")
                    await self.disconnect(connection_id)
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"하트비트 루프 취소: connection_id={connection_id}")
        except Exception as e:
            logger.error(f"하트비트 루프 오류: {str(e)}")
            
    async def _send_queued_messages(
        self,
        user_id: int,
        websocket: WebSocket
    ) -> None:
        """큐에 있는 메시지 전송"""
        try:
            if user_id not in self.message_queues:
                return
                
            queue = self.message_queues[user_id]
            while queue:
                message = queue.popleft()
                try:
                    await websocket.send_json(message)
                    await asyncio.sleep(0.1)  # 짧은 딜레이로 메시지 플러딩 방지
                except Exception as e:
                    # 전송 실패한 메시지는 다시 큐에 추가
                    queue.appendleft(message)
                    logger.error(f"큐 메시지 전송 실패: {str(e)}")
                    break
                    
        except Exception as e:
            logger.error(f"큐 메시지 처리 실패: {str(e)}")
            
    async def queue_message(
        self,
        user_id: int,
        message: Dict[str, Any]
    ) -> None:
        """메시지를 큐에 추가"""
        try:
            self.message_queues[user_id].append(message)
            logger.debug(f"메시지 큐에 추가: user_id={user_id}")
        except Exception as e:
            logger.error(f"메시지 큐 추가 실패: {str(e)}")
            
    async def send_user_message_with_queue(
        self,
        message: Dict[str, Any],
        user_id: int
    ) -> None:
        """특정 사용자에게 메시지 전송 (연결이 없으면 큐에 저장)"""
        try:
            if user_id in self.active_connections and self.active_connections[user_id]:
                # 활성 연결이 있으면 직접 전송
                await self.send_user_message(message, user_id)
            else:
                # 연결이 없으면 큐에 저장
                await self.queue_message(user_id, message)
                logger.info(f"사용자 오프라인, 메시지 큐에 저장: user_id={user_id}")
                
        except Exception as e:
            logger.error(f"메시지 전송/큐잉 실패: {str(e)}")
            
    async def get_connection_status(
        self,
        connection_id: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """연결 상태 조회"""
        try:
            if connection_id:
                if connection_id not in self.connection_info:
                    return {"status": "not_found"}
                    
                info = self.connection_info[connection_id]
                state = self.connection_states.get(connection_id, ConnectionState.DISCONNECTED)
                
                return {
                    "connection_id": connection_id,
                    "user_id": info["user_id"],
                    "state": state.value,
                    "connected_at": info["connected_at"].isoformat(),
                    "last_heartbeat": info["last_heartbeat"].isoformat(),
                    "last_activity": info["last_activity"].isoformat(),
                    "channels": list(info["channels"]),
                    "uptime": (datetime.now() - info["connected_at"]).total_seconds()
                }
                
            elif user_id:
                connections = []
                for conn_id, websocket in self.active_connections.get(user_id, {}).items():
                    connections.append(await self.get_connection_status(connection_id=conn_id))
                    
                return {
                    "user_id": user_id,
                    "total_connections": len(connections),
                    "connections": connections,
                    "queued_messages": len(self.message_queues.get(user_id, []))
                }
                
            else:
                # 전체 상태
                total_connections = sum(len(conns) for conns in self.active_connections.values())
                total_users = len(self.active_connections)
                total_channels = len(self.subscriptions)
                
                return {
                    "total_connections": total_connections,
                    "total_users": total_users,
                    "total_channels": total_channels,
                    "connections_by_state": self._count_connections_by_state()
                }
                
        except Exception as e:
            logger.error(f"연결 상태 조회 실패: {str(e)}")
            return {"error": str(e)}
            
    def _count_connections_by_state(self) -> Dict[str, int]:
        """상태별 연결 수 계산"""
        counts = defaultdict(int)
        for state in self.connection_states.values():
            counts[state.value] += 1
        return dict(counts)
        
    async def monitor_connections(self) -> None:
        """연결 상태 모니터링 (백그라운드 태스크)"""
        try:
            while True:
                await asyncio.sleep(60)  # 1분마다 체크
                
                now = datetime.now()
                disconnected = []
                
                for connection_id, info in self.connection_info.items():
                    # 2분 이상 활동이 없으면 경고
                    if now - info["last_activity"] > timedelta(minutes=2):
                        logger.warning(f"연결 비활성: connection_id={connection_id}")
                        
                    # 3분 이상 하트비트가 없으면 연결 해제
                    if now - info["last_heartbeat"] > timedelta(minutes=3):
                        logger.warning(f"하트비트 없음, 연결 해제: connection_id={connection_id}")
                        disconnected.append(connection_id)
                        
                # 비활성 연결 해제
                for connection_id in disconnected:
                    await self.disconnect(connection_id)
                    
                # 상태 로그
                status = await self.get_connection_status()
                logger.info(f"WebSocket 상태: {status}")
                
        except asyncio.CancelledError:
            logger.info("연결 모니터링 중지")
        except Exception as e:
            logger.error(f"연결 모니터링 오류: {str(e)}")


# 전역 연결 관리자 인스턴스
connection_manager = ConnectionManager()