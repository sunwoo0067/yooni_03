"""
A/B 테스팅 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import numpy as np
from scipy import stats
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.marketing import (
    MarketingCampaign, ABTestVariant, MarketingMessage,
    MessageStatus
)
from app.models.crm import Customer
from app.core.exceptions import BusinessException


class ABTestingService:
    """A/B 테스팅 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.min_sample_size = 100  # 최소 샘플 크기
        self.confidence_level = 0.95  # 신뢰 수준
    
    async def create_ab_test(self, campaign_id: int, variants_data: List[Dict[str, Any]]) -> List[ABTestVariant]:
        """A/B 테스트 생성"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            # A/B 테스트 설정
            campaign.is_ab_test = True
            
            # 변형 생성
            variants = []
            total_allocation = sum(v.get('traffic_allocation', 0) for v in variants_data)
            
            if abs(total_allocation - 100.0) > 0.01:
                raise BusinessException("트래픽 할당 합계는 100%여야 합니다")
            
            for i, variant_data in enumerate(variants_data):
                variant = ABTestVariant(
                    campaign_id=campaign_id,
                    variant_name=variant_data.get('variant_name', chr(65 + i)),  # A, B, C...
                    variant_type=variant_data['variant_type'],
                    subject=variant_data.get('subject'),
                    content=variant_data.get('content'),
                    cta_text=variant_data.get('cta_text'),
                    send_time=variant_data.get('send_time'),
                    traffic_allocation=variant_data['traffic_allocation']
                )
                
                self.db.add(variant)
                variants.append(variant)
            
            self.db.commit()
            
            return variants
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"A/B 테스트 생성 실패: {str(e)}")
    
    async def assign_variant(self, campaign_id: int, customer_id: int) -> ABTestVariant:
        """고객에게 변형 할당"""
        try:
            # 이미 할당된 변형이 있는지 확인
            existing_message = self.db.query(MarketingMessage).filter(
                MarketingMessage.campaign_id == campaign_id,
                MarketingMessage.customer_id == customer_id
            ).first()
            
            if existing_message and existing_message.variant_id:
                variant = self.db.query(ABTestVariant).filter(
                    ABTestVariant.campaign_id == campaign_id,
                    ABTestVariant.variant_name == existing_message.variant_id
                ).first()
                return variant
            
            # 변형들 조회
            variants = self.db.query(ABTestVariant).filter(
                ABTestVariant.campaign_id == campaign_id
            ).all()
            
            if not variants:
                raise BusinessException("A/B 테스트 변형이 없습니다")
            
            # 트래픽 할당에 따라 변형 선택
            variant = self._select_variant_by_allocation(variants)
            
            # 할당 카운트 증가
            variant.assigned_count += 1
            self.db.commit()
            
            return variant
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"변형 할당 실패: {str(e)}")
    
    def _select_variant_by_allocation(self, variants: List[ABTestVariant]) -> ABTestVariant:
        """트래픽 할당 비율에 따라 변형 선택"""
        rand = random.random() * 100
        cumulative = 0
        
        for variant in variants:
            cumulative += variant.traffic_allocation
            if rand <= cumulative:
                return variant
        
        return variants[-1]  # 마지막 변형 반환 (fallback)
    
    async def track_variant_performance(self, campaign_id: int, variant_name: str, 
                                      metric: str, value: float = 1.0):
        """변형 성과 추적"""
        try:
            variant = self.db.query(ABTestVariant).filter(
                ABTestVariant.campaign_id == campaign_id,
                ABTestVariant.variant_name == variant_name
            ).first()
            
            if not variant:
                return
            
            # 메트릭별 카운트 증가
            if metric == 'sent':
                variant.sent_count += int(value)
            elif metric == 'opened':
                variant.opened_count += int(value)
            elif metric == 'clicked':
                variant.clicked_count += int(value)
            elif metric == 'converted':
                variant.converted_count += int(value)
            
            # 비율 재계산
            if variant.sent_count > 0:
                variant.open_rate = (variant.opened_count / variant.sent_count) * 100
                
                if variant.opened_count > 0:
                    variant.click_rate = (variant.clicked_count / variant.opened_count) * 100
                    
                    if variant.clicked_count > 0:
                        variant.conversion_rate = (variant.converted_count / variant.clicked_count) * 100
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            print(f"변형 성과 추적 실패: {str(e)}")
    
    async def analyze_ab_test(self, campaign_id: int) -> Dict[str, Any]:
        """A/B 테스트 분석"""
        try:
            variants = self.db.query(ABTestVariant).filter(
                ABTestVariant.campaign_id == campaign_id
            ).all()
            
            if len(variants) < 2:
                raise BusinessException("A/B 테스트는 최소 2개의 변형이 필요합니다")
            
            # 각 변형의 성과 분석
            analysis_results = {
                'variants': [],
                'winner': None,
                'confidence_level': self.confidence_level,
                'recommendations': []
            }
            
            # 메트릭별 분석
            metrics = ['open_rate', 'click_rate', 'conversion_rate']
            metric_winners = {}
            
            for metric in metrics:
                # 각 변형의 메트릭 값과 샘플 크기
                variant_data = []
                for variant in variants:
                    if metric == 'open_rate':
                        successes = variant.opened_count
                        trials = variant.sent_count
                    elif metric == 'click_rate':
                        successes = variant.clicked_count
                        trials = variant.opened_count
                    else:  # conversion_rate
                        successes = variant.converted_count
                        trials = variant.clicked_count
                    
                    if trials > 0:
                        rate = (successes / trials) * 100
                        variant_data.append({
                            'variant': variant,
                            'rate': rate,
                            'successes': successes,
                            'trials': trials
                        })
                
                # 통계적 유의성 검정
                if len(variant_data) >= 2:
                    winner_data = self._perform_statistical_test(variant_data)
                    if winner_data:
                        metric_winners[metric] = winner_data
            
            # 전체 승자 결정
            overall_winner = self._determine_overall_winner(metric_winners)
            
            # 결과 정리
            for variant in variants:
                variant_result = {
                    'variant_name': variant.variant_name,
                    'variant_type': variant.variant_type,
                    'traffic_allocation': variant.traffic_allocation,
                    'assigned_count': variant.assigned_count,
                    'metrics': {
                        'sent': variant.sent_count,
                        'opened': variant.opened_count,
                        'clicked': variant.clicked_count,
                        'converted': variant.converted_count,
                        'open_rate': variant.open_rate or 0,
                        'click_rate': variant.click_rate or 0,
                        'conversion_rate': variant.conversion_rate or 0
                    },
                    'is_winner': variant.variant_name == overall_winner if overall_winner else False
                }
                
                # 신뢰도 추가
                for metric, winner_data in metric_winners.items():
                    if winner_data['winner'].variant_name == variant.variant_name:
                        variant_result[f'{metric}_confidence'] = winner_data['confidence']
                
                analysis_results['variants'].append(variant_result)
            
            # 승자 설정
            if overall_winner:
                analysis_results['winner'] = overall_winner
                winning_variant = next((v for v in variants if v.variant_name == overall_winner), None)
                if winning_variant:
                    winning_variant.is_winner = True
                    self.db.commit()
            
            # 권장사항 생성
            analysis_results['recommendations'] = self._generate_recommendations(
                variants, metric_winners, overall_winner
            )
            
            return analysis_results
            
        except Exception as e:
            raise BusinessException(f"A/B 테스트 분석 실패: {str(e)}")
    
    def _perform_statistical_test(self, variant_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """통계적 유의성 검정 (카이제곱 검정)"""
        if len(variant_data) < 2:
            return None
        
        # 최소 샘플 크기 확인
        if any(d['trials'] < self.min_sample_size for d in variant_data):
            return None
        
        # 가장 높은 성과의 변형 찾기
        best_variant = max(variant_data, key=lambda x: x['rate'])
        
        # 다른 변형들과 비교
        for other in variant_data:
            if other == best_variant:
                continue
            
            # 2x2 분할표 생성
            observed = np.array([
                [best_variant['successes'], best_variant['trials'] - best_variant['successes']],
                [other['successes'], other['trials'] - other['successes']]
            ])
            
            # 카이제곱 검정
            chi2, p_value, dof, expected = stats.chi2_contingency(observed)
            
            # 유의성 확인
            if p_value >= (1 - self.confidence_level):
                return None  # 통계적으로 유의하지 않음
        
        # 모든 비교에서 유의한 경우
        return {
            'winner': best_variant['variant'],
            'confidence': self.confidence_level,
            'rate': best_variant['rate']
        }
    
    def _determine_overall_winner(self, metric_winners: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """전체 승자 결정"""
        if not metric_winners:
            return None
        
        # 가장 중요한 메트릭 우선순위: conversion_rate > click_rate > open_rate
        priority_metrics = ['conversion_rate', 'click_rate', 'open_rate']
        
        for metric in priority_metrics:
            if metric in metric_winners:
                return metric_winners[metric]['winner'].variant_name
        
        return None
    
    def _generate_recommendations(self, variants: List[ABTestVariant], 
                                metric_winners: Dict[str, Dict[str, Any]], 
                                overall_winner: Optional[str]) -> List[str]:
        """A/B 테스트 권장사항 생성"""
        recommendations = []
        
        # 샘플 크기 확인
        total_sent = sum(v.sent_count for v in variants)
        if total_sent < self.min_sample_size * len(variants):
            recommendations.append(
                f"더 신뢰할 수 있는 결과를 위해 각 변형당 최소 {self.min_sample_size}개 이상의 샘플이 필요합니다."
            )
        
        # 승자가 있는 경우
        if overall_winner:
            winning_variant = next((v for v in variants if v.variant_name == overall_winner), None)
            if winning_variant:
                recommendations.append(
                    f"변형 {overall_winner}가 통계적으로 유의한 승자입니다. "
                    f"이 변형을 100% 트래픽에 적용하는 것을 권장합니다."
                )
                
                # 개선 사항 분석
                if winning_variant.variant_type == 'subject':
                    recommendations.append(
                        "제목이 성과에 큰 영향을 미쳤습니다. "
                        "향후 캠페인에서도 유사한 스타일의 제목을 사용해보세요."
                    )
                elif winning_variant.variant_type == 'content':
                    recommendations.append(
                        "콘텐츠 스타일이 고객 참여에 효과적이었습니다. "
                        "이 콘텐츠 형식을 템플릿으로 저장하는 것을 권장합니다."
                    )
        else:
            recommendations.append(
                "아직 통계적으로 유의한 승자가 없습니다. "
                "더 많은 데이터가 수집될 때까지 테스트를 계속 진행하세요."
            )
        
        # 성과가 낮은 변형에 대한 조언
        worst_variant = min(variants, key=lambda v: v.conversion_rate or 0)
        if worst_variant.conversion_rate is not None and worst_variant.conversion_rate < 1:
            recommendations.append(
                f"변형 {worst_variant.variant_name}의 전환율이 매우 낮습니다. "
                "이 변형의 트래픽 할당을 줄이거나 중단하는 것을 고려하세요."
            )
        
        return recommendations
    
    async def apply_winner(self, campaign_id: int) -> MarketingCampaign:
        """승자 변형을 캠페인에 적용"""
        try:
            # 승자 변형 찾기
            winner_variant = self.db.query(ABTestVariant).filter(
                ABTestVariant.campaign_id == campaign_id,
                ABTestVariant.is_winner == True
            ).first()
            
            if not winner_variant:
                raise BusinessException("승자 변형이 결정되지 않았습니다")
            
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            # 승자 변형의 내용을 캠페인에 적용
            if winner_variant.subject:
                campaign.subject = winner_variant.subject
            if winner_variant.content:
                campaign.content_template = winner_variant.content
            
            # A/B 테스트 종료
            campaign.is_ab_test = False
            
            # 아직 발송되지 않은 메시지들을 승자 변형으로 업데이트
            pending_messages = self.db.query(MarketingMessage).filter(
                MarketingMessage.campaign_id == campaign_id,
                MarketingMessage.status == MessageStatus.PENDING
            ).all()
            
            for message in pending_messages:
                message.variant_id = winner_variant.variant_name
                if winner_variant.subject:
                    message.personalized_subject = winner_variant.subject
                if winner_variant.content:
                    message.personalized_content = winner_variant.content
            
            self.db.commit()
            self.db.refresh(campaign)
            
            return campaign
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"승자 적용 실패: {str(e)}")
    
    async def get_variant_performance_timeline(self, campaign_id: int, 
                                             variant_name: str,
                                             granularity: str = 'hourly') -> List[Dict[str, Any]]:
        """변형 성과 타임라인 조회"""
        try:
            # 메시지 상태 변경 이력을 기반으로 타임라인 생성
            messages = self.db.query(MarketingMessage).filter(
                MarketingMessage.campaign_id == campaign_id,
                MarketingMessage.variant_id == variant_name
            ).all()
            
            timeline_data = []
            
            # 시간대별 집계 (실제 구현에서는 더 정교한 집계 필요)
            # 여기서는 간단한 예시만 제공
            
            return timeline_data
            
        except Exception as e:
            raise BusinessException(f"타임라인 조회 실패: {str(e)}")