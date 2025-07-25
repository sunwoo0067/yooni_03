"""
Marketplace Data Parser - Parse and normalize data from different marketplaces
"""
import re
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


class MarketplaceDataParser:
    """Parse data from marketplace HTML/JSON responses"""
    
    def __init__(self):
        self.currency_patterns = {
            "won": r'[\₩,\s]*([0-9,]+)[\₩\s]*',
            "number": r'[,\s]*([0-9,]+)[,\s]*',
            "percentage": r'([0-9.]+)%',
            "decimal": r'([0-9.]+)'
        }
        
        # Marketplace-specific selectors
        self.selectors = {
            "coupang": {
                "product_rows": ".product-analytics-row, .product-item",
                "product_name": ".product-name, .item-name",
                "product_id": "[data-product-id], [data-item-id]",
                "sales_count": ".sales-count, .order-count",
                "revenue": ".revenue-amount, .sales-amount",
                "page_views": ".view-count, .page-views",
                "conversion_rate": ".conversion-rate, .cvr",
                "click_count": ".click-count, .clicks",
                "impression_count": ".impression-count, .impressions",
                "ranking": ".ranking-position, .rank"
            },
            "naver": {
                "product_rows": ".product-row, .smartstore-item",
                "product_name": ".product-title, .item-title",
                "product_id": "[data-product-no], [data-item-no]",
                "sales_count": ".sales-qty, .order-qty",
                "revenue": ".sales-amt, .revenue",
                "page_views": ".visit-cnt, .view-cnt",
                "conversion_rate": ".purchase-rate, .conversion",
                "click_count": ".click-cnt",
                "search_keywords": ".keyword-list .keyword"
            },
            "11st": {
                "product_rows": ".stats-row, .product-item",
                "product_name": ".product-name",
                "product_id": "[data-prd-no]",
                "sales_count": ".sales-count",
                "revenue": ".sales-amount",
                "page_views": ".view-count",
                "conversion_rate": ".conversion-rate"
            }
        }
    
    def parse_coupang_analytics(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse Coupang seller center analytics data"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        try:
            # Find product analytics table/container
            analytics_container = soup.find(['table', 'div'], class_=re.compile(r'analytics|product.*table'))
            
            if not analytics_container:
                return products
            
            # Parse product rows
            product_rows = analytics_container.find_all(['tr', 'div'], class_=re.compile(r'product.*row|item.*row'))
            
            for row in product_rows:
                try:
                    product_data = self._extract_coupang_product_data(row)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    continue
            
            # Try alternative parsing methods if no data found
            if not products:
                products = self._parse_coupang_alternative(soup)
            
        except Exception as e:
            print(f"Error parsing Coupang analytics: {e}")
        
        return products
    
    def _extract_coupang_product_data(self, row_element) -> Optional[Dict[str, Any]]:
        """Extract product data from Coupang row element"""
        
        try:
            # Extract product name
            name_elem = row_element.find(['a', 'span', 'div'], string=re.compile(r'.+')) or \
                       row_element.find(['a', 'span', 'div'], class_=re.compile(r'name|title'))
            product_name = name_elem.get_text(strip=True) if name_elem else ""
            
            # Extract product ID
            product_id = row_element.get('data-product-id') or \
                        row_element.get('data-item-id') or \
                        self._extract_id_from_href(row_element)
            
            # Extract metrics
            sales_count = self._extract_number_from_element(row_element, [
                '.sales-count', '.order-count', '.qty'
            ])
            
            revenue = self._extract_currency_from_element(row_element, [
                '.revenue', '.sales-amount', '.amount'
            ])
            
            page_views = self._extract_number_from_element(row_element, [
                '.view-count', '.page-views', '.views'
            ])
            
            conversion_rate = self._extract_percentage_from_element(row_element, [
                '.conversion-rate', '.cvr', '.purchase-rate'
            ])
            
            click_count = self._extract_number_from_element(row_element, [
                '.click-count', '.clicks'
            ])
            
            return {
                "marketplace": "coupang",
                "product_name": product_name,
                "product_id": product_id,
                "sales_volume": sales_count,
                "revenue": revenue,
                "page_views": page_views,
                "conversion_rate": conversion_rate,
                "click_count": click_count
            }
            
        except Exception:
            return None
    
    def _parse_coupang_alternative(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Alternative parsing method for Coupang data"""
        
        products = []
        
        try:
            # Look for JSON data in script tags
            script_tags = soup.find_all('script', type='text/javascript')
            
            for script in script_tags:
                if script.string and 'analytics' in script.string.lower():
                    # Extract JSON data
                    json_data = self._extract_json_from_script(script.string)
                    if json_data:
                        products.extend(self._parse_coupang_json(json_data))
            
            # Look for data attributes
            elements_with_data = soup.find_all(attrs={'data-analytics': True})
            for elem in elements_with_data:
                data = json.loads(elem.get('data-analytics', '{}'))
                if data:
                    product = self._normalize_coupang_json_data(data)
                    if product:
                        products.append(product)
                        
        except Exception as e:
            print(f"Error in alternative Coupang parsing: {e}")
        
        return products
    
    def parse_naver_analytics(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse Naver Smart Store analytics data"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        try:
            # Find analytics table
            tables = soup.find_all('table', class_=re.compile(r'analytics|stats|product'))
            
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header
                
                for row in rows:
                    try:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 4:  # Minimum expected columns
                            product_data = self._extract_naver_row_data(cells)
                            if product_data:
                                products.append(product_data)
                    except Exception:
                        continue
            
            # Try alternative parsing if no data found
            if not products:
                products = self._parse_naver_alternative(soup)
                
        except Exception as e:
            print(f"Error parsing Naver analytics: {e}")
        
        return products
    
    def _extract_naver_row_data(self, cells: List) -> Optional[Dict[str, Any]]:
        """Extract product data from Naver table row"""
        
        try:
            # Typical Naver table structure:
            # [Product Name, Sales Qty, Sales Amount, Views, Clicks, Conversion Rate]
            
            if len(cells) < 4:
                return None
            
            product_name = cells[0].get_text(strip=True)
            sales_volume = self._parse_number(cells[1].get_text(strip=True))
            revenue = self._parse_currency(cells[2].get_text(strip=True))
            page_views = self._parse_number(cells[3].get_text(strip=True)) if len(cells) > 3 else 0
            click_count = self._parse_number(cells[4].get_text(strip=True)) if len(cells) > 4 else 0
            conversion_rate = self._parse_percentage(cells[5].get_text(strip=True)) if len(cells) > 5 else 0.0
            
            # Extract product ID from link
            product_link = cells[0].find('a')
            product_id = self._extract_naver_product_id(product_link.get('href')) if product_link else ""
            
            return {
                "marketplace": "naver",
                "product_name": product_name,
                "product_id": product_id,
                "sales_volume": sales_volume,
                "revenue": revenue,
                "page_views": page_views,
                "click_count": click_count,
                "conversion_rate": conversion_rate
            }
            
        except Exception:
            return None
    
    def _parse_naver_alternative(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Alternative parsing for Naver data"""
        
        products = []
        
        try:
            # Look for AJAX response data
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string and any(keyword in script.string.lower() for keyword in ['analytics', 'stats', 'product']):
                    json_data = self._extract_json_from_script(script.string)
                    if json_data:
                        products.extend(self._parse_naver_json(json_data))
                        
        except Exception as e:
            print(f"Error in alternative Naver parsing: {e}")
        
        return products
    
    def parse_11st_analytics(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse 11st business center analytics data"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        products = []
        
        try:
            # Find product analytics section
            analytics_section = soup.find(['div', 'section'], class_=re.compile(r'analytics|stats'))
            
            if analytics_section:
                product_items = analytics_section.find_all(['div', 'tr'], class_=re.compile(r'product|item'))
                
                for item in product_items:
                    product_data = self._extract_11st_product_data(item)
                    if product_data:
                        products.append(product_data)
                        
        except Exception as e:
            print(f"Error parsing 11st analytics: {e}")
        
        return products
    
    def _extract_11st_product_data(self, item_element) -> Optional[Dict[str, Any]]:
        """Extract product data from 11st item element"""
        
        try:
            # Extract basic product info
            name_elem = item_element.find(['span', 'a'], class_=re.compile(r'name|title'))
            product_name = name_elem.get_text(strip=True) if name_elem else ""
            
            product_id = item_element.get('data-prd-no') or self._extract_id_from_href(item_element)
            
            # Extract metrics
            sales_volume = self._extract_number_from_element(item_element, ['.sales-count', '.order-qty'])
            revenue = self._extract_currency_from_element(item_element, ['.sales-amount', '.revenue'])
            page_views = self._extract_number_from_element(item_element, ['.view-count', '.views'])
            conversion_rate = self._extract_percentage_from_element(item_element, ['.conversion-rate'])
            
            return {
                "marketplace": "11st",
                "product_name": product_name,
                "product_id": product_id,
                "sales_volume": sales_volume,
                "revenue": revenue,
                "page_views": page_views,
                "conversion_rate": conversion_rate
            }
            
        except Exception:
            return None
    
    def parse_traffic_data(self, html_content: str, marketplace: str) -> List[Dict[str, Any]]:
        """Parse traffic source data"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        traffic_sources = []
        
        try:
            # Find traffic analytics section
            traffic_section = soup.find(['div', 'section'], class_=re.compile(r'traffic|source|channel'))
            
            if traffic_section:
                source_items = traffic_section.find_all(['tr', 'div'], class_=re.compile(r'source|channel'))
                
                for item in source_items:
                    source_data = self._extract_traffic_source_data(item, marketplace)
                    if source_data:
                        traffic_sources.append(source_data)
                        
        except Exception as e:
            print(f"Error parsing traffic data: {e}")
        
        return traffic_sources
    
    def _extract_traffic_source_data(self, item_element, marketplace: str) -> Optional[Dict[str, Any]]:
        """Extract traffic source data from element"""
        
        try:
            # Extract source information
            source_name = self._extract_text_from_element(item_element, ['.source-name', '.channel-name'])
            sessions = self._extract_number_from_element(item_element, ['.sessions', '.visits'])
            users = self._extract_number_from_element(item_element, ['.users', '.visitors'])
            page_views = self._extract_number_from_element(item_element, ['.pageviews', '.views'])
            bounces = self._extract_number_from_element(item_element, ['.bounces', '.bounce-count'])
            transactions = self._extract_number_from_element(item_element, ['.transactions', '.conversions'])
            revenue = self._extract_currency_from_element(item_element, ['.revenue', '.sales'])
            
            # Calculate derived metrics
            bounce_rate = (bounces / sessions * 100) if sessions > 0 else 0
            conversion_rate = (transactions / sessions * 100) if sessions > 0 else 0
            avg_session_value = (revenue / sessions) if sessions > 0 else 0
            
            return {
                "marketplace": marketplace,
                "source_name": source_name,
                "sessions": sessions,
                "users": users,
                "page_views": page_views,
                "bounces": bounces,
                "transactions": transactions,
                "revenue": revenue,
                "bounce_rate": bounce_rate,
                "conversion_rate": conversion_rate,
                "avg_session_value": avg_session_value
            }
            
        except Exception:
            return None
    
    def parse_keyword_data(self, html_content: str, marketplace: str) -> List[Dict[str, Any]]:
        """Parse search keyword data"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        keywords = []
        
        try:
            # Find keyword analytics section
            keyword_section = soup.find(['div', 'table'], class_=re.compile(r'keyword|search'))
            
            if keyword_section:
                keyword_items = keyword_section.find_all(['tr', 'div'], class_=re.compile(r'keyword|search-term'))
                
                for item in keyword_items:
                    keyword_data = self._extract_keyword_data(item, marketplace)
                    if keyword_data:
                        keywords.append(keyword_data)
                        
        except Exception as e:
            print(f"Error parsing keyword data: {e}")
        
        return keywords
    
    def _extract_keyword_data(self, item_element, marketplace: str) -> Optional[Dict[str, Any]]:
        """Extract keyword data from element"""
        
        try:
            keyword = self._extract_text_from_element(item_element, ['.keyword', '.search-term'])
            search_volume = self._extract_number_from_element(item_element, ['.search-volume', '.volume'])
            ranking = self._extract_number_from_element(item_element, ['.ranking', '.position'])
            clicks = self._extract_number_from_element(item_element, ['.clicks', '.click-count'])
            impressions = self._extract_number_from_element(item_element, ['.impressions', '.impression-count'])
            
            # Calculate derived metrics
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            
            return {
                "marketplace": marketplace,
                "keyword": keyword,
                "search_volume": search_volume,
                "ranking_position": ranking,
                "click_count": clicks,
                "impression_count": impressions,
                "click_through_rate": ctr
            }
            
        except Exception:
            return None
    
    # Helper methods for data extraction
    def _extract_number_from_element(self, parent_element, selectors: List[str]) -> int:
        """Extract number from element using selectors"""
        
        for selector in selectors:
            element = parent_element.select_one(selector)
            if element:
                return self._parse_number(element.get_text(strip=True))
        
        return 0
    
    def _extract_currency_from_element(self, parent_element, selectors: List[str]) -> float:
        """Extract currency amount from element using selectors"""
        
        for selector in selectors:
            element = parent_element.select_one(selector)
            if element:
                return self._parse_currency(element.get_text(strip=True))
        
        return 0.0
    
    def _extract_percentage_from_element(self, parent_element, selectors: List[str]) -> float:
        """Extract percentage from element using selectors"""
        
        for selector in selectors:
            element = parent_element.select_one(selector)
            if element:
                return self._parse_percentage(element.get_text(strip=True))
        
        return 0.0
    
    def _extract_text_from_element(self, parent_element, selectors: List[str]) -> str:
        """Extract text from element using selectors"""
        
        for selector in selectors:
            element = parent_element.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return ""
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text"""
        try:
            match = re.search(self.currency_patterns["number"], text)
            if match:
                return int(match.group(1).replace(',', ''))
            return 0
        except (ValueError, AttributeError):
            return 0
    
    def _parse_currency(self, text: str) -> float:
        """Parse currency amount from text"""
        try:
            match = re.search(self.currency_patterns["won"], text)
            if match:
                return float(match.group(1).replace(',', ''))
            return 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage from text"""
        try:
            match = re.search(self.currency_patterns["percentage"], text)
            if match:
                return float(match.group(1))
            return 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def _extract_id_from_href(self, element) -> str:
        """Extract product ID from href attribute"""
        
        try:
            link = element.find('a')
            if link and link.get('href'):
                # Common patterns for product IDs in URLs
                patterns = [
                    r'product[_-]?id[=:](\d+)',
                    r'item[_-]?id[=:](\d+)',
                    r'prd[_-]?no[=:](\d+)',
                    r'/(\d+)(?:/|$)',  # ID at end of path
                ]
                
                href = link.get('href')
                for pattern in patterns:
                    match = re.search(pattern, href, re.IGNORECASE)
                    if match:
                        return match.group(1)
            
            return ""
        except Exception:
            return ""
    
    def _extract_naver_product_id(self, href: str) -> str:
        """Extract Naver product ID from URL"""
        
        try:
            if not href:
                return ""
            
            # Parse query parameters
            parsed = urlparse(href)
            query_params = parse_qs(parsed.query)
            
            # Common Naver product ID parameters
            id_params = ['nvMid', 'productId', 'itemId']
            
            for param in id_params:
                if param in query_params:
                    return query_params[param][0]
            
            return ""
        except Exception:
            return ""
    
    def _extract_json_from_script(self, script_content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON data from script tag content"""
        
        try:
            # Look for JSON objects in script
            json_patterns = [
                r'var\s+\w+\s*=\s*(\{.*?\});',
                r'window\.\w+\s*=\s*(\{.*?\});',
                r'data\s*:\s*(\{.*?\})',
                r'analytics\s*:\s*(\{.*?\})'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, script_content, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
            
            return None
        except Exception:
            return None
    
    def _parse_coupang_json(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Coupang JSON analytics data"""
        
        products = []
        
        try:
            # Look for product data in various possible structures
            product_lists = [
                json_data.get('products', []),
                json_data.get('items', []),
                json_data.get('data', {}).get('products', []),
                json_data.get('analytics', {}).get('products', [])
            ]
            
            for product_list in product_lists:
                if isinstance(product_list, list):
                    for item in product_list:
                        product = self._normalize_coupang_json_data(item)
                        if product:
                            products.append(product)
                            
        except Exception as e:
            print(f"Error parsing Coupang JSON: {e}")
        
        return products
    
    def _normalize_coupang_json_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize Coupang JSON data to standard format"""
        
        try:
            return {
                "marketplace": "coupang",
                "product_name": data.get('name', data.get('title', '')),
                "product_id": str(data.get('id', data.get('productId', ''))),
                "sales_volume": int(data.get('sales', data.get('orderCount', 0))),
                "revenue": float(data.get('revenue', data.get('salesAmount', 0))),
                "page_views": int(data.get('views', data.get('pageViews', 0))),
                "click_count": int(data.get('clicks', data.get('clickCount', 0))),
                "conversion_rate": float(data.get('conversionRate', data.get('cvr', 0)))
            }
        except Exception:
            return None
    
    def _parse_naver_json(self, json_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse Naver JSON analytics data"""
        
        products = []
        
        try:
            # Similar to Coupang but with Naver-specific structure
            product_lists = [
                json_data.get('productList', []),
                json_data.get('items', []),
                json_data.get('data', [])
            ]
            
            for product_list in product_lists:
                if isinstance(product_list, list):
                    for item in product_list:
                        product = self._normalize_naver_json_data(item)
                        if product:
                            products.append(product)
                            
        except Exception as e:
            print(f"Error parsing Naver JSON: {e}")
        
        return products
    
    def _normalize_naver_json_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize Naver JSON data to standard format"""
        
        try:
            return {
                "marketplace": "naver",
                "product_name": data.get('productName', data.get('name', '')),
                "product_id": str(data.get('productNo', data.get('id', ''))),
                "sales_volume": int(data.get('salesQty', data.get('orderQty', 0))),
                "revenue": float(data.get('salesAmt', data.get('revenue', 0))),
                "page_views": int(data.get('visitCnt', data.get('views', 0))),
                "click_count": int(data.get('clickCnt', data.get('clicks', 0))),
                "conversion_rate": float(data.get('purchaseRate', data.get('conversionRate', 0)))
            }
        except Exception:
            return None