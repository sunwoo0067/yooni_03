"""
1688 (Alibaba) API 커넥터
중국 알리바바 1688 플랫폼 연동을 위한 커넥터
"""
import json
import time
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import requests

from .base import SupplierConnectorBase
from ..models import SupplierProduct


class Alibaba1688Connector(SupplierConnectorBase):
    """
    1688 (Alibaba) API 커넥터
    
    주요 기능:
    - 제품 검색 및 상세정보 조회
    - 가격 및 재고 정보 조회
    - 공급업체 정보 조회
    - 주문 관리 (선택적)
    
    API 문서: https://open.1688.com/
    """
    
    # Connector metadata
    connector_name: str = "1688 (Alibaba) Connector"
    connector_version: str = "1.0.0"
    supported_operations: List[str] = [
        "fetch_products", "get_product_details", "get_product_price",
        "get_inventory", "sync_product_data", "search_suppliers"
    ]
    
    BASE_URL = "https://gw.open.1688.com/openapi"
    
    def __init__(self, supplier):
        super().__init__(supplier)
        credentials = self.credentials or {}
        self.app_key = credentials.get('app_key', '')
        self.app_secret = credentials.get('app_secret', '')
        self.access_token = credentials.get('access_token', '')
        
    def validate_credentials(self) -> Tuple[bool, Optional[str]]:
        """API 자격증명 유효성 검증"""
        try:
            # 간단한 API 호출로 자격증명 확인
            result = self._make_request(
                'param2/1/com.alibaba.account/alibaba.account.basic'
            )
            if result.get('success', False):
                return True, None
            else:
                error_msg = result.get('errorMessage', 'Unknown validation error')
                return False, error_msg
        except Exception as e:
            self.logger.error(f"Credential validation failed: {e}")
            return False, str(e)
    
    def test_connection(self) -> Tuple[bool, Optional[str]]:
        """연결 테스트"""
        try:
            # 기본 계정 정보 조회로 연결 테스트
            result = self._make_request(
                'param2/1/com.alibaba.account/alibaba.account.basic'
            )
            
            if result.get('success', False):
                return True, None
            else:
                error_msg = result.get('errorMessage', 'Unknown connection error')
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
            
    def test_connection_detailed(self) -> Dict[str, Any]:
        """상세 연결 테스트 (기존 메서드 유지)"""
        try:
            start_time = time.time()
            
            # 기본 계정 정보 조회로 연결 테스트
            result = self._make_request(
                'param2/1/com.alibaba.account/alibaba.account.basic'
            )
            
            response_time = time.time() - start_time
            
            if result.get('success', False):
                return {
                    'success': True,
                    'response_time': response_time,
                    'message': '1688 API 연결 성공',
                    'account_info': result.get('result', {})
                }
            else:
                return {
                    'success': False,
                    'response_time': response_time,
                    'error': result.get('errorMessage', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': '1688 API 연결 실패'
            }
    
    def fetch_products(self, **kwargs) -> List[Dict[str, Any]]:
        """제품 목록 조회"""
        try:
            search_text = kwargs.get('search_text', '')
            category_id = kwargs.get('category_id', '')
            page_size = kwargs.get('page_size', 20)
            page_index = kwargs.get('page_index', 1)
            
            # 1688 제품 검색 API 호출
            params = {
                'q': search_text,
                'categoryId': category_id,
                'pageSize': page_size,
                'pageIndex': page_index,
                'orderBy': 'default',  # default, priceAsc, priceDesc, creditAsc, creditDesc
            }
            
            result = self._make_request(
                'param2/1/com.alibaba.product/alibaba.product.search',
                params
            )
            
            if result.get('success', False):
                products = result.get('result', {}).get('products', [])
                return [self._normalize_product_data(product) for product in products]
            else:
                self.logger.error(f"Product fetch failed: {result.get('errorMessage')}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error fetching products: {e}")
            return []
    
    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """제품 상세정보 조회"""
        try:
            # 제품 상세정보 API 호출
            params = {'productId': product_id}
            
            result = self._make_request(
                'param2/1/com.alibaba.product/alibaba.product.get',
                params
            )
            
            if result.get('success', False):
                product = result.get('result', {})
                return self._normalize_product_details(product)
            else:
                self.logger.error(f"Product details fetch failed: {result.get('errorMessage')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching product details: {e}")
            return None
    
    def get_product_price(self, product_id: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """제품 가격 조회"""
        try:
            # 가격 조회 API 호출
            params = {
                'productId': product_id,
                'quantity': quantity
            }
            
            result = self._make_request(
                'param2/1/com.alibaba.product/alibaba.product.price.get',
                params
            )
            
            if result.get('success', False):
                price_info = result.get('result', {})
                return {
                    'product_id': product_id,
                    'quantity': quantity,
                    'unit_price': price_info.get('unitPrice', 0),
                    'currency': price_info.get('currency', 'CNY'),
                    'discount_price': price_info.get('discountPrice'),
                    'min_order_quantity': price_info.get('minOrderQuantity', 1),
                    'price_ranges': price_info.get('priceRanges', []),
                    'updated_at': datetime.now()
                }
            else:
                self.logger.error(f"Price fetch failed: {result.get('errorMessage')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching product price: {e}")
            return None
    
    def get_inventory(self, product_id: str) -> Optional[Dict[str, Any]]:
        """재고 정보 조회"""
        try:
            # 재고 조회 API 호출
            params = {'productId': product_id}
            
            result = self._make_request(
                'param2/1/com.alibaba.product/alibaba.product.stock.get',
                params
            )
            
            if result.get('success', False):
                stock_info = result.get('result', {})
                return {
                    'product_id': product_id,
                    'available_quantity': stock_info.get('availableQuantity', 0),
                    'total_quantity': stock_info.get('totalQuantity', 0),
                    'reserved_quantity': stock_info.get('reservedQuantity', 0),
                    'warehouse_info': stock_info.get('warehouseInfo', []),
                    'last_updated': datetime.now()
                }
            else:
                self.logger.error(f"Inventory fetch failed: {result.get('errorMessage')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching inventory: {e}")
            return None
    
    def fetch_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Base abstract method implementation"""
        return self.get_product_details(product_id)
    
    def fetch_inventory(self, product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """재고 정보 일괄 조회"""
        inventory_data = {}
        
        if product_ids is None:
            return inventory_data
        
        for product_id in product_ids:
            try:
                inventory = self.get_inventory(product_id)
                if inventory:
                    inventory_data[product_id] = inventory
                # Rate limiting
                time.sleep(0.2)
            except Exception as e:
                self.logger.error(f"Error fetching inventory for {product_id}: {e}")
                inventory_data[product_id] = {'error': str(e)}
        
        return inventory_data
    
    def fetch_pricing(self, product_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """가격 정보 일괄 조회"""
        pricing_data = {}
        
        if product_ids is None:
            return pricing_data
        
        for product_id in product_ids:
            try:
                price = self.get_product_price(product_id)
                if price:
                    pricing_data[product_id] = price
                # Rate limiting
                time.sleep(0.2)
            except Exception as e:
                self.logger.error(f"Error fetching price for {product_id}: {e}")
                pricing_data[product_id] = {'error': str(e)}
        
        return pricing_data
    
    def _make_request(self, namespace: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """1688 API 요청 실행"""
        if params is None:
            params = {}
        
        # API 서명 생성
        timestamp = str(int(time.time() * 1000))
        
        # 기본 파라미터 추가
        api_params = {
            'access_token': self.access_token,
            'app_key': self.app_key,
            'timestamp': timestamp,
            'v': '1',
            'namespace': namespace,
            **params
        }
        
        # 서명 생성
        signature = self._generate_signature(api_params, namespace)
        api_params['_aop_signature'] = signature
        
        # API 호출
        url = f"{self.BASE_URL}/{namespace}"
        
        response = requests.post(
            url,
            data=api_params,
            timeout=30,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'YooiniBot/1.0'
            }
        )
        
        response.raise_for_status()
        return response.json()
    
    def _generate_signature(self, params: Dict[str, Any], namespace: str) -> str:
        """API 서명 생성"""
        # 파라미터 정렬
        sorted_params = sorted(params.items())
        
        # 서명 문자열 생성
        sign_string = namespace
        for key, value in sorted_params:
            if key != '_aop_signature':
                sign_string += f"{key}{value}"
        sign_string += self.app_secret
        
        # HMAC-MD5 서명
        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.md5
        ).hexdigest().upper()
        
        return signature
    
    def _normalize_product_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """제품 데이터 정규화"""
        return {
            'supplier_product_id': str(product.get('productId', '')),
            'supplier_sku': product.get('productId', ''),
            'name': product.get('subject', ''),
            'description': product.get('description', ''),
            'category': product.get('categoryName', ''),
            'brand': product.get('brandName', ''),
            'images': product.get('images', []),
            'price': {
                'amount': product.get('priceRange', {}).get('startPrice', 0),
                'currency': 'CNY',
                'min_order_quantity': product.get('minOrderQuantity', 1)
            },
            'supplier_info': {
                'company_name': product.get('company', {}).get('name', ''),
                'location': product.get('company', {}).get('province', ''),
                'rating': product.get('company', {}).get('creditLevel', 0)
            },
            'attributes': product.get('attributes', {}),
            'last_updated': datetime.now(),
            'raw_data': product
        }
    
    def _normalize_product_details(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """제품 상세정보 정규화"""
        return {
            'supplier_product_id': str(product.get('productId', '')),
            'supplier_sku': product.get('productId', ''),
            'name': product.get('subject', ''),
            'description': product.get('description', ''),
            'detailed_description': product.get('detailDesc', ''),
            'category': product.get('categoryName', ''),
            'brand': product.get('brandName', ''),
            'images': product.get('images', []),
            'videos': product.get('videos', []),
            'specifications': product.get('productSpec', []),
            'features': product.get('productFeatures', []),
            'packaging_info': {
                'weight': product.get('weight', 0),
                'dimensions': product.get('dimensions', {}),
                'package_weight': product.get('packageWeight', 0),
                'package_dimensions': product.get('packageDimensions', {})
            },
            'shipping_info': {
                'shipping_methods': product.get('shippingMethods', []),
                'shipping_fee': product.get('shippingFee', 0),
                'delivery_time': product.get('deliveryTime', '')
            },
            'quality_info': {
                'quality_level': product.get('qualityLevel', ''),
                'certifications': product.get('certifications', []),
                'quality_assurance': product.get('qualityAssurance', '')
            },
            'supplier_info': {
                'company_id': product.get('company', {}).get('companyId', ''),
                'company_name': product.get('company', {}).get('name', ''),
                'location': product.get('company', {}).get('province', ''),
                'address': product.get('company', {}).get('address', ''),
                'rating': product.get('company', {}).get('creditLevel', 0),
                'years_in_business': product.get('company', {}).get('establishYear', 0),
                'contact_info': product.get('company', {}).get('contactInfo', {})
            },
            'attributes': product.get('attributes', {}),
            'last_updated': datetime.now(),
            'raw_data': product
        }
    
    def sync_product_data(self, product_id: str) -> bool:
        """제품 데이터 동기화"""
        try:
            # 제품 상세정보 조회
            product_details = self.get_product_details(product_id)
            if not product_details:
                return False
            
            # 가격 정보 조회
            price_info = self.get_product_price(product_id)
            if price_info:
                product_details['pricing'] = price_info
            
            # 재고 정보 조회
            inventory_info = self.get_inventory(product_id)
            if inventory_info:
                product_details['inventory'] = inventory_info
            
            # 데이터베이스에 저장/업데이트
            _, created = SupplierProduct.objects.update_or_create(
                supplier=self.supplier,
                supplier_product_id=product_id,
                defaults={
                    'supplier_sku': product_details.get('supplier_sku', ''),
                    'name': product_details.get('name', ''),
                    'description': product_details.get('description', ''),
                    'category': product_details.get('category', ''),
                    'brand': product_details.get('brand', ''),
                    'cost_price': product_details.get('pricing', {}).get('unit_price', 0),
                    'currency': product_details.get('pricing', {}).get('currency', 'CNY'),
                    'min_order_quantity': product_details.get('pricing', {}).get('min_order_quantity', 1),
                    'available_quantity': product_details.get('inventory', {}).get('available_quantity', 0),
                    'weight': product_details.get('packaging_info', {}).get('weight', 0),
                    'dimensions': json.dumps(product_details.get('packaging_info', {}).get('dimensions', {})),
                    'images': json.dumps(product_details.get('images', [])),
                    'attributes': json.dumps(product_details.get('attributes', {})),
                    'raw_data': json.dumps(product_details.get('raw_data', {})),
                    'status': 'active' if product_details.get('inventory', {}).get('available_quantity', 0) > 0 else 'out_of_stock',
                    'last_sync_at': datetime.now()
                }
            )
            
            self.logger.info(f"Product {product_id} {'created' if created else 'updated'} successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error syncing product {product_id}: {e}")
            return False
    
    def bulk_sync_products(self, product_ids: List[str], batch_size: int = 10) -> Dict[str, Any]:
        """여러 제품 일괄 동기화"""
        results: Dict[str, Any] = {
            'success_count': 0,
            'error_count': 0,
            'errors': []
        }
        
        for i in range(0, len(product_ids), batch_size):
            batch = product_ids[i:i + batch_size]
            
            for product_id in batch:
                try:
                    if self.sync_product_data(product_id):
                        results['success_count'] += 1
                    else:
                        results['error_count'] += 1
                        results['errors'].append(f"Failed to sync product {product_id}")
                        
                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append(f"Error syncing product {product_id}: {str(e)}")
                
                # Rate limiting - 1688 API는 초당 요청 제한이 있음
                time.sleep(0.5)
        
        return results
    
    def search_suppliers(self, **kwargs) -> List[Dict[str, Any]]:
        """공급업체 검색"""
        try:
            search_text = kwargs.get('search_text', '')
            location = kwargs.get('location', '')
            
            params = {
                'q': search_text,
                'province': location,
                'pageSize': kwargs.get('page_size', 20),
                'pageIndex': kwargs.get('page_index', 1)
            }
            
            result = self._make_request(
                'param2/1/com.alibaba.company/alibaba.company.search',
                params
            )
            
            if result.get('success', False):
                companies = result.get('result', {}).get('companies', [])
                return [self._normalize_supplier_data(company) for company in companies]
            else:
                self.logger.error(f"Supplier search failed: {result.get('errorMessage')}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error searching suppliers: {e}")
            return []
    
    def _normalize_supplier_data(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """공급업체 데이터 정규화"""
        return {
            'company_id': str(company.get('companyId', '')),
            'name': company.get('name', ''),
            'description': company.get('description', ''),
            'location': {
                'province': company.get('province', ''),
                'city': company.get('city', ''),
                'address': company.get('address', '')
            },
            'contact_info': {
                'phone': company.get('phone', ''),
                'email': company.get('email', ''),
                'website': company.get('website', ''),
                'contact_person': company.get('contactPerson', '')
            },
            'business_info': {
                'establish_year': company.get('establishYear', 0),
                'business_type': company.get('businessType', ''),
                'main_products': company.get('mainProducts', []),
                'certifications': company.get('certifications', [])
            },
            'rating': {
                'credit_level': company.get('creditLevel', 0),
                'trade_amount': company.get('tradeAmount', 0),
                'customer_rating': company.get('customerRating', 0)
            },
            'raw_data': company
        }