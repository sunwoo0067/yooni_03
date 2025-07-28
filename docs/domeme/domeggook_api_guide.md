# 도매꾹/도매매 API 가이드 (Python)

## 목차
1. [개요](#개요)
2. [인증 및 기본 설정](#인증-및-기본-설정)
3. [카테고리 수집](#카테고리-수집)
4. [상품 목록 수집](#상품-목록-수집)
5. [상품 상세정보 수집](#상품-상세정보-수집)
6. [주문옵션 처리](#주문옵션-처리)
7. [에러 처리](#에러-처리)
8. [전체 상품 수집 프로세스](#전체-상품-수집-프로세스)

---

## 개요

도매꾹/도매매는 B2B 도매 플랫폼으로, 상품 정보를 API를 통해 제공합니다.
전체 상품을 수집하기 위해서는 카테고리 기반 접근 방식을 사용해야 합니다.

### 주요 API 엔드포인트
- **상품 목록 조회 (v4.1)**: 카테고리별 상품 리스트
- **상품 상세정보 조회 (v4.5)**: 개별 상품의 상세 정보
- **카테고리 목록 조회 (v1.0)**: 전체 카테고리 구조

### 카테고리 코드 체계
- 5자리 코드 구조: `XX_XX_XX_XX_XX`
- 전체 상품 수집 시 **중분류(2번째)까지** 사용
- 예시: `01_01_00_00_00` (대분류_중분류_소분류_세분류_세세분류)

---

## 인증 및 기본 설정

### 필요한 라이브러리 설치
```bash
pip install requests pandas json logging
```

### 기본 클래스 구조
```python
import requests
import json
import pandas as pd
import logging
import time
from typing import Dict, List, Optional, Union
from datetime import datetime

class DomeggookAPI:
    """도매꾹/도매매 API 클라이언트"""
    
    def __init__(self, api_key: str, base_url: str = "https://openapi.domeggook.com"):
        """
        API 클라이언트 초기화
        
        Args:
            api_key (str): API 인증키
            base_url (str): API 기본 URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'DomeggookAPI-Python/1.0'
        })
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, params: Dict = None, 
                     max_retries: int = 3, delay: float = 1.0) -> Dict:
        """
        API 요청 공통 함수
        
        Args:
            endpoint (str): API 엔드포인트
            params (Dict): 요청 파라미터
            max_retries (int): 최대 재시도 횟수
            delay (float): 요청 간 지연 시간(초)
            
        Returns:
            Dict: API 응답 데이터
        """
        if params is None:
            params = {}
        
        params['api_key'] = self.api_key
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # API 에러 체크
                if data.get('result') == 'error':
                    raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
                
                time.sleep(delay)  # Rate limiting
                return data
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay * (attempt + 1))
        
        raise Exception(f"Failed to complete request after {max_retries} attempts")
```

---

## 카테고리 수집

카테고리 정보를 먼저 수집하여 전체 상품 수집의 기반을 만듭니다.

```python
def get_categories(self) -> List[Dict]:
    """
    전체 카테고리 목록 조회 (v1.0)
    
    Returns:
        List[Dict]: 카테고리 정보 리스트
    """
    endpoint = "/api/category/list"
    params = {
        'version': '1.0'
    }
    
    response = self._make_request(endpoint, params)
    categories = response.get('data', [])
    
    self.logger.info(f"총 {len(categories)}개 카테고리 수집 완료")
    return categories

def filter_middle_categories(self, categories: List[Dict]) -> List[str]:
    """
    중분류 카테고리 코드만 추출
    
    Args:
        categories (List[Dict]): 전체 카테고리 리스트
        
    Returns:
        List[str]: 중분류 카테고리 코드 리스트
    """
    middle_categories = []
    
    for category in categories:
        code = category.get('category_code', '')
        
        # 중분류 패턴: XX_XX_00_00_00
        if code.endswith('_00_00_00') and not code.endswith('_00_00_00_00'):
            middle_categories.append(code)
    
    # 중복 제거 및 정렬
    middle_categories = sorted(list(set(middle_categories)))
    
    self.logger.info(f"중분류 카테고리 {len(middle_categories)}개 추출")
    return middle_categories

def save_categories_to_file(self, categories: List[Dict], 
                          filename: str = "categories.json"):
    """
    카테고리 정보를 파일로 저장
    
    Args:
        categories (List[Dict]): 카테고리 정보
        filename (str): 저장할 파일명
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    
    self.logger.info(f"카테고리 정보가 {filename}에 저장되었습니다")
```

---

## 상품 목록 수집

카테고리별로 상품 목록을 수집합니다.

```python
def get_product_list(self, category_code: str, page: int = 1, 
                    per_page: int = 100) -> Dict:
    """
    카테고리별 상품 목록 조회 (v4.1)
    
    Args:
        category_code (str): 카테고리 코드
        page (int): 페이지 번호
        per_page (int): 페이지당 상품 수 (최대 100)
        
    Returns:
        Dict: 상품 목록 응답 데이터
    """
    endpoint = "/api/product/list"
    params = {
        'version': '4.1',
        'category_code': category_code,
        'page': page,
        'limit': min(per_page, 100)  # 최대 100개 제한
    }
    
    response = self._make_request(endpoint, params)
    return response

def collect_all_products_from_category(self, category_code: str) -> List[Dict]:
    """
    특정 카테고리의 모든 상품 수집
    
    Args:
        category_code (str): 카테고리 코드
        
    Returns:
        List[Dict]: 해당 카테고리의 모든 상품 리스트
    """
    all_products = []
    page = 1
    
    self.logger.info(f"카테고리 {category_code} 상품 수집 시작")
    
    while True:
        try:
            response = self.get_product_list(category_code, page)
            products = response.get('data', {}).get('items', [])
            
            if not products:
                break
            
            all_products.extend(products)
            
            # 페이지네이션 정보 확인
            pagination = response.get('data', {}).get('pagination', {})
            current_page = pagination.get('current_page', page)
            total_pages = pagination.get('total_pages', 1)
            
            self.logger.info(
                f"카테고리 {category_code}: {current_page}/{total_pages} 페이지 완료 "
                f"({len(products)}개 상품)"
            )
            
            if current_page >= total_pages:
                break
                
            page += 1
            
        except Exception as e:
            self.logger.error(f"카테고리 {category_code}, 페이지 {page} 수집 실패: {e}")
            break
    
    self.logger.info(f"카테고리 {category_code} 총 {len(all_products)}개 상품 수집 완료")
    return all_products

def collect_all_products(self, category_codes: List[str] = None) -> List[Dict]:
    """
    전체 상품 수집 (카테고리 기반)
    
    Args:
        category_codes (List[str]): 수집할 카테고리 코드 리스트 (None시 전체)
        
    Returns:
        List[Dict]: 전체 상품 리스트
    """
    if category_codes is None:
        # 전체 카테고리 수집
        categories = self.get_categories()
        category_codes = self.filter_middle_categories(categories)
    
    all_products = []
    total_categories = len(category_codes)
    
    for idx, category_code in enumerate(category_codes, 1):
        self.logger.info(
            f"진행상황: {idx}/{total_categories} - 카테고리 {category_code} 처리 중"
        )
        
        try:
            products = self.collect_all_products_from_category(category_code)
            all_products.extend(products)
            
        except Exception as e:
            self.logger.error(f"카테고리 {category_code} 수집 실패: {e}")
            continue
        
        # 진행률 로그
        if idx % 10 == 0 or idx == total_categories:
            self.logger.info(
                f"전체 진행률: {idx}/{total_categories} "
                f"({idx/total_categories*100:.1f}%) - "
                f"누적 상품 수: {len(all_products)}개"
            )
    
    self.logger.info(f"전체 상품 수집 완료: {len(all_products)}개")
    return all_products
```

---

## 상품 상세정보 수집

개별 상품의 상세 정보와 주문옵션 정보를 수집합니다.

```python
def get_product_detail(self, product_id: str) -> Dict:
    """
    상품 상세정보 조회 (v4.5)
    
    Args:
        product_id (str): 상품 ID
        
    Returns:
        Dict: 상품 상세정보
    """
    endpoint = "/api/product/detail"
    params = {
        'version': '4.5',
        'product_id': product_id
    }
    
    response = self._make_request(endpoint, params)
    return response

def collect_products_detail(self, product_ids: List[str], 
                          batch_size: int = 10) -> List[Dict]:
    """
    여러 상품의 상세정보 일괄 수집
    
    Args:
        product_ids (List[str]): 상품 ID 리스트
        batch_size (int): 배치 처리 크기
        
    Returns:
        List[Dict]: 상품 상세정보 리스트
    """
    details = []
    total_products = len(product_ids)
    
    for i in range(0, total_products, batch_size):
        batch = product_ids[i:i + batch_size]
        
        for idx, product_id in enumerate(batch):
            try:
                detail = self.get_product_detail(product_id)
                details.append(detail)
                
                current_index = i + idx + 1
                if current_index % 100 == 0:
                    self.logger.info(
                        f"상세정보 수집 진행률: {current_index}/{total_products} "
                        f"({current_index/total_products*100:.1f}%)"
                    )
                    
            except Exception as e:
                self.logger.error(f"상품 {product_id} 상세정보 수집 실패: {e}")
                continue
        
        # 배치 간 대기시간
        time.sleep(0.5)
    
    self.logger.info(f"상품 상세정보 수집 완료: {len(details)}개")
    return details
```

---

## 주문옵션 처리

상품의 주문옵션 JSON 데이터를 파싱하고 처리합니다.

```python
class OrderOptionParser:
    """주문옵션 파싱 및 처리 클래스"""
    
    @staticmethod
    def parse_option_json(option_json_str: str) -> Optional[Dict]:
        """
        주문옵션 JSON 문자열 파싱
        
        Args:
            option_json_str (str): 주문옵션 JSON 문자열
            
        Returns:
            Dict: 파싱된 주문옵션 데이터
        """
        if not option_json_str:
            return None
        
        try:
            return json.loads(option_json_str)
        except json.JSONDecodeError as e:
            logging.error(f"주문옵션 JSON 파싱 실패: {e}")
            return None
    
    @staticmethod
    def extract_option_combinations(option_data: Dict) -> List[Dict]:
        """
        주문옵션 조합 데이터 추출
        
        Args:
            option_data (Dict): 파싱된 주문옵션 데이터
            
        Returns:
            List[Dict]: 주문옵션 조합 리스트
        """
        if not option_data or 'data' not in option_data:
            return []
        
        combinations = []
        data_section = option_data['data']
        
        for key, value in data_section.items():
            combination = {
                'combination_key': key,
                'name': value.get('name', ''),
                'dom_visible': value.get('dom') == 1,
                'dom_price': value.get('domPrice', 0),
                'sample_visible': value.get('sam') == 1,
                'sample_price': value.get('samPrice', 0),
                'supplier_visible': value.get('sup') == 1,
                'supplier_price': value.get('supPrice', 0),
                'quantity': value.get('qty', 0),
                'status': value.get('hid', 0),  # 0:판매중, 1:판매종료, 2:숨김
                'hash': value.get('hash', ''),
                'is_available': value.get('hid') == 0 and value.get('qty', 0) > 0
            }
            combinations.append(combination)
        
        return combinations
    
    @staticmethod
    def extract_option_groups(option_data: Dict) -> List[Dict]:
        """
        주문옵션 그룹 정보 추출 (색상, 크기 등)
        
        Args:
            option_data (Dict): 파싱된 주문옵션 데이터
            
        Returns:
            List[Dict]: 옵션 그룹 리스트
        """
        if not option_data or 'set' not in option_data:
            return []
        
        groups = []
        set_section = option_data['set']
        
        for idx, group in enumerate(set_section):
            group_info = {
                'group_index': idx,
                'name': group.get('name', ''),
                'options': group.get('opts', []),
                'prices': group.get('domPrice', []),
                'change_keys': group.get('changeKey', [])
            }
            groups.append(group_info)
        
        return groups
    
    @staticmethod
    def calculate_final_price(base_price: int, option_price: int) -> int:
        """
        최종 가격 계산 (상품 기본가격 + 옵션 추가가격)
        
        Args:
            base_price (int): 상품 기본 가격
            option_price (int): 옵션 추가 가격
            
        Returns:
            int: 최종 가격
        """
        return base_price + option_price

# DomeggookAPI 클래스에 추가 메서드
def process_product_options(self, product_detail: Dict) -> Dict:
    """
    상품의 주문옵션 처리
    
    Args:
        product_detail (Dict): 상품 상세정보
        
    Returns:
        Dict: 처리된 옵션 정보
    """
    item_info = product_detail.get('data', {}).get('itemInfo', {})
    option_json_str = item_info.get('itemOptJson', '')
    base_price = int(item_info.get('domPrice', 0))
    
    # 주문옵션 파싱
    option_data = OrderOptionParser.parse_option_json(option_json_str)
    
    if not option_data:
        return {
            'has_options': False,
            'option_groups': [],
            'combinations': [],
            'base_price': base_price
        }
    
    # 옵션 그룹 및 조합 추출
    option_groups = OrderOptionParser.extract_option_groups(option_data)
    combinations = OrderOptionParser.extract_option_combinations(option_data)
    
    # 최종 가격 계산
    for combination in combinations:
        combination['final_dom_price'] = OrderOptionParser.calculate_final_price(
            base_price, combination['dom_price']
        )
        combination['final_sample_price'] = OrderOptionParser.calculate_final_price(
            base_price, combination['sample_price']
        )
        combination['final_supplier_price'] = OrderOptionParser.calculate_final_price(
            base_price, combination['supplier_price']
        )
    
    return {
        'has_options': True,
        'option_type': option_data.get('type', ''),
        'option_sort': option_data.get('optSort', ''),
        'option_groups': option_groups,
        'combinations': combinations,
        'base_price': base_price,
        'total_combinations': len(combinations),
        'available_combinations': len([c for c in combinations if c['is_available']])
    }
```

---

## 에러 처리

API 사용 시 발생할 수 있는 다양한 에러를 처리합니다.

```python
class DomeggookAPIError(Exception):
    """도매꾹 API 전용 예외 클래스"""
    pass

class RateLimitError(DomeggookAPIError):
    """API 호출 제한 초과 예외"""
    pass

class AuthenticationError(DomeggookAPIError):
    """인증 실패 예외"""
    pass

# DomeggookAPI 클래스에 에러 처리 강화
def _handle_api_response(self, response: requests.Response) -> Dict:
    """
    API 응답 처리 및 에러 핸들링
    
    Args:
        response: requests Response 객체
        
    Returns:
        Dict: 처리된 응답 데이터
        
    Raises:
        DomeggookAPIError: API 관련 에러
    """
    try:
        data = response.json()
    except json.JSONDecodeError:
        raise DomeggookAPIError(f"Invalid JSON response: {response.text}")
    
    # API 결과 확인
    if data.get('result') == 'error':
        error_message = data.get('message', 'Unknown API error')
        error_code = data.get('error_code', '')
        
        if 'authentication' in error_message.lower() or error_code == 'AUTH_FAILED':
            raise AuthenticationError(f"Authentication failed: {error_message}")
        elif 'rate limit' in error_message.lower() or error_code == 'RATE_LIMIT':
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        else:
            raise DomeggookAPIError(f"API Error [{error_code}]: {error_message}")
    
    return data

def safe_collect_products(self, category_codes: List[str], 
                         continue_on_error: bool = True) -> List[Dict]:
    """
    안전한 상품 수집 (에러 발생시에도 계속 진행)
    
    Args:
        category_codes (List[str]): 카테고리 코드 리스트
        continue_on_error (bool): 에러 발생시 계속 진행 여부
        
    Returns:
        List[Dict]: 수집된 상품 리스트
    """
    all_products = []
    failed_categories = []
    
    for category_code in category_codes:
        try:
            products = self.collect_all_products_from_category(category_code)
            all_products.extend(products)
            
        except RateLimitError as e:
            self.logger.warning(f"Rate limit reached for {category_code}: {e}")
            self.logger.info("Waiting 60 seconds before retry...")
            time.sleep(60)
            
            try:
                products = self.collect_all_products_from_category(category_code)
                all_products.extend(products)
            except Exception as retry_e:
                self.logger.error(f"Retry failed for {category_code}: {retry_e}")
                failed_categories.append(category_code)
                if not continue_on_error:
                    raise
                    
        except AuthenticationError as e:
            self.logger.error(f"Authentication error: {e}")
            raise  # 인증 에러는 즉시 중단
            
        except Exception as e:
            self.logger.error(f"Error collecting {category_code}: {e}")
            failed_categories.append(category_code)
            if not continue_on_error:
                raise
    
    if failed_categories:
        self.logger.warning(f"Failed categories: {failed_categories}")
    
    return all_products
```

---

## 데이터 저장 및 관리

수집한 데이터를 다양한 형태로 저장하고 관리합니다.

```python
import csv
from pathlib import Path

class DataManager:
    """데이터 저장 및 관리 클래스"""
    
    def __init__(self, base_dir: str = "./data"):
        """
        데이터 매니저 초기화
        
        Args:
            base_dir (str): 데이터 저장 기본 디렉토리
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # 서브 디렉토리 생성
        (self.base_dir / "products").mkdir(exist_ok=True)
        (self.base_dir / "categories").mkdir(exist_ok=True)
        (self.base_dir / "options").mkdir(exist_ok=True)
        (self.base_dir / "reports").mkdir(exist_ok=True)
    
    def save_products_to_json(self, products: List[Dict], 
                             filename: str = None) -> str:
        """
        상품 데이터를 JSON 파일로 저장
        
        Args:
            products (List[Dict]): 상품 데이터
            filename (str): 파일명 (None시 자동 생성)
            
        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.json"
        
        filepath = self.base_dir / "products" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        logging.info(f"상품 데이터 저장 완료: {filepath} ({len(products)}개)")
        return str(filepath)
    
    def save_products_to_csv(self, products: List[Dict], 
                           filename: str = None) -> str:
        """
        상품 데이터를 CSV 파일로 저장
        
        Args:
            products (List[Dict]): 상품 데이터
            filename (str): 파일명 (None시 자동 생성)
            
        Returns:
            str: 저장된 파일 경로
        """
        if not products:
            raise ValueError("저장할 상품 데이터가 없습니다")
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_{timestamp}.csv"
        
        filepath = self.base_dir / "products" / filename
        
        # 첫 번째 상품에서 컬럼명 추출
        fieldnames = self._extract_product_fields(products[0])
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in products:
                flattened = self._flatten_product_data(product)
                writer.writerow(flattened)
        
        logging.info(f"상품 CSV 저장 완료: {filepath} ({len(products)}개)")
        return str(filepath)
    
    def save_options_to_csv(self, products_with_options: List[Dict], 
                          filename: str = None) -> str:
        """
        상품 옵션 데이터를 CSV 파일로 저장
        
        Args:
            products_with_options (List[Dict]): 옵션 포함 상품 데이터
            filename (str): 파일명
            
        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"product_options_{timestamp}.csv"
        
        filepath = self.base_dir / "options" / filename
        
        option_rows = []
        for product in products_with_options:
            product_info = product.get('product_info', {})
            option_info = product.get('option_info', {})
            
            if not option_info.get('has_options'):
                continue
            
            for combination in option_info.get('combinations', []):
                row = {
                    'product_id': product_info.get('product_id', ''),
                    'product_name': product_info.get('product_name', ''),
                    'combination_key': combination.get('combination_key', ''),
                    'option_name': combination.get('name', ''),
                    'dom_price': combination.get('dom_price', 0),
                    'final_dom_price': combination.get('final_dom_price', 0),
                    'quantity': combination.get('quantity', 0),
                    'status': combination.get('status', 0),
                    'is_available': combination.get('is_available', False),
                    'hash': combination.get('hash', '')
                }
                option_rows.append(row)
        
        if option_rows:
            df = pd.DataFrame(option_rows)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logging.info(f"옵션 CSV 저장 완료: {filepath} ({len(option_rows)}개)")
        
        return str(filepath)
    
    def _extract_product_fields(self, product: Dict) -> List[str]:
        """상품 데이터에서 필드명 추출"""
        fields = []
        self._extract_fields_recursive(product, '', fields)
        return sorted(list(set(fields)))
    
    def _extract_fields_recursive(self, obj, prefix: str, fields: List[str]):
        """재귀적으로 필드명 추출"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}_{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    self._extract_fields_recursive(value, new_prefix, fields)
                else:
                    fields.append(new_prefix)
        elif isinstance(obj, list) and obj:
            self._extract_fields_recursive(obj[0], prefix, fields)
    
    def _flatten_product_data(self, product: Dict) -> Dict:
        """상품 데이터를 평면화"""
        flattened = {}
        self._flatten_recursive(product, '', flattened)
        return flattened
    
    def _flatten_recursive(self, obj, prefix: str, result: Dict):
        """재귀적으로 데이터 평면화"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}_{key}" if prefix else key
                if isinstance(value, (dict, list)):
                    if isinstance(value, list):
                        # 리스트는 첫 번째 요소만 사용하거나 길이 정보만 저장
                        if value and isinstance(value[0], (str, int, float)):
                            result[new_prefix] = ', '.join(map(str, value))
                        else:
                            result[f"{new_prefix}_count"] = len(value)
                    else:
                        self._flatten_recursive(value, new_prefix, result)
                else:
                    result[new_prefix] = value
        elif isinstance(obj, list):
            result[prefix] = ', '.join(map(str, obj)) if obj else ''

# DomeggookAPI 클래스에 데이터 매니저 연동
def __init__(self, api_key: str, base_url: str = "https://openapi.domeggook.com", 
             data_dir: str = "./data"):
    # 기존 초기화 코드...
    self.data_manager = DataManager(data_dir)

def save_collected_data(self, products: List[Dict], 
                       format_type: str = "both") -> Dict[str, str]:
    """
    수집된 데이터 저장
    
    Args:
        products (List[Dict]): 상품 데이터
        format_type (str): 저장 형식 ("json", "csv", "both")
        
    Returns:
        Dict[str, str]: 저장된 파일 경로들
    """
    saved_files = {}
    
    if format_type in ["json", "both"]:
        json_path = self.data_manager.save_products_to_json(products)
        saved_files["json"] = json_path
    
    if format_type in ["csv", "both"]:
        csv_path = self.data_manager.save_products_to_csv(products)
        saved_files["csv"] = csv_path
    
    return saved_files
```

---

## 전체 상품 수집 프로세스

전체 프로세스를 하나로 통합한 메인 함수입니다.

```python
def full_product_collection(self, include_details: bool = True, 
                          include_options: bool = True,
                          save_format: str = "both",
                          category_limit: int = None) -> Dict:
    """
    전체 상품 수집 프로세스
    
    Args:
        include_details (bool): 상품 상세정보 포함 여부
        include_options (bool): 주문옵션 정보 포함 여부
        save_format (str): 저장 형식 ("json", "csv", "both")
        category_limit (int): 처리할 카테고리 수 제한 (테스트용)
        
    Returns:
        Dict: 수집 결과 정보
    """
    start_time = datetime.now()
    self.logger.info("=== 전체 상품 수집 프로세스 시작 ===")
    
    try:
        # 1. 카테고리 수집
        self.logger.info("1단계: 카테고리 정보 수집")
        categories = self.get_categories()
        middle_categories = self.filter_middle_categories(categories)
        
        if category_limit:
            middle_categories = middle_categories[:category_limit]
            self.logger.info(f"테스트를 위해 {category_limit}개 카테고리로 제한")
        
        # 2. 상품 목록 수집
        self.logger.info("2단계: 상품 목록 수집")
        all_products = self.safe_collect_products(middle_categories)
        
        if not all_products:
            raise Exception("수집된 상품이 없습니다")
        
        # 3. 상품 상세정보 수집 (선택사항)
        detailed_products = []
        if include_details:
            self.logger.info("3단계: 상품 상세정보 수집")
            product_ids = [p.get('product_id') for p in all_products if p.get('product_id')]
            product_details = self.collect_products_detail(product_ids)
            
            # 4. 주문옵션 처리 (선택사항)
            if include_options:
                self.logger.info("4단계: 주문옵션 처리")
                for detail in product_details:
                    option_info = self.process_product_options(detail)
                    detailed_products.append({
                        'product_info': detail.get('data', {}),
                        'option_info': option_info
                    })
            else:
                detailed_products = [{'product_info': d.get('data', {})} for d in product_details]
        
        # 5. 데이터 저장
        self.logger.info("5단계: 데이터 저장")
        final_data = detailed_products if detailed_products else all_products
        saved_files = self.save_collected_data(final_data, save_format)
        
        # 6. 옵션 데이터 별도 저장 (옵션 포함시)
        if include_options and detailed_products:
            option_file = self.data_manager.save_options_to_csv(detailed_products)
            saved_files["options_csv"] = option_file
        
        # 완료 시간 계산
        end_time = datetime.now()
        duration = end_time - start_time
        
        # 결과 정보
        result = {
            'success': True,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'categories_processed': len(middle_categories),
            'products_collected': len(all_products),
            'details_collected': len(detailed_products) if detailed_products else 0,
            'saved_files': saved_files,
            'summary': {
                'total_products': len(final_data),
                'products_with_options': sum(1 for p in detailed_products 
                                           if p.get('option_info', {}).get('has_options', False)) 
                                         if detailed_products else 0
            }
        }
        
        self.logger.info("=== 전체 상품 수집 프로세스 완료 ===")
        self.logger.info(f"소요시간: {duration}")
        self.logger.info(f"수집 상품수: {result['products_collected']}개")
        
        return result
        
    except Exception as e:
        self.logger.error(f"상품 수집 프로세스 실패: {e}")
        return {
            'success': False,
            'error': str(e),
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat()
        }

def generate_collection_report(self, result: Dict) -> str:
    """
    수집 결과 리포트 생성
    
    Args:
        result (Dict): 수집 결과 데이터
        
    Returns:
        str: 리포트 파일 경로
    """
    if not result.get('success'):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = self.data_manager.base_dir / "reports" / f"collection_report_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=== 도매꾹/도매매 상품 수집 리포트 ===\n\n")
        f.write(f"수집 시작시간: {result['start_time']}\n")
        f.write(f"수집 완료시간: {result['end_time']}\n")
        f.write(f"총 소요시간: {result['duration_seconds']:.2f}초\n\n")
        
        f.write(f"처리된 카테고리 수: {result['categories_processed']}개\n")
        f.write(f"수집된 상품 수: {result['products_collected']}개\n")
        f.write(f"상세정보 수집 수: {result['details_collected']}개\n\n")
        
        if result.get('summary'):
            summary = result['summary']
            f.write(f"최종 상품 수: {summary['total_products']}개\n")
            f.write(f"옵션 보유 상품 수: {summary['products_with_options']}개\n\n")
        
        f.write("저장된 파일:\n")
        for file_type, file_path in result.get('saved_files', {}).items():
            f.write(f"  - {file_type}: {file_path}\n")
    
    self.logger.info(f"수집 리포트 생성: {report_file}")
    return str(report_file)
```

---

## 사용 예제

### 기본 사용법

```python
# 1. API 클라이언트 초기화
api_key = "your_api_key_here"
client = DomeggookAPI(api_key)

# 2. 전체 상품 수집 (간단한 방법)
result = client.full_product_collection()

if result['success']:
    print(f"수집 완료: {result['products_collected']}개 상품")
    print(f"저장된 파일: {result['saved_files']}")
else:
    print(f"수집 실패: {result['error']}")

# 3. 리포트 생성
report_path = client.generate_collection_report(result)
print(f"리포트 파일: {report_path}")
```

### 단계별 상세 사용법

```python
# 1. 카테고리만 먼저 확인
categories = client.get_categories()
middle_categories = client.filter_middle_categories(categories)
print(f"처리할 중분류 카테고리: {len(middle_categories)}개")

# 2. 특정 카테고리만 테스트
test_categories = middle_categories[:5]  # 처음 5개만
products = client.safe_collect_products(test_categories)
print(f"테스트 수집 결과: {len(products)}개 상품")

# 3. 특정 상품의 상세정보만 수집
product_ids = [p['product_id'] for p in products[:10]]  # 처음 10개만
details = client.collect_products_detail(product_ids)

# 4. 주문옵션 분석
for detail in details:
    option_info = client.process_product_options(detail)
    if option_info['has_options']:
        print(f"상품 {detail['data']['itemInfo']['itemName']}: "
              f"{option_info['total_combinations']}개 옵션 조합")
```

### 대용량 데이터 처리

```python
# 1. 배치 처리로 메모리 효율적 수집
def batch_collection(client, category_codes, batch_size=50):
    """카테고리를 배치로 나누어 처리"""
    all_results = []
    
    for i in range(0, len(category_codes), batch_size):
        batch = category_codes[i:i + batch_size]
        print(f"배치 {i//batch_size + 1} 처리 중...")
        
        # 배치별 수집
        products = client.safe_collect_products(batch)
        
        # 즉시 저장 (메모리 절약)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"products_batch_{i//batch_size + 1}_{timestamp}.json"
        filepath = client.data_manager.save_products_to_json(products, filename)
        
        all_results.append({
            'batch_index': i//batch_size + 1,
            'categories': len(batch),
            'products': len(products),
            'file_path': filepath
        })
        
        # 메모리 정리
        del products
    
    return all_results

# 사용
categories = client.get_categories()
middle_categories = client.filter_middle_categories(categories)
batch_results = batch_collection(client, middle_categories, batch_size=20)
```

---

## 고급 기능

### 데이터 분석 및 통계

```python
class DataAnalyzer:
    """수집된 데이터 분석 클래스"""
    
    @staticmethod
    def analyze_products(products: List[Dict]) -> Dict:
        """상품 데이터 분석"""
        if not products:
            return {}
        
        # 기본 통계
        total_products = len(products)
        
        # 가격 분석
        prices = []
        categories = []
        suppliers = []
        
        for product in products:
            if 'data' in product and 'itemInfo' in product['data']:
                item_info = product['data']['itemInfo']
                
                # 가격 정보
                dom_price = int(item_info.get('domPrice', 0))
                if dom_price > 0:
                    prices.append(dom_price)
                
                # 카테고리 정보
                category = item_info.get('categoryName', '')
                if category:
                    categories.append(category)
                
                # 공급사 정보
                supplier = item_info.get('supplierName', '')
                if supplier:
                    suppliers.append(supplier)
        
        # 통계 계산
        price_stats = {}
        if prices:
            price_stats = {
                'min': min(prices),
                'max': max(prices),
                'avg': sum(prices) / len(prices),
                'median': sorted(prices)[len(prices)//2]
            }
        
        # 카테고리별 상품 수
        category_counts = {}
        for cat in categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # 공급사별 상품 수
        supplier_counts = {}
        for sup in suppliers:
            supplier_counts[sup] = supplier_counts.get(sup, 0) + 1
        
        return {
            'total_products': total_products,
            'price_statistics': price_stats,
            'category_distribution': dict(sorted(category_counts.items(), 
                                                key=lambda x: x[1], reverse=True)[:20]),
            'supplier_distribution': dict(sorted(supplier_counts.items(), 
                                                key=lambda x: x[1], reverse=True)[:20]),
            'products_with_price': len(prices)
        }
    
    @staticmethod
    def analyze_options(products_with_options: List[Dict]) -> Dict:
        """주문옵션 분석"""
        option_stats = {
            'total_products': len(products_with_options),
            'products_with_options': 0,
            'total_combinations': 0,
            'available_combinations': 0,
            'option_types': {},
            'price_range_analysis': {}
        }
        
        for product in products_with_options:
            option_info = product.get('option_info', {})
            
            if option_info.get('has_options'):
                option_stats['products_with_options'] += 1
                option_stats['total_combinations'] += option_info.get('total_combinations', 0)
                option_stats['available_combinations'] += option_info.get('available_combinations', 0)
                
                # 옵션 타입 분석
                option_type = option_info.get('option_type', 'unknown')
                option_stats['option_types'][option_type] = option_stats['option_types'].get(option_type, 0) + 1
        
        return option_stats

# DomeggookAPI 클래스에 분석 기능 추가
def analyze_collected_data(self, data_path: str = None) -> Dict:
    """수집된 데이터 분석"""
    if data_path:
        with open(data_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
    else:
        # 가장 최근 파일 찾기
        product_files = list((self.data_manager.base_dir / "products").glob("*.json"))
        if not product_files:
            raise FileNotFoundError("분석할 상품 데이터 파일을 찾을 수 없습니다")
        
        latest_file = max(product_files, key=lambda x: x.stat().st_mtime)
        with open(latest_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
    
    analysis = DataAnalyzer.analyze_products(products)
    
    # 옵션 분석 (옵션 정보가 있는 경우)
    if products and 'option_info' in products[0]:
        option_analysis = DataAnalyzer.analyze_options(products)
        analysis['option_analysis'] = option_analysis
    
    return analysis
```

### 데이터 업데이트 및 동기화

```python
def update_products(self, existing_data_path: str, 
                   categories_to_update: List[str] = None) -> Dict:
    """기존 데이터 업데이트"""
    # 기존 데이터 로드
    with open(existing_data_path, 'r', encoding='utf-8') as f:
        existing_products = json.load(f)
    
    existing_ids = set()
    for product in existing_products:
        if 'data' in product and 'itemInfo' in product['data']:
            product_id = product['data']['itemInfo'].get('itemId')
            if product_id:
                existing_ids.add(product_id)
    
    # 새 데이터 수집
    if categories_to_update is None:
        categories = self.get_categories()
        categories_to_update = self.filter_middle_categories(categories)
    
    new_products = self.safe_collect_products(categories_to_update)
    
    # 새로운 상품만 필터링
    truly_new_products = []
    for product in new_products:
        product_id = product.get('product_id')
        if product_id and product_id not in existing_ids:
            truly_new_products.append(product)
    
    # 업데이트된 데이터 저장
    updated_products = existing_products + truly_new_products
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    updated_path = self.data_manager.save_products_to_json(
        updated_products, f"products_updated_{timestamp}.json"
    )
    
    return {
        'existing_count': len(existing_products),
        'new_count': len(truly_new_products),
        'total_count': len(updated_products),
        'updated_file': updated_path
    }
```

---

## 성능 최적화 및 모니터링

### 성능 최적화 팁

```python
# 1. 연결 풀 사용
import requests.adapters

def optimize_session(self):
    """세션 최적화"""
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=3
    )
    self.session.mount('http://', adapter)
    self.session.mount('https://', adapter)

# 2. 비동기 처리 (고급)
import asyncio
import aiohttp

class AsyncDomeggookAPI:
    """비동기 도매꾹 API 클라이언트"""
    
    async def fetch_product_detail_async(self, session, product_id: str) -> Dict:
        """비동기로 상품 상세정보 조회"""
        url = f"{self.base_url}/api/product/detail"
        params = {
            'version': '4.5',
            'product_id': product_id,
            'api_key': self.api_key
        }
        
        async with session.get(url, params=params) as response:
            return await response.json()
    
    async def collect_details_async(self, product_ids: List[str]) -> List[Dict]:
        """비동기로 여러 상품 상세정보 수집"""
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.fetch_product_detail_async(session, pid) 
                for pid in product_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 예외 처리
            valid_results = []
            for result in results:
                if not isinstance(result, Exception):
                    valid_results.append(result)
            
            return valid_results

# 3. 메모리 사용량 모니터링
import psutil
import os

def monitor_memory_usage(self):
    """메모리 사용량 모니터링"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss_mb': memory_info.rss / 1024 / 1024,  # 실제 메모리
        'vms_mb': memory_info.vms / 1024 / 1024,  # 가상 메모리
        'memory_percent': process.memory_percent()
    }
```

### 로깅 및 모니터링

```python
def setup_advanced_logging(self, log_level: str = "INFO"):
    """고급 로깅 설정"""
    
    # 로그 디렉토리 생성
    log_dir = self.data_manager.base_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 파일 핸들러
    log_file = log_dir / f"domeggook_api_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level))
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # 로거에 핸들러 추가
    self.logger.addHandler(file_handler)
    
    # 성능 로깅
    self.logger.info("고급 로깅 설정 완료")

def log_performance_metrics(self, operation: str, start_time: datetime, 
                          item_count: int = 0):
    """성능 메트릭 로깅"""
    duration = (datetime.now() - start_time).total_seconds()
    memory_info = self.monitor_memory_usage()
    
    self.logger.info(
        f"PERFORMANCE - {operation}: "
        f"Duration={duration:.2f}s, "
        f"Items={item_count}, "
        f"Memory={memory_info['rss_mb']:.1f}MB, "
        f"Rate={item_count/duration:.1f} items/s" if duration > 0 else "Rate=N/A"
    )
```

---

## 주의사항 및 베스트 프랙티스

### API 사용 시 주의사항
1. **Rate Limiting**: API 호출 제한을 준수하여 1초당 1-2회 정도로 제한
2. **에러 처리**: 네트워크 오류, API 오류에 대한 적절한 재시도 로직 구현
3. **메모리 관리**: 대용량 데이터 처리 시 배치 처리 및 메모리 정리
4. **데이터 검증**: 수집된 데이터의 무결성 검증

### 베스트 프랙티스
1. **로깅**: 모든 작업에 대한 상세한 로그 기록
2. **백업**: 수집된 데이터의 정기적인 백업
3. **모니터링**: 수집 프로세스의 성능 및 상태 모니터링
4. **테스트**: 소규모 테스트 후 전체 수집 진행

---

## 마무리

이 API 가이드를 통해 도매꾹/도매매의 전체 상품 데이터를 효율적으로 수집할 수 있습니다. 
초보 개발자도 단계별로 따라하면서 점진적으로 고급 기능을 활용할 수 있도록 구성했습니다.

추가 질문이나 특정 부분에 대한 상세한 설명이 필요하시면 언제든 문의해 주세요!