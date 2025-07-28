"""
WebSocket API 엔드포인트
실시간 통신을 위한 WebSocket 연결 관리
"""
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid
import json

from app.api.v1.dependencies.auth import get_current_user_ws, get_current_active_user
from app.api.v1.dependencies.database import get_db
from app.services.realtime.websocket_manager import connection_manager
from app.models.user import User
from app.core.logging import logger


router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    WebSocket 연결 엔드포인트
    
    Query Parameters:
    - token: JWT 인증 토큰
    
    WebSocket 메시지 형식:
    - type: 메시지 타입 (ping, subscribe, unsubscribe, refresh)
    - data: 메시지 데이터
    
    구독 가능한 채널:
    - dashboard:{user_id}: 대시보드 업데이트
    - orders:{user_id}: 주문 업데이트
    - products:{user_id}: 상품 업데이트
    - inventory:{user_id}: 재고 업데이트
    - prices:{user_id}: 가격 업데이트
    - alerts:{user_id}: 알림
    - competitor:{user_id}: 경쟁사 정보
    """
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # 토큰 인증
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # 연결 수락
        await connection_manager.connect(websocket, user.id, connection_id)
        
        # 기본 채널 구독
        default_channels = [
            f"dashboard:{user.id}",
            f"orders:{user.id}",
            f"alerts:{user.id}"
        ]
        await connection_manager.subscribe(connection_id, default_channels)
        
        # 메시지 처리 루프
        await connection_manager.handle_message(websocket, connection_id)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket 연결 끊김: connection_id={connection_id}")
    except Exception as e:
        logger.error(f"WebSocket 오류: {str(e)}")
    finally:
        await connection_manager.disconnect(connection_id)


@router.get("/status")
async def get_websocket_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    WebSocket 연결 상태 조회
    
    Returns:
    - 현재 사용자의 WebSocket 연결 상태
    """
    try:
        status = await connection_manager.get_connection_status(user_id=current_user.id)
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"WebSocket 상태 조회 실패: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get WebSocket status"}
        )


@router.get("/status/all")
async def get_all_websocket_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    전체 WebSocket 연결 상태 조회 (관리자용)
    
    Returns:
    - 전체 WebSocket 연결 상태 통계
    """
    try:
        # 관리자 권한 체크
        if not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"error": "Admin access required"}
            )
            
        status = await connection_manager.get_connection_status()
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"전체 WebSocket 상태 조회 실패: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get WebSocket status"}
        )


@router.post("/broadcast")
async def broadcast_message(
    channel: str,
    message: dict,
    current_user: User = Depends(get_current_active_user)
):
    """
    채널로 메시지 브로드캐스트 (테스트용)
    
    Parameters:
    - channel: 브로드캐스트할 채널
    - message: 전송할 메시지
    
    Returns:
    - 브로드캐스트 결과
    """
    try:
        # 사용자 권한 체크 (자신의 채널만 브로드캐스트 가능)
        if not channel.endswith(f":{current_user.id}") and not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"error": "Unauthorized channel access"}
            )
            
        await connection_manager.broadcast_to_channel(channel, message)
        
        return JSONResponse(
            content={
                "status": "success",
                "channel": channel,
                "subscribers": connection_manager.get_channel_subscribers(channel)
            }
        )
    except Exception as e:
        logger.error(f"브로드캐스트 실패: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to broadcast message"}
        )


@router.post("/notify")
async def send_notification(
    user_id: int,
    notification: dict,
    current_user: User = Depends(get_current_active_user)
):
    """
    특정 사용자에게 알림 전송 (관리자용)
    
    Parameters:
    - user_id: 알림을 받을 사용자 ID
    - notification: 알림 내용
    
    Returns:
    - 알림 전송 결과
    """
    try:
        # 권한 체크
        if user_id != current_user.id and not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"error": "Unauthorized"}
            )
            
        await connection_manager.send_notification(user_id, notification)
        
        return JSONResponse(
            content={
                "status": "success",
                "user_id": user_id,
                "notification_sent": True
            }
        )
    except Exception as e:
        logger.error(f"알림 전송 실패: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to send notification"}
        )


# WebSocket 연결 예제 클라이언트 코드
WEBSOCKET_CLIENT_EXAMPLE = """
// JavaScript WebSocket 클라이언트 예제

class WebSocketClient {
    constructor(token) {
        this.token = token;
        this.ws = null;
        this.reconnectInterval = 5000;
        this.shouldReconnect = true;
    }
    
    connect() {
        const wsUrl = `ws://localhost:8000/api/v1/ws/?token=${this.token}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket 연결됨');
            
            // 추가 채널 구독
            this.subscribe(['products:1', 'inventory:1']);
        };
        
        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('메시지 수신:', message);
            
            // 메시지 타입별 처리
            switch(message.type) {
                case 'order_created':
                    this.handleNewOrder(message.data);
                    break;
                case 'inventory_updated':
                    this.handleInventoryUpdate(message.data);
                    break;
                case 'notification':
                    this.handleNotification(message.notification);
                    break;
                case 'heartbeat':
                    // 하트비트 응답
                    this.send({ type: 'ping' });
                    break;
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket 오류:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket 연결 끊김');
            if (this.shouldReconnect) {
                setTimeout(() => this.connect(), this.reconnectInterval);
            }
        };
    }
    
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    subscribe(channels) {
        this.send({
            type: 'subscribe',
            channels: channels
        });
    }
    
    unsubscribe(channels) {
        this.send({
            type: 'unsubscribe',
            channels: channels
        });
    }
    
    disconnect() {
        this.shouldReconnect = false;
        if (this.ws) {
            this.ws.close();
        }
    }
    
    handleNewOrder(orderData) {
        // 새 주문 처리
        console.log('새 주문:', orderData);
    }
    
    handleInventoryUpdate(inventoryData) {
        // 재고 업데이트 처리
        console.log('재고 업데이트:', inventoryData);
    }
    
    handleNotification(notification) {
        // 알림 표시
        console.log('알림:', notification);
    }
}

// 사용 예제
const wsClient = new WebSocketClient('your-jwt-token');
wsClient.connect();
"""