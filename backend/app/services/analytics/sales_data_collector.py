"""
Sales Data Collector - Web scraping based data collection from marketplaces
"""
import asyncio
import json
import time
import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...models.sales_analytics import (
    SalesAnalytics, MarketplaceSession, TrafficSource, SearchKeyword,
    CompetitorAnalysis, DataCollectionLog, MarketplaceType, DataCollectionStatus
)
from ...models.platform_account import PlatformAccount
from .anti_detection import AntiDetectionManager
from .data_parser import MarketplaceDataParser
from .session_manager import SessionManager


class SalesDataCollector:
    """Main sales data collection service"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.anti_detection = AntiDetectionManager()
        self.parser = MarketplaceDataParser()
        self.session_manager = SessionManager()
        
        # Collection configuration
        self.config = {
            "request_delay": (2, 5),  # Random delay between requests
            "page_timeout": 30,
            "max_retries": 3,
            "concurrent_sessions": 2,
            "rate_limit_delay": 60,  # Delay when rate limited
        }
        
        # Marketplace-specific configurations
        self.marketplace_configs = {
            MarketplaceType.COUPANG: {
                "base_url": "https://wing.coupang.com",
                "login_url": "https://login.coupang.com/login/login.pang",
                "analytics_url": "https://wing.coupang.com/tenants/{tenant_id}/analytics",
                "selectors": {
                    "username": "input[name='username']",
                    "password": "input[name='password']",
                    "login_button": "button[type='submit']",
                    "sales_data": ".analytics-data",
                    "revenue": ".revenue-amount",
                    "orders": ".order-count",
                    "traffic": ".traffic-stats"
                }
            },
            MarketplaceType.NAVER: {
                "base_url": "https://sell.smartstore.naver.com",
                "login_url": "https://nid.naver.com/nidlogin.login",
                "analytics_url": "https://sell.smartstore.naver.com/analytics",
                "selectors": {
                    "username": "input[name='id']",
                    "password": "input[name='pw']",
                    "login_button": ".btn_login",
                    "sales_data": ".analytics-container",
                    "revenue": ".sales-amount",
                    "orders": ".order-count",
                    "traffic": ".visit-stats"
                }
            },
            MarketplaceType.ELEVENTH_STREET: {
                "base_url": "https://business.11st.co.kr",
                "login_url": "https://business.11st.co.kr/login",
                "analytics_url": "https://business.11st.co.kr/analytics",
                "selectors": {
                    "username": "input[name='loginId']",
                    "password": "input[name='password']",
                    "login_button": ".btn-login",
                    "sales_data": ".stats-container",
                    "revenue": ".revenue-info",
                    "orders": ".order-info",
                    "traffic": ".traffic-info"
                }
            }
        }
    
    async def collect_marketplace_data(
        self, 
        marketplace: MarketplaceType,
        account_id: str,
        date_range: Tuple[date, date],
        data_types: List[str] = None
    ) -> Dict[str, Any]:
        """Collect data from specific marketplace"""
        
        if data_types is None:
            data_types = ["sales", "traffic", "keywords", "competitors"]
        
        # Create session record
        session = await self._create_session(marketplace, account_id, date_range)
        
        try:
            # Get account credentials
            account = await self._get_account_credentials(account_id)
            if not account:
                raise ValueError(f"Account not found: {account_id}")
            
            # Initialize browser
            driver = await self._initialize_browser(marketplace)
            
            # Login to marketplace
            login_success = await self._login_to_marketplace(driver, marketplace, account, session)
            if not login_success:
                raise Exception("Failed to login to marketplace")
            
            # Collect different types of data
            results = {}
            
            if "sales" in data_types:
                results["sales"] = await self._collect_sales_data(driver, marketplace, date_range, session)
            
            if "traffic" in data_types:
                results["traffic"] = await self._collect_traffic_data(driver, marketplace, date_range, session)
            
            if "keywords" in data_types:
                results["keywords"] = await self._collect_keyword_data(driver, marketplace, date_range, session)
            
            if "competitors" in data_types:
                results["competitors"] = await self._collect_competitor_data(driver, marketplace, date_range, session)
            
            # Update session status
            session.status = DataCollectionStatus.COMPLETED
            session.ended_at = datetime.utcnow()
            
            return results
            
        except Exception as e:
            session.status = DataCollectionStatus.FAILED
            session.error_log = str(e)
            raise e
            
        finally:
            await self.db.commit()
            if 'driver' in locals():
                driver.quit()
    
    async def _create_session(
        self, 
        marketplace: MarketplaceType,
        account_id: str,
        date_range: Tuple[date, date]
    ) -> MarketplaceSession:
        """Create marketplace session record"""
        
        session = MarketplaceSession(
            marketplace=marketplace.value,
            account_identifier=account_id,
            session_type="analytics",
            started_at=datetime.utcnow(),
            target_date_start=date_range[0],
            target_date_end=date_range[1],
            status=DataCollectionStatus.PENDING
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        return session
    
    async def _get_account_credentials(self, account_id: str) -> Optional[PlatformAccount]:
        """Get account credentials from database"""
        result = await self.db.execute(
            select(PlatformAccount).where(PlatformAccount.id == account_id)
        )
        return result.scalar_one_or_none()
    
    async def _initialize_browser(self, marketplace: MarketplaceType) -> webdriver.Chrome:
        """Initialize browser with anti-detection measures"""
        
        options = Options()
        
        # Anti-detection settings
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Randomize user agent
        user_agent = self.anti_detection.get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        
        # Set viewport size
        options.add_argument("--window-size=1920,1080")
        
        # Create driver
        driver = webdriver.Chrome(options=options)
        
        # Execute script to hide automation
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    async def _login_to_marketplace(
        self, 
        driver: webdriver.Chrome,
        marketplace: MarketplaceType,
        account: PlatformAccount,
        session: MarketplaceSession
    ) -> bool:
        """Login to marketplace"""
        
        config = self.marketplace_configs[marketplace]
        
        try:
            # Navigate to login page
            driver.get(config["login_url"])
            await self._random_delay()
            
            # Wait for login form
            wait = WebDriverWait(driver, self.config["page_timeout"])
            
            # Enter username
            username_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, config["selectors"]["username"]))
            )
            username_field.clear()
            await self._human_type(username_field, account.username)
            
            # Enter password
            password_field = driver.find_element(By.CSS_SELECTOR, config["selectors"]["password"])
            password_field.clear()
            await self._human_type(password_field, account.password)
            
            # Submit form
            login_button = driver.find_element(By.CSS_SELECTOR, config["selectors"]["login_button"])
            login_button.click()
            
            # Wait for redirect and check if login successful
            await asyncio.sleep(3)
            
            # Check for login success (marketplace-specific)
            if marketplace == MarketplaceType.COUPANG:
                success = "wing.coupang.com" in driver.current_url
            elif marketplace == MarketplaceType.NAVER:
                success = "sell.smartstore.naver.com" in driver.current_url
            elif marketplace == MarketplaceType.ELEVENTH_STREET:
                success = "business.11st.co.kr" in driver.current_url and "login" not in driver.current_url
            else:
                success = "login" not in driver.current_url.lower()
            
            if success:
                # Save session cookies
                cookies = driver.get_cookies()
                session.session_cookies = json.dumps(cookies)
                await self.db.commit()
            
            return success
            
        except Exception as e:
            await self._log_collection_error(session, "login", str(e))
            return False
    
    async def _collect_sales_data(
        self, 
        driver: webdriver.Chrome,
        marketplace: MarketplaceType,
        date_range: Tuple[date, date],
        session: MarketplaceSession
    ) -> List[Dict[str, Any]]:
        """Collect sales analytics data"""
        
        sales_data = []
        config = self.marketplace_configs[marketplace]
        
        try:
            # Navigate to analytics page
            analytics_url = config["analytics_url"]
            if marketplace == MarketplaceType.COUPANG:
                # Replace tenant_id placeholder (would need to be determined from account)
                analytics_url = analytics_url.replace("{tenant_id}", "default")
            
            driver.get(analytics_url)
            await self._random_delay()
            
            # Set date range
            await self._set_date_range(driver, marketplace, date_range)
            
            # Wait for data to load
            wait = WebDriverWait(driver, self.config["page_timeout"])
            
            # Extract sales data based on marketplace
            if marketplace == MarketplaceType.COUPANG:
                sales_data = await self._extract_coupang_sales(driver, wait)
            elif marketplace == MarketplaceType.NAVER:
                sales_data = await self._extract_naver_sales(driver, wait)
            elif marketplace == MarketplaceType.ELEVENTH_STREET:
                sales_data = await self._extract_11st_sales(driver, wait)
            
            # Save extracted data to database
            for data in sales_data:
                await self._save_sales_analytics(data, session)
            
            session.total_items_collected += len(sales_data)
            
        except Exception as e:
            await self._log_collection_error(session, "sales_data", str(e))
            session.total_items_failed += 1
        
        return sales_data
    
    async def _extract_coupang_sales(
        self, 
        driver: webdriver.Chrome, 
        wait: WebDriverWait
    ) -> List[Dict[str, Any]]:
        """Extract sales data from Coupang seller center"""
        
        sales_data = []
        
        try:
            # Wait for analytics container
            analytics_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".analytics-data"))
            )
            
            # Extract revenue data
            revenue_elements = driver.find_elements(By.CSS_SELECTOR, ".revenue-amount")
            order_elements = driver.find_elements(By.CSS_SELECTOR, ".order-count")
            
            # Extract product-level data
            product_rows = driver.find_elements(By.CSS_SELECTOR, ".product-row")
            
            for row in product_rows:
                try:
                    product_data = {
                        "product_name": row.find_element(By.CSS_SELECTOR, ".product-name").text,
                        "product_id": row.get_attribute("data-product-id"),
                        "sales_volume": self._parse_number(row.find_element(By.CSS_SELECTOR, ".sales-count").text),
                        "revenue": self._parse_currency(row.find_element(By.CSS_SELECTOR, ".revenue").text),
                        "page_views": self._parse_number(row.find_element(By.CSS_SELECTOR, ".page-views").text),
                        "conversion_rate": self._parse_percentage(row.find_element(By.CSS_SELECTOR, ".conversion-rate").text),
                        "marketplace": "coupang"
                    }
                    sales_data.append(product_data)
                    
                except NoSuchElementException:
                    continue
            
        except TimeoutException:
            # Try alternative selectors or methods
            pass
        
        return sales_data
    
    async def _extract_naver_sales(
        self, 
        driver: webdriver.Chrome, 
        wait: WebDriverWait
    ) -> List[Dict[str, Any]]:
        """Extract sales data from Naver Smart Store"""
        
        sales_data = []
        
        try:
            # Navigate to product analytics
            analytics_menu = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".menu-analytics"))
            )
            analytics_menu.click()
            
            await self._random_delay()
            
            # Extract data from table
            product_table = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".product-analytics-table"))
            )
            
            rows = product_table.find_elements(By.CSS_SELECTOR, "tbody tr")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 6:
                        product_data = {
                            "product_name": cells[0].text,
                            "product_id": cells[0].get_attribute("data-product-id"),
                            "sales_volume": self._parse_number(cells[1].text),
                            "revenue": self._parse_currency(cells[2].text),
                            "page_views": self._parse_number(cells[3].text),
                            "click_count": self._parse_number(cells[4].text),
                            "conversion_rate": self._parse_percentage(cells[5].text),
                            "marketplace": "naver"
                        }
                        sales_data.append(product_data)
                
                except (IndexError, ValueError):
                    continue
        
        except TimeoutException:
            pass
        
        return sales_data
    
    async def _extract_11st_sales(
        self, 
        driver: webdriver.Chrome, 
        wait: WebDriverWait
    ) -> List[Dict[str, Any]]:
        """Extract sales data from 11st business center"""
        
        sales_data = []
        
        try:
            # Navigate to sales report
            sales_menu = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".sales-report-menu"))
            )
            sales_menu.click()
            
            await self._random_delay()
            
            # Extract data
            report_table = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".sales-report-table"))
            )
            
            # Process table data similar to other marketplaces
            # Implementation specific to 11st structure
            
        except TimeoutException:
            pass
        
        return sales_data
    
    async def _collect_traffic_data(
        self, 
        driver: webdriver.Chrome,
        marketplace: MarketplaceType,
        date_range: Tuple[date, date],
        session: MarketplaceSession
    ) -> List[Dict[str, Any]]:
        """Collect traffic analytics data"""
        
        traffic_data = []
        
        try:
            # Navigate to traffic analytics section
            # Implementation varies by marketplace
            if marketplace == MarketplaceType.COUPANG:
                traffic_data = await self._extract_coupang_traffic(driver)
            elif marketplace == MarketplaceType.NAVER:
                traffic_data = await self._extract_naver_traffic(driver)
            
            # Save traffic data
            for data in traffic_data:
                await self._save_traffic_source(data, session)
            
        except Exception as e:
            await self._log_collection_error(session, "traffic_data", str(e))
        
        return traffic_data
    
    async def _collect_keyword_data(
        self, 
        driver: webdriver.Chrome,
        marketplace: MarketplaceType,
        date_range: Tuple[date, date],
        session: MarketplaceSession
    ) -> List[Dict[str, Any]]:
        """Collect search keyword data"""
        
        keyword_data = []
        
        try:
            # Implementation for keyword data collection
            # This would involve navigating to search analytics sections
            pass
            
        except Exception as e:
            await self._log_collection_error(session, "keyword_data", str(e))
        
        return keyword_data
    
    async def _collect_competitor_data(
        self, 
        driver: webdriver.Chrome,
        marketplace: MarketplaceType,
        date_range: Tuple[date, date],
        session: MarketplaceSession
    ) -> List[Dict[str, Any]]:
        """Collect competitor analysis data"""
        
        competitor_data = []
        
        try:
            # Implementation for competitor data collection
            # This would involve searching for competitor products and analyzing them
            pass
            
        except Exception as e:
            await self._log_collection_error(session, "competitor_data", str(e))
        
        return competitor_data
    
    # Helper methods
    async def _set_date_range(
        self, 
        driver: webdriver.Chrome,
        marketplace: MarketplaceType,
        date_range: Tuple[date, date]
    ):
        """Set date range in analytics interface"""
        
        try:
            # Find date picker elements (varies by marketplace)
            date_picker = driver.find_element(By.CSS_SELECTOR, ".date-picker")
            date_picker.click()
            
            await self._random_delay()
            
            # Set start date
            start_date_field = driver.find_element(By.CSS_SELECTOR, ".start-date")
            start_date_field.clear()
            start_date_field.send_keys(date_range[0].strftime("%Y-%m-%d"))
            
            # Set end date
            end_date_field = driver.find_element(By.CSS_SELECTOR, ".end-date")
            end_date_field.clear()
            end_date_field.send_keys(date_range[1].strftime("%Y-%m-%d"))
            
            # Apply date range
            apply_button = driver.find_element(By.CSS_SELECTOR, ".apply-date-range")
            apply_button.click()
            
            await self._random_delay()
            
        except NoSuchElementException:
            # Date range setting failed, continue with default range
            pass
    
    async def _human_type(self, element, text: str):
        """Type text with human-like timing"""
        for char in text:
            element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.2))
    
    async def _random_delay(self):
        """Add random delay between actions"""
        delay = random.uniform(*self.config["request_delay"])
        await asyncio.sleep(delay)
    
    def _parse_number(self, text: str) -> int:
        """Parse number from text"""
        try:
            # Remove commas, spaces, and other non-digit characters
            cleaned = ''.join(filter(str.isdigit, text))
            return int(cleaned) if cleaned else 0
        except ValueError:
            return 0
    
    def _parse_currency(self, text: str) -> float:
        """Parse currency amount from text"""
        try:
            # Remove currency symbols and commas
            cleaned = text.replace(',', '').replace('₩', '').replace(' ', '')
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    
    def _parse_percentage(self, text: str) -> float:
        """Parse percentage from text"""
        try:
            cleaned = text.replace('%', '').replace(' ', '')
            return float(cleaned) if cleaned else 0.0
        except ValueError:
            return 0.0
    
    async def _save_sales_analytics(self, data: Dict[str, Any], session: MarketplaceSession):
        """Save sales analytics data to database"""
        
        analytics = SalesAnalytics(
            product_code=data.get("product_id"),
            product_name=data.get("product_name"),
            marketplace=data.get("marketplace"),
            collection_date=date.today(),
            data_period_start=session.target_date_start,
            data_period_end=session.target_date_end,
            sales_volume=data.get("sales_volume", 0),
            revenue=data.get("revenue", 0.0),
            page_views=data.get("page_views", 0),
            click_count=data.get("click_count", 0),
            conversion_rate=data.get("conversion_rate", 0.0),
            collection_method="scraping"
        )
        
        self.db.add(analytics)
    
    async def _save_traffic_source(self, data: Dict[str, Any], session: MarketplaceSession):
        """Save traffic source data to database"""
        
        # Implementation for saving traffic source data
        pass
    
    async def _log_collection_error(
        self, 
        session: MarketplaceSession,
        operation: str,
        error_message: str
    ):
        """Log collection error"""
        
        log_entry = DataCollectionLog(
            session_id=session.id,
            target_url=operation,
            method="GET",
            success=False,
            error_message=error_message
        )
        
        self.db.add(log_entry)
        session.error_count += 1
    
    # High-level collection methods
    async def collect_all_marketplace_data(
        self, 
        account_ids: List[str] = None,
        date_range: Tuple[date, date] = None,
        marketplaces: List[MarketplaceType] = None
    ) -> Dict[str, Any]:
        """Collect data from all configured marketplaces"""
        
        if date_range is None:
            # Default to last 7 days
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            date_range = (start_date, end_date)
        
        if marketplaces is None:
            marketplaces = [MarketplaceType.COUPANG, MarketplaceType.NAVER, MarketplaceType.ELEVENTH_STREET]
        
        results = {}
        
        for marketplace in marketplaces:
            marketplace_results = []
            
            # Get accounts for this marketplace
            if account_ids:
                accounts = await self._get_marketplace_accounts(marketplace, account_ids)
            else:
                accounts = await self._get_all_marketplace_accounts(marketplace)
            
            # Collect data for each account
            for account in accounts:
                try:
                    account_data = await self.collect_marketplace_data(
                        marketplace, 
                        str(account.id), 
                        date_range
                    )
                    marketplace_results.append({
                        "account_id": str(account.id),
                        "account_name": account.account_name,
                        "data": account_data
                    })
                    
                except Exception as e:
                    marketplace_results.append({
                        "account_id": str(account.id),
                        "account_name": account.account_name,
                        "error": str(e)
                    })
            
            results[marketplace.value] = marketplace_results
        
        return results
    
    async def _get_marketplace_accounts(
        self, 
        marketplace: MarketplaceType, 
        account_ids: List[str]
    ) -> List[PlatformAccount]:
        """Get specific marketplace accounts"""
        
        result = await self.db.execute(
            select(PlatformAccount).where(
                PlatformAccount.platform == marketplace.value,
                PlatformAccount.id.in_(account_ids),
                PlatformAccount.is_active == True
            )
        )
        return result.scalars().all()
    
    async def _get_all_marketplace_accounts(
        self, 
        marketplace: MarketplaceType
    ) -> List[PlatformAccount]:
        """Get all accounts for a marketplace"""
        
        result = await self.db.execute(
            select(PlatformAccount).where(
                PlatformAccount.platform == marketplace.value,
                PlatformAccount.is_active == True
            )
        )
        return result.scalars().all()
    
    async def schedule_regular_collection(self):
        """Schedule regular data collection"""
        
        # This would be called by a scheduler (like celery or APScheduler)
        # to automatically collect data at regular intervals
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Collect yesterday's data
        await self.collect_all_marketplace_data(
            date_range=(yesterday, yesterday)
        )
    
    async def get_collection_status(self) -> Dict[str, Any]:
        """Get current collection status"""
        
        # Get recent sessions
        recent_sessions = await self.db.execute(
            select(MarketplaceSession).where(
                MarketplaceSession.started_at >= datetime.utcnow() - timedelta(hours=24)
            ).order_by(MarketplaceSession.started_at.desc())
        )
        
        sessions = recent_sessions.scalars().all()
        
        status = {
            "total_sessions": len(sessions),
            "completed": len([s for s in sessions if s.status == DataCollectionStatus.COMPLETED]),
            "failed": len([s for s in sessions if s.status == DataCollectionStatus.FAILED]),
            "in_progress": len([s for s in sessions if s.status == DataCollectionStatus.COLLECTING]),
            "sessions": [
                {
                    "id": str(session.id),
                    "marketplace": session.marketplace,
                    "status": session.status,
                    "started_at": session.started_at,
                    "items_collected": session.total_items_collected,
                    "items_failed": session.total_items_failed
                }
                for session in sessions[:10]  # Last 10 sessions
            ]
        }
        
        return status