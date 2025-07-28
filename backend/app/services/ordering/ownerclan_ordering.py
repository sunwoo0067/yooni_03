"""
오너클랜 발주 서비스
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.order_core import DropshippingOrder, OrderItem
from app.models.wholesaler import Wholesaler
from app.services.ordering.base_ordering import BaseOrderingService

logger = logging.getLogger(__name__)


class OwnerClanOrderingService(BaseOrderingService):
    """오너클랜 발주 서비스"""
    
    def __init__(self, db: Session):
        super().__init__(db)
        self.base_url = "https://api.ownerclan.com"
        self.api_version = "v2"
    
    async def submit_order(self, dropshipping_order: DropshippingOrder, supplier: Wholesaler) -> Dict:
        """
        오너클랜에 주문 제출
        
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
            
            # 오너클랜 API 호출
            headers = {
                'Authorization': f'Bearer {credentials["access_token"]}',
                'X-API-Version': self.api_version
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/orders",
                data=order_data,
                headers=headers
            )
            
            if response and response.status == 201:  # Created
                result_data = await response.json()
                
                return {
                    'success': True,
                    'message': '주문이 성공적으로 제출되었습니다',
                    'supplier_order_id': result_data.get('order_id'),
                    'order_number': result_data.get('order_number'),
                    'status': 'submitted',
                    'estimated_delivery_date': result_data.get('estimated_delivery_at'),
                    'total_amount': result_data.get('total_amount'),
                    'response_data': result_data
                }
            elif response and response.status == 400:
                error_data = await response.json()
                return {
                    'success': False,
                    'message': f'오너클랜 주문 실패: {error_data.get("message", "잘못된 요청")}',
                    'response_data': error_data
                }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 주문 제출 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 제출 중 오류 발생: {str(e)}'
            }
    
    async def check_order_status(self, supplier_order_id: str, supplier: Wholesaler) -> Dict:
        """
        오너클랜 주문 상태 확인
        
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
                'Authorization': f'Bearer {credentials["access_token"]}',
                'X-API-Version': self.api_version
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/orders/{supplier_order_id}",
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                # 오너클랜 상태를 표준 상태로 매핑
                ownerclan_status = result_data.get('status', '')
                standard_status = self._map_status_to_standard(ownerclan_status)
                
                return {
                    'success': True,
                    'supplier_order_id': supplier_order_id,
                    'status': standard_status,
                    'original_status': ownerclan_status,
                    'tracking_number': result_data.get('tracking_number'),
                    'carrier': result_data.get('shipping_company'),
                    'shipped_date': result_data.get('shipped_at'),
                    'estimated_delivery': result_data.get('estimated_delivery_at'),
                    'order_items': result_data.get('items', []),
                    'total_amount': result_data.get('total_amount'),
                    'response_data': result_data
                }
            elif response and response.status == 404:
                return {
                    'success': False,
                    'message': '주문을 찾을 수 없습니다'
                }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 주문 상태 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'상태 확인 중 오류 발생: {str(e)}'
            }
    
    async def cancel_order(self, supplier_order_id: str, supplier: Wholesaler, reason: str = "") -> Dict:
        """
        오너클랜 주문 취소
        
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
                'Authorization': f'Bearer {credentials["access_token"]}',
                'X-API-Version': self.api_version
            }
            
            cancel_data = {
                'reason': reason or '고객 요청',
                'cancel_type': 'full',
                'refund_method': 'auto'
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/orders/{supplier_order_id}/cancel",
                data=cancel_data,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                return {
                    'success': True,
                    'message': '주문이 성공적으로 취소되었습니다',
                    'supplier_order_id': supplier_order_id,
                    'cancel_date': result_data.get('cancelled_at', datetime.utcnow().isoformat()),
                    'refund_amount': result_data.get('refund_amount'),
                    'response_data': result_data
                }
            elif response and response.status == 400:
                error_data = await response.json()
                return {
                    'success': False,
                    'message': f'주문 취소 실패: {error_data.get("message", "취소할 수 없는 상태")}',
                    'response_data': error_data
                }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 주문 취소 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 취소 중 오류 발생: {str(e)}'
            }
    
    async def get_tracking_info(self, tracking_number: str, supplier: Wholesaler) -> Dict:
        """
        오너클랜 배송 추적 정보 조회
        
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
                'Authorization': f'Bearer {credentials["access_token"]}',
                'X-API-Version': self.api_version
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/shipping/track/{tracking_number}",
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                return {
                    'success': True,
                    'tracking_number': tracking_number,
                    'carrier': result_data.get('shipping_company', ''),
                    'current_status': result_data.get('status', ''),
                    'current_location': result_data.get('current_location', ''),
                    'estimated_delivery': result_data.get('estimated_delivery_at', ''),
                    'tracking_events': result_data.get('tracking_events', []),
                    'last_updated': result_data.get('last_updated_at', ''),
                    'response_data': result_data
                }
            elif response and response.status == 404:
                return {
                    'success': False,
                    'message': '추적 번호를 찾을 수 없습니다'
                }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 배송 추적 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'배송 추적 중 오류 발생: {str(e)}'
            }
    
    async def check_product_availability(self, product_ids: List[str], supplier: Wholesaler) -> Dict:
        """
        오너클랜 상품 재고 확인
        
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
                'Authorization': f'Bearer {credentials["access_token"]}',
                'X-API-Version': self.api_version
            }
            
            # 오너클랜은 일괄 재고 조회 지원
            if product_ids:
                params = {
                    'product_ids': ','.join(product_ids),
                    'include_stock': 'true',
                    'include_price': 'true'
                }
            else:
                # 빈 리스트인 경우 (health check용)
                return {
                    'success': True,
                    'results': {},
                    'checked_count': 0,
                    'available_count': 0
                }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/products/availability",
                params=params,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                products = result_data.get('products', [])
                
                availability_results = {}
                for product in products:
                    product_id = product.get('product_id')
                    if product_id:
                        availability_results[product_id] = {
                            'available': product.get('in_stock', False),
                            'stock_quantity': product.get('stock_quantity', 0),
                            'price': product.get('wholesale_price', 0),
                            'status': product.get('status', ''),
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
                    'available_count': sum(1 for result in availability_results.values() if result.get('available', False))
                }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 재고 확인 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'재고 확인 중 오류 발생: {str(e)}'
            }
    
    async def _build_order_data(self, dropshipping_order: DropshippingOrder) -> Dict:
        """오너클랜 주문 데이터 구성"""
        order = dropshipping_order.order
        
        # 주문 상품 정보
        order_items = []
        for item in order.order_items:
            order_items.append({
                'product_id': item.platform_item_id or item.sku,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'options': item.product_attributes or {},
                'notes': ''
            })
        
        # 배송지 정보
        shipping_address = {
            'name': order.shipping_name or order.customer_name,
            'phone': self._format_phone_number(order.customer_phone or ''),
            'address': self._format_ownerclan_address(order),
            'postal_code': order.shipping_postal_code or '',
            'delivery_notes': order.customer_notes or ''
        }
        
        # 주문자 정보
        orderer_info = {
            'name': order.customer_name,
            'email': order.customer_email or '',
            'phone': self._format_phone_number(order.customer_phone or '')
        }
        
        order_data = {
            'external_order_id': order.order_number,  # 외부 주문 번호
            'order_date': order.order_date.isoformat() if order.order_date else datetime.utcnow().isoformat(),
            'orderer': orderer_info,
            'shipping_address': shipping_address,
            'items': order_items,
            'payment': {
                'method': 'credit',
                'total_amount': float(dropshipping_order.supplier_price),
                'shipping_cost': float(order.shipping_cost)
            },
            'shipping': {
                'method': 'standard',
                'urgent': False,
                'partial_delivery_allowed': True
            },
            'notes': order.internal_notes or ''
        }
        
        return order_data
    
    def _format_ownerclan_address(self, order) -> str:
        """오너클랜용 주소 형식"""
        address_parts = []
        
        if order.shipping_address1:
            address_parts.append(order.shipping_address1)
        if order.shipping_address2:
            address_parts.append(order.shipping_address2)
        
        return ' '.join(address_parts)
    
    def _map_status_to_standard(self, ownerclan_status: str) -> str:
        """오너클랜 상태를 표준 상태로 매핑"""
        status_mapping = {
            'pending': 'submitted',         # 주문 대기
            'confirmed': 'confirmed',       # 주문 확인
            'preparing': 'processing',      # 상품 준비중
            'ready_to_ship': 'processing',  # 출고 준비
            'shipped': 'shipped',           # 배송 시작
            'delivered': 'delivered',       # 배송 완료
            'cancelled': 'cancelled',       # 주문 취소
            'out_of_stock': 'out_of_stock', # 품절
            'failed': 'failed',             # 주문 실패
            'refunded': 'cancelled'         # 환불 완료
        }
        
        return status_mapping.get(ownerclan_status, 'pending')
    
    def _extract_credentials(self, supplier: Wholesaler) -> Optional[Dict]:
        """공급업체에서 API 인증 정보 추출"""
        try:
            if supplier.api_credentials:
                return {
                    'access_token': supplier.api_credentials.get('access_token', ''),
                    'refresh_token': supplier.api_credentials.get('refresh_token', ''),
                    'client_id': supplier.api_credentials.get('client_id', ''),
                    'client_secret': supplier.api_credentials.get('client_secret', '')
                }
        except Exception as e:
            logger.error(f"API 인증 정보 추출 실패: {str(e)}")
        
        return None
    
    async def refresh_access_token(self, supplier: Wholesaler) -> Dict:
        """
        액세스 토큰 갱신
        
        Args:
            supplier: 공급업체 정보
            
        Returns:
            Dict: 토큰 갱신 결과
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials or not credentials.get('refresh_token'):
                return {
                    'success': False,
                    'message': '리프레시 토큰이 없습니다'
                }
            
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': credentials['refresh_token'],
                'client_id': credentials['client_id'],
                'client_secret': credentials['client_secret']
            }
            
            response = await self._make_api_request(
                method='POST',
                url=f"{self.base_url}/oauth/token",
                data=token_data
            )
            
            if response and response.status == 200:
                token_info = await response.json()
                
                # 새 토큰으로 업데이트
                new_credentials = credentials.copy()
                new_credentials['access_token'] = token_info.get('access_token')
                if token_info.get('refresh_token'):
                    new_credentials['refresh_token'] = token_info.get('refresh_token')
                
                # 데이터베이스 업데이트
                supplier.api_credentials = new_credentials
                self.db.commit()
                
                return {
                    'success': True,
                    'message': '토큰이 성공적으로 갱신되었습니다',
                    'expires_in': token_info.get('expires_in', 3600)
                }
            else:
                return {
                    'success': False,
                    'message': '토큰 갱신 실패'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 토큰 갱신 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'토큰 갱신 중 오류 발생: {str(e)}'
            }
    
    async def get_order_list(self, supplier: Wholesaler, days: int = 30) -> Dict:
        """
        오너클랜 주문 목록 조회
        
        Args:
            supplier: 공급업체 정보
            days: 조회 기간 (일)
            
        Returns:
            Dict: 주문 목록
        """
        try:
            credentials = self._extract_credentials(supplier)
            if not credentials:
                return {
                    'success': False,
                    'message': 'API 인증 정보가 없습니다'
                }
            
            headers = {
                'Authorization': f'Bearer {credentials["access_token"]}',
                'X-API-Version': self.api_version
            }
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            params = {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'page': 1,
                'per_page': 100,
                'sort': 'created_at:desc'
            }
            
            response = await self._make_api_request(
                method='GET',
                url=f"{self.base_url}/orders",
                params=params,
                headers=headers
            )
            
            if response and response.status == 200:
                result_data = await response.json()
                
                return {
                    'success': True,
                    'orders': result_data.get('data', []),
                    'total_count': result_data.get('total', 0),
                    'current_page': result_data.get('current_page', 1),
                    'total_pages': result_data.get('last_page', 1),
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    }
                }
            else:
                return {
                    'success': False,
                    'message': f'API 호출 실패: HTTP {response.status if response else "No Response"}'
                }
                
        except Exception as e:
            logger.error(f"오너클랜 주문 목록 조회 중 오류: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'주문 목록 조회 중 오료 발생: {str(e)}'
            }