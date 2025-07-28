"""
트렌드 분석 모듈
- 베스트셀러 데이터 분석
- 검색 트렌드 분석
- 시장 동향 예측
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import asyncio
import aiohttp

from database.models_v2 import WholesaleProduct, MarketplaceProduct
from collectors.bestseller_collector import BestsellerData
from utils.logger import app_logger


class TrendAnalyzer:
    """트렌드 분석기"""
    
    def __init__(self, db: Session):
        self.db = db
        
    async def analyze_market_trends(self, days: int = 30) -> Dict[str, Any]:
        """시장 트렌드 분석"""
        try:
            # 기간 설정
            since_date = datetime.now() - timedelta(days=days)
            
            # 베스트셀러 데이터 조회
            bestsellers = self.db.query(BestsellerData).filter(
                BestsellerData.collected_at >= since_date
            ).all()
            
            if not bestsellers:
                return {
                    "status": "no_data",
                    "message": "분석할 데이터가 없습니다"
                }
            
            # 데이터프레임 변환
            df = pd.DataFrame([{
                'marketplace': b.marketplace,
                'product_id': b.product_id,
                'product_name': b.product_name,
                'category': b.category,
                'rank': b.rank,
                'price': b.price,
                'review_count': b.review_count,
                'rating': b.rating,
                'collected_at': b.collected_at
            } for b in bestsellers])
            
            # 1. 카테고리별 트렌드
            category_trends = self._analyze_category_trends(df)
            
            # 2. 가격대별 분석
            price_analysis = self._analyze_price_ranges(df)
            
            # 3. 급상승 상품
            rising_products = self._find_rising_products(df)
            
            # 4. 안정적인 베스트셀러
            stable_products = self._find_stable_products(df)
            
            # 5. 리뷰 트렌드
            review_trends = self._analyze_review_trends(df)
            
            return {
                "status": "success",
                "period_days": days,
                "total_products": len(df['product_id'].unique()),
                "category_trends": category_trends,
                "price_analysis": price_analysis,
                "rising_products": rising_products,
                "stable_products": stable_products,
                "review_trends": review_trends,
                "analyzed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            app_logger.error(f"트렌드 분석 오류: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _analyze_category_trends(self, df: pd.DataFrame) -> List[Dict]:
        """카테고리별 트렌드 분석"""
        if df.empty or 'category' not in df.columns:
            return []
            
        # 카테고리별 상품 수
        category_counts = df.groupby('category').agg({
            'product_id': 'nunique',
            'rank': 'mean',
            'price': 'mean',
            'review_count': 'sum'
        }).round(2)
        
        trends = []
        for category, row in category_counts.iterrows():
            if category:  # None 제외
                trends.append({
                    'category': category,
                    'product_count': int(row['product_id']),
                    'avg_rank': float(row['rank']),
                    'avg_price': int(row['price']),
                    'total_reviews': int(row['review_count']),
                    'trend_score': self._calculate_trend_score(
                        product_count=row['product_id'],
                        avg_rank=row['rank'],
                        total_reviews=row['review_count']
                    )
                })
        
        # 트렌드 점수로 정렬
        return sorted(trends, key=lambda x: x['trend_score'], reverse=True)
    
    def _analyze_price_ranges(self, df: pd.DataFrame) -> Dict[str, Any]:
        """가격대별 분석"""
        if df.empty or 'price' not in df.columns:
            return {}
            
        # 가격대 구분
        price_ranges = {
            '1만원 미만': (0, 10000),
            '1-3만원': (10000, 30000),
            '3-5만원': (30000, 50000),
            '5-10만원': (50000, 100000),
            '10만원 이상': (100000, float('inf'))
        }
        
        analysis = {}
        for range_name, (min_price, max_price) in price_ranges.items():
            range_df = df[(df['price'] >= min_price) & (df['price'] < max_price)]
            if not range_df.empty:
                analysis[range_name] = {
                    'product_count': len(range_df['product_id'].unique()),
                    'avg_rank': float(range_df['rank'].mean()),
                    'avg_review': float(range_df['review_count'].mean()),
                    'percentage': round(len(range_df) / len(df) * 100, 1)
                }
        
        return analysis
    
    def _find_rising_products(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """급상승 상품 찾기"""
        if df.empty:
            return []
            
        # 최근 7일과 이전 데이터 비교
        recent_date = datetime.now() - timedelta(days=7)
        recent_df = df[df['collected_at'] >= recent_date]
        older_df = df[df['collected_at'] < recent_date]
        
        if recent_df.empty or older_df.empty:
            return []
        
        # 평균 순위 계산
        recent_ranks = recent_df.groupby('product_id')['rank'].mean()
        older_ranks = older_df.groupby('product_id')['rank'].mean()
        
        # 순위 변화 계산 (음수가 상승)
        rank_changes = older_ranks - recent_ranks
        rank_changes = rank_changes.dropna().sort_values(ascending=False)
        
        rising_products = []
        for product_id, rank_change in rank_changes.head(top_n).items():
            if rank_change > 0:  # 순위 상승
                product_info = df[df['product_id'] == product_id].iloc[0]
                rising_products.append({
                    'product_id': product_id,
                    'product_name': product_info['product_name'],
                    'category': product_info['category'],
                    'marketplace': product_info['marketplace'],
                    'rank_change': int(rank_change),
                    'current_rank': int(recent_ranks.get(product_id, 0)),
                    'price': int(product_info['price'])
                })
        
        return rising_products
    
    def _find_stable_products(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """안정적인 베스트셀러 찾기"""
        if df.empty:
            return []
            
        # 상품별 통계
        product_stats = df.groupby('product_id').agg({
            'rank': ['mean', 'std', 'count'],
            'product_name': 'first',
            'category': 'first',
            'marketplace': 'first',
            'price': 'mean',
            'review_count': 'mean'
        })
        
        # 컬럼명 정리
        product_stats.columns = ['_'.join(col).strip() for col in product_stats.columns]
        
        # 안정성 점수 계산 (표준편차가 작고 등장 횟수가 많을수록 높음)
        product_stats['stability_score'] = (
            product_stats['rank_count'] / product_stats['rank_std'].fillna(1)
        )
        
        # 평균 순위가 좋은 상품 중 안정성이 높은 상품
        stable_products = product_stats[
            product_stats['rank_mean'] <= 50  # 평균 50위 이내
        ].sort_values('stability_score', ascending=False).head(top_n)
        
        results = []
        for product_id, row in stable_products.iterrows():
            results.append({
                'product_id': product_id,
                'product_name': row['product_name_first'],
                'category': row['category_first'],
                'marketplace': row['marketplace_first'],
                'avg_rank': round(row['rank_mean'], 1),
                'rank_stability': round(row['rank_std'], 1) if pd.notna(row['rank_std']) else 0,
                'appearance_count': int(row['rank_count']),
                'avg_price': int(row['price_mean']),
                'avg_reviews': int(row['review_count_mean'])
            })
        
        return results
    
    def _analyze_review_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """리뷰 트렌드 분석"""
        if df.empty or 'review_count' not in df.columns:
            return {}
            
        # 리뷰 수 구간별 분석
        review_ranges = {
            '100개 미만': (0, 100),
            '100-500개': (100, 500),
            '500-1000개': (500, 1000),
            '1000-5000개': (1000, 5000),
            '5000개 이상': (5000, float('inf'))
        }
        
        analysis = {}
        for range_name, (min_reviews, max_reviews) in review_ranges.items():
            range_df = df[
                (df['review_count'] >= min_reviews) & 
                (df['review_count'] < max_reviews)
            ]
            if not range_df.empty:
                analysis[range_name] = {
                    'product_count': len(range_df['product_id'].unique()),
                    'avg_rank': float(range_df['rank'].mean()),
                    'avg_rating': float(range_df['rating'].mean()),
                    'percentage': round(len(range_df) / len(df) * 100, 1)
                }
        
        return analysis
    
    def _calculate_trend_score(self, product_count: int, avg_rank: float, 
                             total_reviews: int) -> float:
        """트렌드 점수 계산"""
        # 상품 수가 많고, 평균 순위가 높고, 리뷰가 많을수록 높은 점수
        score = (
            product_count * 10 +  # 상품 수 가중치
            (100 - avg_rank) * 5 +  # 순위 가중치 (낮을수록 좋음)
            np.log1p(total_reviews) * 2  # 리뷰 수 가중치 (로그 스케일)
        )
        return round(score, 2)
    
    async def get_search_trends(self, keywords: List[str]) -> Dict[str, Any]:
        """검색 트렌드 분석 (추후 외부 API 연동)"""
        # TODO: 네이버 데이터랩, 구글 트렌드 API 연동
        app_logger.info(f"검색 트렌드 분석: {keywords}")
        
        # 현재는 모의 데이터 반환
        return {
            "status": "mock_data",
            "keywords": keywords,
            "message": "실제 API 연동은 추후 구현 예정",
            "trends": [
                {
                    "keyword": kw,
                    "search_volume": np.random.randint(1000, 10000),
                    "growth_rate": np.random.uniform(-20, 50)
                }
                for kw in keywords
            ]
        }
    
    def get_category_recommendations(self) -> List[Dict[str, Any]]:
        """유망 카테고리 추천"""
        try:
            # 최근 30일 데이터
            since_date = datetime.now() - timedelta(days=30)
            
            # 카테고리별 성과 지표
            category_stats = self.db.query(
                BestsellerData.category,
                func.count(func.distinct(BestsellerData.product_id)).label('product_count'),
                func.avg(BestsellerData.rank).label('avg_rank'),
                func.avg(BestsellerData.review_count).label('avg_reviews'),
                func.avg(BestsellerData.price).label('avg_price')
            ).filter(
                and_(
                    BestsellerData.collected_at >= since_date,
                    BestsellerData.category.isnot(None)
                )
            ).group_by(
                BestsellerData.category
            ).having(
                func.count(func.distinct(BestsellerData.product_id)) >= 5  # 최소 5개 상품
            ).all()
            
            recommendations = []
            for stat in category_stats:
                # 추천 점수 계산
                score = self._calculate_category_score(
                    product_count=stat.product_count,
                    avg_rank=stat.avg_rank,
                    avg_reviews=stat.avg_reviews
                )
                
                recommendations.append({
                    'category': stat.category,
                    'product_count': stat.product_count,
                    'avg_rank': round(stat.avg_rank, 1),
                    'avg_reviews': round(stat.avg_reviews),
                    'avg_price': round(stat.avg_price),
                    'recommendation_score': score,
                    'potential': self._get_potential_level(score)
                })
            
            # 점수 순으로 정렬
            return sorted(recommendations, key=lambda x: x['recommendation_score'], reverse=True)
            
        except Exception as e:
            app_logger.error(f"카테고리 추천 오류: {e}")
            return []
    
    def _calculate_category_score(self, product_count: int, avg_rank: float, 
                                avg_reviews: float) -> float:
        """카테고리 점수 계산"""
        # 다양한 요소를 고려한 점수 계산
        diversity_score = min(product_count / 20, 1) * 30  # 상품 다양성
        rank_score = max(0, (100 - avg_rank) / 2)  # 평균 순위
        popularity_score = min(avg_reviews / 1000, 1) * 20  # 인기도
        
        return round(diversity_score + rank_score + popularity_score, 1)
    
    def _get_potential_level(self, score: float) -> str:
        """잠재력 레벨 판단"""
        if score >= 80:
            return "매우 높음"
        elif score >= 60:
            return "높음"
        elif score >= 40:
            return "보통"
        elif score >= 20:
            return "낮음"
        else:
            return "매우 낮음"