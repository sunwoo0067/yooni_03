"""
마케팅 분석 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
import pandas as pd
import numpy as np

from app.models.marketing import (
    MarketingCampaign, MarketingMessage, MarketingAnalytics,
    CampaignType, MessageStatus, ABTestVariant
)
from app.models.crm import Customer, CustomerSegment
from app.models.order import Order
from app.core.exceptions import BusinessException


class MarketingAnalyticsService:
    """마케팅 분석 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_campaign_analytics(self, campaign_id: int) -> Dict[str, Any]:
        """캠페인 분석 데이터 생성"""
        try:
            campaign = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id == campaign_id
            ).first()
            
            if not campaign:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            # 기본 메트릭 계산
            basic_metrics = await self._calculate_basic_metrics(campaign)
            
            # 시간대별 성과
            temporal_performance = await self._analyze_temporal_performance(campaign)
            
            # 세그먼트별 성과
            segment_performance = await self._analyze_segment_performance(campaign)
            
            # 전환 퍼널 분석
            conversion_funnel = await self._analyze_conversion_funnel(campaign)
            
            # ROI 분석
            roi_analysis = await self._analyze_roi(campaign)
            
            # 고객 생애가치 영향
            ltv_impact = await self._analyze_ltv_impact(campaign)
            
            # 채널 성과 비교
            channel_comparison = await self._compare_channel_performance(campaign)
            
            # 분석 결과 저장
            await self._save_analytics_data(campaign, {
                'basic_metrics': basic_metrics,
                'roi_analysis': roi_analysis
            })
            
            return {
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'analysis_date': datetime.utcnow().isoformat(),
                'basic_metrics': basic_metrics,
                'temporal_performance': temporal_performance,
                'segment_performance': segment_performance,
                'conversion_funnel': conversion_funnel,
                'roi_analysis': roi_analysis,
                'ltv_impact': ltv_impact,
                'channel_comparison': channel_comparison,
                'recommendations': await self._generate_recommendations(campaign, basic_metrics)
            }
            
        except Exception as e:
            raise BusinessException(f"캠페인 분석 실패: {str(e)}")
    
    async def generate_marketing_dashboard(self, date_range: Dict[str, datetime]) -> Dict[str, Any]:
        """마케팅 대시보드 데이터 생성"""
        try:
            start_date = date_range.get('start_date', datetime.utcnow() - timedelta(days=30))
            end_date = date_range.get('end_date', datetime.utcnow())
            
            # 전체 캠페인 요약
            campaign_summary = await self._get_campaign_summary(start_date, end_date)
            
            # 채널별 성과
            channel_performance = await self._get_channel_performance(start_date, end_date)
            
            # 고객 참여 트렌드
            engagement_trends = await self._get_engagement_trends(start_date, end_date)
            
            # 수익 분석
            revenue_analysis = await self._get_revenue_analysis(start_date, end_date)
            
            # 상위 캠페인
            top_campaigns = await self._get_top_campaigns(start_date, end_date)
            
            # 고객 세그먼트 성과
            segment_summary = await self._get_segment_summary(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'campaign_summary': campaign_summary,
                'channel_performance': channel_performance,
                'engagement_trends': engagement_trends,
                'revenue_analysis': revenue_analysis,
                'top_campaigns': top_campaigns,
                'segment_summary': segment_summary,
                'kpi_highlights': await self._calculate_kpi_highlights(
                    campaign_summary, revenue_analysis
                )
            }
            
        except Exception as e:
            raise BusinessException(f"대시보드 생성 실패: {str(e)}")
    
    async def analyze_customer_journey(self, customer_id: int) -> Dict[str, Any]:
        """고객 여정 분석"""
        try:
            # 고객의 모든 마케팅 터치포인트
            touchpoints = self.db.query(MarketingMessage).filter(
                MarketingMessage.customer_id == customer_id
            ).order_by(MarketingMessage.created_at).all()
            
            # 주문 이력
            orders = self.db.query(Order).filter(
                Order.customer_id == customer_id
            ).order_by(Order.created_at).all()
            
            # 여정 타임라인 생성
            journey_timeline = []
            
            for touchpoint in touchpoints:
                journey_timeline.append({
                    'timestamp': touchpoint.created_at.isoformat(),
                    'type': 'marketing',
                    'channel': touchpoint.channel,
                    'campaign_id': touchpoint.campaign_id,
                    'status': touchpoint.status.value,
                    'interaction': {
                        'sent': touchpoint.sent_at.isoformat() if touchpoint.sent_at else None,
                        'opened': touchpoint.opened_at.isoformat() if touchpoint.opened_at else None,
                        'clicked': touchpoint.clicked_at.isoformat() if touchpoint.clicked_at else None
                    }
                })
            
            for order in orders:
                journey_timeline.append({
                    'timestamp': order.created_at.isoformat(),
                    'type': 'purchase',
                    'order_id': order.id,
                    'revenue': order.total_price,
                    'attribution': await self._attribute_order_to_campaign(order, touchpoints)
                })
            
            # 타임라인 정렬
            journey_timeline.sort(key=lambda x: x['timestamp'])
            
            # 여정 분석
            analysis = {
                'customer_id': customer_id,
                'total_touchpoints': len(touchpoints),
                'total_purchases': len(orders),
                'journey_timeline': journey_timeline,
                'channel_engagement': await self._analyze_channel_engagement(touchpoints),
                'conversion_path': await self._analyze_conversion_path(touchpoints, orders),
                'engagement_score': await self._calculate_journey_engagement_score(touchpoints),
                'recommendations': await self._generate_journey_recommendations(
                    touchpoints, orders
                )
            }
            
            return analysis
            
        except Exception as e:
            raise BusinessException(f"고객 여정 분석 실패: {str(e)}")
    
    async def _calculate_basic_metrics(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """기본 메트릭 계산"""
        # 메시지 상태별 집계
        status_counts = self.db.query(
            MarketingMessage.status,
            func.count(MarketingMessage.id).label('count')
        ).filter(
            MarketingMessage.campaign_id == campaign.id
        ).group_by(MarketingMessage.status).all()
        
        status_dict = {status.value: count for status, count in status_counts}
        
        total_sent = sum(count for status, count in status_counts 
                        if status != MessageStatus.PENDING)
        
        metrics = {
            'total_recipients': campaign.expected_recipients or 0,
            'messages_sent': total_sent,
            'messages_delivered': status_dict.get(MessageStatus.DELIVERED.value, 0) + 
                               status_dict.get(MessageStatus.OPENED.value, 0) +
                               status_dict.get(MessageStatus.CLICKED.value, 0) +
                               status_dict.get(MessageStatus.CONVERTED.value, 0),
            'messages_opened': status_dict.get(MessageStatus.OPENED.value, 0) +
                             status_dict.get(MessageStatus.CLICKED.value, 0) +
                             status_dict.get(MessageStatus.CONVERTED.value, 0),
            'messages_clicked': status_dict.get(MessageStatus.CLICKED.value, 0) +
                              status_dict.get(MessageStatus.CONVERTED.value, 0),
            'messages_converted': status_dict.get(MessageStatus.CONVERTED.value, 0),
            'messages_bounced': status_dict.get(MessageStatus.BOUNCED.value, 0),
            'messages_unsubscribed': status_dict.get(MessageStatus.UNSUBSCRIBED.value, 0),
            'delivery_rate': 0,
            'open_rate': 0,
            'click_rate': 0,
            'conversion_rate': 0,
            'bounce_rate': 0,
            'unsubscribe_rate': 0
        }
        
        # 비율 계산
        if total_sent > 0:
            metrics['delivery_rate'] = (metrics['messages_delivered'] / total_sent) * 100
            metrics['bounce_rate'] = (metrics['messages_bounced'] / total_sent) * 100
            metrics['unsubscribe_rate'] = (metrics['messages_unsubscribed'] / total_sent) * 100
            
            if metrics['messages_delivered'] > 0:
                metrics['open_rate'] = (metrics['messages_opened'] / metrics['messages_delivered']) * 100
                
                if metrics['messages_opened'] > 0:
                    metrics['click_rate'] = (metrics['messages_clicked'] / metrics['messages_opened']) * 100
                    
                    if metrics['messages_clicked'] > 0:
                        metrics['conversion_rate'] = (metrics['messages_converted'] / metrics['messages_clicked']) * 100
        
        return metrics
    
    async def _analyze_temporal_performance(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """시간대별 성과 분석"""
        # 시간대별 오픈율
        hourly_opens = self.db.query(
            func.extract('hour', MarketingMessage.opened_at).label('hour'),
            func.count(MarketingMessage.id).label('count')
        ).filter(
            MarketingMessage.campaign_id == campaign.id,
            MarketingMessage.opened_at.isnot(None)
        ).group_by('hour').all()
        
        # 요일별 성과
        daily_performance = self.db.query(
            func.extract('dow', MarketingMessage.sent_at).label('day_of_week'),
            func.count(MarketingMessage.id).label('sent'),
            func.sum(case((MarketingMessage.opened_at.isnot(None), 1), else_=0)).label('opened'),
            func.sum(case((MarketingMessage.clicked_at.isnot(None), 1), else_=0)).label('clicked')
        ).filter(
            MarketingMessage.campaign_id == campaign.id,
            MarketingMessage.sent_at.isnot(None)
        ).group_by('day_of_week').all()
        
        return {
            'hourly_distribution': [
                {'hour': hour, 'opens': count} 
                for hour, count in hourly_opens
            ],
            'daily_performance': [
                {
                    'day': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                           'Thursday', 'Friday', 'Saturday'][int(day)],
                    'sent': sent,
                    'opened': opened,
                    'clicked': clicked,
                    'open_rate': (opened / sent * 100) if sent > 0 else 0
                }
                for day, sent, opened, clicked in daily_performance
            ],
            'best_time': self._find_best_time(hourly_opens),
            'best_day': self._find_best_day(daily_performance)
        }
    
    async def _analyze_segment_performance(self, campaign: MarketingCampaign) -> List[Dict[str, Any]]:
        """세그먼트별 성과 분석"""
        # 세그먼트별 메시지 성과
        segment_performance = self.db.query(
            Customer.segment,
            func.count(MarketingMessage.id).label('total'),
            func.sum(case((MarketingMessage.opened_at.isnot(None), 1), else_=0)).label('opened'),
            func.sum(case((MarketingMessage.clicked_at.isnot(None), 1), else_=0)).label('clicked'),
            func.sum(case((MarketingMessage.converted_at.isnot(None), 1), else_=0)).label('converted'),
            func.sum(MarketingMessage.attributed_revenue).label('revenue')
        ).join(
            Customer, MarketingMessage.customer_id == Customer.id
        ).filter(
            MarketingMessage.campaign_id == campaign.id
        ).group_by(Customer.segment).all()
        
        results = []
        for segment, total, opened, clicked, converted, revenue in segment_performance:
            results.append({
                'segment': segment.value if segment else 'unknown',
                'metrics': {
                    'total_sent': total,
                    'opened': opened,
                    'clicked': clicked,
                    'converted': converted,
                    'revenue': revenue or 0
                },
                'rates': {
                    'open_rate': (opened / total * 100) if total > 0 else 0,
                    'click_rate': (clicked / opened * 100) if opened > 0 else 0,
                    'conversion_rate': (converted / clicked * 100) if clicked > 0 else 0
                },
                'performance_index': self._calculate_performance_index(
                    opened, clicked, converted, total
                )
            })
        
        # 성과 순으로 정렬
        results.sort(key=lambda x: x['performance_index'], reverse=True)
        
        return results
    
    async def _analyze_conversion_funnel(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """전환 퍼널 분석"""
        # 각 단계별 수치
        funnel_data = self.db.query(
            func.count(MarketingMessage.id).label('sent'),
            func.sum(case((MarketingMessage.delivered_at.isnot(None), 1), else_=0)).label('delivered'),
            func.sum(case((MarketingMessage.opened_at.isnot(None), 1), else_=0)).label('opened'),
            func.sum(case((MarketingMessage.clicked_at.isnot(None), 1), else_=0)).label('clicked'),
            func.sum(case((MarketingMessage.converted_at.isnot(None), 1), else_=0)).label('converted')
        ).filter(
            MarketingMessage.campaign_id == campaign.id,
            MarketingMessage.status != MessageStatus.PENDING
        ).first()
        
        sent = funnel_data.sent or 0
        delivered = funnel_data.delivered or 0
        opened = funnel_data.opened or 0
        clicked = funnel_data.clicked or 0
        converted = funnel_data.converted or 0
        
        return {
            'stages': [
                {
                    'stage': 'Sent',
                    'count': sent,
                    'percentage': 100.0
                },
                {
                    'stage': 'Delivered',
                    'count': delivered,
                    'percentage': (delivered / sent * 100) if sent > 0 else 0,
                    'drop_rate': ((sent - delivered) / sent * 100) if sent > 0 else 0
                },
                {
                    'stage': 'Opened',
                    'count': opened,
                    'percentage': (opened / sent * 100) if sent > 0 else 0,
                    'drop_rate': ((delivered - opened) / delivered * 100) if delivered > 0 else 0
                },
                {
                    'stage': 'Clicked',
                    'count': clicked,
                    'percentage': (clicked / sent * 100) if sent > 0 else 0,
                    'drop_rate': ((opened - clicked) / opened * 100) if opened > 0 else 0
                },
                {
                    'stage': 'Converted',
                    'count': converted,
                    'percentage': (converted / sent * 100) if sent > 0 else 0,
                    'drop_rate': ((clicked - converted) / clicked * 100) if clicked > 0 else 0
                }
            ],
            'overall_conversion_rate': (converted / sent * 100) if sent > 0 else 0,
            'bottlenecks': self._identify_funnel_bottlenecks(
                sent, delivered, opened, clicked, converted
            )
        }
    
    async def _analyze_roi(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """ROI 분석"""
        # 수익 데이터
        revenue_data = self.db.query(
            func.sum(MarketingMessage.attributed_revenue).label('total_revenue'),
            func.count(case((MarketingMessage.converted_at.isnot(None), 1))).label('conversions'),
            func.avg(MarketingMessage.conversion_value).label('avg_order_value')
        ).filter(
            MarketingMessage.campaign_id == campaign.id
        ).first()
        
        total_revenue = revenue_data.total_revenue or 0
        conversions = revenue_data.conversions or 0
        avg_order_value = revenue_data.avg_order_value or 0
        
        # 비용 계산 (실제 비용 또는 추정치)
        total_cost = campaign.spent_amount or campaign.budget or 0
        
        # ROI 계산
        roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
        roas = (total_revenue / total_cost) if total_cost > 0 else 0
        
        # 고객 획득 비용
        cpa = (total_cost / conversions) if conversions > 0 else 0
        
        return {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'profit': total_revenue - total_cost,
            'roi': roi,
            'roas': roas,
            'conversions': conversions,
            'average_order_value': avg_order_value,
            'cost_per_acquisition': cpa,
            'revenue_per_recipient': (total_revenue / campaign.sent_count) if campaign.sent_count > 0 else 0,
            'break_even_point': self._calculate_break_even_point(
                total_cost, avg_order_value, campaign.sent_count
            )
        }
    
    async def _analyze_ltv_impact(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """고객 생애가치 영향 분석"""
        # 캠페인 참여 고객의 LTV 변화
        ltv_data = self.db.query(
            func.avg(Customer.lifetime_value).label('avg_ltv'),
            func.avg(Customer.predicted_ltv).label('avg_predicted_ltv'),
            func.count(Customer.id).label('customer_count')
        ).join(
            MarketingMessage, Customer.id == MarketingMessage.customer_id
        ).filter(
            MarketingMessage.campaign_id == campaign.id,
            MarketingMessage.converted_at.isnot(None)
        ).first()
        
        # 전환 고객의 후속 구매 분석
        repeat_purchase_data = self._analyze_repeat_purchases(campaign)
        
        return {
            'converted_customers': ltv_data.customer_count or 0,
            'average_ltv': ltv_data.avg_ltv or 0,
            'average_predicted_ltv': ltv_data.avg_predicted_ltv or 0,
            'repeat_purchase_rate': repeat_purchase_data['rate'],
            'additional_revenue': repeat_purchase_data['revenue'],
            'ltv_uplift': self._calculate_ltv_uplift(campaign),
            'customer_value_improvement': self._analyze_value_improvement(campaign)
        }
    
    async def _compare_channel_performance(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """채널 성과 비교"""
        # 현재 캠페인과 같은 기간의 다른 채널 캠페인들
        comparison_period = timedelta(days=30)
        
        if campaign.start_date:
            start_date = campaign.start_date - comparison_period
            end_date = campaign.end_date or datetime.utcnow()
        else:
            end_date = datetime.utcnow()
            start_date = end_date - comparison_period
        
        # 채널별 평균 성과
        channel_averages = self.db.query(
            MarketingCampaign.campaign_type,
            func.avg(MarketingCampaign.open_rate).label('avg_open_rate'),
            func.avg(MarketingCampaign.click_rate).label('avg_click_rate'),
            func.avg(MarketingCampaign.conversion_rate).label('avg_conversion_rate'),
            func.avg(MarketingCampaign.roi).label('avg_roi')
        ).filter(
            MarketingCampaign.start_date.between(start_date, end_date),
            MarketingCampaign.status.in_(['COMPLETED', 'RUNNING'])
        ).group_by(MarketingCampaign.campaign_type).all()
        
        return {
            'current_campaign': {
                'type': campaign.campaign_type.value,
                'open_rate': campaign.open_rate or 0,
                'click_rate': campaign.click_rate or 0,
                'conversion_rate': campaign.conversion_rate or 0,
                'roi': campaign.roi or 0
            },
            'channel_benchmarks': [
                {
                    'channel': channel_type.value,
                    'avg_open_rate': avg_open or 0,
                    'avg_click_rate': avg_click or 0,
                    'avg_conversion_rate': avg_conv or 0,
                    'avg_roi': avg_roi or 0
                }
                for channel_type, avg_open, avg_click, avg_conv, avg_roi in channel_averages
            ],
            'performance_vs_average': self._calculate_performance_vs_average(
                campaign, channel_averages
            )
        }
    
    async def _save_analytics_data(self, campaign: MarketingCampaign, analytics_data: Dict[str, Any]):
        """분석 데이터 저장"""
        try:
            analytics = MarketingAnalytics(
                analytics_type='campaign',
                entity_id=str(campaign.id),
                entity_name=campaign.name,
                period_start=campaign.start_date or datetime.utcnow(),
                period_end=campaign.end_date or datetime.utcnow(),
                granularity='campaign',
                impressions=analytics_data['basic_metrics']['messages_sent'],
                clicks=analytics_data['basic_metrics']['messages_clicked'],
                conversions=analytics_data['basic_metrics']['messages_converted'],
                revenue=analytics_data['roi_analysis']['total_revenue'],
                ctr=analytics_data['basic_metrics']['click_rate'],
                conversion_rate=analytics_data['basic_metrics']['conversion_rate'],
                cost=analytics_data['roi_analysis']['total_cost'],
                cpc=analytics_data['roi_analysis']['total_cost'] / analytics_data['basic_metrics']['messages_clicked'] 
                    if analytics_data['basic_metrics']['messages_clicked'] > 0 else 0,
                cpa=analytics_data['roi_analysis']['cost_per_acquisition'],
                roi=analytics_data['roi_analysis']['roi'],
                roas=analytics_data['roi_analysis']['roas']
            )
            
            self.db.add(analytics)
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            print(f"분석 데이터 저장 실패: {str(e)}")
    
    async def _generate_recommendations(self, campaign: MarketingCampaign, 
                                      metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """캠페인 개선 권장사항 생성"""
        recommendations = []
        
        # 오픈율 개선
        if metrics['open_rate'] < 20:
            recommendations.append({
                'type': 'open_rate',
                'priority': 'high',
                'issue': f"오픈율이 {metrics['open_rate']:.1f}%로 낮습니다",
                'suggestion': "제목을 더 매력적으로 수정하고, 발송 시간을 최적화하세요",
                'potential_impact': "오픈율 5-10% 향상 가능"
            })
        
        # 클릭률 개선
        if metrics['open_rate'] > 20 and metrics['click_rate'] < 5:
            recommendations.append({
                'type': 'click_rate',
                'priority': 'high',
                'issue': f"클릭률이 {metrics['click_rate']:.1f}%로 낮습니다",
                'suggestion': "CTA 버튼을 더 명확하게 하고, 콘텐츠 관련성을 높이세요",
                'potential_impact': "클릭률 2-3% 향상 가능"
            })
        
        # 전환율 개선
        if metrics['click_rate'] > 5 and metrics['conversion_rate'] < 2:
            recommendations.append({
                'type': 'conversion_rate',
                'priority': 'medium',
                'issue': f"전환율이 {metrics['conversion_rate']:.1f}%로 개선 여지가 있습니다",
                'suggestion': "랜딩 페이지 최적화 및 오퍼 개선을 고려하세요",
                'potential_impact': "전환율 1-2% 향상 가능"
            })
        
        # 배송률 개선
        if metrics['bounce_rate'] > 5:
            recommendations.append({
                'type': 'deliverability',
                'priority': 'high',
                'issue': f"반송률이 {metrics['bounce_rate']:.1f}%로 높습니다",
                'suggestion': "이메일 리스트를 정리하고 발송 도메인 평판을 관리하세요",
                'potential_impact': "배송률 개선으로 전체 성과 향상"
            })
        
        return recommendations
    
    def _find_best_time(self, hourly_opens: List[tuple]) -> Optional[int]:
        """최적 발송 시간 찾기"""
        if not hourly_opens:
            return None
        
        best_hour = max(hourly_opens, key=lambda x: x[1])
        return best_hour[0]
    
    def _find_best_day(self, daily_performance: List[tuple]) -> Optional[str]:
        """최적 발송 요일 찾기"""
        if not daily_performance:
            return None
        
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        best_day_data = max(daily_performance, key=lambda x: x[2] / x[1] if x[1] > 0 else 0)
        return days[int(best_day_data[0])]
    
    def _calculate_performance_index(self, opened: int, clicked: int, 
                                   converted: int, total: int) -> float:
        """성과 지수 계산"""
        if total == 0:
            return 0
        
        # 가중치 적용
        weights = {
            'open': 0.3,
            'click': 0.3,
            'conversion': 0.4
        }
        
        open_rate = opened / total
        click_rate = clicked / total
        conversion_rate = converted / total
        
        index = (open_rate * weights['open'] + 
                click_rate * weights['click'] + 
                conversion_rate * weights['conversion']) * 100
        
        return round(index, 2)
    
    def _identify_funnel_bottlenecks(self, sent: int, delivered: int, 
                                   opened: int, clicked: int, 
                                   converted: int) -> List[str]:
        """퍼널 병목 지점 식별"""
        bottlenecks = []
        
        # 각 단계별 전환율 계산
        delivery_rate = delivered / sent if sent > 0 else 0
        open_rate = opened / delivered if delivered > 0 else 0
        click_rate = clicked / opened if opened > 0 else 0
        conversion_rate = converted / clicked if clicked > 0 else 0
        
        # 병목 지점 식별
        if delivery_rate < 0.95:
            bottlenecks.append("배송 단계에서 문제 발생 (반송률이 높음)")
        
        if open_rate < 0.15:
            bottlenecks.append("오픈 단계에서 큰 이탈 (제목이나 발송시간 개선 필요)")
        
        if click_rate < 0.10:
            bottlenecks.append("클릭 단계에서 이탈 (콘텐츠나 CTA 개선 필요)")
        
        if conversion_rate < 0.20:
            bottlenecks.append("전환 단계에서 이탈 (랜딩페이지나 오퍼 개선 필요)")
        
        return bottlenecks
    
    def _calculate_break_even_point(self, total_cost: float, avg_order_value: float, 
                                  sent_count: int) -> Dict[str, Any]:
        """손익분기점 계산"""
        if avg_order_value == 0 or sent_count == 0:
            return {'conversions_needed': 0, 'conversion_rate_needed': 0}
        
        conversions_needed = int(total_cost / avg_order_value) + 1
        conversion_rate_needed = (conversions_needed / sent_count) * 100
        
        return {
            'conversions_needed': conversions_needed,
            'conversion_rate_needed': round(conversion_rate_needed, 2)
        }
    
    def _analyze_repeat_purchases(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """반복 구매 분석"""
        # 캠페인 전환 고객의 후속 구매
        # 실제 구현에서는 더 정교한 로직 필요
        return {
            'rate': 0.0,
            'revenue': 0.0
        }
    
    def _calculate_ltv_uplift(self, campaign: MarketingCampaign) -> float:
        """LTV 상승률 계산"""
        # 실제 구현에서는 전/후 비교 필요
        return 0.0
    
    def _analyze_value_improvement(self, campaign: MarketingCampaign) -> Dict[str, Any]:
        """고객 가치 개선 분석"""
        # 실제 구현에서는 더 상세한 분석 필요
        return {
            'tier_upgrades': 0,
            'engagement_improvement': 0.0
        }
    
    def _calculate_performance_vs_average(self, campaign: MarketingCampaign, 
                                        channel_averages: List[tuple]) -> Dict[str, float]:
        """평균 대비 성과 계산"""
        # 해당 채널의 평균 찾기
        for channel_type, avg_open, avg_click, avg_conv, avg_roi in channel_averages:
            if channel_type == campaign.campaign_type:
                return {
                    'open_rate_diff': (campaign.open_rate or 0) - (avg_open or 0),
                    'click_rate_diff': (campaign.click_rate or 0) - (avg_click or 0),
                    'conversion_rate_diff': (campaign.conversion_rate or 0) - (avg_conv or 0),
                    'roi_diff': (campaign.roi or 0) - (avg_roi or 0)
                }
        
        return {
            'open_rate_diff': 0,
            'click_rate_diff': 0,
            'conversion_rate_diff': 0,
            'roi_diff': 0
        }
    
    # 대시보드 관련 메서드들
    async def _get_campaign_summary(self, start_date: datetime, 
                                  end_date: datetime) -> Dict[str, Any]:
        """캠페인 요약 정보"""
        # 기간 내 캠페인 통계
        summary = self.db.query(
            func.count(MarketingCampaign.id).label('total_campaigns'),
            func.count(case((MarketingCampaign.status == 'RUNNING', 1))).label('active_campaigns'),
            func.count(case((MarketingCampaign.status == 'COMPLETED', 1))).label('completed_campaigns'),
            func.sum(MarketingCampaign.sent_count).label('total_messages'),
            func.sum(MarketingCampaign.revenue_generated).label('total_revenue')
        ).filter(
            or_(
                and_(MarketingCampaign.start_date >= start_date,
                     MarketingCampaign.start_date <= end_date),
                and_(MarketingCampaign.end_date >= start_date,
                     MarketingCampaign.end_date <= end_date)
            )
        ).first()
        
        return {
            'total_campaigns': summary.total_campaigns or 0,
            'active_campaigns': summary.active_campaigns or 0,
            'completed_campaigns': summary.completed_campaigns or 0,
            'total_messages_sent': summary.total_messages or 0,
            'total_revenue': summary.total_revenue or 0
        }
    
    async def _get_channel_performance(self, start_date: datetime, 
                                     end_date: datetime) -> List[Dict[str, Any]]:
        """채널별 성과"""
        performance = self.db.query(
            MarketingCampaign.campaign_type,
            func.count(MarketingCampaign.id).label('campaign_count'),
            func.sum(MarketingCampaign.sent_count).label('messages_sent'),
            func.avg(MarketingCampaign.open_rate).label('avg_open_rate'),
            func.avg(MarketingCampaign.click_rate).label('avg_click_rate'),
            func.avg(MarketingCampaign.conversion_rate).label('avg_conversion_rate'),
            func.sum(MarketingCampaign.revenue_generated).label('total_revenue')
        ).filter(
            MarketingCampaign.start_date.between(start_date, end_date)
        ).group_by(MarketingCampaign.campaign_type).all()
        
        return [
            {
                'channel': channel.value,
                'campaigns': count,
                'messages': messages or 0,
                'avg_open_rate': avg_open or 0,
                'avg_click_rate': avg_click or 0,
                'avg_conversion_rate': avg_conv or 0,
                'revenue': revenue or 0
            }
            for channel, count, messages, avg_open, avg_click, avg_conv, revenue in performance
        ]
    
    async def _get_engagement_trends(self, start_date: datetime, 
                                   end_date: datetime) -> Dict[str, Any]:
        """참여도 트렌드"""
        # 일별 트렌드 데이터
        daily_trends = self.db.query(
            func.date(MarketingMessage.sent_at).label('date'),
            func.count(MarketingMessage.id).label('sent'),
            func.sum(case((MarketingMessage.opened_at.isnot(None), 1), else_=0)).label('opened'),
            func.sum(case((MarketingMessage.clicked_at.isnot(None), 1), else_=0)).label('clicked')
        ).filter(
            MarketingMessage.sent_at.between(start_date, end_date)
        ).group_by('date').order_by('date').all()
        
        return {
            'daily_trends': [
                {
                    'date': date.isoformat() if date else None,
                    'sent': sent,
                    'opened': opened,
                    'clicked': clicked,
                    'open_rate': (opened / sent * 100) if sent > 0 else 0,
                    'click_rate': (clicked / sent * 100) if sent > 0 else 0
                }
                for date, sent, opened, clicked in daily_trends
            ]
        }
    
    async def _get_revenue_analysis(self, start_date: datetime, 
                                  end_date: datetime) -> Dict[str, Any]:
        """수익 분석"""
        revenue_data = self.db.query(
            func.sum(MarketingCampaign.revenue_generated).label('total_revenue'),
            func.sum(MarketingCampaign.spent_amount).label('total_cost'),
            func.avg(MarketingCampaign.roi).label('avg_roi'),
            func.avg(MarketingCampaign.average_order_value).label('avg_order_value')
        ).filter(
            MarketingCampaign.start_date.between(start_date, end_date)
        ).first()
        
        return {
            'total_revenue': revenue_data.total_revenue or 0,
            'total_cost': revenue_data.total_cost or 0,
            'profit': (revenue_data.total_revenue or 0) - (revenue_data.total_cost or 0),
            'average_roi': revenue_data.avg_roi or 0,
            'average_order_value': revenue_data.avg_order_value or 0
        }
    
    async def _get_top_campaigns(self, start_date: datetime, 
                               end_date: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """상위 캠페인"""
        campaigns = self.db.query(MarketingCampaign).filter(
            MarketingCampaign.start_date.between(start_date, end_date)
        ).order_by(MarketingCampaign.revenue_generated.desc()).limit(limit).all()
        
        return [
            {
                'id': campaign.id,
                'name': campaign.name,
                'type': campaign.campaign_type.value,
                'revenue': campaign.revenue_generated or 0,
                'roi': campaign.roi or 0,
                'conversion_rate': campaign.conversion_rate or 0
            }
            for campaign in campaigns
        ]
    
    async def _get_segment_summary(self, start_date: datetime, 
                                 end_date: datetime) -> List[Dict[str, Any]]:
        """세그먼트 요약"""
        # 세그먼트별 캠페인 성과
        # 실제 구현에서는 campaign_segments 테이블과 조인 필요
        return []
    
    async def _calculate_kpi_highlights(self, campaign_summary: Dict[str, Any], 
                                      revenue_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """주요 KPI 하이라이트"""
        return {
            'total_reach': campaign_summary['total_messages_sent'],
            'total_revenue': revenue_analysis['total_revenue'],
            'average_roi': revenue_analysis['average_roi'],
            'active_campaigns': campaign_summary['active_campaigns']
        }
    
    async def _attribute_order_to_campaign(self, order: Order, 
                                         touchpoints: List[MarketingMessage]) -> Optional[Dict[str, Any]]:
        """주문을 캠페인에 귀속"""
        # 주문 전 마지막 클릭한 캠페인 찾기 (Last Click Attribution)
        for touchpoint in reversed(touchpoints):
            if touchpoint.clicked_at and touchpoint.clicked_at < order.created_at:
                time_diff = (order.created_at - touchpoint.clicked_at).days
                if time_diff <= 30:  # 30일 이내 클릭
                    return {
                        'campaign_id': touchpoint.campaign_id,
                        'attribution_model': 'last_click',
                        'days_to_conversion': time_diff
                    }
        
        return None
    
    async def _analyze_channel_engagement(self, touchpoints: List[MarketingMessage]) -> Dict[str, Any]:
        """채널별 참여도 분석"""
        channel_stats = {}
        
        for touchpoint in touchpoints:
            channel = touchpoint.channel
            if channel not in channel_stats:
                channel_stats[channel] = {
                    'sent': 0,
                    'opened': 0,
                    'clicked': 0
                }
            
            channel_stats[channel]['sent'] += 1
            if touchpoint.opened_at:
                channel_stats[channel]['opened'] += 1
            if touchpoint.clicked_at:
                channel_stats[channel]['clicked'] += 1
        
        return channel_stats
    
    async def _analyze_conversion_path(self, touchpoints: List[MarketingMessage], 
                                     orders: List[Order]) -> List[Dict[str, Any]]:
        """전환 경로 분석"""
        conversion_paths = []
        
        for order in orders:
            path = []
            for touchpoint in touchpoints:
                if touchpoint.sent_at and touchpoint.sent_at < order.created_at:
                    path.append({
                        'channel': touchpoint.channel,
                        'campaign_id': touchpoint.campaign_id,
                        'interaction': 'clicked' if touchpoint.clicked_at else 'opened' if touchpoint.opened_at else 'sent'
                    })
            
            if path:
                conversion_paths.append({
                    'order_id': order.id,
                    'order_value': order.total_price,
                    'path_length': len(path),
                    'touchpoints': path[-5:]  # 마지막 5개 터치포인트
                })
        
        return conversion_paths
    
    async def _calculate_journey_engagement_score(self, touchpoints: List[MarketingMessage]) -> float:
        """여정 참여도 점수 계산"""
        if not touchpoints:
            return 0.0
        
        engagement_score = 0.0
        
        # 각 상호작용에 가중치 부여
        for touchpoint in touchpoints:
            if touchpoint.converted_at:
                engagement_score += 10
            elif touchpoint.clicked_at:
                engagement_score += 5
            elif touchpoint.opened_at:
                engagement_score += 2
            elif touchpoint.sent_at:
                engagement_score += 1
        
        # 정규화 (0-100)
        normalized_score = min(engagement_score / len(touchpoints) * 10, 100)
        
        return round(normalized_score, 2)
    
    async def _generate_journey_recommendations(self, touchpoints: List[MarketingMessage], 
                                              orders: List[Order]) -> List[str]:
        """고객 여정 기반 권장사항"""
        recommendations = []
        
        # 마지막 상호작용 확인
        if touchpoints:
            last_touchpoint = touchpoints[-1]
            days_since_last = (datetime.utcnow() - last_touchpoint.created_at).days
            
            if days_since_last > 30:
                recommendations.append("30일 이상 상호작용이 없습니다. 재참여 캠페인을 고려하세요.")
        
        # 전환율 확인
        if touchpoints and not orders:
            recommendations.append("마케팅 메시지는 받았지만 구매가 없습니다. 오퍼를 개선하세요.")
        
        # 채널 다양성
        channels = set(t.channel for t in touchpoints)
        if len(channels) == 1:
            recommendations.append("단일 채널만 사용 중입니다. 멀티채널 전략을 고려하세요.")
        
        return recommendations