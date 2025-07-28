"""스마트 소싱 엔진 - 복합적인 소싱 추천 시스템"""
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np
from sqlalchemy.orm import Session

from .market_data_collector import MarketDataCollector
from .trend_analyzer import TrendAnalyzer
from .ai_product_analyzer import AIProductAnalyzer
from ...services.collection.duplicate_finder import DuplicateFinder
from ...models.product import Product
from ...models.wholesaler import WholesalerAccount


class SmartSourcingEngine:
    """복합 소싱 추천 엔진"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.market_collector = MarketDataCollector(db, logger)
        self.trend_analyzer = TrendAnalyzer(db, logger)
        self.ai_analyzer = AIProductAnalyzer(db, logger)
        self.duplicate_finder = DuplicateFinder(db, logger)
        
    async def run_comprehensive_sourcing(self) -> Dict[str, Any]:
        """종합 소싱 분석 실행"""
        self.logger.info("스마트 소싱 분석 시작")
        
        results = {
            'analysis_id': f"sourcing_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'started_at': datetime.now(),
            'market_analysis': {},
            'trend_analysis': {},
            'ai_recommendations': [],
            'sourcing_opportunities': [],
            'action_plan': {}
        }
        
        try:
            # 1. 마켓 데이터 수집 및 분석
            async with self.market_collector as collector:
                results['market_analysis'] = await collector.collect_all_markets()
                
            # 2. 트렌드 분석
            results['trend_analysis'] = await self.trend_analyzer.analyze_trends()
            
            # 3. 소싱 기회 발굴
            results['sourcing_opportunities'] = await self._identify_sourcing_opportunities(
                results['market_analysis'],
                results['trend_analysis']
            )
            
            # 4. AI 상품 분석 및 추천
            for opportunity in results['sourcing_opportunities'][:20]:  # 상위 20개
                ai_analysis = await self.ai_analyzer.analyze_product_potential(opportunity)
                results['ai_recommendations'].append(ai_analysis)
                
            # 5. 실행 계획 수립
            results['action_plan'] = await self._generate_action_plan(results)
            
            results['completed_at'] = datetime.now()
            results['success'] = True
            
        except Exception as e:
            self.logger.error(f"소싱 분석 중 오류: {str(e)}")
            results['error'] = str(e)
            results['success'] = False
            
        return results
        
    async def _identify_sourcing_opportunities(
        self,
        market_data: Dict[str, Any],
        trend_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """소싱 기회 발굴"""
        opportunities = []
        
        # 1. 베스트셀러 분석 기반 기회
        bestseller_opportunities = await self._analyze_bestsellers(market_data)
        opportunities.extend(bestseller_opportunities)
        
        # 2. 트렌드 키워드 기반 기회
        trend_opportunities = await self._analyze_trend_opportunities(trend_data)
        opportunities.extend(trend_opportunities)
        
        # 3. 갭 분석 기반 기회
        gap_opportunities = await self._find_market_gaps(market_data)
        opportunities.extend(gap_opportunities)
        
        # 4. 크로스 마켓 기회
        cross_market_opportunities = await self._find_cross_market_opportunities(market_data)
        opportunities.extend(cross_market_opportunities)
        
        # 중복 제거 및 점수 계산
        unique_opportunities = self._deduplicate_opportunities(opportunities)
        scored_opportunities = await self._score_opportunities(unique_opportunities)
        
        # 점수 순 정렬
        scored_opportunities.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_opportunities
        
    async def _analyze_bestsellers(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """베스트셀러 분석을 통한 소싱 기회"""
        opportunities = []
        
        # 고잠재력 상품 추출
        high_potential = market_data['analysis'].get('high_potential_products', [])
        
        for product in high_potential[:30]:  # 상위 30개
            # 도매처에서 유사 상품 검색
            wholesale_matches = await self._find_wholesale_matches(product)
            
            if wholesale_matches:
                opportunity = {
                    'type': 'bestseller_match',
                    'market_product': product,
                    'wholesale_options': wholesale_matches,
                    'profit_potential': self._calculate_profit_potential(
                        product['price'],
                        wholesale_matches[0]['wholesale_price']
                    ),
                    'competition_level': self._assess_competition_level(product),
                    'market_validation': True,
                    'source_confidence': 0.9
                }
                opportunities.append(opportunity)
                
        return opportunities
        
    async def _analyze_trend_opportunities(self, trend_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """트렌드 기반 소싱 기회"""
        opportunities = []
        
        # 급상승 키워드
        rising_keywords = trend_data.get('rising_keywords', [])
        
        for keyword_data in rising_keywords[:20]:
            # 키워드와 관련된 상품 검색
            related_products = await self._search_products_by_keyword(
                keyword_data['keyword']
            )
            
            if related_products:
                opportunity = {
                    'type': 'trend_based',
                    'trend_keyword': keyword_data,
                    'product_options': related_products[:10],
                    'trend_score': keyword_data['potential_score'],
                    'timing': 'early_stage' if keyword_data['potential_score'] > 80 else 'growing',
                    'risk_level': self._assess_trend_risk(keyword_data),
                    'source_confidence': 0.8
                }
                opportunities.append(opportunity)
                
        # 계절성 기회
        seasonal_keywords = trend_data.get('seasonal_keywords', [])
        
        for seasonal in seasonal_keywords:
            if seasonal['yoy_growth'] > 20:  # 전년 대비 20% 이상 성장
                seasonal_products = await self._search_products_by_keyword(
                    seasonal['keyword']
                )
                
                if seasonal_products:
                    opportunity = {
                        'type': 'seasonal',
                        'seasonal_data': seasonal,
                        'product_options': seasonal_products[:5],
                        'preparation_time': self._calculate_prep_time(seasonal),
                        'expected_peak': seasonal['peak_month'],
                        'source_confidence': 0.85
                    }
                    opportunities.append(opportunity)
                    
        return opportunities
        
    async def _find_market_gaps(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """시장 갭 분석"""
        opportunities = []
        
        # 카테고리별 분석
        for market, categories in market_data['analysis']['top_categories'].items():
            for category, stats in categories.items():
                # 리뷰 대비 상품 수가 적은 카테고리 (수요 > 공급)
                if stats['avg_review'] > 100 and stats['count'] < 50:
                    gap_products = await self._find_gap_products(category, market)
                    
                    if gap_products:
                        opportunity = {
                            'type': 'market_gap',
                            'category': category,
                            'market': market,
                            'gap_analysis': {
                                'demand_indicator': stats['avg_review'],
                                'supply_count': stats['count'],
                                'gap_score': stats['avg_review'] / max(stats['count'], 1)
                            },
                            'suggested_products': gap_products,
                            'entry_barrier': 'low',
                            'source_confidence': 0.75
                        }
                        opportunities.append(opportunity)
                        
        return opportunities
        
    async def _find_cross_market_opportunities(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """크로스 마켓 기회 (한 마켓에서 잘 팔리지만 다른 마켓에는 없는 상품)"""
        opportunities = []
        
        markets = ['coupang', 'naver', '11st']
        
        for source_market in markets:
            source_products = market_data['market_data'].get(source_market, [])
            
            for product in source_products[:20]:  # 각 마켓 상위 20개
                # 다른 마켓에서 검색
                for target_market in markets:
                    if target_market != source_market:
                        exists = await self._check_product_exists_in_market(
                            product['product_name'],
                            target_market,
                            market_data['market_data'].get(target_market, [])
                        )
                        
                        if not exists:
                            opportunity = {
                                'type': 'cross_market',
                                'source_market': source_market,
                                'target_market': target_market,
                                'product': product,
                                'market_expansion': True,
                                'competition_free': True,
                                'source_confidence': 0.7
                            }
                            opportunities.append(opportunity)
                            
        return opportunities
        
    async def _find_wholesale_matches(self, market_product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """마켓 상품과 매칭되는 도매 상품 찾기"""
        # 상품명 키워드 추출
        keywords = self._extract_key_terms(market_product['product_name'])
        
        # 도매처에서 검색
        wholesale_products = []
        
        query = self.db.query(Product).filter(
            Product.is_active == True
        )
        
        # 키워드 매칭
        for keyword in keywords[:3]:  # 주요 키워드 3개
            query = query.filter(Product.name.ilike(f'%{keyword}%'))
            
        results = query.limit(10).all()
        
        for product in results:
            wholesale_products.append({
                'product_id': product.id,
                'name': product.name,
                'wholesale_price': product.wholesale_price or product.price * 0.6,
                'wholesaler_id': product.wholesaler_id,
                'match_score': self._calculate_match_score(
                    market_product['product_name'],
                    product.name
                )
            })
            
        # 매칭 점수 순 정렬
        wholesale_products.sort(key=lambda x: x['match_score'], reverse=True)
        
        return wholesale_products[:5]
        
    async def _search_products_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """키워드로 상품 검색"""
        products = self.db.query(Product).filter(
            Product.name.ilike(f'%{keyword}%'),
            Product.is_active == True
        ).limit(20).all()
        
        return [
            {
                'product_id': p.id,
                'name': p.name,
                'price': p.price,
                'wholesale_price': p.wholesale_price or p.price * 0.6,
                'category': p.category,
                'wholesaler_id': p.wholesaler_id
            }
            for p in products
        ]
        
    async def _score_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """소싱 기회 점수 계산"""
        for opp in opportunities:
            scores = {
                'market_validation': 0,
                'profit_potential': 0,
                'trend_alignment': 0,
                'competition': 0,
                'risk': 0
            }
            
            # 타입별 점수 계산
            if opp['type'] == 'bestseller_match':
                scores['market_validation'] = 90
                scores['profit_potential'] = opp.get('profit_potential', 0)
                scores['competition'] = 100 - (opp.get('competition_level', 0) * 20)
                
            elif opp['type'] == 'trend_based':
                scores['trend_alignment'] = opp.get('trend_score', 0)
                scores['market_validation'] = 60
                risk_map = {'low': 80, 'medium': 50, 'high': 20}
                scores['risk'] = risk_map.get(opp.get('risk_level', 'medium'), 50)
                
            elif opp['type'] == 'market_gap':
                scores['market_validation'] = 70
                scores['competition'] = 90  # 갭 시장은 경쟁 적음
                scores['profit_potential'] = 80
                
            elif opp['type'] == 'cross_market':
                scores['market_validation'] = 80
                scores['competition'] = 95  # 새 시장 진입
                scores['profit_potential'] = 70
                
            # 신뢰도 가중치 적용
            confidence = opp.get('source_confidence', 0.5)
            
            # 총점 계산
            total_score = sum(scores.values()) / len(scores) * confidence
            
            opp['scores'] = scores
            opp['total_score'] = round(total_score, 1)
            
        return opportunities
        
    async def _generate_action_plan(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """실행 계획 수립"""
        top_opportunities = analysis_results['ai_recommendations'][:10]
        
        action_plan = {
            'immediate_actions': [],
            'short_term_actions': [],
            'monitoring_items': [],
            'investment_plan': {},
            'risk_mitigation': []
        }
        
        total_investment = 0
        expected_monthly_profit = 0
        
        for i, rec in enumerate(top_opportunities):
            if rec['recommendation']['decision'] in ['STRONG_BUY', 'BUY']:
                # 즉시 실행 항목
                action = {
                    'priority': i + 1,
                    'product': rec['product_info']['name'],
                    'action': '즉시 소싱 및 판매 시작',
                    'initial_quantity': self._recommend_initial_quantity(rec),
                    'investment': self._calculate_investment(rec),
                    'expected_profit': rec['profit_estimation']['monthly_profit_estimate'],
                    'key_steps': rec['recommendation']['action_items']
                }
                
                if rec['recommendation']['total_score'] >= 75:
                    action_plan['immediate_actions'].append(action)
                else:
                    action_plan['short_term_actions'].append(action)
                    
                total_investment += action['investment']
                expected_monthly_profit += action['expected_profit']
                
            elif rec['recommendation']['decision'] == 'CONSIDER':
                # 모니터링 항목
                monitor_item = {
                    'product': rec['product_info']['name'],
                    'reason': '추가 시장 검증 필요',
                    'monitor_metrics': ['판매량 추이', '경쟁사 동향', '가격 변동'],
                    'review_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
                }
                action_plan['monitoring_items'].append(monitor_item)
                
        # 투자 계획
        action_plan['investment_plan'] = {
            'total_required': total_investment,
            'phased_approach': self._create_phased_investment(total_investment),
            'expected_monthly_return': expected_monthly_profit,
            'roi_estimate': (expected_monthly_profit / max(total_investment, 1)) * 100,
            'break_even_months': max(1, int(total_investment / max(expected_monthly_profit, 1)))
        }
        
        # 리스크 완화 전략
        action_plan['risk_mitigation'] = [
            "단계적 투자로 리스크 분산",
            "베스트셀러 검증 상품 우선 진입",
            "다양한 카테고리로 포트폴리오 구성",
            "재고 회전율 높은 상품 중심 운영",
            "시장 반응 보고 빠른 피벗"
        ]
        
        return action_plan
        
    def _deduplicate_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 기회 제거"""
        seen = set()
        unique = []
        
        for opp in opportunities:
            # 상품명 기반 중복 체크
            if opp['type'] in ['bestseller_match', 'trend_based']:
                key = opp.get('market_product', {}).get('product_name', '') or \
                      opp.get('trend_keyword', {}).get('keyword', '')
            else:
                key = str(opp)
                
            if key not in seen:
                seen.add(key)
                unique.append(opp)
                
        return unique
        
    def _calculate_profit_potential(self, market_price: float, wholesale_price: float) -> float:
        """수익 잠재력 계산"""
        # 예상 판매가 (마켓 가격의 90%)
        selling_price = market_price * 0.9
        
        # 비용 (도매가 + 수수료 + 배송비)
        total_cost = wholesale_price + (selling_price * 0.15) + 3000
        
        # 마진율
        margin = ((selling_price - total_cost) / selling_price) * 100
        
        return max(0, min(100, margin))
        
    def _assess_competition_level(self, product: Dict[str, Any]) -> int:
        """경쟁 수준 평가 (0-100)"""
        # 리뷰 수 기반 경쟁도
        reviews = product.get('review_count', 0)
        
        if reviews > 5000:
            return 100  # 매우 높음
        elif reviews > 1000:
            return 80
        elif reviews > 500:
            return 60
        elif reviews > 100:
            return 40
        else:
            return 20  # 낮음
            
    def _assess_trend_risk(self, keyword_data: Dict[str, Any]) -> str:
        """트렌드 리스크 평가"""
        rise_value = keyword_data.get('rise_percentage', 0)
        
        if rise_value > 5000:
            return 'high'  # 버블 가능성
        elif rise_value > 1000:
            return 'medium'
        else:
            return 'low'
            
    def _extract_key_terms(self, product_name: str) -> List[str]:
        """상품명에서 핵심 용어 추출"""
        # 불필요한 단어 제거
        stopwords = ['정품', '무료배송', '당일발송', '최저가', '인기', '추천']
        
        words = product_name.split()
        keywords = []
        
        for word in words:
            if len(word) > 1 and word not in stopwords:
                keywords.append(word)
                
        return keywords[:5]
        
    def _calculate_match_score(self, name1: str, name2: str) -> float:
        """상품명 매칭 점수"""
        # 간단한 자카드 유사도
        words1 = set(self._extract_key_terms(name1))
        words2 = set(self._extract_key_terms(name2))
        
        if not words1 or not words2:
            return 0
            
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) * 100
        
    def _recommend_initial_quantity(self, analysis: Dict[str, Any]) -> int:
        """초기 구매 수량 추천"""
        monthly_sales = analysis['sales_prediction']['predictions']['day_30']
        confidence = analysis['recommendation']['confidence']
        
        # 신뢰도에 따른 보수적 접근
        confidence_multiplier = {
            '매우 높음': 0.5,
            '높음': 0.3,
            '보통': 0.2,
            '낮음': 0.1
        }
        
        multiplier = confidence_multiplier.get(confidence, 0.1)
        
        # 2주치 재고 추천
        recommended = int(monthly_sales * 0.5 * multiplier)
        
        # 최소/최대 제한
        return max(10, min(recommended, 200))
        
    def _calculate_investment(self, analysis: Dict[str, Any]) -> int:
        """필요 투자금 계산"""
        wholesale_price = analysis['product_info'].get('wholesale_price', 20000)
        initial_qty = self._recommend_initial_quantity(analysis)
        
        # 상품 구매 비용 + 운영 자금 20%
        return int(wholesale_price * initial_qty * 1.2)
        
    def _create_phased_investment(self, total: int) -> List[Dict[str, Any]]:
        """단계별 투자 계획"""
        if total <= 1000000:
            return [{
                'phase': 1,
                'amount': total,
                'timing': '즉시',
                'focus': '테스트 판매'
            }]
        else:
            return [
                {
                    'phase': 1,
                    'amount': int(total * 0.3),
                    'timing': '즉시',
                    'focus': '초기 테스트'
                },
                {
                    'phase': 2,
                    'amount': int(total * 0.4),
                    'timing': '2주 후',
                    'focus': '검증 후 확대'
                },
                {
                    'phase': 3,
                    'amount': int(total * 0.3),
                    'timing': '1개월 후',
                    'focus': '안정화'
                }
            ]
            
    async def _check_product_exists_in_market(
        self,
        product_name: str,
        market: str,
        market_products: List[Dict[str, Any]]
    ) -> bool:
        """특정 마켓에 상품 존재 여부 확인"""
        keywords = self._extract_key_terms(product_name)
        
        for market_product in market_products:
            market_keywords = self._extract_key_terms(market_product.get('product_name', ''))
            
            # 키워드 2개 이상 일치하면 존재한다고 판단
            if len(set(keywords) & set(market_keywords)) >= 2:
                return True
                
        return False
        
    async def _find_gap_products(self, category: str, market: str) -> List[Dict[str, Any]]:
        """갭 시장을 위한 상품 제안"""
        # 해당 카테고리의 도매 상품 검색
        products = self.db.query(Product).filter(
            Product.category == category,
            Product.is_active == True
        ).limit(10).all()
        
        suggestions = []
        for product in products:
            suggestions.append({
                'product_id': product.id,
                'name': product.name,
                'wholesale_price': product.wholesale_price or product.price * 0.6,
                'gap_fit_score': np.random.randint(70, 95)  # 실제로는 더 정교한 계산
            })
            
        return suggestions
        
    def _calculate_prep_time(self, seasonal_data: Dict[str, Any]) -> str:
        """시즌 준비 시간 계산"""
        peak_month = seasonal_data.get('peak_month', 0)
        current_month = datetime.now().month
        
        months_until_peak = (peak_month - current_month) % 12
        
        if months_until_peak <= 1:
            return "즉시 준비 필요"
        elif months_until_peak <= 2:
            return "1개월 내 준비"
        else:
            return f"{months_until_peak-1}개월 후 준비 시작"