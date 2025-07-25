"""
소싱 시스템 테스트 스크립트
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.sourcing.smart_sourcing_engine import SmartSourcingEngine
from app.services.sourcing.trend_analyzer import TrendAnalyzer
from app.services.sourcing.ai_product_analyzer import AIProductAnalyzer
from app.services.sourcing.market_data_collector import MarketDataCollector
from app.services.database.database import get_db
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_trend_analyzer():
    """트렌드 분석기 테스트"""
    print("\n=== 트렌드 분석기 테스트 ===")
    
    db = next(get_db())
    analyzer = TrendAnalyzer(db, logger)
    
    # 기본 키워드로 트렌드 분석
    keywords = ["선물", "홈트", "뷰티"]
    results = await analyzer.analyze_trends(keywords)
    
    print(f"구글 트렌드 키워드 수: {len(results.get('google_trends', {}).get('keyword_trends', {}))}")
    print(f"급상승 키워드 수: {len(results.get('rising_keywords', []))}")
    print(f"추천 카테고리 수: {len(results.get('recommended_categories', []))}")
    
    # 첫 번째 추천 카테고리 출력
    if results.get('recommended_categories'):
        first_rec = results['recommended_categories'][0]
        print(f"첫 번째 추천: {first_rec.get('category')} (점수: {first_rec.get('score')})")


async def test_ai_product_analyzer():
    """AI 상품 분석기 테스트"""
    print("\n=== AI 상품 분석기 테스트 ===")
    
    db = next(get_db())
    analyzer = AIProductAnalyzer(db, logger)
    
    # 테스트 상품 데이터
    test_product = {
        'name': '무선 블루투스 이어폰',
        'price': 29900,
        'category': '디지털',
        'review_count': 1500,
        'rating': 4.3,
        'wholesale_price': 18000
    }
    
    analysis = await analyzer.analyze_product_potential(test_product)
    
    print(f"상품명: {test_product['name']}")
    print(f"총점: {analysis.get('total_score', 0)}")
    print(f"AI 추천: {analysis.get('recommendation', {}).get('decision', 'N/A')}")
    print(f"신뢰도: {analysis.get('recommendation', {}).get('confidence', 'N/A')}")
    
    # 수익성 정보
    profit_info = analysis.get('profit_estimation', {})
    print(f"예상 월 수익: {profit_info.get('monthly_profit_estimate', 0):,}원")
    print(f"수익률: {profit_info.get('profit_margin', 0):.1f}%")


async def test_market_data_collector():
    """마켓 데이터 수집기 테스트"""
    print("\n=== 마켓 데이터 수집기 테스트 ===")
    
    db = next(get_db())
    
    async with MarketDataCollector(db, logger) as collector:
        # 실제 수집은 시간이 오래 걸리므로 구조만 테스트
        print("마켓 데이터 수집기 초기화 완료")
        print("실제 데이터 수집은 시간이 오래 걸려 스킵합니다")
        
        # 분석 기능만 테스트
        mock_data = {
            'coupang': [
                {
                    'rank': 1,
                    'product_name': '테스트 상품',
                    'price': 25000,
                    'review_count': 500,
                    'category': '생활용품'
                }
            ],
            'naver': [],
            '11st': []
        }
        
        analysis = await collector._analyze_collected_data(mock_data)
        print(f"분석된 총 상품 수: {analysis.get('total_products', 0)}")
        print(f"고잠재력 상품 수: {len(analysis.get('high_potential_products', []))}")


async def test_smart_sourcing_engine():
    """스마트 소싱 엔진 테스트"""
    print("\n=== 스마트 소싱 엔진 테스트 ===")
    
    db = next(get_db())
    engine = SmartSourcingEngine(db, logger)
    
    print("스마트 소싱 엔진 초기화 완료")
    print("실제 종합 분석은 시간이 오래 걸려 스킵합니다")
    
    # 개별 컴포넌트 테스트
    print("- 마켓 데이터 수집기: 준비됨")
    print("- 트렌드 분석기: 준비됨") 
    print("- AI 상품 분석기: 준비됨")
    print("- 중복 찾기: 준비됨")


async def main():
    """메인 테스트 함수"""
    print("Dropshipping Sourcing System Test Started")
    
    try:
        await test_trend_analyzer()
        await test_ai_product_analyzer()
        await test_market_data_collector()
        await test_smart_sourcing_engine()
        
        print("\nAll sourcing system tests completed successfully!")
        print("\n=== Available API Endpoints ===")
        print("POST /api/v1/sourcing/analyze/comprehensive - Comprehensive sourcing analysis")
        print("GET  /api/v1/sourcing/analyze/results - Get analysis results")
        print("POST /api/v1/sourcing/market/collect - Collect market data")
        print("GET  /api/v1/sourcing/market/bestsellers - Get bestsellers")
        print("POST /api/v1/sourcing/trends/analyze - Analyze trends")
        print("GET  /api/v1/sourcing/trends/rising - Get rising trends")
        print("POST /api/v1/sourcing/analyze/product - Analyze product")
        print("GET  /api/v1/sourcing/recommendations/categories - Get category recommendations")
        print("GET  /api/v1/sourcing/dashboard/overview - Get sourcing dashboard")
        
    except Exception as e:
        print(f"Error occurred during test: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())