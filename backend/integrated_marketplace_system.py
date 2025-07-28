#!/usr/bin/env python3
"""
통합 마켓플레이스 시스템
도매처에서 상품을 수집하고 마켓플레이스에 등록하는 시스템
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
import asyncpg
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()


class IntegratedMarketplaceSystem:
    """통합 마켓플레이스 시스템"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.conn = None
        
    async def connect_db(self):
        """데이터베이스 연결"""
        db_parts = self.database_url.replace('postgresql://', '').split('@')
        user_pass = db_parts[0].split(':')
        host_db = db_parts[1].split('/')
        host_port = host_db[0].split(':')
        
        self.conn = await asyncpg.connect(
            user=user_pass[0],
            password=user_pass[1],
            database=host_db[1],
            host=host_port[0],
            port=int(host_port[1])
        )
        print("데이터베이스 연결 성공")
        
    async def close_db(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            await self.conn.close()
            
    async def setup_tables(self):
        """통합 테이블 생성"""
        # 마켓플레이스 등록 상품 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_products (
                id SERIAL PRIMARY KEY,
                source_product_id VARCHAR(100) NOT NULL,
                source_wholesaler VARCHAR(50) NOT NULL,
                marketplace_name VARCHAR(50) NOT NULL,
                marketplace_product_id VARCHAR(100),
                product_name VARCHAR(500) NOT NULL,
                selling_price INTEGER NOT NULL,
                original_price INTEGER NOT NULL,
                margin_rate DECIMAL(5,2),
                stock_quantity INTEGER DEFAULT 0,
                status VARCHAR(50) DEFAULT 'PENDING',
                listing_url VARCHAR(1000),
                last_sync_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_product_id, source_wholesaler, marketplace_name)
            )
        """)
        
        # 마켓플레이스 동기화 로그 테이블
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS marketplace_sync_logs (
                id SERIAL PRIMARY KEY,
                marketplace_name VARCHAR(50) NOT NULL,
                sync_type VARCHAR(50) NOT NULL,
                total_products INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                error_details JSONB,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        print("테이블 설정 완료")
        
    async def get_wholesaler_products(self, limit: int = 10) -> List[Dict]:
        """도매처 상품 조회"""
        products = await self.conn.fetch("""
            SELECT 
                wholesaler_name,
                product_id,
                product_name,
                price,
                stock_quantity,
                category,
                image_url,
                is_active
            FROM simple_collected_products
            WHERE is_active = true
            AND stock_quantity > 0
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)
        
        return [dict(product) for product in products]
        
    def calculate_selling_price(self, wholesale_price: int, margin_rate: float = 0.3) -> int:
        """판매가 계산 (30% 마진)"""
        selling_price = int(wholesale_price * (1 + margin_rate))
        # 100원 단위로 반올림
        return (selling_price // 100) * 100
        
    async def register_to_marketplace(self, product: Dict, marketplace: str) -> Dict:
        """마켓플레이스에 상품 등록 (시뮬레이션)"""
        # 실제로는 각 마켓플레이스 API를 호출
        # 여기서는 시뮬레이션으로 처리
        
        selling_price = self.calculate_selling_price(product['price'])
        margin_rate = ((selling_price - product['price']) / product['price']) * 100
        
        # 마켓플레이스별 상품 ID 생성 (시뮬레이션)
        marketplace_product_id = f"{marketplace.upper()}_{product['product_id']}"
        
        # DB에 등록 정보 저장
        await self.conn.execute("""
            INSERT INTO marketplace_products 
            (source_product_id, source_wholesaler, marketplace_name, 
             marketplace_product_id, product_name, selling_price, 
             original_price, margin_rate, stock_quantity, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (source_product_id, source_wholesaler, marketplace_name)
            DO UPDATE SET
                selling_price = EXCLUDED.selling_price,
                stock_quantity = EXCLUDED.stock_quantity,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
        """,
        product['product_id'],
        product['wholesaler_name'],
        marketplace,
        marketplace_product_id,
        product['product_name'],
        selling_price,
        product['price'],
        margin_rate,
        product['stock_quantity'],
        'ACTIVE'
        )
        
        return {
            'marketplace': marketplace,
            'product_id': marketplace_product_id,
            'status': 'SUCCESS',
            'selling_price': selling_price,
            'margin_rate': margin_rate
        }
        
    async def sync_all_marketplaces(self):
        """모든 마켓플레이스 동기화"""
        print("\n" + "=" * 60)
        print("마켓플레이스 동기화 시작")
        print("=" * 60)
        
        # 동기화 로그 시작
        sync_log_id = await self.conn.fetchval("""
            INSERT INTO marketplace_sync_logs 
            (marketplace_name, sync_type, started_at)
            VALUES ('ALL', 'PRODUCT_SYNC', $1)
            RETURNING id
        """, datetime.now())
        
        # 도매처 상품 조회
        products = await self.get_wholesaler_products(limit=20)
        print(f"\n총 {len(products)}개 상품 조회됨")
        
        # 마켓플레이스 목록
        marketplaces = ['coupang', 'naver', '11st']
        
        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        # 각 상품을 모든 마켓플레이스에 등록
        for product in products:
            print(f"\n상품: {product['product_name'][:50]}...")
            print(f"  도매가: {product['price']:,}원")
            
            for marketplace in marketplaces:
                try:
                    result = await self.register_to_marketplace(product, marketplace)
                    results['total'] += 1
                    results['success'] += 1
                    results['details'].append(result)
                    
                    print(f"  [{marketplace}] 등록 성공 - 판매가: {result['selling_price']:,}원 (마진: {result['margin_rate']:.1f}%)")
                    
                except Exception as e:
                    results['total'] += 1
                    results['failed'] += 1
                    print(f"  [{marketplace}] 등록 실패: {e}")
        
        # 동기화 로그 완료
        await self.conn.execute("""
            UPDATE marketplace_sync_logs
            SET total_products = $1,
                success_count = $2,
                failed_count = $3,
                completed_at = $4
            WHERE id = $5
        """, 
        results['total'],
        results['success'],
        results['failed'],
        datetime.now(),
        sync_log_id
        )
        
        return results
        
    async def get_marketplace_status(self):
        """마켓플레이스 현황 조회"""
        # 마켓플레이스별 통계
        stats = await self.conn.fetch("""
            SELECT 
                marketplace_name,
                COUNT(*) as total_products,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_products,
                AVG(margin_rate) as avg_margin_rate,
                SUM(selling_price * stock_quantity) as total_value
            FROM marketplace_products
            GROUP BY marketplace_name
            ORDER BY marketplace_name
        """)
        
        print("\n" + "=" * 60)
        print("마켓플레이스 현황")
        print("=" * 60)
        
        for stat in stats:
            print(f"\n[{stat['marketplace_name']}]")
            print(f"  총 상품 수: {stat['total_products']}개")
            print(f"  활성 상품: {stat['active_products']}개")
            print(f"  평균 마진율: {stat['avg_margin_rate']:.1f}%")
            print(f"  총 재고 가치: {stat['total_value']:,.0f}원")
        
        # 최근 등록 상품
        recent = await self.conn.fetch("""
            SELECT 
                marketplace_name,
                product_name,
                selling_price,
                margin_rate,
                created_at
            FROM marketplace_products
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        print("\n최근 등록 상품:")
        for item in recent:
            print(f"  [{item['marketplace_name']}] {item['product_name'][:40]}... - {item['selling_price']:,}원 (마진: {item['margin_rate']:.1f}%)")
        
        return stats
        
    async def main(self):
        """메인 실행 함수"""
        print("통합 마켓플레이스 시스템")
        print(f"시작 시간: {datetime.now()}")
        
        try:
            # 데이터베이스 연결
            await self.connect_db()
            
            # 테이블 설정
            await self.setup_tables()
            
            # 마켓플레이스 동기화
            sync_results = await self.sync_all_marketplaces()
            
            print("\n" + "=" * 60)
            print("동기화 결과")
            print("=" * 60)
            print(f"총 처리: {sync_results['total']}건")
            print(f"성공: {sync_results['success']}건")
            print(f"실패: {sync_results['failed']}건")
            
            # 마켓플레이스 현황 조회
            await self.get_marketplace_status()
            
            # 결과 저장
            with open('integrated_marketplace_result.json', 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'sync_results': sync_results,
                    'notes': {
                        'info': '도매처 상품을 마켓플레이스에 등록하는 통합 시스템',
                        'margin': '기본 30% 마진 적용',
                        'status': '실제 API 연동은 인증 문제로 시뮬레이션으로 처리'
                    }
                }, f, ensure_ascii=False, indent=2)
            
            print(f"\n완료 시간: {datetime.now()}")
            print("\n결과가 integrated_marketplace_result.json에 저장되었습니다.")
            
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_db()


if __name__ == "__main__":
    system = IntegratedMarketplaceSystem()
    asyncio.run(system.main())