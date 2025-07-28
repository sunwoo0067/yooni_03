"""
고객 지원 채팅 API 엔드포인트
Claude AI 기반 자동 응답 시스템
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
import uuid
from datetime import datetime

from app.api.v1.dependencies.database import get_db
from app.api.v1.dependencies.auth import get_current_user_optional
from app.services.customer_support.claude_support_agent import CustomerSupportAgent
from app.schemas.base import BaseResponse


router = APIRouter()

# 활성 채팅 세션 관리
active_sessions: Dict[str, CustomerSupportAgent] = {}


@router.post("/chat/start")
async def start_chat_session(
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
) -> BaseResponse:
    """새 채팅 세션 시작"""
    session_id = str(uuid.uuid4())
    
    # 새 에이전트 인스턴스 생성
    agent = CustomerSupportAgent(db_session=db)
    
    # 고객 정보 설정
    if current_user:
        customer_id = str(current_user.id)
    
    # 세션 저장
    active_sessions[session_id] = agent
    
    return BaseResponse(
        success=True,
        data={
            "session_id": session_id,
            "welcome_message": f"안녕하세요! {agent.settings.PROJECT_NAME} 고객지원팀입니다. 무엇을 도와드릴까요?",
            "suggested_topics": [
                "주문 상태 확인",
                "배송 조회",
                "반품/교환 문의",
                "상품 정보",
                "결제 관련"
            ]
        }
    )


@router.post("/chat/{session_id}/message")
async def send_message(
    session_id: str,
    message: str,
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> BaseResponse:
    """채팅 메시지 전송"""
    
    # 세션 확인
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다")
    
    agent = active_sessions[session_id]
    
    try:
        # 메시지 처리
        response = await agent.process_message(
            user_message=message,
            customer_id=customer_id,
            order_id=order_id,
            session_id=session_id
        )
        
        return BaseResponse(
            success=True,
            data=response
        )
        
    except Exception as e:
        return BaseResponse(
            success=False,
            error=f"메시지 처리 중 오류 발생: {str(e)}"
        )


@router.get("/chat/{session_id}/history")
async def get_chat_history(
    session_id: str,
    format: str = "json"
) -> BaseResponse:
    """채팅 내역 조회"""
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다")
    
    agent = active_sessions[session_id]
    
    try:
        history = await agent.export_conversation(format=format)
        
        return BaseResponse(
            success=True,
            data={
                "session_id": session_id,
                "format": format,
                "history": history if format == "text" else json.loads(history)
            }
        )
    except Exception as e:
        return BaseResponse(
            success=False,
            error=f"대화 내역 조회 실패: {str(e)}"
        )


@router.post("/chat/{session_id}/end")
async def end_chat_session(session_id: str) -> BaseResponse:
    """채팅 세션 종료"""
    
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다")
    
    # 세션 요약 생성
    agent = active_sessions[session_id]
    summary = agent.get_conversation_summary()
    
    # 세션 제거
    del active_sessions[session_id]
    
    return BaseResponse(
        success=True,
        data={
            "session_id": session_id,
            "ended_at": datetime.now().isoformat(),
            "summary": summary,
            "message": "채팅이 종료되었습니다. 감사합니다!"
        }
    )


# WebSocket 실시간 채팅
@router.websocket("/chat/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """WebSocket 기반 실시간 채팅"""
    await websocket.accept()
    
    # 새 세션이면 에이전트 생성
    if session_id not in active_sessions:
        active_sessions[session_id] = CustomerSupportAgent(db_session=db)
    
    agent = active_sessions[session_id]
    
    # 환영 메시지
    await websocket.send_json({
        "type": "welcome",
        "message": f"안녕하세요! {agent.settings.PROJECT_NAME} 고객지원팀입니다.",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # 메시지 처리
                response = await agent.process_message(
                    user_message=data.get("message", ""),
                    customer_id=data.get("customer_id"),
                    order_id=data.get("order_id"),
                    session_id=session_id
                )
                
                # 응답 전송
                await websocket.send_json({
                    "type": "response",
                    "data": response,
                    "timestamp": datetime.now().isoformat()
                })
                
            elif data.get("type") == "typing":
                # 타이핑 인디케이터
                await websocket.send_json({
                    "type": "agent_typing",
                    "timestamp": datetime.now().isoformat()
                })
                
    except WebSocketDisconnect:
        # 연결 종료 시 세션 정리
        if session_id in active_sessions:
            del active_sessions[session_id]


# 사전 정의된 응답 및 FAQ
@router.get("/chat/faq")
async def get_faq_list() -> BaseResponse:
    """자주 묻는 질문 목록"""
    
    faq_list = [
        {
            "id": 1,
            "category": "주문",
            "question": "주문을 취소하고 싶어요",
            "answer": "주문 취소는 배송 시작 전까지 가능합니다. 마이페이지 > 주문내역에서 취소 신청해주세요."
        },
        {
            "id": 2,
            "category": "배송",
            "question": "배송은 얼마나 걸리나요?",
            "answer": "일반적으로 결제 완료 후 2-3일 내 배송됩니다. (주말/공휴일 제외)"
        },
        {
            "id": 3,
            "category": "반품",
            "question": "반품은 어떻게 하나요?",
            "answer": "수령 후 7일 이내 마이페이지에서 반품 신청이 가능합니다."
        },
        {
            "id": 4,
            "category": "결제",
            "question": "어떤 결제 수단을 사용할 수 있나요?",
            "answer": "신용카드, 체크카드, 무통장입금, 간편결제(카카오페이, 네이버페이) 등을 지원합니다."
        }
    ]
    
    return BaseResponse(
        success=True,
        data={"faq": faq_list}
    )


@router.get("/chat/quick-replies")
async def get_quick_replies(category: Optional[str] = None) -> BaseResponse:
    """빠른 답변 템플릿"""
    
    quick_replies = {
        "greeting": [
            "주문 상태를 확인하고 싶어요",
            "배송은 언제 되나요?",
            "반품하고 싶어요",
            "상품 정보를 알고 싶어요"
        ],
        "order_status": [
            "송장번호를 알려주세요",
            "주문을 취소하고 싶어요",
            "주문 내역을 확인하고 싶어요"
        ],
        "shipping": [
            "배송비는 얼마인가요?",
            "해외배송도 가능한가요?",
            "배송지를 변경하고 싶어요"
        ],
        "returns": [
            "반품 절차를 알려주세요",
            "교환은 어떻게 하나요?",
            "환불은 언제 되나요?"
        ]
    }
    
    if category and category in quick_replies:
        return BaseResponse(
            success=True,
            data={"replies": quick_replies[category]}
        )
    
    return BaseResponse(
        success=True,
        data={"categories": list(quick_replies.keys()), "all_replies": quick_replies}
    )