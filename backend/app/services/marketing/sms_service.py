"""
SMS 마케팅 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio
from sqlalchemy.orm import Session
import re

from app.models.marketing import MarketingMessage, MessageStatus
from app.models.crm import Customer
from app.core.config import settings
from app.core.exceptions import BusinessException


class SMSService:
    """SMS 발송 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.SMS_API_KEY
        self.api_secret = settings.SMS_API_SECRET
        self.sender_number = settings.SMS_SENDER_NUMBER
        self.api_base_url = settings.SMS_API_URL
        
    async def send_campaign_sms(self, message_ids: List[int], batch_size: int = 100):
        """캠페인 SMS 일괄 발송"""
        try:
            # 배치 단위로 처리
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                await self._process_sms_batch(batch_ids)
                
                # 배치 간 딜레이 (발송 속도 제한)
                await asyncio.sleep(0.5)
                
        except Exception as e:
            raise BusinessException(f"SMS 발송 실패: {str(e)}")
    
    async def send_single_sms(self, message_id: int) -> bool:
        """단일 SMS 발송"""
        try:
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if not message:
                raise BusinessException("메시지를 찾을 수 없습니다")
            
            customer = self.db.query(Customer).filter(
                Customer.id == message.customer_id
            ).first()
            
            if not customer or not customer.phone:
                message.status = MessageStatus.FAILED
                message.error_message = "수신자 전화번호 없음"
                self.db.commit()
                return False
            
            # SMS 발송
            success = await self._send_sms(
                phone_number=customer.phone,
                content=message.personalized_content,
                message_id=message.id
            )
            
            if success:
                message.status = MessageStatus.SENT
                message.sent_at = datetime.utcnow()
            else:
                message.status = MessageStatus.FAILED
                
            self.db.commit()
            return success
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"SMS 발송 실패: {str(e)}")
    
    async def _process_sms_batch(self, message_ids: List[int]):
        """SMS 배치 처리"""
        try:
            messages = self.db.query(MarketingMessage).filter(
                MarketingMessage.id.in_(message_ids),
                MarketingMessage.status == MessageStatus.PENDING
            ).all()
            
            # SMS 발송 데이터 준비
            sms_data = []
            for message in messages:
                customer = self.db.query(Customer).filter(
                    Customer.id == message.customer_id
                ).first()
                
                if customer and customer.phone:
                    # 전화번호 정규화
                    normalized_phone = self._normalize_phone_number(customer.phone)
                    if normalized_phone:
                        sms_data.append({
                            'message_id': message.id,
                            'phone': normalized_phone,
                            'content': message.personalized_content
                        })
                    else:
                        message.status = MessageStatus.FAILED
                        message.error_message = "유효하지 않은 전화번호"
                else:
                    message.status = MessageStatus.FAILED
                    message.error_message = "수신자 전화번호 없음"
            
            # 배치 SMS 발송
            if sms_data:
                results = await self._send_batch_sms(sms_data)
                
                # 결과 처리
                for i, message in enumerate(messages):
                    if i < len(results) and results[i]['success']:
                        message.status = MessageStatus.SENT
                        message.sent_at = datetime.utcnow()
                    else:
                        if message.status != MessageStatus.FAILED:
                            message.status = MessageStatus.FAILED
                            message.error_message = results[i].get('error', '발송 실패') if i < len(results) else '발송 실패'
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"배치 처리 실패: {str(e)}")
    
    async def _send_sms(self, phone_number: str, content: str, message_id: int) -> bool:
        """SMS 발송 API 호출"""
        try:
            # 전화번호 정규화
            normalized_phone = self._normalize_phone_number(phone_number)
            if not normalized_phone:
                return False
            
            # SMS 길이 체크 및 분할
            messages = self._split_sms_content(content)
            
            async with httpx.AsyncClient() as client:
                for i, msg_content in enumerate(messages):
                    # API 요청 데이터
                    request_data = {
                        'api_key': self.api_key,
                        'api_secret': self.api_secret,
                        'from': self.sender_number,
                        'to': normalized_phone,
                        'text': msg_content,
                        'type': 'SMS',
                        'msg_id': f"{message_id}_{i}"
                    }
                    
                    # API 호출
                    response = await client.post(
                        f"{self.api_base_url}/messages",
                        json=request_data
                    )
                    
                    if response.status_code != 200:
                        return False
                    
                    result = response.json()
                    if result.get('status') != 'success':
                        return False
            
            return True
            
        except Exception as e:
            print(f"SMS 발송 오류: {str(e)}")
            return False
    
    async def _send_batch_sms(self, sms_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """배치 SMS 발송"""
        try:
            results = []
            
            async with httpx.AsyncClient() as client:
                # 배치 API 요청
                batch_request = {
                    'api_key': self.api_key,
                    'api_secret': self.api_secret,
                    'messages': []
                }
                
                for sms in sms_data:
                    # SMS 길이 체크 및 분할
                    messages = self._split_sms_content(sms['content'])
                    
                    for i, msg_content in enumerate(messages):
                        batch_request['messages'].append({
                            'from': self.sender_number,
                            'to': sms['phone'],
                            'text': msg_content,
                            'type': 'SMS',
                            'msg_id': f"{sms['message_id']}_{i}"
                        })
                
                # 배치 발송
                response = await client.post(
                    f"{self.api_base_url}/messages/batch",
                    json=batch_request
                )
                
                if response.status_code == 200:
                    batch_result = response.json()
                    
                    # 각 메시지별 결과 매핑
                    for sms in sms_data:
                        message_results = [
                            r for r in batch_result.get('results', [])
                            if r.get('msg_id', '').startswith(str(sms['message_id']))
                        ]
                        
                        success = all(r.get('status') == 'success' for r in message_results)
                        results.append({
                            'message_id': sms['message_id'],
                            'success': success,
                            'error': message_results[0].get('error') if message_results and not success else None
                        })
                else:
                    # 실패 시 모든 메시지 실패 처리
                    for sms in sms_data:
                        results.append({
                            'message_id': sms['message_id'],
                            'success': False,
                            'error': 'API 호출 실패'
                        })
            
            return results
            
        except Exception as e:
            print(f"배치 SMS 발송 오류: {str(e)}")
            return [{'message_id': sms['message_id'], 'success': False, 'error': str(e)} for sms in sms_data]
    
    def _normalize_phone_number(self, phone: str) -> Optional[str]:
        """전화번호 정규화"""
        # 숫자만 추출
        numbers = re.sub(r'[^0-9]', '', phone)
        
        # 한국 전화번호 형식 체크
        if len(numbers) == 11 and numbers.startswith('01'):
            return f"+82{numbers[1:]}"
        elif len(numbers) == 10 and numbers.startswith('1'):
            return f"+82{numbers}"
        elif numbers.startswith('+82'):
            return numbers
        elif numbers.startswith('82') and len(numbers) >= 11:
            return f"+{numbers}"
        
        return None
    
    def _split_sms_content(self, content: str) -> List[str]:
        """SMS 내용 분할 (장문 SMS 처리)"""
        max_length = 90  # 한글 기준 SMS 최대 길이
        
        if len(content) <= max_length:
            return [content]
        
        # 장문 SMS 분할
        messages = []
        words = content.split()
        current_message = ""
        
        for word in words:
            if len(current_message) + len(word) + 1 <= max_length - 10:  # 페이지 정보 공간 확보
                current_message += word + " "
            else:
                messages.append(current_message.strip())
                current_message = word + " "
        
        if current_message:
            messages.append(current_message.strip())
        
        # 페이지 정보 추가
        total_pages = len(messages)
        for i, msg in enumerate(messages):
            messages[i] = f"({i+1}/{total_pages}) {msg}"
        
        return messages
    
    def validate_sms_content(self, content: str) -> Dict[str, Any]:
        """SMS 내용 검증"""
        # 길이 체크
        length = len(content)
        is_long = length > 90
        
        # 특수문자 체크
        special_chars = re.findall(r'[^\w\s\.,!?-]', content)
        
        # URL 추출
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)
        
        # 분할 예상
        messages = self._split_sms_content(content)
        
        return {
            'valid': True,
            'length': length,
            'is_long': is_long,
            'message_count': len(messages),
            'special_chars': list(set(special_chars)),
            'urls': urls,
            'warnings': self._check_sms_warnings(content)
        }
    
    def _check_sms_warnings(self, content: str) -> List[str]:
        """SMS 경고 사항 체크"""
        warnings = []
        
        # 스팸 키워드 체크
        spam_keywords = ['무료', '대출', '도박', '성인', '수익']
        for keyword in spam_keywords:
            if keyword in content:
                warnings.append(f"스팸으로 차단될 수 있는 키워드 포함: {keyword}")
        
        # URL 단축 권장
        if re.search(r'http[s]?://[^\s]+', content) and len(content) > 70:
            warnings.append("URL이 포함된 경우 단축 URL 사용을 권장합니다")
        
        # 특수문자 과다 사용
        special_char_ratio = len(re.findall(r'[^\w\s]', content)) / len(content)
        if special_char_ratio > 0.2:
            warnings.append("특수문자가 많아 스팸으로 분류될 수 있습니다")
        
        return warnings
    
    async def track_sms_delivery(self, delivery_data: Dict[str, Any]):
        """SMS 전송 결과 추적"""
        try:
            msg_id = delivery_data.get('msg_id')
            status = delivery_data.get('status')
            
            if not msg_id:
                return
            
            # 메시지 ID에서 원본 message_id 추출
            message_id = int(msg_id.split('_')[0])
            
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if message:
                if status == 'delivered':
                    message.status = MessageStatus.DELIVERED
                    message.delivered_at = datetime.utcnow()
                elif status == 'failed':
                    message.status = MessageStatus.FAILED
                    message.error_message = delivery_data.get('error', '전송 실패')
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            print(f"SMS 전송 결과 추적 실패: {str(e)}")
    
    async def track_sms_click(self, message_id: int, link_url: str):
        """SMS 링크 클릭 추적"""
        try:
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if message:
                # 상태 업데이트
                if message.status in [MessageStatus.SENT, MessageStatus.DELIVERED]:
                    message.status = MessageStatus.CLICKED
                    if not message.clicked_at:
                        message.clicked_at = datetime.utcnow()
                
                # 클릭 카운트 증가
                message.click_count += 1
                
                # 클릭한 링크 저장
                clicked_links = message.clicked_links or []
                if link_url not in clicked_links:
                    clicked_links.append(link_url)
                    message.clicked_links = clicked_links
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            print(f"SMS 클릭 추적 실패: {str(e)}")
    
    async def handle_opt_out(self, phone_number: str):
        """SMS 수신 거부 처리"""
        try:
            # 전화번호 정규화
            normalized_phone = self._normalize_phone_number(phone_number)
            if not normalized_phone:
                return
            
            # 해당 전화번호의 고객 찾기
            customer = self.db.query(Customer).filter(
                Customer.phone.like(f"%{phone_number[-4:]}%")
            ).first()
            
            if customer:
                customer.sms_marketing_consent = False
                
                # 최근 SMS 메시지 상태 업데이트
                recent_message = self.db.query(MarketingMessage).filter(
                    MarketingMessage.customer_id == customer.id,
                    MarketingMessage.message_type == 'sms'
                ).order_by(MarketingMessage.sent_at.desc()).first()
                
                if recent_message:
                    recent_message.status = MessageStatus.UNSUBSCRIBED
                    recent_message.unsubscribed_at = datetime.utcnow()
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"수신 거부 처리 실패: {str(e)}")