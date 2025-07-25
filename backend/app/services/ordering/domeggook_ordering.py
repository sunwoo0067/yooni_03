"""
도매매(도매꾹) 발주 서비스
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.order import DropshippingOrder, OrderItem
from app.models.wholesaler import Wholesaler
from app.services.ordering.base_ordering import BaseOrderingService

logger = logging.getLogger(__name__)


class DomeggookOrderingService(BaseOrderingService):
    """도매매(도매꾹) 발주 서비스"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.base_url = "https://openapi.domeggook.com"
        self.api_version = "1.0"
    
    async def submit_order(self, dropshipping_order: DropshippingOrder, supplier: Wholesaler) -> Dict:
        """
        도매매에 주문 제출
        
        Args:
            dropshipping_order: 드롭쉬핑 주문
            supplier: 공급업체 정보
            
        Returns:
            Dict: 발주 결과
        """
        try:
            # API 인증 정보 추출
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            # 주문 데이터 구성
            order_data = await self._build_order_data(dropshipping_order)
            
            # 도매매 API 호출
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/api/order/submit",
                params={
                    'api_key': credentials['api_key'],
                    'version': self.api_version
                },
                data=order_data
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('result') == 'success':
                    order_info = result_data.get('data', {})
                    
                    return {
                        'success': True,
                        'message': '주문이 성공적으로 제출되었습니다',
                        'supplier_order_id': order_info.get('order_id'),
                        'order_number': order_info.get('order_number'),
                        'status': 'submitted',
                        'estimated_delivery_date': order_info.get('estimated_delivery'),
                        'response_data': result_data
                    }
                else:
                    error_message = result_data.get('message', 'Unknown error')
                    return {
                        'success': False,
                        'message': f'도매매 주문 실패: {error_message}',
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"도매매 주문 제출 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 제출 중 오류 발생: {str(e)}'
            }
    
    async def check_order_status(self, supplier_order_id: str, supplier: Wholesaler) -> Dict:
        """
        도매매 주문 상태 확인
        
        Args:
            supplier_order_id: 공급업체 주문 ID
            supplier: 공급업체 정보
            
        Returns:
            Dict: 상태 확인 결과
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/api/order/status",
                params={
                    'api_key': credentials['api_key'],
                    'version': self.api_version,
                    'order_id': supplier_order_id
                }
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('result') == 'success':
                    order_info = result_data.get('data', {})
                    
                    # 도매매 상태를 표준 상태로 매핑
                    domeggook_status = order_info.get('status', '')
                    standard_status = self._map_status_to_standard(domeggook_status)
                    
                    return {
                        'success': True,
                        'supplier_order_id': supplier_order_id,
                        'status': standard_status,
                        'original_status': domeggook_status,
                        'tracking_number': order_info.get('tracking_number'),
                        'carrier': order_info.get('carrier'),
                        'shipped_date': order_info.get('shipped_date'),
                        'estimated_delivery': order_info.get('estimated_delivery'),
                        'order_items': order_info.get('items', []),
                        'response_data': result_data
                    }
                else:
                    return {
                        'success': False,
                        'message': f'상태 조회 실패: {result_data.get("message", "Unknown error")}',
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"도매매 주문 상태 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'상태 확인 중 오류 발생: {str(e)}'
            }
    
    async def cancel_order(self, supplier_order_id: str, supplier: Wholesaler, reason: str = "") -> Dict:
        """
        도매매 주문 취소
        
        Args:
            supplier_order_id: 공급업체 주문 ID
            supplier: 공급업체 정보
            reason: 취소 사유
            
        Returns:
            Dict: 취소 결과
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            cancel_data = {
                'order_id': supplier_order_id,
                'reason': reason or '고객 요청',
                'cancel_type': 'full'  # 전체 취소
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/api/order/cancel",
                params={
                    'api_key': credentials['api_key'],
                    'version': self.api_version
                },
                data=cancel_data
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('result') == 'success':
                    return {
                        'success': True,
                        'message': '주문이 성공적으로 취소되었습니다',
                        'supplier_order_id': supplier_order_id,
                        'cancel_date': datetime.utcnow().isoformat(),
                        'response_data': result_data
                    }
                else:
                    return {
                        'success': False,
                        'message': f'주문 취소 실패: {result_data.get("message", "Unknown error")}',
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"도매매 주문 취소 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 취소 중 오류 발생: {str(e)}'
            }
    
    async def get_tracking_info(self, tracking_number: str, supplier: Wholesaler) -> Dict:
        """
        도매매 배송 추적 정보 조회
        
        Args:
            tracking_number: 배송 추적 번호
            supplier: 공급업체 정보
            
        Returns:
            Dict: 추적 정보
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/api/delivery/track",
                params={
                    'api_key': credentials['api_key'],
                    'version': self.api_version,
                    'tracking_number': tracking_number
                }
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('result') == 'success':
                    tracking_data = result_data.get('data', {})
                    
                    return {
                        'success': True,
                        'tracking_number': tracking_number,
                        'carrier': tracking_data.get('carrier', ''),
                        'current_status': tracking_data.get('status', ''),
                        'current_location': tracking_data.get('current_location', ''),
                        'estimated_delivery': tracking_data.get('estimated_delivery', ''),
                        'tracking_events': tracking_data.get('events', []),
                        'last_updated': tracking_data.get('last_updated', ''),
                        'response_data': result_data
                    }
                else:
                    return {
                        'success': False,
                        'message': f'추적 정보 조회 실패: {result_data.get("message", "Unknown error")}',
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"도매매 배송 추적 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 추적 중 오류 발생: {str(e)}'
            }
    
    async def check_product_availability(self, product_ids: List[str], supplier: Wholesaler) -> Dict:
        """
        도매매 상품 재고 확인
        
        Args:  
            product_ids: 상품 ID 리스트
            supplier: 공급업체 정보
            
        Returns:
            Dict: 재고 확인 결과
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            availability_results = {}
            
            # 개별 상품별로 재고 확인 (도매매는 일괄 조회 미지원)
            for product_id in product_ids:
                try:
                    response = await self._make_api_request(
                        method='GET',
                        url=f"{self.base_url}/api/product/stock",
                        params={
                            'api_key': credentials['api_key'],
                            'version': self.api_version,
                            'product_id': product_id
                        }
                    )
                    
                    if response and response.status == 200:
                        result_data = await response.json()
                        
                        if result_data.get('result') == 'success':
                            stock_data = result_data.get('data', {})
                            
                            availability_results[product_id] = {
                                'available': stock_data.get('stock_quantity', 0) > 0,
                                'stock_quantity': stock_data.get('stock_quantity', 0),
                                'price': stock_data.get('price', 0),
                                'status': stock_data.get('status', ''),
                                'last_updated': datetime.utcnow().isoformat()
                            }
                        else:
                            availability_results[product_id] = {
                                'available': False,
                                'error': result_data.get('message', 'Unknown error')
                            }
                    else:
                        availability_results[product_id] = {
                            'available': False,
                            'error': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                        }
                    
                    # Rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    availability_results[product_id] = {
                        'available': False,
                        'error': str(e)
                    }
            
            return {
                'success': True,
                'results': availability_results,
                'checked_count': len(product_ids),
                'available_count': sum(1 for result in availability_results.values() if result.get('available', False))
            }
            
        except Exception as e:
            logger.error(f"도매매 재고 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'재고 확인 중 오류 발생: {str(e)}'
            }
    
    async def _build_order_data(self, dropshipping_order: DropshippingOrder) -> Dict:
        """도매매 주문 데이터 구성"""
        order = dropshipping_order.order
        
        # 주문 상품 정보
        order_items = []
        for item in order.order_items:
            order_items.append({
                'product_id': item.platform_item_id or item.sku,  # 도매매 상품 ID
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'option_info': item.product_attributes or {}
            })
        
        # 배송지 정보
        shipping_address = {
            'recipient_name': order.shipping_name or order.customer_name,
            'phone': order.customer_phone or '',
            'address1': order.shipping_address1,
            'address2': order.shipping_address2 or '',
            'city': order.shipping_city,
            'state': order.shipping_state or '',
            'postal_code': order.shipping_postal_code or '',
            'country': order.shipping_country or 'KR'
        }
        
        # 주문자 정보
        orderer_info = {
            'name': order.customer_name,
            'email': order.customer_email or '',
            'phone': order.customer_phone or ''
        }
        
        order_data = {
            'order_number': order.order_number,
            'order_date': order.order_date.isoformat() if order.order_date else datetime.utcnow().isoformat(),
            'orderer': orderer_info,
            'shipping_address': shipping_address,
            'items': order_items,
            'total_amount': float(dropshipping_order.supplier_price),
            'shipping_cost': float(order.shipping_cost),
            'payment_method': 'credit',  # 도매매는 신용결제
            'delivery_request': order.customer_notes or '',
            'urgent_order': False,  # 일반 주문
            'partial_delivery_allowed': True  # 부분 배송 허용
        }
        
        return order_data
    
    def _map_status_to_standard(self, domeggook_status: str) -> str:
        """도매매 상태를 표준 상태로 매핑"""
        status_mapping = {
            'order_received': 'submitted',      # 주문 접수
            'order_confirmed': 'confirmed',     # 주문 확인
            'preparing': 'processing',          # 상품 준비중
            'shipped': 'shipped',               # 배송 시작
            'delivered': 'delivered',           # 배송 완료
            'cancelled': 'cancelled',           # 주문 취소
            'out_of_stock': 'out_of_stock',     # 품절
            'order_failed': 'failed'            # 주문 실패
        }
        
        return status_mapping.get(domeggook_status, 'pending')
    
    def _extract_credentials(self, supplier: Wholesaler) -> Optional[Dict]:
        """공급업체에서 API 인증 정보 추출"""
        try:
            if supplier.api_credentials:
                return {
                    'api_key': supplier.api_credentials.get('api_key', ''),
                    'secret_key': supplier.api_credentials.get('secret_key', ''),
                    'user_id': supplier.api_credentials.get('user_id', '')
                }
        except Exception as e:
            logger.error(f"API 인증 정보 추출 실패: {str(e)}")
        
        return None
    
    async def get_order_history(self, supplier: Wholesaler, days: int = 30) -> Dict:
        """
        도매매 주문 내역 조회
        
        Args:
            supplier: 공급업체 정보
            days: 조회 기간 (일)
            
        Returns:
            Dict: 주문 내역
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/api/order/history",
                params={
                    'api_key': credentials['api_key'],
                    'version': self.api_version,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'page': 1,
                    'limit': 100
                }
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('result') == 'success':
                    orders = result_data.get('data', {}).get('orders', [])
                    
                    return {
                        'success': True,
                        'orders': orders,
                        'total_count': result_data.get('data', {}).get('total_count', 0),
                        'period': {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat()
                        }
                    }
                else:
                    return {
                        'success': False,
                        'message': f'주문 내역 조회 실패: {result_data.get("message", "Unknown error")}'
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"도매매 주문 내역 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 내역 조회 중 오류 발생: {str(e)}'
            }