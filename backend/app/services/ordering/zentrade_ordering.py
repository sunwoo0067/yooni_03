"""
젠트레이드 발주 서비스
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.order import DropshippingOrder, OrderItem
from app.models.wholesaler import Wholesaler
from app.services.ordering.base_ordering import BaseOrderingService

logger = logging.getLogger(__name__)


class ZentradeOrderingService(BaseOrderingService):
    """젠트레이드 발주 서비스"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.base_url = "https://api.zentrade.co.kr"
        self.api_version = "v1"
    
    async def submit_order(self, dropshipping_order: DropshippingOrder, supplier: Wholesaler) -> Dict:
        """
        젠트레이드에 주문 제출
        
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
            
            # 주문 데이터 검증
            validation = self._validate_order_data(order_data)
            if not validation['valid']:
                return {
                    'success': False,
                    'message': f'주문 데이터 검증 실패: {", ".join(validation["errors"])}'
                }
            
            # 젠트레이드 API 호출
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/{self.api_version}/orders/create",
                data=order_data,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    order_info = result_data.get('data', {})
                    
                    return {
                        'success': True,
                        'message': '주문이 성공적으로 제출되었습니다',
                        'supplier_order_id': order_info.get('order_id'),
                        'order_number': order_info.get('order_no'),
                        'status': 'submitted',
                        'estimated_delivery_date': order_info.get('delivery_date'),
                        'tracking_info': order_info.get('tracking_info', {}),
                        'response_data': result_data
                    }
                else:
                    error_message = result_data.get('message', 'Unknown error')
                    return {
                        'success': False,
                        'message': f'젠트레이드 주문 실패: {error_message}',
                        'error_code': result_data.get('error_code'),
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"젠트레이드 주문 제출 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 제출 중 오류 발생: {str(e)}'
            }
    
    async def check_order_status(self, supplier_order_id: str, supplier: Wholesaler) -> Dict:
        """
        젠트레이드 주문 상태 확인
        
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
            
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/{self.api_version}/orders/{supplier_order_id}/status",
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    order_info = result_data.get('data', {})
                    
                    # 젠트레이드 상태를 표준 상태로 매핑
                    zentrade_status = order_info.get('status', '')
                    standard_status = self._map_status_to_standard(zentrade_status)
                    
                    return {
                        'success': True,
                        'supplier_order_id': supplier_order_id,
                        'status': standard_status,
                        'original_status': zentrade_status,
                        'tracking_number': order_info.get('tracking_no'),
                        'carrier': order_info.get('delivery_company'),
                        'shipped_date': order_info.get('ship_date'),
                        'estimated_delivery': order_info.get('delivery_date'),
                        'order_items': order_info.get('items', []),
                        'progress_info': order_info.get('progress', {}),
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
            logger.error(f"젠트레이드 주문 상태 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'상태 확인 중 오류 발생: {str(e)}'
            }
    
    async def cancel_order(self, supplier_order_id: str, supplier: Wholesaler, reason: str = "") -> Dict:
        """
        젠트레이드 주문 취소
        
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
            
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            cancel_data = {
                'cancel_reason': reason or '고객 요청',
                'cancel_type': 'full',
                'request_time': datetime.utcnow().isoformat()
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/{self.api_version}/orders/{supplier_order_id}/cancel",
                data=cancel_data,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    cancel_info = result_data.get('data', {})
                    
                    return {
                        'success': True,
                        'message': '주문이 성공적으로 취소되었습니다',
                        'supplier_order_id': supplier_order_id,
                        'cancel_date': cancel_info.get('cancel_date', datetime.utcnow().isoformat()),
                        'cancel_status': cancel_info.get('cancel_status'),
                        'refund_info': cancel_info.get('refund_info', {}),
                        'response_data': result_data
                    }
                else:
                    return {
                        'success': False,
                        'message': f'주문 취소 실패: {result_data.get("message", "Unknown error")}',
                        'error_code': result_data.get('error_code'),
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"젠트레이드 주문 취소 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 취소 중 오류 발생: {str(e)}'
            }
    
    async def get_tracking_info(self, tracking_number: str, supplier: Wholesaler) -> Dict:
        """
        젠트레이드 배송 추적 정보 조회
        
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
            
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            params = {
                'tracking_no': tracking_number
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/{self.api_version}/delivery/tracking",
                params=params,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    tracking_data = result_data.get('data', {})
                    
                    return {
                        'success': True,
                        'tracking_number': tracking_number,
                        'carrier': tracking_data.get('delivery_company', ''),
                        'current_status': tracking_data.get('current_status', ''),
                        'current_location': tracking_data.get('current_location', ''),
                        'estimated_delivery': tracking_data.get('estimated_date', ''),
                        'tracking_events': tracking_data.get('tracking_history', []),
                        'delivery_info': tracking_data.get('delivery_info', {}),
                        'last_updated': tracking_data.get('last_update', ''),
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
            logger.error(f"젠트레이드 배송 추적 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 추적 중 오류 발생: {str(e)}'
            }
    
    async def check_product_availability(self, product_ids: List[str], supplier: Wholesaler) -> Dict:
        """
        젠트레이드 상품 재고 확인
        
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
            
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            # 빈 리스트인 경우 (health check용)
            if not product_ids:
                return {
                    'success': True,
                    'results': {},
                    'checked_count': 0,
                    'available_count': 0
                }
            
            # 젠트레이드는 일괄 재고 조회 지원
            stock_data = {
                'product_ids': product_ids,
                'include_price': True,
                'include_options': False
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/{self.api_version}/products/stock-check",
                data=stock_data,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    products = result_data.get('data', {}).get('products', [])
                    
                    availability_results = {}
                    for product in products:
                        product_id = product.get('product_id')
                        if product_id:
                            availability_results[product_id] = {
                                'available': product.get('in_stock', False) and product.get('stock_qty', 0) > 0,
                                'stock_quantity': product.get('stock_qty', 0),
                                'price': product.get('wholesale_price', 0),
                                'status': product.get('status', ''),
                                'supplier_code': product.get('supplier_code', ''),
                                'last_updated': product.get('updated_at', datetime.utcnow().isoformat())
                            }
                    
                    # 요청했지만 응답에 없는 상품들 처리
                    for product_id in product_ids:
                        if product_id not in availability_results:
                            availability_results[product_id] = {
                                'available': False,
                                'error': '상품 정보를 찾을 수 없습니다'
                            }
                    
                    return {
                        'success': True,
                        'results': availability_results,
                        'checked_count': len(product_ids),
                        'available_count': sum(1 for result in availability_results.values() if result.get('available', False)),
                        'check_time': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'message': f'재고 조회 실패: {result_data.get("message", "Unknown error")}',
                        'response_data': result_data
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"젠트레이드 재고 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'재고 확인 중 오류 발생: {str(e)}'
            }
    
    async def _build_order_data(self, dropshipping_order: DropshippingOrder) -> Dict:
        """젠트레이드 주문 데이터 구성"""
        order = dropshipping_order.order
        
        # 주문 상품 정보
        order_items = []
        for item in order.order_items:
            order_items.append({
                'product_code': item.platform_item_id or item.sku,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
                'options': self._format_zentrade_options(item.product_attributes),
                'memo': ''
            })
        
        # 배송지 정보 (젠트레이드 형식)
        delivery_info = {
            'recv_name': order.shipping_name or order.customer_name,
            'recv_phone': self._format_phone_number(order.customer_phone or ''),
            'recv_zipcode': order.shipping_postal_code or '',
            'recv_addr1': order.shipping_address1 or '',
            'recv_addr2': order.shipping_address2 or '',
            'delivery_memo': order.customer_notes or '',
            'delivery_method': 'standard'
        }
        
        # 주문자 정보
        order_info = {
            'order_name': order.customer_name,
            'order_phone': self._format_phone_number(order.customer_phone or ''),
            'order_email': order.customer_email or ''
        }
        
        order_data = {
            'partner_order_no': order.order_number,  # 파트너사 주문번호
            'order_date': order.order_date.strftime('%Y-%m-%d %H:%M:%S') if order.order_date else datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'order_info': order_info,
            'delivery_info': delivery_info,
            'items': order_items,
            'payment_info': {
                'total_product_price': float(dropshipping_order.supplier_price),
                'delivery_price': float(order.shipping_cost),
                'total_price': float(dropshipping_order.supplier_price) + float(order.shipping_cost),
                'payment_method': 'prepaid'  # 선불결제
            },
            'delivery_option': {
                'fast_delivery': False,  # 빠른배송 여부
                'partial_delivery': True,  # 부분배송 허용
                'safety_delivery': False  # 안전배송 여부
            },
            'memo': order.internal_notes or ''
        }
        
        return order_data
    
    def _format_zentrade_options(self, product_attributes: Optional[Dict]) -> List[Dict]:
        """젠트레이드용 옵션 형식"""
        if not product_attributes or not isinstance(product_attributes, dict):
            return []
        
        options = []
        for key, value in product_attributes.items():
            options.append({
                'option_name': str(key),
                'option_value': str(value)
            })
        
        return options
    
    def _map_status_to_standard(self, zentrade_status: str) -> str:
        """젠트레이드 상태를 표준 상태로 매핑"""
        status_mapping = {
            'order_accept': 'submitted',        # 주문 접수
            'order_confirm': 'confirmed',       # 주문 확인
            'product_prepare': 'processing',    # 상품 준비중
            'delivery_prepare': 'processing',   # 출고 준비
            'delivery_start': 'shipped',        # 배송 시작
            'delivery_complete': 'delivered',   # 배송 완료
            'order_cancel': 'cancelled',        # 주문 취소
            'stock_shortage': 'out_of_stock',   # 재고 부족
            'order_fail': 'failed',             # 주문 실패
            'return_complete': 'cancelled'      # 반품 완료
        }
        
        return status_mapping.get(zentrade_status, 'pending')
    
    def _extract_credentials(self, supplier: Wholesaler) -> Optional[Dict]:
        """공급업체에서 API 인증 정보 추출"""
        try:
            if supplier.api_credentials:
                return {
                    'api_key': supplier.api_credentials.get('api_key', ''),
                    'secret_key': supplier.api_credentials.get('secret_key', ''),
                    'user_id': supplier.api_credentials.get('user_id', ''),
                    'partner_code': supplier.api_credentials.get('partner_code', '')
                }
        except Exception as e:
            logger.error(f"API 인증 정보 추출 실패: {str(e)}")
        
        return None
    
    async def get_delivery_companies(self, supplier: Wholesaler) -> Dict:
        """
        젠트레이드 배송업체 목록 조회
        
        Args:
            supplier: 공급업체 정보
            
        Returns:
            Dict: 배송업체 목록
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/{self.api_version}/delivery/companies",
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    companies = result_data.get('data', {}).get('companies', [])
                    
                    return {
                        'success': True,
                        'companies': companies,
                        'total_count': len(companies)
                    }
                else:
                    return {
                        'success': False,
                        'message': f'배송업체 조회 실패: {result_data.get("message", "Unknown error")}'
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"젠트레이드 배송업체 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송업체 조회 중 오류 발생: {str(e)}'
            }
    
    async def get_order_statistics(self, supplier: Wholesaler, period: str = 'month') -> Dict:
        """
        젠트레이드 주문 통계 조회
        
        Args:
            supplier: 공급업체 정보
            period: 조회 기간 ('week', 'month', 'quarter')
            
        Returns:
            Dict: 주문 통계
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            headers = {
                'X-API-Key': credentials['api_key'],
                'X-Secret-Key': credentials['secret_key'],
                'X-User-ID': credentials['user_id']
            }
            
            params = {
                'period': period,
                'timezone': 'Asia/Seoul'
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/{self.api_version}/orders/statistics",
                params=params,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                if result_data.get('success', False):
                    stats = result_data.get('data', {})
                    
                    return {
                        'success': True,
                        'period': period,
                        'statistics': {
                            'total_orders': stats.get('total_orders', 0),
                            'completed_orders': stats.get('completed_orders', 0),
                            'cancelled_orders': stats.get('cancelled_orders', 0),
                            'total_amount': stats.get('total_amount', 0),
                            'success_rate': stats.get('success_rate', 0),
                            'avg_delivery_days': stats.get('avg_delivery_days', 0)
                        },
                        'generated_at': datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        'success': False,
                        'message': f'통계 조회 실패: {result_data.get("message", "Unknown error")}'
                    }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"젠트레이드 주문 통계 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 통계 조회 중 오류 발생: {str(e)}'
            }