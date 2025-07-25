import re
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from html import unescape
from urllib.parse import urlparse

from ..wholesalers.base_wholesaler import ProductData
from ...models.wholesaler import WholesalerType


class DataNormalizer:
    """도매처별 데이터를 통합 스키마로 정규화하는 서비스"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
    def normalize_product_data(
        self,
        product_data: ProductData,
        wholesaler_type: WholesalerType
    ) -> Dict[str, Any]:
        """상품 데이터를 DB 저장용 형태로 정규화"""
        
        try:
            normalized = {
                'wholesaler_product_id': self._normalize_product_id(product_data.wholesaler_product_id),
                'wholesaler_sku': self._normalize_sku(product_data.wholesaler_sku),
                'name': self._normalize_product_name(product_data.name),
                'description': self._normalize_description(product_data.description),
                'category_path': self._normalize_category_path(product_data.category_path),
                'wholesale_price': self._normalize_price(product_data.wholesale_price),
                'retail_price': self._normalize_price(product_data.retail_price),
                'discount_rate': self._normalize_discount_rate(product_data.discount_rate),
                'stock_quantity': self._normalize_stock_quantity(product_data.stock_quantity),
                'is_in_stock': self._normalize_stock_status(product_data.is_in_stock),
                'main_image_url': self._normalize_image_url(product_data.main_image_url),
                'additional_images': self._normalize_image_list(product_data.additional_images),
                'options': self._normalize_options(product_data.options, wholesaler_type),
                'variants': self._normalize_variants(product_data.variants, wholesaler_type),
                'shipping_info': self._normalize_shipping_info(product_data.shipping_info, wholesaler_type),
                'raw_data': product_data.raw_data or {},
                'is_active': True,
                'is_collected': True,
                'first_collected_at': datetime.utcnow(),
                'last_updated_at': datetime.utcnow()
            }
            
            # 도매처별 특별 처리
            normalized = self._apply_wholesaler_specific_normalization(
                normalized, wholesaler_type, product_data
            )
            
            return normalized
            
        except Exception as e:
            self.logger.error(f"데이터 정규화 실패: {str(e)}")
            raise
            
    def _normalize_product_id(self, product_id: str) -> str:
        """상품 ID 정규화"""
        if not product_id:
            return ""
            
        # 문자열로 변환 후 공백 제거
        normalized_id = str(product_id).strip()
        
        # 특수문자 제거 (필요시)
        # normalized_id = re.sub(r'[^\w\-_]', '', normalized_id)
        
        return normalized_id[:100]  # 최대 길이 제한
        
    def _normalize_sku(self, sku: Optional[str]) -> Optional[str]:
        """SKU 정규화"""
        if not sku:
            return None
            
        normalized_sku = str(sku).strip()
        return normalized_sku[:100] if normalized_sku else None
        
    def _normalize_product_name(self, name: str) -> str:
        """상품명 정규화"""
        if not name:
            return ""
            
        # HTML 태그 제거
        clean_name = self._remove_html_tags(name)
        
        # 연속 공백을 하나로 변경
        clean_name = re.sub(r'\s+', ' ', clean_name)
        
        # 앞뒤 공백 제거
        clean_name = clean_name.strip()
        
        return clean_name[:500]  # 최대 길이 제한
        
    def _normalize_description(self, description: Optional[str]) -> Optional[str]:
        """상품 설명 정규화"""
        if not description:
            return None
            
        # HTML 태그 제거
        clean_desc = self._remove_html_tags(description)
        
        # 연속 줄바꿈을 두 개로 제한
        clean_desc = re.sub(r'\n{3,}', '\n\n', clean_desc)
        
        # 앞뒤 공백 제거
        clean_desc = clean_desc.strip()
        
        return clean_desc if clean_desc else None
        
    def _normalize_category_path(self, category_path: Optional[str]) -> Optional[str]:
        """카테고리 경로 정규화"""
        if not category_path:
            return None
            
        # 구분자 통일 (>, /, \ 등을 >로 통일)
        normalized_path = str(category_path).strip()
        normalized_path = re.sub(r'\s*[>/\\]\s*', ' > ', normalized_path)
        
        # 연속 공백 제거
        normalized_path = re.sub(r'\s+', ' ', normalized_path)
        
        return normalized_path[:500] if normalized_path else None
        
    def _normalize_price(self, price: Union[int, float, str, None]) -> int:
        """가격 정규화 (정수형 원 단위)"""
        if price is None:
            return 0
            
        # 문자열인 경우 숫자만 추출
        if isinstance(price, str):
            # 숫자, 소수점, 콤마만 남기고 제거
            price_str = re.sub(r'[^\d.,]', '', price)
            
            # 콤마 제거
            price_str = price_str.replace(',', '')
            
            if not price_str:
                return 0
                
            try:
                price = float(price_str)
            except ValueError:
                return 0
                
        try:
            return max(0, int(float(price)))
        except (ValueError, TypeError):
            return 0
            
    def _normalize_discount_rate(self, discount_rate: Union[int, float, None]) -> Optional[int]:
        """할인율 정규화 (0-100 사이의 정수)"""
        if discount_rate is None:
            return None
            
        try:
            rate = int(float(discount_rate))
            return max(0, min(100, rate))  # 0-100 사이로 제한
        except (ValueError, TypeError):
            return None
            
    def _normalize_stock_quantity(self, quantity: Union[int, str, None]) -> int:
        """재고 수량 정규화"""
        if quantity is None:
            return 0
            
        try:
            return max(0, int(quantity))
        except (ValueError, TypeError):
            return 0
            
    def _normalize_stock_status(self, is_in_stock: Union[bool, str, int, None]) -> bool:
        """재고 상태 정규화"""
        if isinstance(is_in_stock, bool):
            return is_in_stock
        elif isinstance(is_in_stock, str):
            return is_in_stock.lower() in ('true', '1', 'yes', 'y', 'in_stock', 'active')
        elif isinstance(is_in_stock, int):
            return is_in_stock > 0
        else:
            return False
            
    def _normalize_image_url(self, url: Optional[str]) -> Optional[str]:
        """이미지 URL 정규화"""
        if not url:
            return None
            
        url = str(url).strip()
        
        # 상대 경로를 절대 경로로 변환 (필요시)
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            # 도메인이 필요한 경우 도매처별로 처리
            pass
            
        # URL 유효성 기본 검증
        if self._is_valid_url(url):
            return url[:1000]  # 최대 길이 제한
        else:
            return None
            
    def _normalize_image_list(self, images: Optional[List[str]]) -> Optional[List[str]]:
        """이미지 URL 목록 정규화"""
        if not images:
            return None
            
        normalized_images = []
        for img_url in images:
            normalized_url = self._normalize_image_url(img_url)
            if normalized_url:
                normalized_images.append(normalized_url)
                
        return normalized_images if normalized_images else None
        
    def _normalize_options(
        self,
        options: Optional[Dict[str, Any]],
        wholesaler_type: WholesalerType
    ) -> Optional[Dict[str, Any]]:
        """옵션 정보 정규화"""
        if not options:
            return None
            
        normalized_options = {}
        
        # 기본 필드
        normalized_options['has_options'] = bool(options.get('has_options', False))
        
        if normalized_options['has_options']:
            # 도매처별 옵션 정규화
            if wholesaler_type == WholesalerType.DOMEGGOOK:
                normalized_options.update(self._normalize_domeggook_options(options))
            elif wholesaler_type == WholesalerType.OWNERCLAN:
                normalized_options.update(self._normalize_ownerclan_options(options))
            elif wholesaler_type == WholesalerType.ZENTRADE:
                normalized_options.update(self._normalize_zentrade_options(options))
                
        return normalized_options
        
    def _normalize_variants(
        self,
        variants: Optional[List[Dict[str, Any]]],
        wholesaler_type: WholesalerType
    ) -> Optional[List[Dict[str, Any]]]:
        """변형 정보 정규화"""
        if not variants:
            return None
            
        normalized_variants = []
        
        for variant in variants:
            normalized_variant = {
                'id': str(variant.get('id', '')),
                'name': str(variant.get('name', '')),
                'price': self._normalize_price(variant.get('price', 0)),
                'quantity': self._normalize_stock_quantity(variant.get('quantity', 0)),
                'available': bool(variant.get('available', True)),
                'attributes': variant.get('attributes', {})
            }
            
            # 추가 필드 (도매처별)
            if 'image_url' in variant:
                normalized_variant['image_url'] = self._normalize_image_url(variant['image_url'])
                
            normalized_variants.append(normalized_variant)
            
        return normalized_variants if normalized_variants else None
        
    def _normalize_shipping_info(
        self,
        shipping_info: Optional[Dict[str, Any]],
        wholesaler_type: WholesalerType
    ) -> Optional[Dict[str, Any]]:
        """배송 정보 정규화"""
        if not shipping_info:
            return None
            
        normalized_shipping = {}
        
        # 공통 필드
        if 'shipping_cost' in shipping_info:
            normalized_shipping['shipping_cost'] = self._normalize_price(shipping_info['shipping_cost'])
            
        if 'free_shipping_minimum' in shipping_info:
            normalized_shipping['free_shipping_minimum'] = self._normalize_price(shipping_info['free_shipping_minimum'])
            
        if 'shipping_method' in shipping_info:
            normalized_shipping['shipping_method'] = str(shipping_info['shipping_method'])[:100]
            
        if 'delivery_days' in shipping_info:
            try:
                normalized_shipping['delivery_days'] = int(shipping_info['delivery_days'])
            except (ValueError, TypeError):
                pass
                
        # 도매처별 특수 필드
        additional_fields = ['origin', 'manufacturer', 'brand', 'keywords', 'shipping_type', 'returnable', 'tax_free']
        for field in additional_fields:
            if field in shipping_info:
                normalized_shipping[field] = shipping_info[field]
                
        return normalized_shipping if normalized_shipping else None
        
    def _apply_wholesaler_specific_normalization(
        self,
        normalized: Dict[str, Any],
        wholesaler_type: WholesalerType,
        product_data: ProductData
    ) -> Dict[str, Any]:
        """도매처별 특별 정규화 처리"""
        
        if wholesaler_type == WholesalerType.DOMEGGOOK:
            # 도매매 특별 처리
            pass
        elif wholesaler_type == WholesalerType.OWNERCLAN:
            # 오너클랜 특별 처리
            pass
        elif wholesaler_type == WholesalerType.ZENTRADE:
            # 젠트레이드 특별 처리
            # EUC-KR 인코딩 관련 처리 등
            pass
            
        return normalized
        
    def _normalize_domeggook_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """도매매 옵션 정규화"""
        normalized = {}
        
        if 'combinations' in options:
            normalized['combinations'] = []
            for combo in options['combinations']:
                normalized_combo = {
                    'key': str(combo.get('key', '')),
                    'name': str(combo.get('name', '')),
                    'price': self._normalize_price(combo.get('price', 0)),
                    'quantity': self._normalize_stock_quantity(combo.get('quantity', 0)),
                    'available': bool(combo.get('available', True))
                }
                normalized['combinations'].append(normalized_combo)
                
        if 'total_combinations' in options:
            normalized['total_combinations'] = int(options['total_combinations'])
            
        if 'available_combinations' in options:
            normalized['available_combinations'] = int(options['available_combinations'])
            
        return normalized
        
    def _normalize_ownerclan_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """오너클랜 옵션 정규화"""
        normalized = {}
        
        if 'attribute_groups' in options:
            normalized['attribute_groups'] = options['attribute_groups']
            
        if 'total_combinations' in options:
            normalized['total_combinations'] = int(options['total_combinations'])
            
        if 'available_combinations' in options:
            normalized['available_combinations'] = int(options['available_combinations'])
            
        return normalized
        
    def _normalize_zentrade_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """젠트레이드 옵션 정규화"""
        normalized = {}
        
        if 'option_name' in options:
            normalized['option_name'] = str(options['option_name'])
            
        if 'parsed_options' in options:
            normalized['parsed_options'] = []
            for option in options['parsed_options']:
                normalized_option = {
                    'name': str(option.get('name', '')),
                    'buy_price': self._normalize_price(option.get('buy_price', 0)),
                    'consumer_price': self._normalize_price(option.get('consumer_price', 0)),
                    'image_url': self._normalize_image_url(option.get('image_url')),
                    'available': bool(option.get('available', True))
                }
                normalized['parsed_options'].append(normalized_option)
                
        if 'total_combinations' in options:
            normalized['total_combinations'] = int(options['total_combinations'])
            
        if 'available_combinations' in options:
            normalized['available_combinations'] = int(options['available_combinations'])
            
        return normalized
        
    def _remove_html_tags(self, html_string: str) -> str:
        """HTML 태그 제거"""
        if not html_string:
            return ""
            
        # HTML 엔티티 디코딩
        clean_text = unescape(html_string)
        
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        # 연속 공백을 하나로
        clean_text = re.sub(r'\s+', ' ', clean_text)
        
        return clean_text.strip()
        
    def _is_valid_url(self, url: str) -> bool:
        """URL 유효성 기본 검증"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
            
    def normalize_collection_filters(
        self,
        filters: Dict[str, Any],
        wholesaler_type: WholesalerType
    ) -> Dict[str, Any]:
        """수집 필터 정규화"""
        
        normalized_filters = {}
        
        # 공통 필터
        if 'days' in filters:
            try:
                days = int(filters['days'])
                normalized_filters['days'] = max(1, min(365, days))  # 1-365일 제한
            except (ValueError, TypeError):
                normalized_filters['days'] = 7  # 기본값
                
        if 'categories' in filters and isinstance(filters['categories'], list):
            normalized_filters['categories'] = [str(cat) for cat in filters['categories']]
            
        if 'max_products' in filters:
            try:
                max_products = int(filters['max_products'])
                normalized_filters['max_products'] = max(1, min(10000, max_products))
            except (ValueError, TypeError):
                normalized_filters['max_products'] = 1000
                
        # 도매처별 특수 필터
        if wholesaler_type == WholesalerType.DOMEGGOOK:
            # 도매매 전용 필터
            pass
        elif wholesaler_type == WholesalerType.OWNERCLAN:
            # 오너클랜 전용 필터
            if 'keywords' in filters:
                normalized_filters['keywords'] = [str(kw).strip() for kw in filters['keywords'] if str(kw).strip()]
                
            if 'price_ranges' in filters:
                normalized_filters['price_ranges'] = []
                for price_range in filters['price_ranges']:
                    if isinstance(price_range, dict):
                        normalized_range = {}
                        if 'min' in price_range:
                            normalized_range['min'] = self._normalize_price(price_range['min'])
                        if 'max' in price_range:
                            normalized_range['max'] = self._normalize_price(price_range['max'])
                        if normalized_range:
                            normalized_filters['price_ranges'].append(normalized_range)
        elif wholesaler_type == WholesalerType.ZENTRADE:
            # 젠트레이드 전용 필터
            if 'stock_only' in filters:
                normalized_filters['stock_only'] = bool(filters['stock_only'])
                
            if 'start_date' in filters and 'end_date' in filters:
                # 날짜 형식 검증 (YYYY-MM-DD)
                try:
                    start_date = str(filters['start_date'])
                    end_date = str(filters['end_date'])
                    
                    # 기본 날짜 형식 검증
                    datetime.strptime(start_date, '%Y-%m-%d')
                    datetime.strptime(end_date, '%Y-%m-%d')
                    
                    normalized_filters['start_date'] = start_date
                    normalized_filters['end_date'] = end_date
                    
                except ValueError:
                    # 잘못된 날짜 형식은 무시
                    pass
                    
        return normalized_filters
        
    def create_product_summary(self, products: List[ProductData]) -> Dict[str, Any]:
        """상품 목록 요약 생성"""
        
        if not products:
            return {
                'total_products': 0,
                'average_price': 0,
                'price_range': {'min': 0, 'max': 0},
                'categories': [],
                'in_stock_count': 0,
                'with_options_count': 0
            }
            
        # 가격 정보
        prices = [p.wholesale_price for p in products if p.wholesale_price > 0]
        
        # 카테고리 정보
        categories = list(set(p.category_path for p in products if p.category_path))
        
        # 재고 정보
        in_stock_count = sum(1 for p in products if p.is_in_stock)
        
        # 옵션 정보
        with_options_count = sum(1 for p in products if p.options and p.options.get('has_options'))
        
        summary = {
            'total_products': len(products),
            'average_price': sum(prices) / len(prices) if prices else 0,
            'price_range': {
                'min': min(prices) if prices else 0,
                'max': max(prices) if prices else 0
            },
            'categories': categories[:20],  # 최대 20개 카테고리만
            'in_stock_count': in_stock_count,
            'with_options_count': with_options_count,
            'stock_rate': (in_stock_count / len(products)) * 100 if products else 0,
            'options_rate': (with_options_count / len(products)) * 100 if products else 0
        }
        
        return summary