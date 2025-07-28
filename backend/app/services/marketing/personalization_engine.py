"""
개인화 엔진
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

from app.models.crm import (
    Customer, CustomerBehavior, CustomerPreference,
    CustomerRecommendation, CustomerSegment
)
from app.models.marketing import MarketingMessage
from app.models.order_core import Order
from app.models.product import Product
from app.services.ai.ai_manager import AIManager
from app.core.exceptions import BusinessException


class PersonalizationEngine:
    """개인화 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_manager = AIManager()
    
    async def generate_personalized_content(self, customer_id: int, 
                                          template: str, 
                                          context: Dict[str, Any] = None) -> str:
        """개인화된 콘텐츠 생성"""
        try:
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer:
                raise BusinessException("고객을 찾을 수 없습니다")
            
            # 고객 데이터 수집
            customer_data = await self._collect_customer_data(customer)
            
            # 개인화 변수 준비
            personalization_vars = self._prepare_personalization_variables(customer, customer_data)
            
            # 템플릿 변수 치환
            personalized_content = self._replace_template_variables(template, personalization_vars)
            
            # AI 기반 고급 개인화
            if context and context.get('use_ai_personalization'):
                personalized_content = await self._apply_ai_personalization(
                    customer, customer_data, personalized_content, context
                )
            
            return personalized_content
            
        except Exception as e:
            raise BusinessException(f"개인화 콘텐츠 생성 실패: {str(e)}")
    
    async def generate_product_recommendations(self, customer_id: int, 
                                             recommendation_type: str = 'collaborative',
                                             limit: int = 10) -> List[Dict[str, Any]]:
        """상품 추천 생성"""
        try:
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer:
                raise BusinessException("고객을 찾을 수 없습니다")
            
            # 추천 알고리즘 선택
            if recommendation_type == 'collaborative':
                recommendations = await self._collaborative_filtering(customer, limit)
            elif recommendation_type == 'content_based':
                recommendations = await self._content_based_filtering(customer, limit)
            elif recommendation_type == 'hybrid':
                recommendations = await self._hybrid_recommendations(customer, limit)
            else:
                recommendations = await self._rule_based_recommendations(customer, limit)
            
            # 추천 로그 저장
            for i, rec in enumerate(recommendations):
                recommendation_log = CustomerRecommendation(
                    customer_id=customer_id,
                    recommendation_type='product',
                    algorithm_used=recommendation_type,
                    recommended_items=[rec['product_id']],
                    recommendation_score=rec['score'],
                    personalization_factors={
                        'rank': i + 1,
                        'reason': rec.get('reason', '')
                    }
                )
                self.db.add(recommendation_log)
            
            self.db.commit()
            
            return recommendations
            
        except Exception as e:
            raise BusinessException(f"상품 추천 생성 실패: {str(e)}")
    
    async def update_customer_preferences(self, customer_id: int, 
                                        behavior_data: Dict[str, Any]) -> CustomerPreference:
        """고객 선호도 업데이트"""
        try:
            # 기존 선호도 조회 또는 생성
            preference = self.db.query(CustomerPreference).filter(
                CustomerPreference.customer_id == customer_id
            ).first()
            
            if not preference:
                preference = CustomerPreference(customer_id=customer_id)
                self.db.add(preference)
            
            # 행동 데이터 기반 선호도 업데이트
            await self._update_category_preferences(preference, behavior_data)
            await self._update_price_preferences(preference, behavior_data)
            await self._update_time_preferences(preference, behavior_data)
            await self._update_brand_preferences(preference, behavior_data)
            
            # 할인 민감도 계산
            preference.discount_sensitivity = await self._calculate_discount_sensitivity(customer_id)
            
            # 신뢰도 점수 업데이트
            preference.confidence_score = await self._calculate_preference_confidence(preference)
            preference.last_updated = datetime.utcnow()
            preference.data_points_count = (preference.data_points_count or 0) + 1
            
            self.db.commit()
            self.db.refresh(preference)
            
            return preference
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"선호도 업데이트 실패: {str(e)}")
    
    async def get_personalization_insights(self, customer_id: int) -> Dict[str, Any]:
        """고객 개인화 인사이트 조회"""
        try:
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer:
                raise BusinessException("고객을 찾을 수 없습니다")
            
            # 고객 데이터 수집
            customer_data = await self._collect_customer_data(customer)
            
            # 인사이트 생성
            insights = {
                'customer_id': customer_id,
                'profile': self._generate_customer_profile(customer, customer_data),
                'preferences': self._analyze_preferences(customer_data),
                'behavior_patterns': self._analyze_behavior_patterns(customer_data),
                'engagement_score': self._calculate_engagement_score(customer_data),
                'personalization_opportunities': self._identify_opportunities(customer, customer_data),
                'recommended_actions': self._generate_recommended_actions(customer, customer_data)
            }
            
            return insights
            
        except Exception as e:
            raise BusinessException(f"인사이트 조회 실패: {str(e)}")
    
    async def _collect_customer_data(self, customer: Customer) -> Dict[str, Any]:
        """고객 관련 데이터 수집"""
        # 최근 주문 내역
        recent_orders = self.db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.created_at >= datetime.utcnow() - timedelta(days=180)
        ).order_by(Order.created_at.desc()).limit(50).all()
        
        # 최근 행동 데이터
        recent_behaviors = self.db.query(CustomerBehavior).filter(
            CustomerBehavior.customer_id == customer.id,
            CustomerBehavior.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).order_by(CustomerBehavior.timestamp.desc()).limit(100).all()
        
        # 선호도 데이터
        preferences = self.db.query(CustomerPreference).filter(
            CustomerPreference.customer_id == customer.id
        ).first()
        
        # 최근 마케팅 반응
        marketing_responses = self.db.query(MarketingMessage).filter(
            MarketingMessage.customer_id == customer.id,
            MarketingMessage.created_at >= datetime.utcnow() - timedelta(days=90)
        ).all()
        
        return {
            'customer': customer,
            'recent_orders': recent_orders,
            'recent_behaviors': recent_behaviors,
            'preferences': preferences,
            'marketing_responses': marketing_responses
        }
    
    def _prepare_personalization_variables(self, customer: Customer, 
                                         customer_data: Dict[str, Any]) -> Dict[str, str]:
        """개인화 변수 준비"""
        # 기본 변수
        variables = {
            '{{name}}': customer.name or '고객님',
            '{{first_name}}': customer.name.split()[0] if customer.name else '고객님',
            '{{email}}': customer.email or '',
            '{{phone}}': customer.phone or '',
            '{{city}}': customer.city or '',
            '{{member_since}}': customer.registration_date.strftime('%Y년 %m월') if customer.registration_date else '',
            '{{total_orders}}': str(customer.total_orders or 0),
            '{{total_spent}}': f"{customer.total_spent or 0:,.0f}원",
            '{{average_order_value}}': f"{customer.average_order_value or 0:,.0f}원",
            '{{loyalty_tier}}': self._get_loyalty_tier_name(customer.customer_value_tier),
            '{{lifecycle_stage}}': self._get_lifecycle_stage_name(customer.lifecycle_stage)
        }
        
        # 최근 구매 정보
        if customer_data['recent_orders']:
            last_order = customer_data['recent_orders'][0]
            variables['{{last_purchase_date}}'] = last_order.created_at.strftime('%Y년 %m월 %d일')
            variables['{{days_since_purchase}}'] = str((datetime.utcnow() - last_order.created_at).days)
        else:
            variables['{{last_purchase_date}}'] = '구매 이력 없음'
            variables['{{days_since_purchase}}'] = 'N/A'
        
        # 선호 카테고리
        if customer.preferred_categories:
            variables['{{preferred_category}}'] = customer.preferred_categories[0] if customer.preferred_categories else ''
        
        # 선호 브랜드
        if customer.preferred_brands:
            variables['{{preferred_brand}}'] = customer.preferred_brands[0] if customer.preferred_brands else ''
        
        return variables
    
    def _replace_template_variables(self, template: str, variables: Dict[str, str]) -> str:
        """템플릿 변수 치환"""
        content = template
        for var, value in variables.items():
            content = content.replace(var, value)
        return content
    
    async def _apply_ai_personalization(self, customer: Customer, 
                                      customer_data: Dict[str, Any],
                                      content: str, 
                                      context: Dict[str, Any]) -> str:
        """AI 기반 고급 개인화"""
        try:
            # 고객 컨텍스트 준비
            customer_context = {
                'customer_segment': customer.segment.value if customer.segment else 'unknown',
                'lifecycle_stage': customer.lifecycle_stage.value if customer.lifecycle_stage else 'new',
                'preferences': customer_data['preferences'].__dict__ if customer_data['preferences'] else {},
                'recent_behaviors': [
                    {
                        'action': b.action_type,
                        'category': b.product_category,
                        'timestamp': b.timestamp.isoformat()
                    }
                    for b in customer_data['recent_behaviors'][:10]
                ],
                'campaign_context': context
            }
            
            # AI를 통한 개인화
            personalized_content = await self.ai_manager.enhance_marketing_content(
                original_content=content,
                customer_context=customer_context
            )
            
            return personalized_content
            
        except Exception as e:
            print(f"AI 개인화 실패: {str(e)}")
            return content  # 실패 시 원본 반환
    
    async def _collaborative_filtering(self, customer: Customer, limit: int) -> List[Dict[str, Any]]:
        """협업 필터링 기반 추천"""
        # 유사한 고객 찾기
        similar_customers = await self._find_similar_customers(customer, top_k=20)
        
        # 유사 고객들이 구매한 상품 중 현재 고객이 구매하지 않은 상품
        customer_products = self.db.query(Order.product_id).filter(
            Order.customer_id == customer.id
        ).distinct().subquery()
        
        recommendations = []
        
        for similar_customer in similar_customers:
            # 유사 고객의 구매 상품
            products = self.db.query(
                Product,
                func.count(Order.id).label('purchase_count')
            ).join(Order).filter(
                Order.customer_id == similar_customer['customer_id'],
                ~Product.id.in_(customer_products),
                Product.is_active == True
            ).group_by(Product.id).order_by(
                func.count(Order.id).desc()
            ).limit(5).all()
            
            for product, purchase_count in products:
                score = similar_customer['similarity'] * (purchase_count / 10)  # 정규화
                recommendations.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'score': score,
                    'reason': f"유사한 고객들이 자주 구매한 상품"
                })
        
        # 점수별 정렬 및 중복 제거
        recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)
        seen = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec['product_id'] not in seen:
                seen.add(rec['product_id'])
                unique_recommendations.append(rec)
                if len(unique_recommendations) >= limit:
                    break
        
        return unique_recommendations
    
    async def _content_based_filtering(self, customer: Customer, limit: int) -> List[Dict[str, Any]]:
        """콘텐츠 기반 필터링 추천"""
        # 고객이 최근 관심을 보인 상품들
        recent_products = self.db.query(Product).join(CustomerBehavior).filter(
            CustomerBehavior.customer_id == customer.id,
            CustomerBehavior.action_type.in_(['view', 'add_to_cart', 'purchase']),
            CustomerBehavior.timestamp >= datetime.utcnow() - timedelta(days=30)
        ).distinct().limit(10).all()
        
        if not recent_products:
            return []
        
        recommendations = []
        
        # 각 관심 상품과 유사한 상품 찾기
        for product in recent_products:
            # 같은 카테고리의 상품
            similar_products = self.db.query(Product).filter(
                Product.category == product.category,
                Product.id != product.id,
                Product.is_active == True,
                Product.price.between(product.price * 0.7, product.price * 1.3)  # 비슷한 가격대
            ).limit(3).all()
            
            for similar_product in similar_products:
                # 유사도 점수 계산 (간단한 예시)
                score = 0.8  # 기본 점수
                
                # 브랜드가 같으면 점수 증가
                if hasattr(product, 'brand') and hasattr(similar_product, 'brand'):
                    if product.brand == similar_product.brand:
                        score += 0.1
                
                recommendations.append({
                    'product_id': similar_product.id,
                    'product_name': similar_product.name,
                    'score': score,
                    'reason': f"{product.name}와 유사한 상품"
                })
        
        # 점수별 정렬 및 중복 제거
        recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)
        seen = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec['product_id'] not in seen:
                seen.add(rec['product_id'])
                unique_recommendations.append(rec)
                if len(unique_recommendations) >= limit:
                    break
        
        return unique_recommendations
    
    async def _hybrid_recommendations(self, customer: Customer, limit: int) -> List[Dict[str, Any]]:
        """하이브리드 추천 (협업 + 콘텐츠 기반)"""
        # 두 방식의 추천 결과 가져오기
        collaborative_recs = await self._collaborative_filtering(customer, limit // 2)
        content_recs = await self._content_based_filtering(customer, limit // 2)
        
        # 결과 병합 및 점수 조정
        all_recommendations = {}
        
        for rec in collaborative_recs:
            all_recommendations[rec['product_id']] = rec
        
        for rec in content_recs:
            if rec['product_id'] in all_recommendations:
                # 두 방식 모두에서 추천된 경우 점수 증가
                all_recommendations[rec['product_id']]['score'] *= 1.5
                all_recommendations[rec['product_id']]['reason'] = "여러 요인으로 강력 추천"
            else:
                all_recommendations[rec['product_id']] = rec
        
        # 최종 정렬
        final_recommendations = sorted(
            all_recommendations.values(), 
            key=lambda x: x['score'], 
            reverse=True
        )[:limit]
        
        return final_recommendations
    
    async def _rule_based_recommendations(self, customer: Customer, limit: int) -> List[Dict[str, Any]]:
        """규칙 기반 추천"""
        recommendations = []
        
        # 베스트셀러 추천
        bestsellers = self.db.query(
            Product,
            func.count(Order.id).label('order_count')
        ).join(Order).filter(
            Product.is_active == True,
            Order.created_at >= datetime.utcnow() - timedelta(days=30)
        ).group_by(Product.id).order_by(
            func.count(Order.id).desc()
        ).limit(5).all()
        
        for product, order_count in bestsellers:
            recommendations.append({
                'product_id': product.id,
                'product_name': product.name,
                'score': 0.7,
                'reason': "인기 상품"
            })
        
        # 신상품 추천
        new_products = self.db.query(Product).filter(
            Product.is_active == True,
            Product.created_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(Product.created_at.desc()).limit(3).all()
        
        for product in new_products:
            recommendations.append({
                'product_id': product.id,
                'product_name': product.name,
                'score': 0.6,
                'reason': "신상품"
            })
        
        # 할인 상품 추천 (할인 민감도가 높은 고객에게)
        if hasattr(customer, 'discount_sensitivity') and customer.discount_sensitivity > 0.5:
            # 할인 상품 로직 (실제 구현 시 할인 정보 필요)
            pass
        
        return recommendations[:limit]
    
    async def _find_similar_customers(self, customer: Customer, top_k: int = 10) -> List[Dict[str, Any]]:
        """유사한 고객 찾기"""
        # 고객 특성 벡터 생성
        customer_features = self._create_customer_feature_vector(customer)
        
        # 같은 세그먼트의 다른 고객들
        similar_customers = []
        
        other_customers = self.db.query(Customer).filter(
            Customer.id != customer.id,
            Customer.segment == customer.segment
        ).limit(100).all()
        
        for other in other_customers:
            other_features = self._create_customer_feature_vector(other)
            similarity = self._calculate_cosine_similarity(customer_features, other_features)
            
            similar_customers.append({
                'customer_id': other.id,
                'similarity': similarity
            })
        
        # 유사도 순으로 정렬
        similar_customers.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar_customers[:top_k]
    
    def _create_customer_feature_vector(self, customer: Customer) -> np.ndarray:
        """고객 특성 벡터 생성"""
        features = [
            customer.total_orders or 0,
            customer.total_spent or 0,
            customer.average_order_value or 0,
            customer.recency_score or 3,
            customer.frequency_score or 3,
            customer.monetary_score or 3,
            len(customer.preferred_categories) if customer.preferred_categories else 0,
            customer.age or 35,  # 기본값
            1 if customer.gender == 'M' else 0,
            customer.mobile_usage_rate or 0.5
        ]
        
        return np.array(features)
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """코사인 유사도 계산"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)
    
    async def _update_category_preferences(self, preference: CustomerPreference, 
                                         behavior_data: Dict[str, Any]):
        """카테고리 선호도 업데이트"""
        category_scores = preference.preferred_categories or {}
        
        # 행동 타입별 가중치
        action_weights = {
            'view': 1,
            'add_to_cart': 3,
            'purchase': 5
        }
        
        # 새로운 행동 데이터 반영
        if 'action_type' in behavior_data and 'category' in behavior_data:
            action = behavior_data['action_type']
            category = behavior_data['category']
            weight = action_weights.get(action, 1)
            
            current_score = category_scores.get(category, 0)
            # 지수 이동 평균 적용
            category_scores[category] = current_score * 0.8 + weight * 0.2
        
        preference.preferred_categories = category_scores
    
    async def _update_price_preferences(self, preference: CustomerPreference, 
                                      behavior_data: Dict[str, Any]):
        """가격대 선호도 업데이트"""
        price_ranges = preference.preferred_price_ranges or {}
        
        if 'price' in behavior_data:
            price = behavior_data['price']
            # 가격대 구간 결정
            if price < 10000:
                range_key = '0-10000'
            elif price < 30000:
                range_key = '10000-30000'
            elif price < 50000:
                range_key = '30000-50000'
            elif price < 100000:
                range_key = '50000-100000'
            else:
                range_key = '100000+'
            
            current_score = price_ranges.get(range_key, 0)
            price_ranges[range_key] = current_score + 1
        
        preference.preferred_price_ranges = price_ranges
    
    async def _update_time_preferences(self, preference: CustomerPreference, 
                                     behavior_data: Dict[str, Any]):
        """시간대 선호도 업데이트"""
        time_preferences = {
            'day_of_week': preference.preferred_day_of_week or {},
            'time_of_day': preference.preferred_time_of_day or {}
        }
        
        if 'timestamp' in behavior_data:
            timestamp = behavior_data['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            # 요일 선호도
            day_name = timestamp.strftime('%A')
            time_preferences['day_of_week'][day_name] = \
                time_preferences['day_of_week'].get(day_name, 0) + 1
            
            # 시간대 선호도
            hour = timestamp.hour
            if hour < 6:
                time_slot = 'dawn'
            elif hour < 12:
                time_slot = 'morning'
            elif hour < 18:
                time_slot = 'afternoon'
            else:
                time_slot = 'evening'
            
            time_preferences['time_of_day'][time_slot] = \
                time_preferences['time_of_day'].get(time_slot, 0) + 1
        
        preference.preferred_day_of_week = time_preferences['day_of_week']
        preference.preferred_time_of_day = time_preferences['time_of_day']
    
    async def _update_brand_preferences(self, preference: CustomerPreference, 
                                      behavior_data: Dict[str, Any]):
        """브랜드 선호도 업데이트"""
        brand_scores = preference.preferred_brands or {}
        
        if 'brand' in behavior_data:
            brand = behavior_data['brand']
            current_score = brand_scores.get(brand, 0)
            brand_scores[brand] = current_score + 1
        
        preference.preferred_brands = brand_scores
    
    async def _calculate_discount_sensitivity(self, customer_id: int) -> float:
        """할인 민감도 계산"""
        # 할인 상품 구매 비율 계산
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.customer_id == customer_id
        ).scalar() or 0
        
        if total_orders == 0:
            return 0.5  # 기본값
        
        # 할인 상품 구매 수 (실제 구현 시 할인 정보 필요)
        discount_orders = 0  # TODO: 실제 할인 구매 수 계산
        
        return discount_orders / total_orders if total_orders > 0 else 0.5
    
    async def _calculate_preference_confidence(self, preference: CustomerPreference) -> float:
        """선호도 신뢰도 계산"""
        data_points = preference.data_points_count or 0
        
        # 데이터 포인트 수에 따른 신뢰도 (최대 0.95)
        confidence = min(data_points / 100, 0.95)
        
        return confidence
    
    def _generate_customer_profile(self, customer: Customer, 
                                 customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """고객 프로필 생성"""
        return {
            'demographics': {
                'age': customer.age,
                'gender': customer.gender,
                'location': customer.city
            },
            'value_metrics': {
                'lifetime_value': customer.lifetime_value,
                'average_order_value': customer.average_order_value,
                'total_orders': customer.total_orders,
                'customer_tier': customer.customer_value_tier
            },
            'engagement': {
                'lifecycle_stage': customer.lifecycle_stage.value if customer.lifecycle_stage else None,
                'last_engagement': customer.last_engagement_date.isoformat() if customer.last_engagement_date else None,
                'email_consent': customer.email_marketing_consent,
                'sms_consent': customer.sms_marketing_consent
            },
            'rfm_profile': {
                'recency_score': customer.recency_score,
                'frequency_score': customer.frequency_score,
                'monetary_score': customer.monetary_score,
                'segment': customer.segment.value if customer.segment else None
            }
        }
    
    def _analyze_preferences(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """선호도 분석"""
        preferences = customer_data.get('preferences')
        if not preferences:
            return {}
        
        return {
            'top_categories': self._get_top_items(preferences.preferred_categories, 3),
            'top_brands': self._get_top_items(preferences.preferred_brands, 3),
            'price_sensitivity': self._analyze_price_sensitivity(preferences.preferred_price_ranges),
            'time_preferences': {
                'best_day': self._get_top_items(preferences.preferred_day_of_week, 1)[0] if preferences.preferred_day_of_week else None,
                'best_time': self._get_top_items(preferences.preferred_time_of_day, 1)[0] if preferences.preferred_time_of_day else None
            },
            'discount_sensitivity': preferences.discount_sensitivity
        }
    
    def _analyze_behavior_patterns(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """행동 패턴 분석"""
        behaviors = customer_data.get('recent_behaviors', [])
        
        if not behaviors:
            return {}
        
        # 행동 타입별 집계
        action_counts = {}
        for behavior in behaviors:
            action = behavior.action_type
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            'dominant_action': max(action_counts, key=action_counts.get) if action_counts else None,
            'action_distribution': action_counts,
            'activity_level': len(behaviors),
            'engagement_trend': self._calculate_engagement_trend(behaviors)
        }
    
    def _calculate_engagement_score(self, customer_data: Dict[str, Any]) -> float:
        """참여도 점수 계산"""
        score = 0.0
        
        # 최근 주문 가중치
        recent_orders = customer_data.get('recent_orders', [])
        if recent_orders:
            days_since_order = (datetime.utcnow() - recent_orders[0].created_at).days
            order_score = max(0, 1 - (days_since_order / 90))  # 90일 기준
            score += order_score * 0.4
        
        # 최근 행동 가중치
        recent_behaviors = customer_data.get('recent_behaviors', [])
        if recent_behaviors:
            behavior_score = min(len(recent_behaviors) / 50, 1)  # 50개 기준
            score += behavior_score * 0.3
        
        # 마케팅 반응 가중치
        marketing_responses = customer_data.get('marketing_responses', [])
        if marketing_responses:
            opened = sum(1 for m in marketing_responses if m.opened_at is not None)
            clicked = sum(1 for m in marketing_responses if m.clicked_at is not None)
            response_score = (opened + clicked * 2) / (len(marketing_responses) * 3)
            score += response_score * 0.3
        
        return round(score, 2)
    
    def _identify_opportunities(self, customer: Customer, 
                              customer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """개인화 기회 식별"""
        opportunities = []
        
        # 이탈 위험 고객
        if customer.churn_probability and customer.churn_probability > 0.7:
            opportunities.append({
                'type': 'retention',
                'priority': 'high',
                'description': '이탈 위험이 높은 고객입니다. 재참여 캠페인이 필요합니다.',
                'suggested_action': 'personalized_win_back_campaign'
            })
        
        # 업셀링 기회
        if customer.average_order_value and customer.total_spent:
            if customer.average_order_value < customer.total_spent / (customer.total_orders or 1) * 0.8:
                opportunities.append({
                    'type': 'upselling',
                    'priority': 'medium',
                    'description': '평균 주문 금액이 감소 추세입니다. 업셀링 기회가 있습니다.',
                    'suggested_action': 'premium_product_recommendation'
                })
        
        # 크로스셀링 기회
        if customer_data.get('preferences'):
            pref = customer_data['preferences']
            if pref.preferred_categories and len(pref.preferred_categories) < 3:
                opportunities.append({
                    'type': 'cross_selling',
                    'priority': 'medium',
                    'description': '구매 카테고리가 제한적입니다. 크로스셀링 기회가 있습니다.',
                    'suggested_action': 'category_expansion_campaign'
                })
        
        return opportunities
    
    def _generate_recommended_actions(self, customer: Customer, 
                                    customer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """권장 액션 생성"""
        actions = []
        
        # 생애주기 단계별 액션
        if customer.lifecycle_stage:
            stage_actions = {
                'NEW': {
                    'action': 'welcome_series',
                    'description': '웰컴 시리즈 캠페인 실행',
                    'timing': 'immediate'
                },
                'ACTIVE': {
                    'action': 'loyalty_program',
                    'description': '로열티 프로그램 안내',
                    'timing': 'next_purchase'
                },
                'AT_RISK': {
                    'action': 'reactivation_campaign',
                    'description': '재활성화 캠페인 실행',
                    'timing': 'within_7_days'
                },
                'DORMANT': {
                    'action': 'win_back_offer',
                    'description': '특별 할인 오퍼 제공',
                    'timing': 'immediate'
                }
            }
            
            if customer.lifecycle_stage.value in stage_actions:
                actions.append(stage_actions[customer.lifecycle_stage.value])
        
        # 선호도 기반 액션
        preferences = customer_data.get('preferences')
        if preferences and preferences.discount_sensitivity > 0.7:
            actions.append({
                'action': 'discount_alert',
                'description': '할인 알림 설정',
                'timing': 'ongoing'
            })
        
        return actions
    
    def _get_top_items(self, items_dict: Dict[str, float], n: int) -> List[str]:
        """상위 N개 아이템 추출"""
        if not items_dict:
            return []
        
        sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items[:n]]
    
    def _analyze_price_sensitivity(self, price_ranges: Dict[str, int]) -> str:
        """가격 민감도 분석"""
        if not price_ranges:
            return 'unknown'
        
        # 가장 많이 구매한 가격대 찾기
        top_range = max(price_ranges, key=price_ranges.get)
        
        if '0-10000' in top_range or '10000-30000' in top_range:
            return 'high'
        elif '30000-50000' in top_range:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_engagement_trend(self, behaviors: List[CustomerBehavior]) -> str:
        """참여도 트렌드 계산"""
        if len(behaviors) < 10:
            return 'insufficient_data'
        
        # 최근 행동과 과거 행동 비교
        midpoint = len(behaviors) // 2
        recent_count = len(behaviors[:midpoint])
        past_count = len(behaviors[midpoint:])
        
        if recent_count > past_count * 1.2:
            return 'increasing'
        elif recent_count < past_count * 0.8:
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_loyalty_tier_name(self, tier: str) -> str:
        """로열티 티어 한글명"""
        tier_names = {
            'bronze': '브론즈',
            'silver': '실버',
            'gold': '골드',
            'platinum': '플래티넘'
        }
        return tier_names.get(tier, tier or '일반')
    
    def _get_lifecycle_stage_name(self, stage) -> str:
        """생애주기 단계 한글명"""
        if not stage:
            return '신규'
        
        stage_names = {
            'NEW': '신규 고객',
            'ACTIVE': '활성 고객',
            'ENGAGED': '충성 고객',
            'AT_RISK': '이탈 위험',
            'DORMANT': '휴면 고객',
            'CHURNED': '이탈 고객',
            'VIP': 'VIP 고객'
        }
        return stage_names.get(stage.value, '일반')