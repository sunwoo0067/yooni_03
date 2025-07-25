"""
이메일 마케팅 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import asyncio
import aiosmtplib
from jinja2 import Template
import re
import base64
from sqlalchemy.orm import Session

from app.models.marketing import MarketingMessage, MessageStatus
from app.models.crm import Customer
from app.core.config import settings
from app.core.exceptions import BusinessException


class EmailService:
    """이메일 발송 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        
    async def send_campaign_emails(self, message_ids: List[int], batch_size: int = 50):
        """캠페인 이메일 일괄 발송"""
        try:
            # 배치 단위로 처리
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i + batch_size]
                await self._process_email_batch(batch_ids)
                
                # 배치 간 딜레이 (발송 속도 제한)
                await asyncio.sleep(1)
                
        except Exception as e:
            raise BusinessException(f"이메일 발송 실패: {str(e)}")
    
    async def send_single_email(self, message_id: int) -> bool:
        """단일 이메일 발송"""
        try:
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if not message:
                raise BusinessException("메시지를 찾을 수 없습니다")
            
            customer = self.db.query(Customer).filter(
                Customer.id == message.customer_id
            ).first()
            
            if not customer or not customer.email:
                message.status = MessageStatus.FAILED
                message.error_message = "수신자 이메일 없음"
                self.db.commit()
                return False
            
            # 이메일 발송
            success = await self._send_email(
                to_email=customer.email,
                to_name=customer.name,
                subject=message.personalized_subject,
                html_content=message.personalized_content,
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
            raise BusinessException(f"이메일 발송 실패: {str(e)}")
    
    async def _process_email_batch(self, message_ids: List[int]):
        """이메일 배치 처리"""
        try:
            messages = self.db.query(MarketingMessage).filter(
                MarketingMessage.id.in_(message_ids),
                MarketingMessage.status == MessageStatus.PENDING
            ).all()
            
            # 비동기 이메일 발송
            tasks = []
            for message in messages:
                customer = self.db.query(Customer).filter(
                    Customer.id == message.customer_id
                ).first()
                
                if customer and customer.email:
                    task = self._send_email_async(
                        to_email=customer.email,
                        to_name=customer.name,
                        subject=message.personalized_subject,
                        html_content=message.personalized_content,
                        message_id=message.id
                    )
                    tasks.append(task)
                else:
                    message.status = MessageStatus.FAILED
                    message.error_message = "수신자 이메일 없음"
            
            # 모든 이메일 동시 발송
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 결과 처리
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        messages[i].status = MessageStatus.FAILED
                        messages[i].error_message = str(result)
                    else:
                        if result:
                            messages[i].status = MessageStatus.SENT
                            messages[i].sent_at = datetime.utcnow()
                        else:
                            messages[i].status = MessageStatus.FAILED
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"배치 처리 실패: {str(e)}")
    
    async def _send_email_async(self, to_email: str, to_name: str, 
                              subject: str, html_content: str, 
                              message_id: int) -> bool:
        """비동기 이메일 발송"""
        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            msg['Message-ID'] = f"<{message_id}@{self.smtp_host}>"
            
            # 추적 픽셀 추가
            tracking_pixel = self._generate_tracking_pixel(message_id)
            html_with_tracking = html_content + tracking_pixel
            
            # 텍스트 버전 생성
            text_content = self._html_to_text(html_content)
            
            # 콘텐츠 추가
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_with_tracking, 'html'))
            
            # 이메일 발송
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=True
            ) as smtp:
                await smtp.login(self.smtp_user, self.smtp_password)
                await smtp.send_message(msg)
                
            return True
            
        except Exception as e:
            print(f"이메일 발송 오류: {str(e)}")
            return False
    
    async def _send_email(self, to_email: str, to_name: str, 
                         subject: str, html_content: str, 
                         message_id: int) -> bool:
        """동기 이메일 발송 (폴백)"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = f"{to_name} <{to_email}>"
            msg['Message-ID'] = f"<{message_id}@{self.smtp_host}>"
            
            # 추적 픽셀 추가
            tracking_pixel = self._generate_tracking_pixel(message_id)
            html_with_tracking = html_content + tracking_pixel
            
            # 텍스트 버전 생성
            text_content = self._html_to_text(html_content)
            
            # 콘텐츠 추가
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_with_tracking, 'html'))
            
            # SMTP 연결 및 발송
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
            return True
            
        except Exception as e:
            print(f"이메일 발송 오류: {str(e)}")
            return False
    
    def _generate_tracking_pixel(self, message_id: int) -> str:
        """이메일 오픈 추적 픽셀 생성"""
        tracking_url = f"{settings.API_BASE_URL}/api/v1/marketing/track/open/{message_id}"
        return f'<img src="{tracking_url}" width="1" height="1" style="display:none;" />'
    
    def _html_to_text(self, html: str) -> str:
        """HTML을 텍스트로 변환"""
        # 기본적인 HTML 태그 제거
        text = re.sub('<[^<]+?>', '', html)
        # 연속된 공백 제거
        text = re.sub(r'\s+', ' ', text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text
    
    async def process_email_bounce(self, bounce_data: Dict[str, Any]):
        """이메일 반송 처리"""
        try:
            email = bounce_data.get('email')
            bounce_type = bounce_data.get('type')  # hard, soft
            
            # 해당 이메일의 최근 메시지 찾기
            message = self.db.query(MarketingMessage).join(Customer).filter(
                Customer.email == email,
                MarketingMessage.status == MessageStatus.SENT
            ).order_by(MarketingMessage.sent_at.desc()).first()
            
            if message:
                message.status = MessageStatus.BOUNCED
                message.error_message = f"Bounce type: {bounce_type}"
                
                # Hard bounce인 경우 고객 이메일 비활성화
                if bounce_type == 'hard':
                    customer = self.db.query(Customer).filter(
                        Customer.id == message.customer_id
                    ).first()
                    if customer:
                        customer.email_marketing_consent = False
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"반송 처리 실패: {str(e)}")
    
    async def track_email_open(self, message_id: int):
        """이메일 오픈 추적"""
        try:
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if message and message.status in [MessageStatus.SENT, MessageStatus.DELIVERED]:
                message.status = MessageStatus.OPENED
                if not message.opened_at:
                    message.opened_at = datetime.utcnow()
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            print(f"오픈 추적 실패: {str(e)}")
    
    async def track_email_click(self, message_id: int, link_url: str):
        """이메일 클릭 추적"""
        try:
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if message:
                # 상태 업데이트
                if message.status in [MessageStatus.SENT, MessageStatus.DELIVERED, MessageStatus.OPENED]:
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
            print(f"클릭 추적 실패: {str(e)}")
    
    async def handle_unsubscribe(self, message_id: int):
        """구독 해지 처리"""
        try:
            message = self.db.query(MarketingMessage).filter(
                MarketingMessage.id == message_id
            ).first()
            
            if message:
                message.status = MessageStatus.UNSUBSCRIBED
                message.unsubscribed_at = datetime.utcnow()
                
                # 고객 마케팅 동의 철회
                customer = self.db.query(Customer).filter(
                    Customer.id == message.customer_id
                ).first()
                
                if customer:
                    customer.email_marketing_consent = False
                
                self.db.commit()
                
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"구독 해지 처리 실패: {str(e)}")
    
    def validate_email_template(self, template: str) -> Dict[str, Any]:
        """이메일 템플릿 검증"""
        try:
            # Jinja2 템플릿 검증
            jinja_template = Template(template)
            
            # 사용된 변수 추출
            variables = re.findall(r'\{\{(\w+)\}\}', template)
            
            # HTML 검증
            has_html = bool(re.search(r'<[^>]+>', template))
            
            # 이미지 태그 검사
            images = re.findall(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', template)
            
            # 링크 검사
            links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>', template)
            
            return {
                'valid': True,
                'variables': list(set(variables)),
                'has_html': has_html,
                'images': images,
                'links': links,
                'warnings': self._check_template_warnings(template)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def _check_template_warnings(self, template: str) -> List[str]:
        """템플릿 경고 사항 체크"""
        warnings = []
        
        # 스팸 키워드 체크
        spam_keywords = ['무료', '할인', '클릭', '지금', '한정', '특가']
        for keyword in spam_keywords:
            if keyword in template:
                warnings.append(f"스팸 필터에 걸릴 수 있는 키워드 포함: {keyword}")
        
        # 이미지 비율 체크
        text_length = len(re.sub(r'<[^>]+>', '', template))
        img_count = len(re.findall(r'<img', template))
        if img_count > 3 and text_length < 500:
            warnings.append("이미지 대비 텍스트가 적어 스팸으로 분류될 수 있습니다")
        
        # 대문자 비율 체크
        uppercase_ratio = sum(1 for c in template if c.isupper()) / len(template)
        if uppercase_ratio > 0.3:
            warnings.append("대문자 비율이 높아 스팸으로 분류될 수 있습니다")
        
        return warnings