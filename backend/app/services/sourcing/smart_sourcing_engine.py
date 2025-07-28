"""
스마트 소싱 엔진 (벤치마크 테이블 활용)
모든 시장 데이터를 통합하여 최적의 소싱 기회 발굴
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import asyncio
import logging

from .market_data_collector_v2 import MarketDataCollector
from .trend_analyzer import TrendAnalyzer
from .ai_product_analyzer import AIProductAnalyzer
from ..benchmark.benchmark_manager import BenchmarkManager
from ...models.benchmark import BenchmarkProduct, BenchmarkKeyword, BenchmarkMarketTrend


class SmartSourcingEngine:
    """통합 소싱 분석 엔진 (벤치마크 기반)"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.market_collector = MarketDataCollector(db, logger)
        self.trend_analyzer = TrendAnalyzer(db, logger)
        self.ai_analyzer = AIProductAnalyzer(db, logger)
        self.benchmark_manager = BenchmarkManager(db)
        
    async def run_comprehensive_sourcing(self) -> Dict[str, Any]:
        """포괄적인 소싱 분석 실행"""
        self.logger.info("스마트 소싱 분석 시작...")
        
        # 1. 시장 데이터 수집 (벤치마크 테이블에 저장됨)
        async with self.market_collector:
            market_data = await self.market_collector.collect_all_markets()
        
        # 2. 트렌드 분석
        trend_analysis = await self.trend_analyzer.analyze_current_trends()
        
        # 3. 벤치마크 데이터 기반 기회 발굴
        opportunities = await self._identify_opportunities_from_benchmark()
        
        # 4. AI 분석으로 기회 평가
        evaluated_opportunities = []
        for opp in opportunities[:20]:  # 상위 20개만 상세 분석
            ai_analysis = await self.ai_analyzer.analyze_product_potential(opp)
            evaluated_opportunities.append({
                **opp,
                'ai_analysis': ai_analysis
            })
        
        # 5. 최종 추천 생성
        recommendations = await self._generate_sourcing_recommendations(
            evaluated_opportunities, trend_analysis
        )
        
        return {
            'analysis_date': datetime.now(),
            'market_summary': await self._get_market_summary(),
            'trend_insights': trend_analysis,
            'opportunities': evaluated_opportunities,
            'recommendations': recommendations,
            'action_items': await self._generate_action_items(recommendations)
        }
        
    async def _identify_opportunities_from_benchmark(self) -> List[Dict[str, Any]]:
        """벤치마크 데이터에서 기회 발굴"""
        opportunities = []
        
        # 1. 급성장 상품 찾기 (모든 마켓에서)
        trending_products = await self.benchmark_manager.get_trending_products(days=7)
        
        for item in trending_products:
            product = item['product']
            opportunity = {
                'type': 'trending_product',
                'product_name': product.product_name,
                'category': product.main_category,
                'current_sales': product.monthly_sales,
                'price': product.sale_price,
                'market': product.market_type,
                'score': self._calculate_opportunity_score(product),
                'reasons': await self._analyze_opportunity_reasons(product)
            }
            opportunities.append(opportunity)
        
        # 2. 가격 차이가 큰 상품 찾기 (차익거래 기회)
        arbitrage_opps = await self._find_arbitrage_opportunities()
        opportunities.extend(arbitrage_opps)
        
        # 3. 공백 시장 찾기 (경쟁이 적은 카테고리)
        gap_markets = await self._find_market_gaps()
        opportunities.extend(gap_markets)
        
        # 4. 계절성 상품 기회
        seasonal_opps = await self._find_seasonal_opportunities()
        opportunities.extend(seasonal_opps)
        
        # 점수 기준으로 정렬
        opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return opportunities
        
    async def _find_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """차익거래 기회 찾기"""
        opportunities = []
        
        # 같은 상품이 다른 마켓에서 다른 가격으로 판매되는 경우
        # 상품명 유사도 기반으로 찾기
        categories = ['패션의류', '뷰티', '디지털/가전']
        
        for category in categories:
            products = await self.benchmark_manager.get_category_bestsellers(category, limit=50)
            
            # 상품명으로 그룹핑하여 가격 비교
            for product in products:
                similar_products = await self.benchmark_manager.find_similar_products(
                    product.product_name,
                    category=category,
                    price_range=(product.sale_price * 0.5, product.sale_price * 2.0)
                )
                
                if len(similar_products) >= 2:
                    prices = [p.sale_price for p in similar_products]
                    min_price = min(prices)
                    max_price = max(prices)
                    
                    if max_price > min_price * 1.3:  # 30% 이상 차이
                        opportunities.append({
                            'type': 'arbitrage',
                            'product_name': product.product_name,
                            'category': category,
                            'min_price': min_price,
                            'max_price': max_price,
                            'profit_margin': (max_price - min_price) / min_price * 100,
                            'markets': [p.market_type for p in similar_products],
                            'score': (max_price - min_price) / min_price * 50,  # 수익률 기반 점수
                            'reasons': [
                                f"가격 차이: {int((max_price - min_price) / min_price * 100)}%",
                                f"최저가: {min_price:,}원, 최고가: {max_price:,}원"
                            ]
                        })
        
        return opportunities
        
    async def _find_market_gaps(self) -> List[Dict[str, Any]]:
        """시장 공백 찾기"""
        opportunities = []
        
        # 각 카테고리별 상품 수와 경쟁 강도 분석
        categories = self.db.query(
            BenchmarkProduct.main_category,
            func.count(BenchmarkProduct.id).label('product_count'),
            func.avg(BenchmarkProduct.monthly_sales).label('avg_sales')
        ).group_by(
            BenchmarkProduct.main_category
        ).all()
        
        for cat in categories:
            if cat.product_count < 50 and cat.avg_sales > 100:
                # 상품 수는 적지만 평균 판매량이 높은 카테고리
                opportunities.append({
                    'type': 'market_gap',
                    'category': cat.main_category,
                    'product_count': cat.product_count,
                    'avg_monthly_sales': int(cat.avg_sales),
                    'score': (1000 / cat.product_count) * (cat.avg_sales / 100),
                    'reasons': [
                        f"낮은 경쟁도: 상품 수 {cat.product_count}개",
                        f"높은 수요: 평균 월 판매 {int(cat.avg_sales)}개"
                    ]
                })
        
        return opportunities
        
    async def _find_seasonal_opportunities(self) -> List[Dict[str, Any]]:
        """계절성 상품 기회 찾기"""
        opportunities = []
        current_month = datetime.now().month
        
        # 계절별 카테고리 매핑
        seasonal_categories = {
            'summer': [6, 7, 8],  # 여름
            'winter': [12, 1, 2],  # 겨울
            'spring': [3, 4, 5],   # 봄
            'fall': [9, 10, 11]    # 가을
        }
        
        # 현재 계절 확인
        current_season = None
        for season, months in seasonal_categories.items():
            if current_month in months:
                current_season = season
                break
        
        # 계절 상품 키워드
        seasonal_keywords = {
            'summer': ['에어컨', '선풍기', '수영복', '선크림', '샌들'],
            'winter': ['패딩', '히터', '가습기', '목도리', '부츠'],
            'spring': ['미세먼지', '마스크', '화분', '운동화', '가디건'],
            'fall': ['니트', '자켓', '등산', '캠핑', '따뜻한']
        }
        
        if current_season and current_season in seasonal_keywords:
            for keyword in seasonal_keywords[current_season]:
                # 벤치마크 키워드 테이블에서 트렌드 확인
                keyword_trend = self.db.query(BenchmarkKeyword).filter(
                    BenchmarkKeyword.keyword == keyword
                ).first()
                
                if keyword_trend and keyword_trend.growth_rate > 20:
                    opportunities.append({
                        'type': 'seasonal',
                        'keyword': keyword,
                        'season': current_season,
                        'growth_rate': keyword_trend.growth_rate,
                        'search_volume': keyword_trend.search_volume,
                        'score': keyword_trend.trend_score,
                        'reasons': [
                            f"{current_season} 시즌 상품",
                            f"성장률: {keyword_trend.growth_rate}%",
                            f"월 검색량: {keyword_trend.search_volume:,}"
                        ]
                    })
        
        return opportunities
        
    def _calculate_opportunity_score(self, product: BenchmarkProduct) -> float:
        """기회 점수 계산"""
        score = 0.0
        
        # 판매량 기반 점수
        if product.monthly_sales > 1000:
            score += 30
        elif product.monthly_sales > 500:
            score += 20
        elif product.monthly_sales > 100:
            score += 10
        
        # 리뷰 기반 점수
        if product.review_count > 100:
            score += 20
        
        # 평점 기반 점수
        if product.rating >= 4.5:
            score += 20
        elif product.rating >= 4.0:
            score += 10
        
        # 할인율 기반 점수
        if product.discount_rate > 30:
            score += 15
        
        # 베스트셀러 순위 기반 점수
        if product.bestseller_rank <= 10:
            score += 25
        elif product.bestseller_rank <= 50:
            score += 15
        elif product.bestseller_rank <= 100:
            score += 5
        
        return score
        
    async def _analyze_opportunity_reasons(self, product: BenchmarkProduct) -> List[str]:
        """기회 요인 분석"""
        reasons = []
        
        if product.monthly_sales > 1000:
            reasons.append(f"높은 판매량: 월 {product.monthly_sales:,}개")
        
        if product.bestseller_rank <= 10:
            reasons.append(f"베스트셀러 {product.bestseller_rank}위")
        
        if product.rating >= 4.5:
            reasons.append(f"높은 평점: {product.rating}")
        
        if product.discount_rate > 30:
            reasons.append(f"높은 할인율: {product.discount_rate}%")
        
        # 가격 트렌드 확인
        price_trends = await self.benchmark_manager.get_price_trends(
            product.market_product_id,
            product.market_type,
            days=7
        )
        
        if price_trends and len(price_trends) >= 2:
            first_price = price_trends[0]['sale_price']
            last_price = price_trends[-1]['sale_price']
            if last_price < first_price:
                reasons.append("가격 하락 추세")
        
        return reasons
        
    async def _get_market_summary(self) -> Dict[str, Any]:
        """시장 요약 정보"""
        # 전체 벤치마크 상품 수
        total_products = self.db.query(func.count(BenchmarkProduct.id)).scalar()
        
        # 마켓별 상품 수
        market_distribution = self.db.query(
            BenchmarkProduct.market_type,
            func.count(BenchmarkProduct.id).label('count')
        ).group_by(BenchmarkProduct.market_type).all()
        
        # 카테고리별 평균 가격
        category_prices = self.db.query(
            BenchmarkProduct.main_category,
            func.avg(BenchmarkProduct.sale_price).label('avg_price')
        ).group_by(BenchmarkProduct.main_category).all()
        
        return {
            'total_products_tracked': total_products,
            'market_distribution': {m.market_type: m.count for m in market_distribution},
            'category_avg_prices': {c.main_category: int(c.avg_price) for c in category_prices},
            'last_updated': datetime.now()
        }
        
    async def _generate_sourcing_recommendations(
        self,
        opportunities: List[Dict[str, Any]],
        trend_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """소싱 추천 생성"""
        recommendations = []
        
        # 상위 10개 기회에 대해 구체적인 추천 생성
        for opp in opportunities[:10]:
            if opp['type'] == 'trending_product':
                rec = {
                    'priority': 'HIGH',
                    'action': 'immediate_sourcing',
                    'product': opp['product_name'],
                    'category': opp['category'],
                    'expected_monthly_sales': opp['current_sales'],
                    'recommended_price': opp['price'] * 0.95,  # 5% 낮은 가격
                    'investment_required': opp['price'] * 100,  # 100개 기준
                    'expected_roi': 25.0,  # 예상 수익률
                    'risk_level': 'MEDIUM',
                    'reasoning': opp['reasons']
                }
            elif opp['type'] == 'arbitrage':
                rec = {
                    'priority': 'VERY_HIGH',
                    'action': 'arbitrage_trading',
                    'product': opp['product_name'],
                    'buy_from': '최저가 마켓',
                    'sell_to': '최고가 마켓',
                    'profit_margin': opp['profit_margin'],
                    'investment_required': opp['min_price'] * 50,
                    'expected_roi': opp['profit_margin'] * 0.7,  # 수수료 고려
                    'risk_level': 'LOW',
                    'reasoning': opp['reasons']
                }
            elif opp['type'] == 'market_gap':
                rec = {
                    'priority': 'MEDIUM',
                    'action': 'market_entry',
                    'category': opp['category'],
                    'market_size': opp['avg_monthly_sales'] * opp['product_count'],
                    'competition_level': 'LOW',
                    'recommended_products': 5,  # 추천 상품 수
                    'investment_required': 1000000,  # 예상 초기 투자
                    'expected_roi': 30.0,
                    'risk_level': 'MEDIUM',
                    'reasoning': opp['reasons']
                }
            else:  # seasonal
                rec = {
                    'priority': 'HIGH',
                    'action': 'seasonal_preparation',
                    'keyword': opp['keyword'],
                    'season': opp['season'],
                    'growth_rate': opp['growth_rate'],
                    'recommended_stock': 200,  # 추천 재고
                    'investment_required': 2000000,
                    'expected_roi': 35.0,
                    'risk_level': 'MEDIUM',
                    'reasoning': opp['reasons']
                }
            
            recommendations.append(rec)
        
        return recommendations
        
    async def _generate_action_items(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """실행 가능한 액션 아이템 생성"""
        action_items = []
        
        for idx, rec in enumerate(recommendations[:5]):  # 상위 5개만
            if rec['action'] == 'immediate_sourcing':
                action_items.append({
                    'order': idx + 1,
                    'task': f"{rec['product']} 소싱 시작",
                    'steps': [
                        "도매사이트에서 동일/유사 상품 검색",
                        f"목표 구매가: {int(rec['recommended_price'] * 0.6):,}원",
                        f"초기 구매 수량: 50개 (테스트)",
                        "상품 상세페이지 준비",
                        "3개 마켓에 동시 등록"
                    ],
                    'deadline': '3일 이내',
                    'expected_profit': int(rec['expected_roi'] * rec['investment_required'] / 100)
                })
            elif rec['action'] == 'arbitrage_trading':
                action_items.append({
                    'order': idx + 1,
                    'task': f"{rec['product']} 차익거래",
                    'steps': [
                        "최저가 마켓에서 즉시 구매",
                        "상품 검수 및 재포장",
                        "최고가 마켓에 프리미엄 등록",
                        f"목표 마진: {rec['profit_margin']:.1f}%"
                    ],
                    'deadline': '즉시',
                    'expected_profit': int(rec['expected_roi'] * rec['investment_required'] / 100)
                })
        
        return action_items