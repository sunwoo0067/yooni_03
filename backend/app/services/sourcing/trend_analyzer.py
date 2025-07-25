"""트렌드 분석 서비스 (구글트렌드, 네이버 데이터랩)"""
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from pytrends.request import TrendReq
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from ...models.trend import TrendKeyword, TrendData, KeywordAnalysis


class TrendAnalyzer:
    """트렌드 분석기"""
    
    def __init__(self, db: Session, logger: logging.Logger = None):
        self.db = db
        self.logger = logger or logging.getLogger(__name__)
        self.pytrends = TrendReq(hl='ko', tz=540)  # 한국어, 한국 시간대
        
    async def analyze_trends(self, initial_keywords: List[str] = None) -> Dict[str, Any]:
        """종합 트렌드 분석"""
        if not initial_keywords:
            # 초보 셀러를 위한 기본 카테고리 키워드
            initial_keywords = [
                "선물", "인기상품", "신상품", "트렌드",
                "집콕", "홈트", "다이어트", "뷰티",
                "캠핑", "반려동물", "육아", "인테리어"
            ]
            
        results = {
            'google_trends': {},
            'naver_trends': {},
            'rising_keywords': [],
            'seasonal_keywords': [],
            'recommended_categories': [],
            'analysis_date': datetime.now()
        }
        
        # 1. 구글 트렌드 분석
        results['google_trends'] = await self.analyze_google_trends(initial_keywords)
        
        # 2. 네이버 데이터랩 분석
        results['naver_trends'] = await self.analyze_naver_datalab(initial_keywords)
        
        # 3. 급상승 키워드 발굴
        results['rising_keywords'] = await self.find_rising_keywords()
        
        # 4. 계절성 키워드 분석
        results['seasonal_keywords'] = await self.analyze_seasonal_trends()
        
        # 5. AI 기반 카테고리 추천
        results['recommended_categories'] = await self.recommend_categories(results)
        
        # 분석 결과 저장
        await self._save_trend_analysis(results)
        
        return results
        
    async def analyze_google_trends(self, keywords: List[str]) -> Dict[str, Any]:
        """구글 트렌드 분석"""
        try:
            trend_data = {}
            
            # 키워드를 5개씩 묶어서 분석 (API 제한)
            for i in range(0, len(keywords), 5):
                batch = keywords[i:i+5]
                
                # 관심도 시간별 추이
                self.pytrends.build_payload(
                    batch,
                    timeframe='today 3-m',  # 최근 3개월
                    geo='KR'
                )
                
                interest_over_time = self.pytrends.interest_over_time()
                
                if not interest_over_time.empty:
                    for keyword in batch:
                        if keyword in interest_over_time.columns:
                            trend_data[keyword] = {
                                'current_interest': int(interest_over_time[keyword].iloc[-1]),
                                'avg_interest': float(interest_over_time[keyword].mean()),
                                'trend_direction': self._calculate_trend_direction(
                                    interest_over_time[keyword].values
                                ),
                                'volatility': float(interest_over_time[keyword].std())
                            }
                            
                await asyncio.sleep(1)  # Rate limiting
                
            # 연관 검색어 수집
            related_queries = {}
            for keyword in keywords[:10]:  # 상위 10개만
                try:
                    self.pytrends.build_payload([keyword], timeframe='today 3-m', geo='KR')
                    related = self.pytrends.related_queries()
                    
                    if keyword in related:
                        rising = related[keyword]['rising']
                        if rising is not None and not rising.empty:
                            related_queries[keyword] = rising.head(10).to_dict('records')
                            
                except Exception as e:
                    self.logger.warning(f"연관 검색어 수집 실패 ({keyword}): {str(e)}")
                    
                await asyncio.sleep(1)
                
            return {
                'keyword_trends': trend_data,
                'related_queries': related_queries,
                'analysis_period': 'last_3_months'
            }
            
        except Exception as e:
            self.logger.error(f"구글 트렌드 분석 실패: {str(e)}")
            return {}
            
    async def analyze_naver_datalab(self, keywords: List[str]) -> Dict[str, Any]:
        """네이버 데이터랩 트렌드 분석"""
        # 네이버 데이터랩 API는 인증이 필요하므로 실제 구현 시 API 키 필요
        # 여기서는 시뮬레이션 데이터 제공
        
        naver_data = {}
        
        for keyword in keywords:
            # 실제로는 네이버 API 호출
            naver_data[keyword] = {
                'search_volume': np.random.randint(1000, 50000),
                'click_rate': round(np.random.uniform(0.1, 0.5), 2),
                'competition': np.random.choice(['낮음', '보통', '높음']),
                'cpc_range': (np.random.randint(50, 200), np.random.randint(200, 1000)),
                'demographic': {
                    'age_group': self._simulate_age_distribution(),
                    'gender': {'male': 45, 'female': 55}  # 예시
                }
            }
            
        return naver_data
        
    async def find_rising_keywords(self) -> List[Dict[str, Any]]:
        """급상승 키워드 발굴"""
        rising_keywords = []
        
        # 주요 카테고리별 급상승 검색어 수집
        categories = ['패션', '뷰티', '식품', '생활용품', '디지털']
        
        for category in categories:
            try:
                self.pytrends.build_payload(
                    [category],
                    timeframe='now 7-d',  # 최근 7일
                    geo='KR'
                )
                
                # 급상승 검색어
                rising = self.pytrends.related_queries()[category]['rising']
                
                if rising is not None and not rising.empty:
                    for _, row in rising.head(5).iterrows():
                        keyword_data = {
                            'keyword': row['query'],
                            'category': category,
                            'rise_percentage': row['value'],
                            'potential_score': self._calculate_potential_score(row),
                            'recommended_action': self._get_keyword_recommendation(row)
                        }
                        rising_keywords.append(keyword_data)
                        
            except Exception as e:
                self.logger.warning(f"급상승 키워드 수집 실패 ({category}): {str(e)}")
                
            await asyncio.sleep(1)
            
        # 잠재력 점수로 정렬
        rising_keywords.sort(key=lambda x: x['potential_score'], reverse=True)
        
        return rising_keywords[:20]  # 상위 20개
        
    async def analyze_seasonal_trends(self) -> List[Dict[str, Any]]:
        """계절성 트렌드 분석"""
        current_month = datetime.now().month
        season = self._get_season(current_month)
        
        seasonal_keywords = {
            'spring': ['봄신상', '꽃', '피크닉', '봄나들이', '신학기'],
            'summer': ['여름휴가', '수영복', '에어컨', '캠핑', '선크림'],
            'autumn': ['가을신상', '단풍', '김장', '난방', '코트'],
            'winter': ['겨울신상', '패딩', '크리스마스', '연말선물', '핫팩']
        }
        
        upcoming_season = self._get_next_season(season)
        keywords_to_analyze = seasonal_keywords.get(upcoming_season, [])
        
        seasonal_analysis = []
        
        for keyword in keywords_to_analyze:
            try:
                # 작년 동기간 대비 분석
                self.pytrends.build_payload(
                    [keyword],
                    timeframe='today 12-m',  # 12개월
                    geo='KR'
                )
                
                interest = self.pytrends.interest_over_time()
                
                if not interest.empty and keyword in interest.columns:
                    data = interest[keyword]
                    
                    # 작년 동기간과 현재 비교
                    last_year_same_month = data.iloc[-12] if len(data) > 12 else 0
                    current = data.iloc[-1]
                    
                    growth = ((current - last_year_same_month) / max(last_year_same_month, 1)) * 100
                    
                    seasonal_analysis.append({
                        'keyword': keyword,
                        'season': upcoming_season,
                        'current_interest': int(current),
                        'yoy_growth': round(growth, 1),
                        'peak_month': self._find_peak_month(data),
                        'preparation_advice': self._get_seasonal_advice(keyword, upcoming_season)
                    })
                    
            except Exception as e:
                self.logger.warning(f"계절 트렌드 분석 실패 ({keyword}): {str(e)}")
                
            await asyncio.sleep(1)
            
        return seasonal_analysis
        
    async def recommend_categories(self, trend_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """AI 기반 카테고리 추천"""
        recommendations = []
        
        # 트렌드 데이터 기반 점수 계산
        category_scores = {}
        
        # 1. 구글 트렌드 점수
        if 'google_trends' in trend_results and 'keyword_trends' in trend_results['google_trends']:
            for keyword, data in trend_results['google_trends']['keyword_trends'].items():
                category = self._keyword_to_category(keyword)
                if category not in category_scores:
                    category_scores[category] = 0
                    
                # 관심도와 트렌드 방향성 고려
                score = data['current_interest'] * 0.5
                if data['trend_direction'] == 'rising':
                    score *= 1.5
                elif data['trend_direction'] == 'falling':
                    score *= 0.7
                    
                category_scores[category] += score
                
        # 2. 급상승 키워드 점수
        if 'rising_keywords' in trend_results:
            for keyword_data in trend_results['rising_keywords']:
                category = keyword_data.get('category', 'unknown')
                if category not in category_scores:
                    category_scores[category] = 0
                    
                category_scores[category] += keyword_data.get('potential_score', 0) * 2
                
        # 3. 계절성 점수
        if 'seasonal_keywords' in trend_results:
            for seasonal in trend_results['seasonal_keywords']:
                category = self._keyword_to_category(seasonal['keyword'])
                if category not in category_scores:
                    category_scores[category] = 0
                    
                # YoY 성장률 반영
                growth_score = max(0, seasonal['yoy_growth']) / 10
                category_scores[category] += growth_score * 50
                
        # 카테고리별 추천 생성
        for category, score in sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:10]:
            recommendation = {
                'category': category,
                'score': round(score, 1),
                'confidence': self._calculate_confidence(score),
                'market_size': self._estimate_market_size(category),
                'competition_level': self._assess_competition(category),
                'entry_difficulty': self._assess_entry_difficulty(category),
                'recommended_products': await self._get_category_product_ideas(category),
                'tips': self._get_category_tips(category)
            }
            recommendations.append(recommendation)
            
        return recommendations
        
    def _calculate_trend_direction(self, values: np.ndarray) -> str:
        """트렌드 방향 계산"""
        if len(values) < 3:
            return 'stable'
            
        # 선형 회귀로 추세 확인
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        
        if slope > 0.5:
            return 'rising'
        elif slope < -0.5:
            return 'falling'
        else:
            return 'stable'
            
    def _calculate_potential_score(self, row) -> float:
        """키워드 잠재력 점수 계산"""
        # 상승률이 높을수록 높은 점수
        rise_value = row.get('value', 0)
        
        if rise_value > 5000:
            return 100
        elif rise_value > 1000:
            return 80
        elif rise_value > 500:
            return 60
        elif rise_value > 100:
            return 40
        else:
            return 20
            
    def _get_keyword_recommendation(self, row) -> str:
        """키워드별 추천 액션"""
        rise_value = row.get('value', 0)
        
        if rise_value > 5000:
            return "즉시 진입 추천 - 폭발적 성장 중"
        elif rise_value > 1000:
            return "적극 검토 - 빠른 성장세"
        elif rise_value > 500:
            return "관심 목록 추가 - 성장 잠재력 있음"
        else:
            return "모니터링 - 초기 성장 단계"
            
    def _get_season(self, month: int) -> str:
        """월별 계절 판단"""
        if 3 <= month <= 5:
            return 'spring'
        elif 6 <= month <= 8:
            return 'summer'
        elif 9 <= month <= 11:
            return 'autumn'
        else:
            return 'winter'
            
    def _get_next_season(self, current_season: str) -> str:
        """다음 계절"""
        seasons = ['spring', 'summer', 'autumn', 'winter']
        current_idx = seasons.index(current_season)
        return seasons[(current_idx + 1) % 4]
        
    def _find_peak_month(self, data: pd.Series) -> int:
        """피크 월 찾기"""
        monthly_avg = data.resample('M').mean()
        if not monthly_avg.empty:
            return monthly_avg.idxmax().month
        return 0
        
    def _get_seasonal_advice(self, keyword: str, season: str) -> str:
        """계절별 준비 조언"""
        advice_map = {
            'spring': "3-4월 준비 시작, 신선한 이미지 강조",
            'summer': "5-6월 준비 시작, 시원함과 편의성 강조",
            'autumn': "8-9월 준비 시작, 따뜻함과 감성 강조",
            'winter': "10-11월 준비 시작, 보온성과 선물 수요 고려"
        }
        return advice_map.get(season, "시즌 2개월 전 준비 권장")
        
    def _keyword_to_category(self, keyword: str) -> str:
        """키워드를 카테고리로 매핑"""
        category_map = {
            '패션': ['신상', '옷', '의류', '패션', '코트', '패딩'],
            '뷰티': ['화장품', '뷰티', '스킨케어', '선크림'],
            '식품': ['식품', '먹거리', '간식', '김장'],
            '생활용품': ['생활', '홈', '인테리어', '청소'],
            '디지털': ['전자', '가전', '디지털', '스마트'],
            '스포츠': ['운동', '홈트', '캠핑', '등산'],
            '육아': ['육아', '아기', '유아', '신학기']
        }
        
        for category, keywords in category_map.items():
            if any(kw in keyword.lower() for kw in keywords):
                return category
                
        return '기타'
        
    def _simulate_age_distribution(self) -> Dict[str, int]:
        """연령대 분포 시뮬레이션"""
        age_groups = ['10대', '20대', '30대', '40대', '50대+']
        distribution = np.random.multinomial(100, [0.1, 0.25, 0.3, 0.25, 0.1])
        return dict(zip(age_groups, distribution))
        
    def _calculate_confidence(self, score: float) -> str:
        """신뢰도 계산"""
        if score >= 80:
            return '매우 높음'
        elif score >= 60:
            return '높음'
        elif score >= 40:
            return '보통'
        elif score >= 20:
            return '낮음'
        else:
            return '매우 낮음'
            
    def _estimate_market_size(self, category: str) -> str:
        """시장 규모 추정"""
        market_sizes = {
            '패션': '대규모 (10조원+)',
            '뷰티': '대규모 (8조원+)',
            '식품': '초대규모 (20조원+)',
            '생활용품': '대규모 (5조원+)',
            '디지털': '대규모 (15조원+)',
            '스포츠': '중규모 (3조원+)',
            '육아': '중규모 (2조원+)'
        }
        return market_sizes.get(category, '소규모')
        
    def _assess_competition(self, category: str) -> str:
        """경쟁 강도 평가"""
        competition_levels = {
            '패션': '매우 높음',
            '뷰티': '매우 높음',
            '식품': '높음',
            '생활용품': '보통',
            '디지털': '높음',
            '스포츠': '보통',
            '육아': '보통'
        }
        return competition_levels.get(category, '낮음')
        
    def _assess_entry_difficulty(self, category: str) -> str:
        """진입 난이도 평가"""
        difficulty_map = {
            '패션': '낮음 (낮은 초기 투자)',
            '뷰티': '보통 (인증 필요)',
            '식품': '높음 (허가/인증 필수)',
            '생활용품': '낮음',
            '디지털': '보통 (A/S 고려)',
            '스포츠': '낮음',
            '육아': '보통 (안전 인증)'
        }
        return difficulty_map.get(category, '보통')
        
    async def _get_category_product_ideas(self, category: str) -> List[str]:
        """카테고리별 상품 아이디어"""
        product_ideas = {
            '패션': ['계절 신상', '베이직 아이템', '액세서리', 'SPA 브랜드'],
            '뷰티': ['K-뷰티', '클린뷰티', '홈케어 기기', '맞춤형 화장품'],
            '식품': ['건강식품', '간편식', '지역 특산품', '프리미엄 먹거리'],
            '생활용품': ['수납용품', '청소용품', '홈데코', '친환경 제품'],
            '디지털': ['스마트홈', '액세서리', '중고 리퍼비시', '소형 가전'],
            '스포츠': ['홈트레이닝', '아웃도어', '스포츠웨어', '보조 용품'],
            '육아': ['교육 완구', '안전 용품', '유기농 제품', '성장 단계별 용품']
        }
        return product_ideas.get(category, ['일반 상품'])
        
    def _get_category_tips(self, category: str) -> List[str]:
        """카테고리별 팁"""
        tips_map = {
            '패션': [
                "시즌 2-3개월 전 준비",
                "사이즈 교환 정책 명확히",
                "상세 사이즈 정보 필수",
                "모델 착용 사진 다양하게"
            ],
            '뷰티': [
                "성분 정보 상세히 기재",
                "사용 전후 비교 이미지",
                "피부 타입별 설명",
                "정품 인증 강조"
            ],
            '식품': [
                "식품 허가 사항 확인",
                "유통기한 관리 철저",
                "보관 방법 명시",
                "원산지 표기 필수"
            ]
        }
        return tips_map.get(category, ["시장 조사 철저히", "차별화 포인트 찾기"])
        
    async def _save_trend_analysis(self, results: Dict[str, Any]):
        """트렌드 분석 결과 저장"""
        try:
            # 주요 키워드 저장
            for keyword, data in results.get('google_trends', {}).get('keyword_trends', {}).items():
                trend_keyword = TrendKeyword(
                    keyword=keyword,
                    trend_score=data.get('current_interest', 0),
                    trend_direction=data.get('trend_direction', 'stable'),
                    platform='google',
                    analyzed_at=datetime.now()
                )
                self.db.add(trend_keyword)
                
            # 급상승 키워드 저장
            for rising in results.get('rising_keywords', []):
                trend_keyword = TrendKeyword(
                    keyword=rising['keyword'],
                    category=rising.get('category'),
                    trend_score=rising.get('potential_score', 0),
                    trend_direction='rising',
                    platform='google',
                    trend_metadata=rising,
                    analyzed_at=datetime.now()
                )
                self.db.add(trend_keyword)
                
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"트렌드 분석 결과 저장 실패: {str(e)}")
            self.db.rollback()