"""
RFM 분석 엔진
Recency(최근성), Frequency(빈도), Monetary(금액) 분석을 통한 고객 세분화
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ...models.crm import Customer, RFMAnalysis, CustomerSegment
from ...models.order import Order


class RFMAnalyzer:
    """RFM 분석을 수행하는 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # RFM 세그먼트 정의
        self.segment_mapping = {
            "555": CustomerSegment.CHAMPIONS,
            "554": CustomerSegment.CHAMPIONS,
            "544": CustomerSegment.CHAMPIONS,
            "545": CustomerSegment.CHAMPIONS,
            "454": CustomerSegment.CHAMPIONS,
            "455": CustomerSegment.CHAMPIONS,
            "445": CustomerSegment.CHAMPIONS,
            
            "543": CustomerSegment.LOYAL_CUSTOMERS,
            "444": CustomerSegment.LOYAL_CUSTOMERS,
            "435": CustomerSegment.LOYAL_CUSTOMERS,
            "355": CustomerSegment.LOYAL_CUSTOMERS,
            "354": CustomerSegment.LOYAL_CUSTOMERS,
            "345": CustomerSegment.LOYAL_CUSTOMERS,
            "344": CustomerSegment.LOYAL_CUSTOMERS,
            
            "512": CustomerSegment.POTENTIAL_LOYALISTS,
            "511": CustomerSegment.POTENTIAL_LOYALISTS,
            "422": CustomerSegment.POTENTIAL_LOYALISTS,
            "421": CustomerSegment.POTENTIAL_LOYALISTS,
            "412": CustomerSegment.POTENTIAL_LOYALISTS,
            "411": CustomerSegment.POTENTIAL_LOYALISTS,
            
            "512": CustomerSegment.NEW_CUSTOMERS,
            "511": CustomerSegment.NEW_CUSTOMERS,
            "422": CustomerSegment.NEW_CUSTOMERS,
            "421": CustomerSegment.NEW_CUSTOMERS,
            "412": CustomerSegment.NEW_CUSTOMERS,
            "411": CustomerSegment.NEW_CUSTOMERS,
            
            "522": CustomerSegment.PROMISING,
            "521": CustomerSegment.PROMISING,
            "523": CustomerSegment.PROMISING,
            "513": CustomerSegment.PROMISING,
            "414": CustomerSegment.PROMISING,
            
            "155": CustomerSegment.NEED_ATTENTION,
            "154": CustomerSegment.NEED_ATTENTION,
            "144": CustomerSegment.NEED_ATTENTION,
            "214": CustomerSegment.NEED_ATTENTION,
            
            "155": CustomerSegment.ABOUT_TO_SLEEP,
            "254": CustomerSegment.ABOUT_TO_SLEEP,
            "244": CustomerSegment.ABOUT_TO_SLEEP,
            
            "155": CustomerSegment.AT_RISK,
            "254": CustomerSegment.AT_RISK,
            "244": CustomerSegment.AT_RISK,
            
            "155": CustomerSegment.CANNOT_LOSE_THEM,
            "254": CustomerSegment.CANNOT_LOSE_THEM,
            "244": CustomerSegment.CANNOT_LOSE_THEM,
            
            "132": CustomerSegment.HIBERNATING,
            "231": CustomerSegment.HIBERNATING,
            "221": CustomerSegment.HIBERNATING,
            "213": CustomerSegment.HIBERNATING,
            "131": CustomerSegment.HIBERNATING,
            
            "111": CustomerSegment.LOST,
            "112": CustomerSegment.LOST,
            "121": CustomerSegment.LOST,
            "122": CustomerSegment.LOST,
            "211": CustomerSegment.LOST,
        }
    
    def calculate_rfm_scores(self, analysis_date: datetime = None) -> pd.DataFrame:
        """
        모든 고객의 RFM 점수를 계산
        
        Args:
            analysis_date: 분석 기준일 (기본값: 오늘)
            
        Returns:
            RFM 데이터가 포함된 DataFrame
        """
        if analysis_date is None:
            analysis_date = datetime.now()
        
        # 고객별 주문 데이터 집계
        rfm_query = self.db.query(
            Order.customer_id,
            func.max(Order.order_date).label('last_order_date'),
            func.count(Order.id).label('frequency'),
            func.sum(Order.total_amount).label('monetary')
        ).filter(
            Order.order_status != 'cancelled'
        ).group_by(Order.customer_id)
        
        rfm_data = []
        for row in rfm_query.all():
            # Recency 계산 (마지막 주문으로부터 경과일)
            recency_days = (analysis_date - row.last_order_date).days
            
            rfm_data.append({
                'customer_id': row.customer_id,
                'recency_days': recency_days,
                'frequency': row.frequency,
                'monetary': float(row.monetary)
            })
        
        if not rfm_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(rfm_data)
        
        # RFM 점수 계산 (1-5 분위수)
        df['recency_score'] = pd.qcut(df['recency_days'], q=5, labels=[5,4,3,2,1], duplicates='drop')
        df['frequency_score'] = pd.qcut(df['frequency'].rank(method='first'), q=5, labels=[1,2,3,4,5], duplicates='drop')
        df['monetary_score'] = pd.qcut(df['monetary'].rank(method='first'), q=5, labels=[1,2,3,4,5], duplicates='drop')
        
        # RFM 점수 문자열 생성
        df['rfm_score'] = (
            df['recency_score'].astype(str) + 
            df['frequency_score'].astype(str) + 
            df['monetary_score'].astype(str)
        )
        
        # 세그먼트 매핑
        df['segment'] = df['rfm_score'].map(self._get_segment_from_score)
        
        return df
    
    def _get_segment_from_score(self, rfm_score: str) -> CustomerSegment:
        """RFM 점수를 기반으로 고객 세그먼트 결정"""
        # 정확한 매칭을 찾지 못한 경우 점수 기반으로 추정
        r, f, m = int(rfm_score[0]), int(rfm_score[1]), int(rfm_score[2])
        
        if r >= 4 and f >= 4 and m >= 4:
            return CustomerSegment.CHAMPIONS
        elif r >= 3 and f >= 3 and m >= 3:
            return CustomerSegment.LOYAL_CUSTOMERS
        elif r >= 4 and f <= 2:
            return CustomerSegment.NEW_CUSTOMERS
        elif r >= 3 and f <= 2:
            return CustomerSegment.PROMISING
        elif r <= 2 and f >= 3 and m >= 3:
            return CustomerSegment.CANNOT_LOSE_THEM
        elif r <= 2 and f >= 2:
            return CustomerSegment.AT_RISK
        elif r <= 2 and f <= 2:
            return CustomerSegment.HIBERNATING
        else:
            return CustomerSegment.NEED_ATTENTION
    
    def update_customer_rfm_data(self, analysis_date: datetime = None) -> Dict:
        """
        고객 테이블의 RFM 데이터를 업데이트
        
        Args:
            analysis_date: 분석 기준일
            
        Returns:
            업데이트 결과 요약
        """
        if analysis_date is None:
            analysis_date = datetime.now()
        
        rfm_df = self.calculate_rfm_scores(analysis_date)
        
        if rfm_df.empty:
            return {"updated_customers": 0, "message": "No customer data found"}
        
        updated_count = 0
        
        for _, row in rfm_df.iterrows():
            customer = self.db.query(Customer).filter(
                Customer.id == row['customer_id']
            ).first()
            
            if customer:
                # Customer 테이블 업데이트
                customer.recency_score = int(row['recency_score'])
                customer.frequency_score = int(row['frequency_score'])
                customer.monetary_score = int(row['monetary_score'])
                customer.rfm_score = row['rfm_score']
                customer.segment = row['segment']
                customer.updated_at = analysis_date
                
                # RFM Analysis 레코드 생성
                rfm_analysis = RFMAnalysis(
                    customer_id=customer.id,
                    analysis_date=analysis_date,
                    analysis_period_start=analysis_date - timedelta(days=365),
                    analysis_period_end=analysis_date,
                    recency_days=row['recency_days'],
                    frequency_count=row['frequency'],
                    monetary_value=row['monetary'],
                    recency_score=int(row['recency_score']),
                    frequency_score=int(row['frequency_score']),
                    monetary_score=int(row['monetary_score']),
                    rfm_score=row['rfm_score'],
                    segment=row['segment'],
                    segment_description=self._get_segment_description(row['segment']),
                    average_order_value=row['monetary'] / row['frequency'] if row['frequency'] > 0 else 0
                )
                
                self.db.add(rfm_analysis)
                updated_count += 1
        
        self.db.commit()
        
        return {
            "updated_customers": updated_count,
            "analysis_date": analysis_date.isoformat(),
            "segment_distribution": self._get_segment_distribution(rfm_df)
        }
    
    def _get_segment_description(self, segment: CustomerSegment) -> str:
        """세그먼트별 설명 반환"""
        descriptions = {
            CustomerSegment.CHAMPIONS: "최고의 고객들. 최근에 자주 구매하며 많은 금액을 지출합니다.",
            CustomerSegment.LOYAL_CUSTOMERS: "충성도 높은 고객들. 정기적으로 구매하는 핵심 고객층입니다.",
            CustomerSegment.POTENTIAL_LOYALISTS: "충성 고객이 될 가능성이 높은 고객들입니다.",
            CustomerSegment.NEW_CUSTOMERS: "최근에 구매한 신규 고객들입니다.",
            CustomerSegment.PROMISING: "최근 구매했지만 자주 구매하지는 않는 고객들입니다.",
            CustomerSegment.NEED_ATTENTION: "평균보다 낮은 빈도와 금액의 고객들로 관심이 필요합니다.",
            CustomerSegment.ABOUT_TO_SLEEP: "구매 빈도가 낮아지고 있는 고객들입니다.",
            CustomerSegment.AT_RISK: "이탈 위험이 있는 고객들입니다.",
            CustomerSegment.CANNOT_LOSE_THEM: "과거 높은 가치 고객이었지만 최근 구매가 없는 중요 고객들입니다.",
            CustomerSegment.HIBERNATING: "오랫동안 구매하지 않은 휴면 고객들입니다.",
            CustomerSegment.LOST: "이미 이탈한 것으로 보이는 고객들입니다."
        }
        return descriptions.get(segment, "세그먼트 설명이 없습니다.")
    
    def _get_segment_distribution(self, rfm_df: pd.DataFrame) -> Dict:
        """세그먼트별 고객 분포 반환"""
        segment_counts = rfm_df['segment'].value_counts()
        total_customers = len(rfm_df)
        
        distribution = {}
        for segment, count in segment_counts.items():
            distribution[segment.value] = {
                "count": int(count),
                "percentage": round((count / total_customers) * 100, 2)
            }
        
        return distribution
    
    def get_customer_rfm_profile(self, customer_id: int) -> Optional[Dict]:
        """
        특정 고객의 RFM 프로필 조회
        
        Args:
            customer_id: 고객 ID
            
        Returns:
            고객의 RFM 프로필 데이터
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return None
        
        # 최신 RFM 분석 결과 조회
        latest_rfm = self.db.query(RFMAnalysis).filter(
            RFMAnalysis.customer_id == customer_id
        ).order_by(RFMAnalysis.analysis_date.desc()).first()
        
        profile = {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "segment": customer.segment.value if customer.segment else None,
            "rfm_score": customer.rfm_score,
            "recency_score": customer.recency_score,
            "frequency_score": customer.frequency_score,
            "monetary_score": customer.monetary_score,
            "total_orders": customer.total_orders,
            "total_spent": customer.total_spent,
            "average_order_value": customer.average_order_value,
            "last_purchase_date": customer.last_purchase_date.isoformat() if customer.last_purchase_date else None
        }
        
        if latest_rfm:
            profile.update({
                "recency_days": latest_rfm.recency_days,
                "frequency_count": latest_rfm.frequency_count,
                "monetary_value": latest_rfm.monetary_value,
                "segment_description": latest_rfm.segment_description,
                "last_analysis_date": latest_rfm.analysis_date.isoformat()
            })
        
        return profile
    
    def get_segment_customers(self, segment: CustomerSegment, limit: int = 100) -> List[Dict]:
        """
        특정 세그먼트의 고객 목록 조회
        
        Args:
            segment: 조회할 세그먼트
            limit: 반환할 최대 고객 수
            
        Returns:
            해당 세그먼트 고객 목록
        """
        customers = self.db.query(Customer).filter(
            Customer.segment == segment,
            Customer.is_active == True
        ).limit(limit).all()
        
        result = []
        for customer in customers:
            result.append({
                "customer_id": customer.id,
                "name": customer.name,
                "email": customer.email,
                "rfm_score": customer.rfm_score,
                "total_spent": customer.total_spent,
                "total_orders": customer.total_orders,
                "last_purchase_date": customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
                "registration_date": customer.registration_date.isoformat()
            })
        
        return result
    
    def get_rfm_trends(self, customer_id: int, months: int = 12) -> List[Dict]:
        """
        고객의 RFM 트렌드 분석
        
        Args:
            customer_id: 고객 ID
            months: 분석할 개월 수
            
        Returns:
            월별 RFM 트렌드 데이터
        """
        start_date = datetime.now() - timedelta(days=months * 30)
        
        rfm_analyses = self.db.query(RFMAnalysis).filter(
            and_(
                RFMAnalysis.customer_id == customer_id,
                RFMAnalysis.analysis_date >= start_date
            )
        ).order_by(RFMAnalysis.analysis_date).all()
        
        trends = []
        for analysis in rfm_analyses:
            trends.append({
                "analysis_date": analysis.analysis_date.isoformat(),
                "recency_score": analysis.recency_score,
                "frequency_score": analysis.frequency_score,
                "monetary_score": analysis.monetary_score,
                "rfm_score": analysis.rfm_score,
                "segment": analysis.segment.value,
                "monetary_value": analysis.monetary_value,
                "frequency_count": analysis.frequency_count,
                "recency_days": analysis.recency_days
            })
        
        return trends