#!/usr/bin/env python3
"""
도매처 상품 수집 및 PostgreSQL 저장
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.wholesaler import WholesalerAccount, WholesalerType, WholesalerProduct
from app.models.user import User
from app.services.database.database import get_db
from app.core.database import Base, engine
from app.services.wholesalers.ownerclan_api import OwnerClanAPI
from app.services.wholesalers.zentrade_api import ZentradeAPI
from app.services.wholesalers.domeggook_api import DomeggookAPI

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductCollector:
    """상품 수집 및 저장 클래스"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.session_local = None
        self.init_database()
        
    def init_database(self):
        """데이터베이스 초기화"""
        try:
            # SQLAlchemy 엔진 생성
            self.engine = create_engine(self.database_url)
            
            # 테이블 생성
            Base.metadata.create_all(bind=self.engine)
            
            # 세션 생성
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.session_local = SessionLocal
            
            logger.info("데이터베이스 연결 성공")
            
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
            
    def get_or_create_wholesaler(self, session, wholesaler_type: str, name: str) -> WholesalerAccount:
        """도매처 계정 정보 조회 또는 생성"""
        # 시스템 계정으로 기본 도매처 계정 생성
        from app.models.user import User
        
        # 시스템 유저 확인 (또는 첫 번째 유저 사용)
        user = session.query(User).first()
        if not user:
            # 시스템 유저 생성
            user = User(
                email="system@yooni.com",
                username="system",
                full_name="System User",
                hashed_password="dummy_password",
                is_active=True,
                is_superuser=True
            )
            session.add(user)
            session.commit()
            logger.info("시스템 유저 생성")
        
        # 도매처 타입 매핑
        type_map = {
            "ownerclan": WholesalerType.OWNERCLAN,
            "zentrade": WholesalerType.ZENTRADE,
            "domeggook": WholesalerType.DOMEGGOOK
        }
        
        wholesaler_enum = type_map.get(wholesaler_type)
        if not wholesaler_enum:
            raise ValueError(f"알 수 없는 도매처 타입: {wholesaler_type}")
        
        wholesaler = session.query(WholesalerAccount).filter_by(
            wholesaler_type=wholesaler_enum,
            user_id=user.id
        ).first()
        
        if not wholesaler:
            # API 자격증명 (실제로는 암호화해야 함)
            credentials = {
                "api_key": os.getenv(f"{wholesaler_type.upper()}_API_KEY"),
                "api_secret": os.getenv(f"{wholesaler_type.upper()}_API_SECRET")
            }
            
            wholesaler = WholesalerAccount(
                user_id=user.id,
                wholesaler_type=wholesaler_enum,
                account_name=f"{name} 기본 계정",
                api_credentials=json.dumps(credentials),
                is_active=True,
                auto_collect_enabled=True
            )
            session.add(wholesaler)
            session.commit()
            logger.info(f"도매처 계정 생성: {name}")
        
        return wholesaler
        
    async def collect_ownerclan_products(self, session, limit: int = 100):
        """OwnerClan 상품 수집"""
        logger.info("OwnerClan 상품 수집 시작...")
        
        try:
            # API 초기화
            credentials = {
                'username': os.getenv('OWNERCLAN_USERNAME'),
                'password': os.getenv('OWNERCLAN_PASSWORD')
            }
            api = OwnerClanAPI(credentials)
            
            # 도매처 정보 조회/생성
            wholesaler = self.get_or_create_wholesaler(session, "ownerclan", "오너클랜")
            
            # 로그인
            token = await api.login()
            if not token:
                logger.error("OwnerClan 로그인 실패")
                return 0
                
            # 상품 목록 조회
            query = """
            query {
                searchProduct(
                    searchType: SUPPLIER
                    filter: { displayYn: Y }
                    pageable: { page: 1, size: %d }
                ) {
                    totalElements
                    content {
                        productId
                        name
                        salePrice
                        stockCnt
                        images {
                            url
                        }
                        category {
                            categoryId
                            name
                        }
                        shippingPrice
                        status
                    }
                }
            }
            """ % limit
            
            products_data = await api.execute_query(query)
            
            if not products_data or 'searchProduct' not in products_data:
                logger.error("상품 데이터 없음")
                return 0
                
            products = products_data['searchProduct']['content']
            count = 0
            
            for product in products:
                try:
                    # 기존 상품 확인
                    existing = session.query(WholesalerProduct).filter_by(
                        wholesaler_account_id=wholesaler.id,
                        wholesaler_product_id=product['productId']
                    ).first()
                    
                    if existing:
                        # 업데이트
                        existing.name = product['name']
                        existing.wholesale_price = int(product['salePrice'])
                        existing.stock_quantity = product.get('stockCnt', 0)
                        existing.is_active = product.get('status') == 'ACTIVE'
                        existing.is_in_stock = product.get('stockCnt', 0) > 0
                        existing.updated_at = datetime.utcnow()
                        logger.info(f"상품 업데이트: {product['name']}")
                    else:
                        # 신규 생성
                        collected_product = WholesalerProduct(
                            wholesaler_account_id=wholesaler.id,
                            wholesaler_product_id=product['productId'],
                            name=product['name'],
                            wholesale_price=int(product['salePrice']),
                            retail_price=int(product['salePrice']),
                            stock_quantity=product.get('stockCnt', 0),
                            is_in_stock=product.get('stockCnt', 0) > 0,
                            category_path=product['category']['name'] if product.get('category') else None,
                            main_image_url=product['images'][0]['url'] if product.get('images') else None,
                            is_active=product.get('status') == 'ACTIVE',
                            shipping_info={'price': product.get('shippingPrice', 0)},
                            raw_data=product
                        )
                        session.add(collected_product)
                        logger.info(f"상품 추가: {product['name']}")
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"상품 저장 실패: {e}")
                    continue
            
            session.commit()
            logger.info(f"OwnerClan: {count}개 상품 저장 완료")
            return count
            
        except Exception as e:
            logger.error(f"OwnerClan 수집 실패: {e}")
            session.rollback()
            return 0
            
    async def collect_zentrade_products(self, session, limit: int = 100):
        """Zentrade 상품 수집"""
        logger.info("Zentrade 상품 수집 시작...")
        
        try:
            # API 초기화
            credentials = {
                'api_key': os.getenv('ZENTRADE_API_KEY'),
                'api_secret': os.getenv('ZENTRADE_API_SECRET')
            }
            api = ZentradeAPI(credentials)
            
            # 도매처 정보 조회/생성
            wholesaler = self.get_or_create_wholesaler(session, "zentrade", "젠트레이드")
            
            # 상품 목록 조회
            products_data = await api.get_products(page=1, per_page=limit)
            
            if not products_data:
                logger.error("상품 데이터 없음")
                return 0
                
            products = products_data.get('products', [])
            count = 0
            
            for product in products:
                try:
                    # 기존 상품 확인
                    existing = session.query(WholesalerProduct).filter_by(
                        wholesaler_account_id=wholesaler.id,
                        wholesaler_product_id=product['id']
                    ).first()
                    
                    if existing:
                        # 업데이트
                        existing.name = product['name']
                        existing.wholesale_price = int(product['price'])
                        existing.stock_quantity = product.get('stock', 0)
                        existing.is_active = product.get('status') == '판매중'
                        existing.is_in_stock = product.get('stock', 0) > 0
                        existing.updated_at = datetime.utcnow()
                        logger.info(f"상품 업데이트: {product['name']}")
                    else:
                        # 신규 생성
                        collected_product = WholesalerProduct(
                            wholesaler_account_id=wholesaler.id,
                            wholesaler_product_id=product['id'],
                            name=product['name'],
                            wholesale_price=int(product['price']),
                            retail_price=int(product.get('consumer_price', product['price'])),
                            stock_quantity=product.get('stock', 0),
                            is_in_stock=product.get('stock', 0) > 0,
                            category_path=product.get('category'),
                            main_image_url=product.get('image'),
                            is_active=product.get('status') == '판매중',
                            shipping_info={'price': product.get('delivery_charge', 0)},
                            description=product.get('description'),
                            raw_data=product
                        )
                        session.add(collected_product)
                        logger.info(f"상품 추가: {product['name']}")
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"상품 저장 실패: {e}")
                    continue
            
            session.commit()
            logger.info(f"Zentrade: {count}개 상품 저장 완료")
            return count
            
        except Exception as e:
            logger.error(f"Zentrade 수집 실패: {e}")
            session.rollback()
            return 0
            
    async def collect_all_products(self):
        """모든 도매처 상품 수집"""
        logger.info("="*60)
        logger.info("전체 상품 수집 시작")
        logger.info(f"시작 시간: {datetime.now()}")
        logger.info("="*60)
        
        session = self.session_local()
        results = {
            'ownerclan': 0,
            'zentrade': 0,
            'total': 0,
            'start_time': datetime.now()
        }
        
        try:
            # OwnerClan 수집
            results['ownerclan'] = await self.collect_ownerclan_products(session, limit=50)
            
            # Zentrade 수집
            results['zentrade'] = await self.collect_zentrade_products(session, limit=50)
            
            # 전체 통계
            results['total'] = results['ownerclan'] + results['zentrade']
            results['end_time'] = datetime.now()
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
            
            # 결과 출력
            logger.info("="*60)
            logger.info("수집 완료!")
            logger.info(f"OwnerClan: {results['ownerclan']}개")
            logger.info(f"Zentrade: {results['zentrade']}개")
            logger.info(f"총 수집: {results['total']}개")
            logger.info(f"소요 시간: {results['duration']:.2f}초")
            logger.info("="*60)
            
            # 저장된 데이터 확인
            total_count = session.query(WholesalerProduct).count()
            logger.info(f"\n데이터베이스 총 상휥 수: {total_count}개")
            
            # 도매처별 통계
            wholesalers = session.query(WholesalerAccount).all()
            for wholesaler in wholesalers:
                count = session.query(WholesalerProduct).filter_by(
                    wholesaler_account_id=wholesaler.id
                ).count()
                logger.info(f"{wholesaler.account_name}: {count}개")
            
            # 결과 파일 저장
            with open('collection_result.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': {
                        'ownerclan': results['ownerclan'],
                        'zentrade': results['zentrade'],
                        'total': results['total']
                    },
                    'duration': results['duration'],
                    'database_total': total_count
                }, f, ensure_ascii=False, indent=2)
            
            return results
            
        except Exception as e:
            logger.error(f"수집 중 오류 발생: {e}")
            session.rollback()
            raise
        finally:
            session.close()


async def main():
    """메인 함수"""
    collector = ProductCollector()
    
    try:
        # 전체 상품 수집
        results = await collector.collect_all_products()
        
        logger.info("\n수집 작업이 완료되었습니다!")
        logger.info(f"결과가 collection_result.json 파일에 저장되었습니다.")
        
    except Exception as e:
        logger.error(f"수집 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())