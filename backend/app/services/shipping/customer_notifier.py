"""
드롭쉬핑 고객 알림 서비스
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.order_core import DropshippingOrder, SupplierOrderStatus, Order
from app.models.wholesaler import Wholesaler

logger = logging.getLogger(__name__)


class CustomerNotifier:
    """드롭쉬핑 고객 알림 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_templates = {
            'order_confirmed': {
                'title': '주문이 확인되었습니다',
                'message': '안녕하세요 {customer_name}님, 주문번호 {order_number}가 확인되어 상품 준비를 시작했습니다.',
                'sms_message': '[주문확인] {order_number} 주문이 확인되었습니다. 곧 배송 준비를 시작합니다.'
            },
            'order_shipped': {
                'title': '상품이 발송되었습니다',
                'message': '안녕하세요 {customer_name}님, 주문하신 상품이 발송되었습니다. 택배사: {carrier}, 송장번호: {tracking_number}',
                'sms_message': '[배송시작] {tracking_number} 상품이 발송되었습니다. {carrier}에서 배송합니다.'
            },
            'delivery_delay': {
                'title': '배송이 지연되고 있습니다',
                'message': '안녕하세요 {customer_name}님, 주문번호 {order_number}의 배송이 예상보다 지연되고 있습니다. 양해 부탁드립니다.',
                'sms_message': '[배송지연] {order_number} 배송이 지연되고 있습니다. 빠른 시일 내 배송하겠습니다.'
            },
            'delivery_completed': {
                'title': '배송이 완료되었습니다',
                'message': '안녕하세요 {customer_name}님, 주문번호 {order_number}의 배송이 완료되었습니다. 이용해 주셔서 감사합니다.',
                'sms_message': '[배송완료] {order_number} 배송이 완료되었습니다. 이용해 주셔서 감사합니다.'
            },
            'order_cancelled': {
                'title': '주문이 취소되었습니다',
                'message': '안녕하세요 {customer_name}님, 주문번호 {order_number}가 취소되었습니다. 사유: {cancel_reason}',
                'sms_message': '[주문취소] {order_number} 주문이 취소되었습니다. 문의사항은 고객센터로 연락해 주세요.'
            },
            'out_of_stock': {
                'title': '상품이 일시적으로 품절되었습니다',
                'message': '안녕하세요 {customer_name}님, 주문하신 상품이 일시적으로 품절되어 대체 상품을 안내드리겠습니다.',
                'sms_message': '[품절안내] {order_number} 상품이 품절되었습니다. 고객센터에서 안내드리겠습니다.'
            }
        }
    
    async def notify_order_status_change(
        self, 
        dropshipping_order: DropshippingOrder, 
        notification_type: str,
        additional_data: Optional[Dict] = None
    ) -> Dict:
        """
        주문 상태 변경 알림
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            notification_type: 알림 타입
            additional_data: 추가 데이터
            
        Returns:
            Dict: 알림 결과
        """
        try:
            order = dropshipping_order.order
            template = self.notification_templates.get(notification_type)
            
            if not template:
                return {
                    'success': False,
                    'message': f'지원하지 않는 알림 타입: {notification_type}'
                }
            
            # 알림 데이터 구성
            notification_data = {
                'customer_name': order.customer_name,
                'order_number': order.order_number,
                'tracking_number': dropshipping_order.supplier_tracking_number or '',
                'carrier': dropshipping_order.supplier_carrier or '',
                'cancel_reason': additional_data.get('cancel_reason', '') if additional_data else '',
                'estimated_delivery': dropshipping_order.estimated_delivery_date.strftime('%Y-%m-%d') if dropshipping_order.estimated_delivery_date else ''
            }
            
            # 메시지 템플릿 적용
            title = template['title'].format(**notification_data)
            message = template['message'].format(**notification_data)
            sms_message = template['sms_message'].format(**notification_data)
            
            # 알림 발송
            notification_results = []
            
            # 이메일 알림
            if order.customer_email:
                email_result = await self._send_email_notification(
                    order.customer_email,
                    title,
                    message,
                    order,
                    notification_type
                )
                notification_results.append(email_result)
            
            # SMS 알림
            if order.customer_phone:
                sms_result = await self._send_sms_notification(
                    order.customer_phone,
                    sms_message,
                    order,
                    notification_type
                )
                notification_results.append(sms_result)
            
            # 푸시 알림 (앱이 있는 경우)
            if order.customer_id:
                push_result = await self._send_push_notification(
                    order.customer_id,
                    title,
                    message,
                    order,
                    notification_type
                )
                notification_results.append(push_result)
            
            # 알림 로그 저장
            await self._save_notification_log(
                dropshipping_order,
                notification_type,
                notification_results,
                {
                    'title': title,
                    'message': message,
                    'sms_message': sms_message
                }
            )
            
            success_count = sum(1 for result in notification_results if result.get('success', False))
            total_count = len(notification_results)
            
            return {
                'success': success_count > 0,
                'message': f'{success_count}/{total_count} 알림 발송 성공',
                'notification_type': notification_type,
                'results': notification_results,
                'sent_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"주문 상태 변경 알림 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 상태 변경 알림 중 오류 발생: {str(e)}'
            }
    
    async def _send_email_notification(
        self, 
        email: str, 
        title: str, 
        message: str, 
        order: Order,
        notification_type: str
    ) -> Dict:
        """이메일 알림 발송"""
        try:
            # 실제 이메일 발송 로직 구현
            # 여기서는 가상의 이메일 서비스를 사용한다고 가정
            
            email_data = {
                'to': email,
                'subject': title,
                'html_content': await self._generate_email_html(message, order, notification_type),
                'text_content': message
            }
            
            # 실제 이메일 발송 (예: SendGrid, AWS SES 등)
            # success = await email_service.send_email(email_data)
            success = True  # 임시로 성공으로 설정
            
            if success:
                logger.info(f"이메일 알림 발송 성공: {email} ({notification_type})")
                return {
                    'channel': 'email',
                    'success': True,
                    'recipient': email,
                    'message': '이메일 발송 성공'
                }
            else:
                logger.warning(f"이메일 알림 발송 실패: {email}")
                return {
                    'channel': 'email',
                    'success': False,
                    'recipient': email,
                    'message': '이메일 발송 실패'
                }
                
        except Exception as e:
            logger.error(f"이메일 알림 발송 중 오류: {str(e)}")
            return {
                'channel': 'email',
                'success': False,
                'recipient': email,
                'message': f'이메일 발송 오류: {str(e)}'
            }
    
    async def _send_sms_notification(
        self, 
        phone: str, 
        message: str, 
        order: Order,
        notification_type: str
    ) -> Dict:
        """SMS 알림 발송"""
        try:
            # 전화번호 형식 정규화
            normalized_phone = self._normalize_phone_number(phone)
            
            if not normalized_phone:
                return {
                    'channel': 'sms',
                    'success': False,
                    'recipient': phone,
                    'message': '잘못된 전화번호 형식'
                }
            
            sms_data = {
                'to': normalized_phone,
                'message': message,
                'sender': '1588-0000'  # 발신번호
            }
            
            # 실제 SMS 발송 (예: Twilio, NHN Toast SMS 등)
            # success = await sms_service.send_sms(sms_data)
            success = True  # 임시로 성공으로 설정
            
            if success:
                logger.info(f"SMS 알림 발송 성공: {normalized_phone} ({notification_type})")
                return {
                    'channel': 'sms',
                    'success': True,
                    'recipient': normalized_phone,
                    'message': 'SMS 발송 성공'
                }
            else:
                logger.warning(f"SMS 알림 발송 실패: {normalized_phone}")
                return {
                    'channel': 'sms',
                    'success': False,
                    'recipient': normalized_phone,
                    'message': 'SMS 발송 실패'
                }
                
        except Exception as e:
            logger.error(f"SMS 알림 발송 중 오류: {str(e)}")
            return {
                'channel': 'sms',
                'success': False,
                'recipient': phone,
                'message': f'SMS 발송 오류: {str(e)}'
            }
    
    async def _send_push_notification(
        self, 
        customer_id: str, 
        title: str, 
        message: str, 
        order: Order,
        notification_type: str
    ) -> Dict:
        """푸시 알림 발송"""
        try:
            push_data = {
                'user_id': customer_id,
                'title': title,
                'body': message,
                'data': {
                    'order_id': str(order.id),
                    'order_number': order.order_number,
                    'notification_type': notification_type,
                    'deep_link': f'/orders/{order.id}'
                }
            }
            
            # 실제 푸시 알림 발송 (예: Firebase FCM, AWS SNS 등)
            # success = await push_service.send_push(push_data)
            success = True  # 임시로 성공으로 설정
            
            if success:
                logger.info(f"푸시 알림 발송 성공: {customer_id} ({notification_type})")
                return {
                    'channel': 'push',
                    'success': True,
                    'recipient': customer_id,
                    'message': '푸시 알림 발송 성공'
                }
            else:
                logger.warning(f"푸시 알림 발송 실패: {customer_id}")
                return {
                    'channel': 'push',
                    'success': False,
                    'recipient': customer_id,
                    'message': '푸시 알림 발송 실패'
                }
                
        except Exception as e:
            logger.error(f"푸시 알림 발송 중 오류: {str(e)}")
            return {
                'channel': 'push',
                'success': False,
                'recipient': customer_id,
                'message': f'푸시 알림 발송 오류: {str(e)}'
            }
    
    async def _generate_email_html(self, message: str, order: Order, notification_type: str) -> str:
        """이메일 HTML 템플릿 생성"""
        try:
            # 간단한 HTML 템플릿
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>주문 알림</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ background-color: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .content {{ line-height: 1.6; }}
                    .order-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>주문 알림</h2>
                    </div>
                    <div class="content">
                        <p>{message}</p>
                        <div class="order-info">
                            <strong>주문 정보</strong><br>
                            주문번호: {order.order_number}<br>
                            주문일자: {order.order_date.strftime('%Y-%m-%d %H:%M') if order.order_date else 'N/A'}<br>
                            총 금액: {order.total_amount:,}원
                        </div>
                    </div>
                    <div class="footer">
                        <p>본 메일은 자동 발송 메일입니다.</p>
                        <p>궁금한 사항이 있으시면 고객센터로 문의해 주세요.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_template
            
        except Exception as e:
            logger.error(f"이메일 HTML 생성 중 오류: {str(e)}")
            return f"<html><body><p>{message}</p></body></html>"
    
    def _normalize_phone_number(self, phone: str) -> Optional[str]:
        """전화번호 정규화"""
        if not phone:
            return None
        
        # 숫자만 추출
        import re
        numbers = re.sub(r'[^\d]', '', phone)
        
        # 한국 전화번호 형식 확인
        if len(numbers) == 11 and numbers.startswith('010'):
            return numbers
        elif len(numbers) == 10:
            return '0' + numbers
        
        return None
    
    async def _save_notification_log(
        self, 
        dropshipping_order: DropshippingOrder, 
        notification_type: str,
        results: List[Dict],
        message_data: Dict
    ):
        """알림 로그 저장"""
        try:
            # 실제로는 별도의 알림 로그 테이블에 저장
            # 여기서는 드롭쉬핑 주문 로그에 저장
            from app.models.order_core import DropshippingOrderLog
            
            log_data = {
                'notification_type': notification_type,
                'results': results,
                'message_data': message_data,
                'sent_at': datetime.utcnow().isoformat()
            }
            
            log = DropshippingOrderLog(
                dropshipping_order_id=dropshipping_order.id,
                action=f'notify_{notification_type}',
                success=any(r.get('success', False) for r in results),
                response_data=log_data,
                processing_time_ms=0
            )
            
            self.db.add(log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"알림 로그 저장 중 오류: {str(e)}")
            self.db.rollback()
    
    async def send_bulk_notifications(self, notification_requests: List[Dict]) -> Dict:
        """대량 알림 발송"""
        try:
            results = {
                'total_requests': len(notification_requests),
                'successful_notifications': 0,
                'failed_notifications': 0,
                'results': []
            }
            
            for request in notification_requests:
                try:
                    dropshipping_order_id = request.get('dropshipping_order_id')
                    notification_type = request.get('notification_type')  
                    additional_data = request.get('additional_data')
                    
                    dropshipping_order = self.db.query(DropshippingOrder).filter(
                        DropshippingOrder.id == dropshipping_order_id
                    ).first()
                    
                    if not dropshipping_order:
                        results['results'].append({
                            'dropshipping_order_id': dropshipping_order_id,
                            'success': False,
                            'message': '드롭쉬핑 주문을 찾을 수 없습니다'
                        })
                        results['failed_notifications'] += 1
                        continue
                    
                    result = await self.notify_order_status_change(
                        dropshipping_order,
                        notification_type,
                        additional_data
                    )
                    
                    results['results'].append({
                        'dropshipping_order_id': dropshipping_order_id,
                        'success': result['success'],
                        'message': result['message']
                    })
                    
                    if result['success']:
                        results['successful_notifications'] += 1
                    else:
                        results['failed_notifications'] += 1
                    
                    # API 호출 간격 조절
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"개별 알림 발송 중 오류: {str(e)}")
                    results['results'].append({
                        'dropshipping_order_id': request.get('dropshipping_order_id'),
                        'success': False,
                        'message': str(e)
                    })
                    results['failed_notifications'] += 1
            
            return {
                'success': True,
                'results': results,
                'processed_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"대량 알림 발송 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'대량 알림 발송 중 오류 발생: {str(e)}'
            }
    
    async def schedule_delivery_reminders(self) -> Dict:
        """배송 예정 알림 스케줄링"""
        try:
            tomorrow = datetime.utcnow() + timedelta(days=1)
            
            # 내일 배송 예정인 주문들 조회
            upcoming_deliveries = (
                self.db.query(DropshippingOrder)
                .filter(
                    and_(
                        DropshippingOrder.status == SupplierOrderStatus.SHIPPED,
                        DropshippingOrder.estimated_delivery_date >= tomorrow.date(),
                        DropshippingOrder.estimated_delivery_date <= (tomorrow + timedelta(days=1)).date()
                    )
                )
                .all()
            )
            
            reminder_results = []
            
            for order in upcoming_deliveries:
                try:
                    # 배송 예정 알림 발송
                    notification_data = {
                        'estimated_delivery': order.estimated_delivery_date.strftime('%Y-%m-%d'),
                        'tracking_number': order.supplier_tracking_number
                    }
                    
                    result = await self.notify_order_status_change(
                        order,
                        'delivery_reminder',
                        notification_data
                    )
                    
                    reminder_results.append({
                        'order_id': str(order.order_id),
                        'order_number': order.order.order_number,
                        'success': result['success'],
                        'message': result['message']
                    })
                    
                except Exception as e:
                    logger.error(f"배송 예정 알림 발송 중 오류 ({order.order_id}): {str(e)}")
                    reminder_results.append({
                        'order_id': str(order.order_id),
                        'success': False,
                        'message': str(e)
                    })
            
            successful_reminders = sum(1 for r in reminder_results if r['success'])
            
            return {
                'success': True,
                'total_reminders': len(upcoming_deliveries),
                'successful_reminders': successful_reminders,
                'failed_reminders': len(upcoming_deliveries) - successful_reminders,
                'results': reminder_results,
                'scheduled_for': tomorrow.date().isoformat()
            }
            
        except Exception as e:
            logger.error(f"배송 예정 알림 스케줄링 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 예정 알림 스케줄링 중 오류 발생: {str(e)}'
            }
    
    async def get_notification_preferences(self, customer_id: str) -> Dict:
        """고객 알림 설정 조회"""
        try:
            # 실제로는 고객 알림 설정 테이블에서 조회
            # 여기서는 기본 설정을 반환
            default_preferences = {
                'email_notifications': True,
                'sms_notifications': True,
                'push_notifications': True,
                'notification_types': {
                    'order_confirmed': True,
                    'order_shipped': True,
                    'delivery_delay': True,
                    'delivery_completed': True,
                    'order_cancelled': True,
                    'out_of_stock': True
                },
                'quiet_hours': {
                    'enabled': True,
                    'start_time': '22:00',
                    'end_time': '08:00'
                }
            }
            
            return {
                'success': True,
                'customer_id': customer_id,
                'preferences': default_preferences
            }
            
        except Exception as e:
            logger.error(f"알림 설정 조회 중 오류: {str(e)}")
            return {
                'success': False,
                'message': f'알림 설정 조회 중 오류 발생: {str(e)}'
            }
    
    async def get_notification_statistics(self, days: int = 7) -> Dict:
        """알림 발송 통계"""
        try:
            from app.models.order_core import DropshippingOrderLog
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # 알림 로그 조회
            notification_logs = (
                self.db.query(DropshippingOrderLog)
                .filter(
                    and_(
                        DropshippingOrderLog.action.like('notify_%'),
                        DropshippingOrderLog.created_at >= start_date
                    )
                )
                .all()
            )
            
            # 통계 계산
            total_notifications = len(notification_logs)
            successful_notifications = sum(1 for log in notification_logs if log.success)
            failed_notifications = total_notifications - successful_notifications
            
            # 알림 타입별 통계
            type_stats = {}
            for log in notification_logs:
                action = log.action.replace('notify_', '')
                if action not in type_stats:
                    type_stats[action] = {'total': 0, 'success': 0, 'failed': 0}
                
                type_stats[action]['total'] += 1
                if log.success:
                    type_stats[action]['success'] += 1
                else:
                    type_stats[action]['failed'] += 1
            
            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                },
                'summary': {
                    'total_notifications': total_notifications,
                    'successful_notifications': successful_notifications,
                    'failed_notifications': failed_notifications,
                    'success_rate': (successful_notifications / total_notifications * 100) if total_notifications > 0 else 0
                },
                'type_statistics': type_stats,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"알림 통계 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'알림 통계 조회 중 오류 발생: {str(e)}'
            }