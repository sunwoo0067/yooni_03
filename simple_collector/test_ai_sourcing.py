"""
AI 기반 상품 소싱 테스트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from database.connection import SessionLocal
from services.ai.trend_analyzer import TrendAnalyzer
from services.ai.profit_predictor import ProfitPredictor
from services.ai.product_recommender import ProductRecommender
from utils.logger import app_logger


async def test_trend_analysis():
    """트렌드 분석 테스트"""
    app_logger.info("=== 트렌드 분석 테스트 시작 ===")
    
    db = SessionLocal()
    try:
        analyzer = TrendAnalyzer(db)
        
        # 시장 트렌드 분석
        trends = await analyzer.analyze_market_trends(days=7)
        
        if trends['status'] == 'success':
            app_logger.info(f"분석된 상품 수: {trends['total_products']}")
            
            # 카테고리 트렌드
            if trends.get('category_trends'):
                app_logger.info("\n카테고리 트렌드:")
                for cat in trends['category_trends'][:3]:
                    app_logger.info(f"  - {cat['category']}: 점수 {cat['trend_score']}")
            
            # 급상승 상품
            if trends.get('rising_products'):
                app_logger.info("\n급상승 상품:")
                for product in trends['rising_products'][:3]:
                    app_logger.info(f"  - {product['product_name'][:30]}... (순위 {product['rank_change']}위 상승)")
        else:
            app_logger.warning("트렌드 데이터가 없습니다")
            
    except Exception as e:
        app_logger.error(f"트렌드 분석 오류: {e}")
    finally:
        db.close()


def test_profit_prediction():
    """수익성 예측 테스트"""
    app_logger.info("\n=== 수익성 예측 테스트 시작 ===")
    
    db = SessionLocal()
    try:
        from database.models_v2 import WholesaleProduct
        
        predictor = ProfitPredictor(db)
        
        # 샘플 상품 조회
        sample_products = db.query(WholesaleProduct).filter(
            WholesaleProduct.wholesale_price > 0
        ).limit(5).all()
        
        if sample_products:
            app_logger.info(f"테스트할 상품 수: {len(sample_products)}")
            
            for product in sample_products:
                analysis = predictor.calculate_profit_potential(product)
                
                app_logger.info(f"\n상품: {product.product_name[:30]}...")
                app_logger.info(f"  도매가: {product.wholesale_price:,}원")
                app_logger.info(f"  추천 판매가: {analysis['recommended_price']:,}원")
                app_logger.info(f"  예상 순수익: {analysis['net_profit']:,}원")
                app_logger.info(f"  수익성 점수: {analysis['profit_score']}점")
                app_logger.info(f"  추천: {analysis['recommendation']}")
        else:
            app_logger.warning("분석할 상품이 없습니다")
            
    except Exception as e:
        app_logger.error(f"수익성 예측 오류: {e}")
    finally:
        db.close()


async def test_product_recommendations():
    """상품 추천 테스트"""
    app_logger.info("\n=== 상품 추천 테스트 시작 ===")
    
    db = SessionLocal()
    try:
        recommender = ProductRecommender(db)
        
        # 균형 추천
        recommendations = await recommender.get_recommendations(
            recommendation_type='balanced',
            limit=5
        )
        
        if recommendations['status'] == 'success':
            app_logger.info(f"추천 상품 수: {recommendations['count']}")
            
            for idx, rec in enumerate(recommendations['recommendations'], 1):
                app_logger.info(f"\n[추천 {idx}]")
                app_logger.info(f"상품명: {rec['product_name']}")
                app_logger.info(f"공급사: {rec['supplier']}")
                app_logger.info(f"카테고리: {rec['category']}")
                app_logger.info(f"도매가: {rec['wholesale_price']:,}원")
                app_logger.info(f"추천 점수: {rec['recommendation_score']}")
                app_logger.info(f"추천 사유: {rec['reason']}")
        else:
            app_logger.warning("추천을 생성할 수 없습니다")
            
    except Exception as e:
        app_logger.error(f"상품 추천 오류: {e}")
    finally:
        db.close()


def test_category_opportunities():
    """카테고리 기회 분석 테스트"""
    app_logger.info("\n=== 카테고리 기회 분석 테스트 ===")
    
    db = SessionLocal()
    try:
        recommender = ProductRecommender(db)
        
        opportunities = recommender.get_category_opportunities()
        
        if opportunities:
            app_logger.info(f"분석된 카테고리 수: {len(opportunities)}")
            
            for opp in opportunities[:3]:
                app_logger.info(f"\n카테고리: {opp['category']}")
                app_logger.info(f"  시장 잠재력: {opp['market_potential']}")
                app_logger.info(f"  베스트셀러 수: {opp['current_bestsellers']}")
                app_logger.info(f"  도매 상품 수: {opp['wholesale_available']}")
                app_logger.info(f"  평균 수익성: {opp['avg_profit_score']}")
                app_logger.info(f"  기회 점수: {opp['opportunity_score']}")
                app_logger.info(f"  추천: {opp['recommendation']}")
        else:
            app_logger.warning("카테고리 기회를 분석할 수 없습니다")
            
    except Exception as e:
        app_logger.error(f"카테고리 기회 분석 오류: {e}")
    finally:
        db.close()


async def main():
    """메인 테스트 함수"""
    app_logger.info("=== AI 기반 상품 소싱 테스트 시작 ===")
    app_logger.info(f"테스트 시작 시간: {datetime.now()}")
    
    # 1. 트렌드 분석
    await test_trend_analysis()
    
    # 2. 수익성 예측
    test_profit_prediction()
    
    # 3. 상품 추천
    await test_product_recommendations()
    
    # 4. 카테고리 기회
    test_category_opportunities()
    
    app_logger.info("\n=== 테스트 완료 ===")
    app_logger.info("웹 UI에서 AI 소싱 메뉴를 확인하세요.")
    app_logger.info("URL: http://localhost:4173/ai-sourcing")


if __name__ == "__main__":
    asyncio.run(main())