"""
도매처 데이터 분석 서비스
최근 자료 조회, 가격 변동 추적, 재고 모니터링, 트렌드 분석 기능을 제공합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import json

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
import pandas as pd
import numpy as np

from app.models.wholesaler import (
    WholesalerAccount,
    WholesalerProduct,
    CollectionLog,
    CollectionStatus,
    WholesalerType
)
from app.models.product import Product

logger = logging.getLogger(__name__)


class ProductAnalyzer:
    """상품 분석 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_recent_products(self, wholesaler_account_id: int = None, 
                           days: int = 7, limit: int = 100) -> Dict:
        """최근 N일간 신규 수집된 상품을 조회합니다."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(WholesalerProduct).filter(
                WholesalerProduct.first_collected_at >= cutoff_date,
                WholesalerProduct.is_active == True
            )
            
            if wholesaler_account_id:
                query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
            
            # 최신순으로 정렬
            products = query.order_by(desc(WholesalerProduct.first_collected_at)).limit(limit).all()
            
            # 통계 정보 계산
            total_count = query.count()
            
            # 도매처별 분포
            wholesaler_stats = self.db.query(
                WholesalerAccount.account_name,
                WholesalerAccount.wholesaler_type,
                func.count(WholesalerProduct.id).label('product_count')
            ).join(WholesalerProduct).filter(
                WholesalerProduct.first_collected_at >= cutoff_date,
                WholesalerProduct.is_active == True
            ).group_by(
                WholesalerAccount.id,
                WholesalerAccount.account_name,
                WholesalerAccount.wholesaler_type
            ).all()
            
            # 카테고리별 분포
            category_stats = self.db.query(
                WholesalerProduct.category_path,
                func.count(WholesalerProduct.id).label('product_count')
            ).filter(
                WholesalerProduct.first_collected_at >= cutoff_date,
                WholesalerProduct.is_active == True,
                WholesalerProduct.category_path.isnot(None)
            ).group_by(WholesalerProduct.category_path).limit(20).all()
            
            return {
                'success': True,
                'data': {
                    'products': [
                        {
                            'id': p.id,
                            'name': p.name,
                            'wholesaler_account_id': p.wholesaler_account_id,
                            'category_path': p.category_path,
                            'wholesale_price': p.wholesale_price,
                            'retail_price': p.retail_price,
                            'stock_quantity': p.stock_quantity,
                            'is_in_stock': p.is_in_stock,
                            'main_image_url': p.main_image_url,
                            'first_collected_at': p.first_collected_at.isoformat() if p.first_collected_at else None
                        } for p in products
                    ],
                    'stats': {
                        'total_count': total_count,
                        'returned_count': len(products),
                        'date_range': {
                            'from': cutoff_date.isoformat(),
                            'to': datetime.utcnow().isoformat()
                        },
                        'wholesaler_distribution': [
                            {
                                'account_name': ws.account_name,
                                'wholesaler_type': ws.wholesaler_type.value,
                                'product_count': ws.product_count
                            } for ws in wholesaler_stats
                        ],
                        'category_distribution': [
                            {
                                'category_path': cs.category_path,
                                'product_count': cs.product_count
                            } for cs in category_stats
                        ]
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"최근 상품 조회 실패: {str(e)}")
            return {
                'success': False,
                'message': f"최근 상품 조회 실패: {str(e)}"
            }
    
    def analyze_price_changes(self, wholesaler_account_id: int = None, 
                             days: int = 30, min_change_rate: float = 0.05) -> Dict:
        """가격 변동 분석을 수행합니다."""
        try:
            # 가격 변동 추적을 위한 서브쿼리 (실제 구현에서는 별도 가격 이력 테이블이 필요)
            # 현재는 간단한 분석만 제공
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(WholesalerProduct).filter(
                WholesalerProduct.last_updated_at >= cutoff_date,
                WholesalerProduct.is_active == True
            )
            
            if wholesaler_account_id:
                query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
            
            products = query.all()
            
            # 가격 분포 분석
            prices = [p.wholesale_price for p in products if p.wholesale_price > 0]
            retail_prices = [p.retail_price for p in products if p.retail_price and p.retail_price > 0]
            
            price_stats = {}
            if prices:
                price_stats = {
                    'wholesale_price': {
                        'min': min(prices),
                        'max': max(prices),
                        'avg': sum(prices) / len(prices),
                        'median': sorted(prices)[len(prices) // 2] if prices else 0
                    }
                }
            
            if retail_prices:
                price_stats['retail_price'] = {
                    'min': min(retail_prices),
                    'max': max(retail_prices),
                    'avg': sum(retail_prices) / len(retail_prices),
                    'median': sorted(retail_prices)[len(retail_prices) // 2] if retail_prices else 0
                }
            
            # 가격대별 상품 분포
            price_ranges = {
                '1만원 미만': 0,
                '1-5만원': 0,
                '5-10만원': 0,
                '10-50만원': 0,
                '50만원 이상': 0
            }
            
            for price in prices:
                if price < 10000:
                    price_ranges['1만원 미만'] += 1
                elif price < 50000:
                    price_ranges['1-5만원'] += 1
                elif price < 100000:
                    price_ranges['5-10만원'] += 1
                elif price < 500000:
                    price_ranges['10-50만원'] += 1
                else:
                    price_ranges['50만원 이상'] += 1
            
            return {
                'success': True,
                'data': {
                    'analysis_period': {
                        'from': cutoff_date.isoformat(),
                        'to': datetime.utcnow().isoformat(),
                        'days': days
                    },
                    'total_products': len(products),
                    'price_statistics': price_stats,
                    'price_distribution': price_ranges,
                    'top_expensive_products': [
                        {
                            'name': p.name,
                            'wholesale_price': p.wholesale_price,
                            'retail_price': p.retail_price,
                            'category_path': p.category_path
                        } for p in sorted(products, key=lambda x: x.wholesale_price, reverse=True)[:10]
                    ],
                    'budget_friendly_products': [
                        {
                            'name': p.name,
                            'wholesale_price': p.wholesale_price,
                            'retail_price': p.retail_price,
                            'category_path': p.category_path
                        } for p in sorted(products, key=lambda x: x.wholesale_price)[:10]
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"가격 변동 분석 실패: {str(e)}")
            return {
                'success': False,
                'message': f"가격 변동 분석 실패: {str(e)}"
            }
    
    def monitor_stock_changes(self, wholesaler_account_id: int = None, 
                             days: int = 7) -> Dict:
        """재고 변화 모니터링을 수행합니다."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(WholesalerProduct).filter(
                WholesalerProduct.last_updated_at >= cutoff_date,
                WholesalerProduct.is_active == True
            )
            
            if wholesaler_account_id:
                query = query.filter(WholesalerProduct.wholesaler_account_id == wholesaler_account_id)
            
            products = query.all()
            
            # 재고 상태 분석
            in_stock_count = sum(1 for p in products if p.is_in_stock)
            out_of_stock_count = len(products) - in_stock_count
            
            # 재고 수량별 분포
            stock_distribution = {
                '품절 (0개)': 0,
                '소량 (1-10개)': 0,
                '보통 (11-50개)': 0,
                '충분 (51-100개)': 0,
                '대량 (100개 이상)': 0
            }
            
            for product in products:
                stock = product.stock_quantity
                if stock == 0:
                    stock_distribution['품절 (0개)'] += 1
                elif stock <= 10:
                    stock_distribution['소량 (1-10개)'] += 1
                elif stock <= 50:
                    stock_distribution['보통 (11-50개)'] += 1
                elif stock <= 100:
                    stock_distribution['충분 (51-100개)'] += 1
                else:
                    stock_distribution['대량 (100개 이상)'] += 1
            
            # 재고 부족 상품 (재고 10개 이하)
            low_stock_products = [
                {
                    'name': p.name,
                    'stock_quantity': p.stock_quantity,
                    'wholesale_price': p.wholesale_price,
                    'category_path': p.category_path,
                    'last_updated_at': p.last_updated_at.isoformat() if p.last_updated_at else None
                } for p in products if p.stock_quantity <= 10
            ]
            
            # 품절 상품
            out_of_stock_products = [
                {
                    'name': p.name,
                    'wholesale_price': p.wholesale_price,
                    'category_path': p.category_path,
                    'last_updated_at': p.last_updated_at.isoformat() if p.last_updated_at else None
                } for p in products if p.stock_quantity == 0 or not p.is_in_stock
            ]
            
            return {
                'success': True,
                'data': {
                    'analysis_period': {
                        'from': cutoff_date.isoformat(),
                        'to': datetime.utcnow().isoformat(),
                        'days': days
                    },
                    'summary': {
                        'total_products': len(products),
                        'in_stock_count': in_stock_count,
                        'out_of_stock_count': out_of_stock_count,
                        'stock_rate': (in_stock_count / len(products) * 100) if products else 0
                    },
                    'stock_distribution': stock_distribution,
                    'alerts': {
                        'low_stock_products': low_stock_products[:20],  # 상위 20개만
                        'out_of_stock_products': out_of_stock_products[:20]  # 상위 20개만
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"재고 변화 모니터링 실패: {str(e)}")
            return {
                'success': False,
                'message': f"재고 변화 모니터링 실패: {str(e)}"
            }


class TrendAnalyzer:
    """트렌드 분석 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_product_trends(self, days: int = 30, top_n: int = 20) -> Dict:
        """상품 트렌드를 분석합니다."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 최근 수집된 상품들
            recent_products = self.db.query(WholesalerProduct).filter(
                WholesalerProduct.first_collected_at >= cutoff_date,
                WholesalerProduct.is_active == True
            ).all()
            
            # 카테고리별 트렌드
            category_trends = defaultdict(list)
            for product in recent_products:
                if product.category_path:
                    category_trends[product.category_path].append(product)
            
            # 상위 카테고리 추출
            top_categories = sorted(
                category_trends.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:top_n]
            
            # 키워드 분석 (상품명에서 공통 키워드 추출)
            keyword_count = defaultdict(int)
            for product in recent_products:
                if product.name:
                    # 간단한 키워드 추출 (실제로는 더 정교한 NLP 처리 필요)
                    words = product.name.split()
                    for word in words:
                        if len(word) >= 2:  # 2글자 이상만
                            keyword_count[word] += 1
            
            top_keywords = sorted(keyword_count.items(), key=lambda x: x[1], reverse=True)[:20]
            
            # 가격대별 트렌드
            price_trends = self._analyze_price_trends(recent_products)
            
            # 신상품 추가 속도 분석
            daily_new_products = self._analyze_daily_new_products(cutoff_date, days)
            
            return {
                'success': True,
                'data': {
                    'analysis_period': {
                        'from': cutoff_date.isoformat(),
                        'to': datetime.utcnow().isoformat(),
                        'days': days
                    },
                    'summary': {
                        'total_new_products': len(recent_products),
                        'categories_count': len(category_trends),
                        'avg_daily_new_products': len(recent_products) / days if days > 0 else 0
                    },
                    'category_trends': [
                        {
                            'category': category,
                            'product_count': len(products),
                            'avg_wholesale_price': sum(p.wholesale_price for p in products if p.wholesale_price) / len(products) if products else 0,
                            'sample_products': [
                                {
                                    'name': p.name,
                                    'wholesale_price': p.wholesale_price,
                                    'first_collected_at': p.first_collected_at.isoformat() if p.first_collected_at else None
                                } for p in products[:3]  # 샘플 3개만
                            ]
                        } for category, products in top_categories
                    ],
                    'keyword_trends': [
                        {
                            'keyword': keyword,
                            'frequency': count,
                            'percentage': (count / len(recent_products) * 100) if recent_products else 0
                        } for keyword, count in top_keywords
                    ],
                    'price_trends': price_trends,
                    'daily_new_products': daily_new_products
                }
            }
            
        except Exception as e:
            logger.error(f"상품 트렌드 분석 실패: {str(e)}")
            return {
                'success': False,
                'message': f"상품 트렌드 분석 실패: {str(e)}"
            }
    
    def _analyze_price_trends(self, products: List[WholesalerProduct]) -> Dict:
        """가격대별 트렌드를 분석합니다."""
        price_ranges = {
            '1만원 미만': [],
            '1-5만원': [],
            '5-10만원': [],
            '10-50만원': [],
            '50만원 이상': []
        }
        
        for product in products:
            if not product.wholesale_price:
                continue
                
            price = product.wholesale_price
            if price < 10000:
                price_ranges['1만원 미만'].append(product)
            elif price < 50000:
                price_ranges['1-5만원'].append(product)
            elif price < 100000:
                price_ranges['5-10만원'].append(product)
            elif price < 500000:
                price_ranges['10-50만원'].append(product)
            else:
                price_ranges['50만원 이상'].append(product)
        
        return {
            range_name: {
                'product_count': len(products_in_range),
                'percentage': (len(products_in_range) / len(products) * 100) if products else 0,
                'popular_categories': list(set(p.category_path for p in products_in_range[:10] if p.category_path))
            } for range_name, products_in_range in price_ranges.items()
        }
    
    def _analyze_daily_new_products(self, start_date: datetime, days: int) -> List[Dict]:
        """일별 신상품 추가 현황을 분석합니다."""
        daily_stats = []
        
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            daily_count = self.db.query(WholesalerProduct).filter(
                and_(
                    WholesalerProduct.first_collected_at >= day_start,
                    WholesalerProduct.first_collected_at < day_end,
                    WholesalerProduct.is_active == True
                )
            ).count()
            
            daily_stats.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'new_products_count': daily_count
            })
        
        return daily_stats


class CollectionAnalyzer:
    """수집 성과 분석 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_collection_performance(self, wholesaler_account_id: int = None,
                                     days: int = 30) -> Dict:
        """수집 성과를 분석합니다."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(CollectionLog).filter(
                CollectionLog.started_at >= cutoff_date
            )
            
            if wholesaler_account_id:
                query = query.filter(CollectionLog.wholesaler_account_id == wholesaler_account_id)
            
            logs = query.all()
            
            # 기본 통계
            total_collections = len(logs)
            successful_collections = len([log for log in logs if log.status == CollectionStatus.COMPLETED])
            failed_collections = len([log for log in logs if log.status == CollectionStatus.FAILED])
            
            # 수집 성과 통계
            total_products = sum(log.products_collected or 0 for log in logs)
            total_updated = sum(log.products_updated or 0 for log in logs)
            total_failed = sum(log.products_failed or 0 for log in logs)
            
            # 평균 수집 시간
            completed_logs = [log for log in logs if log.duration_seconds is not None]
            avg_duration = sum(log.duration_seconds for log in completed_logs) / len(completed_logs) if completed_logs else 0
            
            # 도매처별 성과 (전체 조회 시)
            wholesaler_performance = []
            if not wholesaler_account_id:
                wholesaler_stats = self.db.query(
                    WholesalerAccount.account_name,
                    WholesalerAccount.wholesaler_type,
                    func.count(CollectionLog.id).label('collection_count'),
                    func.sum(CollectionLog.products_collected).label('total_collected'),
                    func.avg(CollectionLog.duration_seconds).label('avg_duration')
                ).join(CollectionLog).filter(
                    CollectionLog.started_at >= cutoff_date
                ).group_by(
                    WholesalerAccount.id,
                    WholesalerAccount.account_name,
                    WholesalerAccount.wholesaler_type
                ).all()
                
                wholesaler_performance = [
                    {
                        'account_name': ws.account_name,
                        'wholesaler_type': ws.wholesaler_type.value,
                        'collection_count': ws.collection_count,
                        'total_collected': ws.total_collected or 0,
                        'avg_duration_minutes': (ws.avg_duration / 60) if ws.avg_duration else 0
                    } for ws in wholesaler_stats
                ]
            
            # 최근 수집 현황
            recent_collections = [
                {
                    'id': log.id,
                    'collection_type': log.collection_type,
                    'status': log.status.value,
                    'products_collected': log.products_collected or 0,
                    'products_updated': log.products_updated or 0,
                    'products_failed': log.products_failed or 0,
                    'duration_seconds': log.duration_seconds,
                    'started_at': log.started_at.isoformat() if log.started_at else None,
                    'completed_at': log.completed_at.isoformat() if log.completed_at else None,
                    'error_message': log.error_message
                } for log in sorted(logs, key=lambda x: x.started_at, reverse=True)[:10]
            ]
            
            return {
                'success': True,
                'data': {
                    'analysis_period': {
                        'from': cutoff_date.isoformat(),
                        'to': datetime.utcnow().isoformat(),
                        'days': days
                    },
                    'summary': {
                        'total_collections': total_collections,
                        'successful_collections': successful_collections,
                        'failed_collections': failed_collections,
                        'success_rate': (successful_collections / total_collections * 100) if total_collections > 0 else 0,
                        'total_products_collected': total_products,
                        'total_products_updated': total_updated,
                        'total_products_failed': total_failed,
                        'avg_collection_duration_minutes': avg_duration / 60 if avg_duration > 0 else 0
                    },
                    'wholesaler_performance': wholesaler_performance,
                    'recent_collections': recent_collections
                }
            }
            
        except Exception as e:
            logger.error(f"수집 성과 분석 실패: {str(e)}")
            return {
                'success': False,
                'message': f"수집 성과 분석 실패: {str(e)}"
            }


class AnalysisService:
    """분석 서비스 메인 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_analyzer = ProductAnalyzer(db)
        self.trend_analyzer = TrendAnalyzer(db)
        self.collection_analyzer = CollectionAnalyzer(db)
    
    def get_dashboard_summary(self, wholesaler_account_id: int = None) -> Dict:
        """대시보드용 요약 정보를 제공합니다."""
        try:
            # 최근 7일 신상품
            recent_products = self.product_analyzer.get_recent_products(
                wholesaler_account_id, days=7, limit=50
            )
            
            # 재고 현황
            stock_status = self.product_analyzer.monitor_stock_changes(
                wholesaler_account_id, days=7
            )
            
            # 수집 성과
            collection_performance = self.collection_analyzer.analyze_collection_performance(
                wholesaler_account_id, days=7
            )
            
            # 간단한 트렌드 정보
            trends = self.trend_analyzer.analyze_product_trends(days=7, top_n=5)
            
            return {
                'success': True,
                'data': {
                    'recent_products': recent_products['data'] if recent_products['success'] else None,
                    'stock_status': stock_status['data'] if stock_status['success'] else None,
                    'collection_performance': collection_performance['data'] if collection_performance['success'] else None,
                    'trends': trends['data'] if trends['success'] else None,
                    'last_updated': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"대시보드 요약 정보 조회 실패: {str(e)}")
            return {
                'success': False,
                'message': f"대시보드 요약 정보 조회 실패: {str(e)}"
            }
    
    def generate_report(self, wholesaler_account_id: int = None, 
                       report_type: str = "weekly") -> Dict:
        """분석 보고서를 생성합니다."""
        try:
            # 보고서 기간 설정
            if report_type == "daily":
                days = 1
            elif report_type == "weekly":
                days = 7
            elif report_type == "monthly":
                days = 30
            else:
                days = 7
            
            # 전체 분석 수행
            recent_products = self.product_analyzer.get_recent_products(wholesaler_account_id, days, 100)
            price_analysis = self.product_analyzer.analyze_price_changes(wholesaler_account_id, days)
            stock_analysis = self.product_analyzer.monitor_stock_changes(wholesaler_account_id, days)
            trend_analysis = self.trend_analyzer.analyze_product_trends(days, 10)
            collection_analysis = self.collection_analyzer.analyze_collection_performance(wholesaler_account_id, days)
            
            return {
                'success': True,
                'report': {
                    'type': report_type,
                    'period': days,
                    'generated_at': datetime.utcnow().isoformat(),
                    'wholesaler_account_id': wholesaler_account_id,
                    'sections': {
                        'recent_products': recent_products if recent_products['success'] else None,
                        'price_analysis': price_analysis if price_analysis['success'] else None,
                        'stock_analysis': stock_analysis if stock_analysis['success'] else None,
                        'trend_analysis': trend_analysis if trend_analysis['success'] else None,
                        'collection_analysis': collection_analysis if collection_analysis['success'] else None
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"분석 보고서 생성 실패: {str(e)}")
            return {
                'success': False,
                'message': f"분석 보고서 생성 실패: {str(e)}"
            }