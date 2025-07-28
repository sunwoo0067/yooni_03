#!/usr/bin/env python3
"""
마켓플레이스 통합 대시보드
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import asyncpg
from dotenv import load_dotenv

# stdout 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()


class MarketplaceDashboard:
    """마켓플레이스 통합 대시보드"""
    
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
        
    async def close_db(self):
        """데이터베이스 연결 종료"""
        if self.conn:
            await self.conn.close()
            
    async def get_overall_statistics(self):
        """전체 통계 조회"""
        # 도매처 통계
        wholesaler_stats = await self.conn.fetch("""
            SELECT 
                wholesaler_name,
                COUNT(*) as product_count,
                SUM(price * stock_quantity) as inventory_value,
                AVG(price) as avg_price
            FROM simple_collected_products
            WHERE is_active = true
            GROUP BY wholesaler_name
        """)
        
        # 마켓플레이스 통계
        marketplace_stats = await self.conn.fetch("""
            SELECT 
                marketplace_name,
                COUNT(*) as product_count,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_count,
                AVG(margin_rate) as avg_margin,
                SUM(selling_price * stock_quantity) as total_value
            FROM marketplace_products
            GROUP BY marketplace_name
        """)
        
        # 전체 요약
        total_wholesaler_products = await self.conn.fetchval(
            "SELECT COUNT(*) FROM simple_collected_products WHERE is_active = true"
        )
        total_marketplace_products = await self.conn.fetchval(
            "SELECT COUNT(*) FROM marketplace_products WHERE status = 'ACTIVE'"
        )
        
        return {
            'wholesalers': [dict(row) for row in wholesaler_stats],
            'marketplaces': [dict(row) for row in marketplace_stats],
            'summary': {
                'total_wholesaler_products': total_wholesaler_products,
                'total_marketplace_products': total_marketplace_products
            }
        }
        
    async def get_profit_analysis(self):
        """수익성 분석"""
        # 마진율별 상품 분포
        margin_distribution = await self.conn.fetch("""
            SELECT 
                CASE 
                    WHEN margin_rate < 0 THEN '손실'
                    WHEN margin_rate < 10 THEN '0-10%'
                    WHEN margin_rate < 20 THEN '10-20%'
                    WHEN margin_rate < 30 THEN '20-30%'
                    ELSE '30% 이상'
                END as margin_range,
                COUNT(*) as product_count,
                AVG(margin_rate) as avg_margin
            FROM marketplace_products
            WHERE status = 'ACTIVE'
            GROUP BY margin_range
            ORDER BY avg_margin
        """)
        
        # 고수익 상품 TOP 10
        high_profit_products = await self.conn.fetch("""
            SELECT 
                product_name,
                marketplace_name,
                original_price,
                selling_price,
                margin_rate,
                (selling_price - original_price) * stock_quantity as total_profit
            FROM marketplace_products
            WHERE status = 'ACTIVE'
            ORDER BY total_profit DESC
            LIMIT 10
        """)
        
        return {
            'margin_distribution': [dict(row) for row in margin_distribution],
            'high_profit_products': [dict(row) for row in high_profit_products]
        }
        
    async def get_inventory_status(self):
        """재고 현황 분석"""
        # 도매처별 재고 현황
        wholesaler_inventory = await self.conn.fetch("""
            SELECT 
                wholesaler_name,
                COUNT(*) as total_products,
                COUNT(CASE WHEN stock_quantity = 0 THEN 1 END) as out_of_stock,
                COUNT(CASE WHEN stock_quantity < 10 THEN 1 END) as low_stock,
                SUM(stock_quantity) as total_stock
            FROM simple_collected_products
            WHERE is_active = true
            GROUP BY wholesaler_name
        """)
        
        # 재고 부족 상품
        low_stock_products = await self.conn.fetch("""
            SELECT 
                mp.product_name,
                mp.marketplace_name,
                mp.stock_quantity,
                mp.selling_price
            FROM marketplace_products mp
            WHERE mp.status = 'ACTIVE'
            AND mp.stock_quantity < 10
            ORDER BY mp.stock_quantity, mp.selling_price DESC
            LIMIT 20
        """)
        
        return {
            'wholesaler_inventory': [dict(row) for row in wholesaler_inventory],
            'low_stock_products': [dict(row) for row in low_stock_products]
        }
        
    async def generate_dashboard_report(self):
        """대시보드 리포트 생성"""
        print("\n" + "=" * 80)
        print(" 마켓플레이스 통합 대시보드 ")
        print("=" * 80)
        print(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 전체 통계
        stats = await self.get_overall_statistics()
        
        print("\n[ 1. 전체 현황 ]")
        print("-" * 40)
        print(f"도매처 상품 총계: {stats['summary']['total_wholesaler_products']:,}개")
        print(f"마켓 등록 상품 총계: {stats['summary']['total_marketplace_products']:,}개")
        
        print("\n도매처별 현황:")
        for ws in stats['wholesalers']:
            print(f"  {ws['wholesaler_name']}: {ws['product_count']}개 (재고가치: {ws['inventory_value']:,.0f}원)")
        
        print("\n마켓플레이스별 현황:")
        for mp in stats['marketplaces']:
            print(f"  {mp['marketplace_name']}: {mp['active_count']}개 활성 (평균마진: {mp['avg_margin']:.1f}%)")
        
        # 2. 수익성 분석
        profit = await self.get_profit_analysis()
        
        print("\n[ 2. 수익성 분석 ]")
        print("-" * 40)
        print("마진율 분포:")
        for md in profit['margin_distribution']:
            print(f"  {md['margin_range']}: {md['product_count']}개 (평균 {md['avg_margin']:.1f}%)")
        
        print("\n고수익 상품 TOP 5:")
        for i, hp in enumerate(profit['high_profit_products'][:5], 1):
            print(f"  {i}. {hp['product_name'][:40]}...")
            print(f"     [{hp['marketplace_name']}] 원가: {hp['original_price']:,}원 → 판매가: {hp['selling_price']:,}원 (마진: {hp['margin_rate']:.1f}%)")
        
        # 3. 재고 현황
        inventory = await self.get_inventory_status()
        
        print("\n[ 3. 재고 현황 ]")
        print("-" * 40)
        print("도매처별 재고:")
        for wi in inventory['wholesaler_inventory']:
            oos_rate = (wi['out_of_stock'] / wi['total_products'] * 100) if wi['total_products'] > 0 else 0
            print(f"  {wi['wholesaler_name']}: 총 {wi['total_products']}개 (품절: {wi['out_of_stock']}개, {oos_rate:.1f}%)")
        
        if inventory['low_stock_products']:
            print("\n재고 부족 상품 (10개 미만):")
            for ls in inventory['low_stock_products'][:5]:
                print(f"  - {ls['product_name'][:40]}... [{ls['marketplace_name']}] 재고: {ls['stock_quantity']}개")
        
        # 결과 저장
        dashboard_data = {
            'generated_at': datetime.now().isoformat(),
            'statistics': stats,
            'profit_analysis': profit,
            'inventory_status': inventory
        }
        
        with open('marketplace_dashboard_report.json', 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)
        
        print("\n" + "=" * 80)
        print("대시보드 리포트가 marketplace_dashboard_report.json에 저장되었습니다.")
        
        return dashboard_data
        
    async def main(self):
        """메인 실행 함수"""
        try:
            await self.connect_db()
            await self.generate_dashboard_report()
        except Exception as e:
            print(f"오류 발생: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_db()


if __name__ == "__main__":
    dashboard = MarketplaceDashboard()
    asyncio.run(dashboard.main())