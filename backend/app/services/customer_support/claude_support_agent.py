"""
Claude 기반 고객 지원 챗봇 서비스
드롭시핑 비즈니스를 위한 맞춤형 고객 지원
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import anthropic
from pydantic import BaseModel, Field

from ...core.config import get_settings
from ...models.order import Order
from ...models.product import Product
from ...crud.order import crud_order
from ...crud.product import crud_product


class ConversationRole(str, Enum):
    """대화 참여자 역할"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel):
    """대화 메시지"""
    role: ConversationRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class SupportCategory(str, Enum):
    """지원 카테고리"""
    ORDER_STATUS = "order_status"
    SHIPPING = "shipping"
    RETURNS = "returns"
    PRODUCT_INFO = "product_info"
    PAYMENT = "payment"
    GENERAL = "general"


class CustomerSupportAgent:
    """드롭시핑 고객 지원 AI 에이전트"""
    
    def __init__(self, db_session=None):
        self.settings = get_settings()
        self.db = db_session
        self.client = None
        self.conversation_history: List[Message] = []
        self.customer_context: Dict[str, Any] = {}
        
        # Anthropic 클라이언트 초기화
        if self.settings.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(
                api_key=self.settings.ANTHROPIC_API_KEY.get_secret_value()
            )
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return f"""당신은 {self.settings.PROJECT_NAME}의 전문 고객 지원 상담원입니다.

주요 역할:
1. 고객의 주문 상태 확인 및 안내
2. 배송 정보 제공
3. 반품/교환 절차 안내
4. 상품 정보 제공
5. 결제 관련 문의 응답

지침:
- 항상 친절하고 전문적으로 응답하세요
- 고객의 감정을 이해하고 공감하세요
- 명확하고 간결한 답변을 제공하세요
- 필요시 상위 담당자에게 연결을 제안하세요
- 개인정보 보호에 주의하세요

사용 가능한 도구:
- 주문 조회: check_order_status
- 배송 추적: track_shipping
- 상품 정보 조회: get_product_info
- 반품 요청 생성: create_return_request
- FAQ 검색: search_faq

현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    async def process_message(
        self,
        user_message: str,
        customer_id: Optional[str] = None,
        order_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """사용자 메시지 처리"""
        
        # 대화 기록에 추가
        self.conversation_history.append(
            Message(role=ConversationRole.USER, content=user_message)
        )
        
        # 고객 컨텍스트 업데이트
        if customer_id:
            self.customer_context["customer_id"] = customer_id
        if order_id:
            self.customer_context["order_id"] = order_id
        
        # 메시지 분류
        category = await self._classify_message(user_message)
        
        # Claude API 호출
        response = await self._generate_response(
            user_message,
            category,
            self.customer_context
        )
        
        # 응답 기록
        self.conversation_history.append(
            Message(
                role=ConversationRole.ASSISTANT,
                content=response["content"],
                metadata={"category": category}
            )
        )
        
        return {
            "response": response["content"],
            "category": category,
            "suggested_actions": response.get("actions", []),
            "confidence": response.get("confidence", 0.9),
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _classify_message(self, message: str) -> SupportCategory:
        """메시지 카테고리 분류"""
        classification_prompt = f"""다음 고객 문의를 분류하세요:
        
메시지: "{message}"

카테고리:
- order_status: 주문 상태 확인
- shipping: 배송 관련
- returns: 반품/교환
- product_info: 상품 정보
- payment: 결제 관련  
- general: 일반 문의

카테고리만 응답하세요."""

        if not self.client:
            # API 키가 없으면 키워드 기반 분류
            message_lower = message.lower()
            if any(word in message_lower for word in ["주문", "상태", "언제"]):
                return SupportCategory.ORDER_STATUS
            elif any(word in message_lower for word in ["배송", "택배", "도착"]):
                return SupportCategory.SHIPPING
            elif any(word in message_lower for word in ["반품", "교환", "환불"]):
                return SupportCategory.RETURNS
            elif any(word in message_lower for word in ["상품", "제품", "사이즈"]):
                return SupportCategory.PRODUCT_INFO
            elif any(word in message_lower for word in ["결제", "카드", "입금"]):
                return SupportCategory.PAYMENT
            else:
                return SupportCategory.GENERAL
        
        # Claude API로 분류
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                messages=[{
                    "role": "user",
                    "content": classification_prompt
                }]
            )
            
            category_str = response.content[0].text.strip().lower()
            return SupportCategory(category_str)
        except:
            return SupportCategory.GENERAL
    
    async def _generate_response(
        self,
        message: str,
        category: SupportCategory,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """응답 생성"""
        
        # 카테고리별 처리
        if category == SupportCategory.ORDER_STATUS:
            return await self._handle_order_status(message, context)
        elif category == SupportCategory.SHIPPING:
            return await self._handle_shipping(message, context)
        elif category == SupportCategory.RETURNS:
            return await self._handle_returns(message, context)
        elif category == SupportCategory.PRODUCT_INFO:
            return await self._handle_product_info(message, context)
        elif category == SupportCategory.PAYMENT:
            return await self._handle_payment(message, context)
        else:
            return await self._handle_general(message, context)
    
    async def _handle_order_status(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """주문 상태 처리"""
        order_id = context.get("order_id")
        
        if order_id and self.db:
            # 실제 주문 조회
            order = crud_order.get(self.db, id=order_id)
            if order:
                status_map = {
                    "pending": "주문 확인 중",
                    "confirmed": "주문 확인됨",
                    "shipped": "배송 중",
                    "delivered": "배송 완료",
                    "cancelled": "주문 취소됨"
                }
                
                response = f"""주문번호 {order.order_number}의 현재 상태를 알려드립니다.

📦 주문 상태: {status_map.get(order.status, order.status)}
📅 주문일: {order.created_at.strftime('%Y년 %m월 %d일')}
💰 주문 금액: {order.total_amount:,}원

"""
                if order.status == "shipped" and order.tracking_number:
                    response += f"🚚 송장번호: {order.tracking_number}\n"
                    response += f"배송 조회: [택배사 링크]\n"
                
                return {
                    "content": response,
                    "confidence": 1.0,
                    "actions": ["track_shipping", "contact_support"]
                }
        
        # 주문 정보가 없는 경우
        return {
            "content": """주문 정보를 확인하기 위해 주문번호나 주문하신 이메일 주소를 알려주시겠어요?
            
주문번호는 주문 확인 이메일에서 확인하실 수 있습니다.""",
            "confidence": 0.8,
            "actions": ["request_order_info"]
        }
    
    async def _handle_shipping(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """배송 관련 처리"""
        return {
            "content": """배송 관련 문의 감사합니다.

일반적인 배송 정보:
📦 평균 배송 기간: 2-3일 (영업일 기준)
🚚 배송비: 3,000원 (50,000원 이상 무료)
📍 배송 지역: 전국 (제주/도서산간 추가비용)

구체적인 배송 정보를 원하시면 주문번호를 알려주세요.""",
            "confidence": 0.9
        }
    
    async def _handle_returns(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """반품/교환 처리"""
        return {
            "content": """반품/교환 안내해드립니다.

📋 반품/교환 조건:
- 수령 후 7일 이내
- 제품 하자 시 무료 반품
- 단순 변심 시 왕복 배송비 고객 부담

절차:
1. 고객센터 연락 또는 마이페이지에서 신청
2. 반품 승인 후 제품 발송
3. 제품 확인 후 환불/교환 처리

반품을 원하시는 제품의 주문번호를 알려주시면 바로 도와드리겠습니다.""",
            "confidence": 0.9,
            "actions": ["create_return_request"]
        }
    
    async def _handle_product_info(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """상품 정보 처리"""
        # 메시지에서 상품명 추출 시도
        # 실제 구현에서는 NLP로 상품명 추출
        
        return {
            "content": """상품 정보를 찾고 계신가요?

저희 쇼핑몰에서는:
- 상품명이나 카테고리로 검색 가능
- 상세 페이지에서 사이즈, 재질 확인
- 리뷰로 실제 구매자 의견 확인

어떤 상품을 찾고 계신지 알려주시면 자세히 안내해드리겠습니다.""",
            "confidence": 0.8
        }
    
    async def _handle_payment(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """결제 관련 처리"""
        return {
            "content": """결제 관련 안내입니다.

💳 사용 가능한 결제 수단:
- 신용/체크카드 (모든 카드사)
- 무통장입금
- 간편결제 (카카오페이, 네이버페이)

🔒 안전한 결제:
- SSL 암호화 적용
- 안전거래 보증

결제 관련 구체적인 문의사항이 있으시면 말씀해주세요.""",
            "confidence": 0.9
        }
    
    async def _handle_general(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """일반 문의 처리"""
        if not self.client:
            return {
                "content": """문의 감사합니다. 
                
어떻게 도와드릴까요? 주문, 배송, 반품, 상품 정보 등 궁금하신 점을 자세히 말씀해주세요.""",
                "confidence": 0.7
            }
        
        # Claude API로 일반 응답 생성
        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": message}
            ]
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                messages=messages
            )
            
            return {
                "content": response.content[0].text,
                "confidence": 0.85
            }
        except Exception as e:
            return {
                "content": "죄송합니다. 시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "confidence": 0.5,
                "error": str(e)
            }
    
    def get_conversation_summary(self) -> str:
        """대화 요약"""
        if len(self.conversation_history) < 2:
            return "대화 내역이 충분하지 않습니다."
        
        messages = [
            f"{msg.role}: {msg.content}"
            for msg in self.conversation_history[-10:]  # 최근 10개 메시지
        ]
        
        return "\n".join(messages)
    
    async def export_conversation(self, format: str = "json") -> str:
        """대화 내역 내보내기"""
        if format == "json":
            return json.dumps(
                [msg.dict() for msg in self.conversation_history],
                ensure_ascii=False,
                indent=2,
                default=str
            )
        elif format == "text":
            return self.get_conversation_summary()
        else:
            raise ValueError(f"Unsupported format: {format}")


# 도구 함수들 (Claude Function Calling용)
async def check_order_status(order_id: str, db) -> Dict[str, Any]:
    """주문 상태 확인 도구"""
    order = crud_order.get(db, id=order_id)
    if order:
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at.isoformat()
        }
    return {"error": "주문을 찾을 수 없습니다"}


async def track_shipping(tracking_number: str) -> Dict[str, Any]:
    """배송 추적 도구"""
    # 실제 택배 API 연동 필요
    return {
        "tracking_number": tracking_number,
        "status": "배송중",
        "current_location": "서울 물류센터",
        "estimated_delivery": "2024-01-15"
    }


async def get_product_info(product_id: str, db) -> Dict[str, Any]:
    """상품 정보 조회 도구"""
    product = crud_product.get(db, id=product_id)
    if product:
        return {
            "product_id": product.id,
            "name": product.name,
            "price": product.price,
            "stock": product.stock_quantity,
            "description": product.description
        }
    return {"error": "상품을 찾을 수 없습니다"}


async def create_return_request(
    order_id: str,
    reason: str,
    db
) -> Dict[str, Any]:
    """반품 요청 생성 도구"""
    # 반품 요청 로직 구현
    return {
        "return_id": f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_id": order_id,
        "status": "requested",
        "reason": reason
    }