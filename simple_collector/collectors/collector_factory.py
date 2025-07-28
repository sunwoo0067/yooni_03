"""
수집기 팩토리 - 공급사별 수집기 인스턴스 생성
"""

from typing import Optional
from sqlalchemy.orm import Session

from database.models import Supplier
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector
from collectors.base_collector import BaseCollector
from utils.logger import app_logger

class CollectorFactory:
    """수집기 생성 팩토리"""
    
    @staticmethod
    def create_collector(supplier_code: str, db: Session, test_mode: bool = True) -> Optional[BaseCollector]:
        """공급사 코드로 수집기 생성
        
        Args:
            supplier_code: 공급사 코드
            db: 데이터베이스 세션
            test_mode: 테스트 모드 여부 (True면 더미 데이터 사용)
            
        Returns:
            수집기 인스턴스 또는 None
        """
        # 데이터베이스에서 공급사 정보 조회
        supplier = db.query(Supplier).filter(
            Supplier.supplier_code == supplier_code,
            Supplier.is_active == True
        ).first()
        
        if not supplier:
            app_logger.error(f"활성화된 공급사를 찾을 수 없습니다: {supplier_code}")
            return None
            
        # API 설정이 없으면 테스트 모드 강제
        if not supplier.api_config:
            app_logger.warning(f"{supplier_code} API 설정이 없어 테스트 모드로 실행합니다")
            test_mode = True
            
        # 공급사별 수집기 생성
        try:
            if supplier_code == "zentrade":
                credentials = supplier.api_config or {
                    'api_id': 'test_id',
                    'api_key': 'test_key',
                    'base_url': 'https://www.zentrade.co.kr/shop/proc'
                }
                collector = ZentradeCollector(credentials)
                
            elif supplier_code == "ownerclan":
                credentials = supplier.api_config or {
                    'username': 'test_user',
                    'password': 'test_password',
                    'api_url': 'https://api.ownerclan.com/v1/graphql',
                    'auth_url': 'https://auth.ownerclan.com/auth'
                }
                collector = OwnerClanCollector(credentials)
                
            elif supplier_code == "domeggook":
                credentials = supplier.api_config or {
                    'api_key': 'test_key',
                    'base_url': 'https://openapi.domeggook.com'
                }
                collector = DomeggookCollector(credentials)
                
            else:
                app_logger.error(f"지원하지 않는 공급사: {supplier_code}")
                return None
                
            # 테스트 모드 설정
            collector.test_mode = test_mode
            
            app_logger.info(f"{supplier_code} 수집기 생성 완료 (테스트 모드: {test_mode})")
            return collector
            
        except Exception as e:
            app_logger.error(f"{supplier_code} 수집기 생성 실패: {e}")
            return None
            
    @staticmethod
    def get_all_active_collectors(db: Session, test_mode: bool = True) -> dict:
        """모든 활성 공급사의 수집기 반환
        
        Returns:
            {supplier_code: collector} 딕셔너리
        """
        collectors = {}
        
        # 활성화된 모든 공급사 조회
        suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
        
        for supplier in suppliers:
            collector = CollectorFactory.create_collector(
                supplier.supplier_code, 
                db, 
                test_mode
            )
            if collector:
                collectors[supplier.supplier_code] = collector
                
        return collectors