"""
리타겟팅 서비스
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import json

from app.models.crm import Customer, CustomerBehavior
from app.models.marketing import MarketingCampaign, MarketingMessage, CampaignType
from app.models.order_core import Order
from app.models.product import Product
from app.services.marketing.campaign_manager import CampaignManager
from app.services.marketing.personalization_engine import PersonalizationEngine
from app.core.exceptions import BusinessException


class RetargetingService:
    """리타겟팅 캠페인 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.campaign_manager = CampaignManager(db)
        self.personalization_engine = PersonalizationEngine(db)
    
    async def create_cart_abandonment_campaign(self, settings: Dict[str, Any]) -> MarketingCampaign:
        """장바구니 이탈 리타겟팅 캠페인 생성"""
        try:
            # 타겟 고객 식별
            target_customers = await self._identify_cart_abandoners(
                hours_since=settings.get('hours_since_abandonment', 24),
                min_cart_value=settings.get('min_cart_value', 0)
            )
            
            if not target_customers:
                raise BusinessException("타겟 고객이 없습니다")
            
            # 캠페인 데이터 준비
            campaign_data = {
                'name': settings.get('name', f'장바구니 이탈 리타겟팅 - {datetime.now().strftime("%Y%m%d")}'),
                'description': '장바구니에 상품을 담고 이탈한 고객 대상 리타겟팅',
                'campaign_type': settings.get('campaign_type', CampaignType.EMAIL.value),
                'subject': settings.get('subject', '장바구니에 담으신 상품이 기다리고 있어요! 🛒'),
                'content_template': await self._generate_cart_recovery_template(settings),
                'personalization_tags': ['name', 'cart_items', 'cart_value', 'discount_code'],
                'target_conditions': {
                    'customer_ids': [c['customer_id'] for c in target_customers]
                },
                'schedule_type': settings.get('schedule_type', 'immediate'),
                'created_by': settings.get('created_by', 'system')
            }
            
            # 캠페인 생성
            campaign = await self.campaign_manager.create_campaign(campaign_data)
            
            # 개인화된 메시지 생성
            await self._create_personalized_cart_messages(campaign, target_customers)
            
            return campaign
            
        except Exception as e:
            raise BusinessException(f"장바구니 이탈 캠페인 생성 실패: {str(e)}")
    
    async def create_browse_abandonment_campaign(self, settings: Dict[str, Any]) -> MarketingCampaign:
        """상품 조회 이탈 리타겟팅 캠페인 생성"""
        try:
            # 타겟 고객 식별
            target_customers = await self._identify_browse_abandoners(
                days_since=settings.get('days_since_browse', 3),
                min_views=settings.get('min_product_views', 3)
            )
            
            if not target_customers:
                raise BusinessException("타겟 고객이 없습니다")
            
            # 캠페인 데이터 준비
            campaign_data = {
                'name': settings.get('name', f'상품 조회 리타겟팅 - {datetime.now().strftime("%Y%m%d")}'),
                'description': '상품을 조회했지만 구매하지 않은 고객 대상 리타겟팅',
                'campaign_type': settings.get('campaign_type', CampaignType.EMAIL.value),
                'subject': settings.get('subject', '관심있게 보셨던 상품을 다시 보세요! 👀'),
                'content_template': await self._generate_browse_recovery_template(settings),
                'personalization_tags': ['name', 'viewed_products', 'recommendations'],
                'target_conditions': {
                    'customer_ids': [c['customer_id'] for c in target_customers]
                },
                'schedule_type': settings.get('schedule_type', 'immediate'),
                'created_by': settings.get('created_by', 'system')
            }
            
            # 캠페인 생성
            campaign = await self.campaign_manager.create_campaign(campaign_data)
            
            # 개인화된 메시지 생성
            await self._create_personalized_browse_messages(campaign, target_customers)
            
            return campaign
            
        except Exception as e:
            raise BusinessException(f"상품 조회 리타겟팅 캠페인 생성 실패: {str(e)}")
    
    async def create_customer_winback_campaign(self, settings: Dict[str, Any]) -> MarketingCampaign:
        """고객 재활성화 캠페인 생성"""
        try:
            # 타겟 고객 식별
            target_customers = await self._identify_inactive_customers(
                days_inactive=settings.get('days_inactive', 90),
                min_previous_orders=settings.get('min_previous_orders', 1)
            )
            
            if not target_customers:
                raise BusinessException("타겟 고객이 없습니다")
            
            # 캠페인 데이터 준비
            campaign_data = {
                'name': settings.get('name', f'고객 재활성화 - {datetime.now().strftime("%Y%m%d")}'),
                'description': '오랫동안 구매가 없는 고객 대상 재활성화 캠페인',
                'campaign_type': settings.get('campaign_type', CampaignType.EMAIL.value),
                'subject': settings.get('subject', '오랜만이에요! 특별한 혜택을 준비했어요 🎁'),
                'content_template': await self._generate_winback_template(settings),
                'personalization_tags': ['name', 'last_purchase_date', 'special_offer', 'loyalty_points'],
                'target_conditions': {
                    'customer_ids': [c['customer_id'] for c in target_customers]
                },
                'schedule_type': settings.get('schedule_type', 'immediate'),
                'created_by': settings.get('created_by', 'system')
            }
            
            # 캠페인 생성
            campaign = await self.campaign_manager.create_campaign(campaign_data)
            
            # 개인화된 메시지 생성
            await self._create_personalized_winback_messages(campaign, target_customers)
            
            return campaign
            
        except Exception as e:
            raise BusinessException(f"고객 재활성화 캠페인 생성 실패: {str(e)}")
    
    async def create_post_purchase_campaign(self, settings: Dict[str, Any]) -> MarketingCampaign:
        """구매 후 리타겟팅 캠페인 생성"""
        try:
            # 타겟 고객 식별
            target_customers = await self._identify_recent_purchasers(
                days_since_purchase=settings.get('days_since_purchase', 7),
                campaign_type=settings.get('post_purchase_type', 'cross_sell')
            )
            
            if not target_customers:
                raise BusinessException("타겟 고객이 없습니다")
            
            # 캠페인 유형별 템플릿
            if settings.get('post_purchase_type') == 'review_request':
                subject = '구매하신 상품은 어떠셨나요? 리뷰를 남겨주세요 ⭐'
                template = await self._generate_review_request_template(settings)
            elif settings.get('post_purchase_type') == 'cross_sell':
                subject = '이 상품도 마음에 드실 거예요! 🛍️'
                template = await self._generate_cross_sell_template(settings)
            else:  # repurchase
                subject = '재구매 시기가 되었어요! 할인 혜택을 확인하세요 🔄'
                template = await self._generate_repurchase_template(settings)
            
            # 캠페인 데이터 준비
            campaign_data = {
                'name': settings.get('name', f'구매 후 리타겟팅 - {datetime.now().strftime("%Y%m%d")}'),
                'description': '최근 구매 고객 대상 리타겟팅',
                'campaign_type': settings.get('campaign_type', CampaignType.EMAIL.value),
                'subject': settings.get('subject', subject),
                'content_template': template,
                'personalization_tags': ['name', 'purchased_products', 'recommendations', 'special_offer'],
                'target_conditions': {
                    'customer_ids': [c['customer_id'] for c in target_customers]
                },
                'schedule_type': settings.get('schedule_type', 'immediate'),
                'created_by': settings.get('created_by', 'system')
            }
            
            # 캠페인 생성
            campaign = await self.campaign_manager.create_campaign(campaign_data)
            
            # 개인화된 메시지 생성
            await self._create_personalized_post_purchase_messages(campaign, target_customers)
            
            return campaign
            
        except Exception as e:
            raise BusinessException(f"구매 후 리타겟팅 캠페인 생성 실패: {str(e)}")
    
    async def analyze_retargeting_performance(self, campaign_ids: List[int]) -> Dict[str, Any]:
        """리타겟팅 캠페인 성과 분석"""
        try:
            campaigns = self.db.query(MarketingCampaign).filter(
                MarketingCampaign.id.in_(campaign_ids)
            ).all()
            
            if not campaigns:
                raise BusinessException("캠페인을 찾을 수 없습니다")
            
            # 전체 성과 집계
            total_metrics = {
                'total_campaigns': len(campaigns),
                'total_sent': sum(c.sent_count or 0 for c in campaigns),
                'total_opened': sum(c.opened_count or 0 for c in campaigns),
                'total_clicked': sum(c.clicked_count or 0 for c in campaigns),
                'total_converted': sum(c.converted_count or 0 for c in campaigns),
                'total_revenue': sum(c.revenue_generated or 0 for c in campaigns)
            }
            
            # 평균 성과율
            if total_metrics['total_sent'] > 0:
                total_metrics['avg_open_rate'] = (total_metrics['total_opened'] / total_metrics['total_sent']) * 100
                total_metrics['avg_click_rate'] = (total_metrics['total_clicked'] / total_metrics['total_opened']) * 100 if total_metrics['total_opened'] > 0 else 0
                total_metrics['avg_conversion_rate'] = (total_metrics['total_converted'] / total_metrics['total_sent']) * 100
            
            # 캠페인 유형별 성과
            performance_by_type = {}
            for campaign in campaigns:
                campaign_type = self._identify_campaign_type(campaign)
                if campaign_type not in performance_by_type:
                    performance_by_type[campaign_type] = {
                        'count': 0,
                        'sent': 0,
                        'converted': 0,
                        'revenue': 0
                    }
                
                performance_by_type[campaign_type]['count'] += 1
                performance_by_type[campaign_type]['sent'] += campaign.sent_count or 0
                performance_by_type[campaign_type]['converted'] += campaign.converted_count or 0
                performance_by_type[campaign_type]['revenue'] += campaign.revenue_generated or 0
            
            # 최고/최저 성과 캠페인
            best_performer = max(campaigns, key=lambda c: c.conversion_rate or 0)
            worst_performer = min(campaigns, key=lambda c: c.conversion_rate or 0)
            
            return {
                'summary': total_metrics,
                'by_type': performance_by_type,
                'best_performer': {
                    'id': best_performer.id,
                    'name': best_performer.name,
                    'conversion_rate': best_performer.conversion_rate,
                    'revenue': best_performer.revenue_generated
                },
                'worst_performer': {
                    'id': worst_performer.id,
                    'name': worst_performer.name,
                    'conversion_rate': worst_performer.conversion_rate,
                    'revenue': worst_performer.revenue_generated
                },
                'insights': self._generate_retargeting_insights(campaigns, performance_by_type)
            }
            
        except Exception as e:
            raise BusinessException(f"리타겟팅 성과 분석 실패: {str(e)}")
    
    async def _identify_cart_abandoners(self, hours_since: int, min_cart_value: float) -> List[Dict[str, Any]]:
        """장바구니 이탈 고객 식별"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_since)
        
        # 장바구니에 상품을 담았지만 구매하지 않은 고객
        cart_abandoners = self.db.query(
            CustomerBehavior.customer_id,
            func.max(CustomerBehavior.timestamp).label('last_cart_time'),
            func.sum(CustomerBehavior.product_price).label('cart_value')
        ).filter(
            CustomerBehavior.action_type == 'add_to_cart',
            CustomerBehavior.timestamp >= cutoff_time
        ).group_by(CustomerBehavior.customer_id).all()
        
        target_customers = []
        for customer_id, last_cart_time, cart_value in cart_abandoners:
            # 이후 구매 여부 확인
            purchase_after_cart = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.created_at > last_cart_time
            ).first()
            
            if not purchase_after_cart and (cart_value or 0) >= min_cart_value:
                # 장바구니 상품 정보 수집
                cart_items = self._get_customer_cart_items(customer_id, last_cart_time)
                
                target_customers.append({
                    'customer_id': customer_id,
                    'cart_abandonment_time': last_cart_time,
                    'cart_value': cart_value,
                    'cart_items': cart_items
                })
        
        return target_customers
    
    async def _identify_browse_abandoners(self, days_since: int, min_views: int) -> List[Dict[str, Any]]:
        """상품 조회 이탈 고객 식별"""
        cutoff_time = datetime.utcnow() - timedelta(days=days_since)
        
        # 상품을 여러 번 조회했지만 구매하지 않은 고객
        browse_data = self.db.query(
            CustomerBehavior.customer_id,
            CustomerBehavior.product_id,
            func.count(CustomerBehavior.id).label('view_count')
        ).filter(
            CustomerBehavior.action_type == 'view',
            CustomerBehavior.timestamp >= cutoff_time
        ).group_by(
            CustomerBehavior.customer_id,
            CustomerBehavior.product_id
        ).having(
            func.count(CustomerBehavior.id) >= min_views
        ).all()
        
        # 고객별로 그룹화
        customer_products = {}
        for customer_id, product_id, view_count in browse_data:
            if customer_id not in customer_products:
                customer_products[customer_id] = []
            customer_products[customer_id].append({
                'product_id': product_id,
                'view_count': view_count
            })
        
        target_customers = []
        for customer_id, products in customer_products.items():
            # 해당 상품들의 구매 여부 확인
            product_ids = [p['product_id'] for p in products]
            purchased = self.db.query(Order).filter(
                Order.customer_id == customer_id,
                Order.product_id.in_(product_ids),
                Order.created_at >= cutoff_time
            ).first()
            
            if not purchased:
                target_customers.append({
                    'customer_id': customer_id,
                    'viewed_products': products,
                    'total_views': sum(p['view_count'] for p in products)
                })
        
        return target_customers
    
    async def _identify_inactive_customers(self, days_inactive: int, 
                                         min_previous_orders: int) -> List[Dict[str, Any]]:
        """비활성 고객 식별"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
        
        # 과거에는 구매했지만 최근 구매가 없는 고객
        inactive_customers = self.db.query(
            Customer.id,
            Customer.name,
            Customer.email,
            Customer.last_purchase_date,
            Customer.total_orders,
            Customer.lifetime_value
        ).filter(
            Customer.total_orders >= min_previous_orders,
            Customer.last_purchase_date < cutoff_date,
            Customer.is_active == True
        ).all()
        
        target_customers = []
        for customer in inactive_customers:
            days_since_purchase = (datetime.utcnow() - customer.last_purchase_date).days
            
            target_customers.append({
                'customer_id': customer.id,
                'customer_name': customer.name,
                'customer_email': customer.email,
                'last_purchase_date': customer.last_purchase_date,
                'days_inactive': days_since_purchase,
                'total_orders': customer.total_orders,
                'lifetime_value': customer.lifetime_value
            })
        
        return target_customers
    
    async def _identify_recent_purchasers(self, days_since_purchase: int, 
                                        campaign_type: str) -> List[Dict[str, Any]]:
        """최근 구매 고객 식별"""
        start_date = datetime.utcnow() - timedelta(days=days_since_purchase + 7)
        end_date = datetime.utcnow() - timedelta(days=days_since_purchase)
        
        # 특정 기간에 구매한 고객
        recent_orders = self.db.query(
            Order.customer_id,
            Order.product_id,
            Order.created_at,
            Product.name.label('product_name'),
            Product.category
        ).join(Product).filter(
            Order.created_at.between(start_date, end_date),
            Order.status == 'completed'
        ).all()
        
        # 고객별로 그룹화
        customer_orders = {}
        for order in recent_orders:
            if order.customer_id not in customer_orders:
                customer_orders[order.customer_id] = []
            customer_orders[order.customer_id].append({
                'product_id': order.product_id,
                'product_name': order.product_name,
                'category': order.category,
                'purchase_date': order.created_at
            })
        
        target_customers = []
        for customer_id, orders in customer_orders.items():
            target_customers.append({
                'customer_id': customer_id,
                'purchased_products': orders,
                'campaign_type': campaign_type
            })
        
        return target_customers
    
    def _get_customer_cart_items(self, customer_id: int, since: datetime) -> List[Dict[str, Any]]:
        """고객의 장바구니 상품 조회"""
        cart_behaviors = self.db.query(
            CustomerBehavior.product_id,
            CustomerBehavior.product_price,
            func.max(CustomerBehavior.timestamp).label('added_time')
        ).filter(
            CustomerBehavior.customer_id == customer_id,
            CustomerBehavior.action_type == 'add_to_cart',
            CustomerBehavior.timestamp >= since
        ).group_by(
            CustomerBehavior.product_id,
            CustomerBehavior.product_price
        ).all()
        
        cart_items = []
        for product_id, price, added_time in cart_behaviors:
            # 상품 정보 조회
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if product:
                cart_items.append({
                    'product_id': product_id,
                    'product_name': product.name,
                    'price': price or product.price,
                    'image_url': product.image_url,
                    'added_time': added_time
                })
        
        return cart_items
    
    async def _generate_cart_recovery_template(self, settings: Dict[str, Any]) -> str:
        """장바구니 복구 이메일 템플릿 생성"""
        template = """
        <h2>안녕하세요 {{name}}님!</h2>
        
        <p>장바구니에 담아두신 상품들이 {{name}}님을 기다리고 있어요.</p>
        
        <h3>장바구니 상품:</h3>
        {{cart_items}}
        
        <p><strong>총 금액: {{cart_value}}원</strong></p>
        
        <p>지금 구매하시면 특별 할인 혜택을 받으실 수 있어요!</p>
        <p>할인 코드: <strong>{{discount_code}}</strong></p>
        
        <a href="{{checkout_url}}" style="background-color: #ff6b6b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            지금 구매하기
        </a>
        
        <p>이 할인 코드는 48시간 동안만 유효합니다.</p>
        """
        
        return template
    
    async def _generate_browse_recovery_template(self, settings: Dict[str, Any]) -> str:
        """상품 조회 복구 이메일 템플릿 생성"""
        template = """
        <h2>{{name}}님, 관심있게 보신 상품이 있으시네요!</h2>
        
        <p>최근에 둘러보신 상품들을 다시 확인해보세요.</p>
        
        <h3>최근 본 상품:</h3>
        {{viewed_products}}
        
        <h3>이런 상품도 추천드려요:</h3>
        {{recommendations}}
        
        <a href="{{shop_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            쇼핑 계속하기
        </a>
        """
        
        return template
    
    async def _generate_winback_template(self, settings: Dict[str, Any]) -> str:
        """고객 재활성화 이메일 템플릿 생성"""
        template = """
        <h2>{{name}}님, 오랜만이에요! 🎉</h2>
        
        <p>마지막 구매 이후 {{last_purchase_date}}일이 지났네요.</p>
        <p>{{name}}님을 위한 특별한 혜택을 준비했어요!</p>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3>🎁 컴백 특별 혜택</h3>
            <p>{{special_offer}}</p>
            <p>추가로 {{loyalty_points}} 포인트도 적립해드려요!</p>
        </div>
        
        <h3>{{name}}님을 위한 추천 상품:</h3>
        {{personalized_products}}
        
        <a href="{{shop_url}}" style="background-color: #007bff; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px;">
            지금 쇼핑하러 가기
        </a>
        """
        
        return template
    
    async def _generate_review_request_template(self, settings: Dict[str, Any]) -> str:
        """리뷰 요청 이메일 템플릿 생성"""
        template = """
        <h2>{{name}}님, 구매하신 상품은 어떠셨나요?</h2>
        
        <p>최근 구매하신 상품에 대한 {{name}}님의 소중한 의견을 들려주세요!</p>
        
        <h3>구매하신 상품:</h3>
        {{purchased_products}}
        
        <p>리뷰를 작성해주시면 다음 구매 시 사용할 수 있는 {{special_offer}} 쿠폰을 드려요!</p>
        
        <a href="{{review_url}}" style="background-color: #ffc107; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            리뷰 작성하기
        </a>
        """
        
        return template
    
    async def _generate_cross_sell_template(self, settings: Dict[str, Any]) -> str:
        """크로스셀 이메일 템플릿 생성"""
        template = """
        <h2>{{name}}님께 추천드리는 상품이에요!</h2>
        
        <p>최근 구매하신 상품과 잘 어울리는 제품들을 소개해드려요.</p>
        
        <h3>함께 구매하면 좋은 상품:</h3>
        {{recommendations}}
        
        <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p>💡 <strong>팁:</strong> 함께 구매 시 {{special_offer}}</p>
        </div>
        
        <a href="{{shop_url}}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            지금 보러가기
        </a>
        """
        
        return template
    
    async def _generate_repurchase_template(self, settings: Dict[str, Any]) -> str:
        """재구매 유도 이메일 템플릿 생성"""
        template = """
        <h2>{{name}}님, 재구매 시기가 되었어요!</h2>
        
        <p>이전에 구매하신 상품을 다시 구매할 시기가 되었습니다.</p>
        
        <h3>재구매 추천 상품:</h3>
        {{purchased_products}}
        
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p>🎯 지금 재구매하시면 {{special_offer}} 할인!</p>
        </div>
        
        <a href="{{reorder_url}}" style="background-color: #fd7e14; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            간편 재구매하기
        </a>
        """
        
        return template
    
    async def _create_personalized_cart_messages(self, campaign: MarketingCampaign, 
                                               target_customers: List[Dict[str, Any]]):
        """개인화된 장바구니 복구 메시지 생성"""
        for customer_data in target_customers:
            # 장바구니 상품 HTML 생성
            cart_items_html = self._generate_cart_items_html(customer_data['cart_items'])
            
            # 할인 코드 생성 (필요시)
            discount_code = f"CART{customer_data['customer_id']}{datetime.now().strftime('%m%d')}"
            
            # 개인화 데이터
            personalization_data = {
                'cart_items': cart_items_html,
                'cart_value': f"{customer_data['cart_value']:,.0f}",
                'discount_code': discount_code,
                'checkout_url': f"{settings.FRONTEND_URL}/checkout"
            }
            
            # 메시지 생성은 campaign_manager에서 처리
            pass
    
    async def _create_personalized_browse_messages(self, campaign: MarketingCampaign, 
                                                 target_customers: List[Dict[str, Any]]):
        """개인화된 상품 조회 복구 메시지 생성"""
        for customer_data in target_customers:
            # 상품 추천 생성
            recommendations = await self.personalization_engine.generate_product_recommendations(
                customer_data['customer_id'],
                recommendation_type='content_based',
                limit=3
            )
            
            # 개인화 데이터
            personalization_data = {
                'viewed_products': self._generate_viewed_products_html(customer_data['viewed_products']),
                'recommendations': self._generate_recommendations_html(recommendations),
                'shop_url': settings.FRONTEND_URL
            }
            
            # 메시지 생성은 campaign_manager에서 처리
            pass
    
    async def _create_personalized_winback_messages(self, campaign: MarketingCampaign, 
                                                  target_customers: List[Dict[str, Any]]):
        """개인화된 재활성화 메시지 생성"""
        for customer_data in target_customers:
            # 특별 오퍼 생성
            if customer_data['lifetime_value'] > 100000:
                special_offer = "30% 할인 쿠폰"
                loyalty_points = 5000
            elif customer_data['lifetime_value'] > 50000:
                special_offer = "20% 할인 쿠폰"
                loyalty_points = 3000
            else:
                special_offer = "15% 할인 쿠폰"
                loyalty_points = 1000
            
            # 개인화된 상품 추천
            recommendations = await self.personalization_engine.generate_product_recommendations(
                customer_data['customer_id'],
                recommendation_type='hybrid',
                limit=4
            )
            
            # 개인화 데이터
            personalization_data = {
                'last_purchase_date': customer_data['days_inactive'],
                'special_offer': special_offer,
                'loyalty_points': f"{loyalty_points:,}",
                'personalized_products': self._generate_recommendations_html(recommendations),
                'shop_url': settings.FRONTEND_URL
            }
            
            # 메시지 생성은 campaign_manager에서 처리
            pass
    
    async def _create_personalized_post_purchase_messages(self, campaign: MarketingCampaign, 
                                                        target_customers: List[Dict[str, Any]]):
        """개인화된 구매 후 메시지 생성"""
        for customer_data in target_customers:
            if customer_data['campaign_type'] == 'cross_sell':
                # 크로스셀 추천
                recommendations = await self.personalization_engine.generate_product_recommendations(
                    customer_data['customer_id'],
                    recommendation_type='collaborative',
                    limit=4
                )
                
                personalization_data = {
                    'recommendations': self._generate_recommendations_html(recommendations),
                    'special_offer': '번들 구매 시 10% 추가 할인',
                    'shop_url': settings.FRONTEND_URL
                }
            else:
                # 리뷰 요청 또는 재구매
                personalization_data = {
                    'purchased_products': self._generate_purchased_products_html(
                        customer_data['purchased_products']
                    ),
                    'special_offer': '500 포인트',
                    'review_url': f"{settings.FRONTEND_URL}/reviews",
                    'reorder_url': f"{settings.FRONTEND_URL}/reorder"
                }
            
            # 메시지 생성은 campaign_manager에서 처리
            pass
    
    def _generate_cart_items_html(self, cart_items: List[Dict[str, Any]]) -> str:
        """장바구니 상품 HTML 생성"""
        html = '<div style="margin: 20px 0;">'
        for item in cart_items:
            html += f"""
            <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; display: flex;">
                <img src="{item['image_url']}" style="width: 80px; height: 80px; margin-right: 15px;">
                <div>
                    <h4>{item['product_name']}</h4>
                    <p>가격: {item['price']:,}원</p>
                </div>
            </div>
            """
        html += '</div>'
        return html
    
    def _generate_viewed_products_html(self, viewed_products: List[Dict[str, Any]]) -> str:
        """조회한 상품 HTML 생성"""
        html = '<div style="display: flex; flex-wrap: wrap;">'
        for product_data in viewed_products[:4]:  # 최대 4개
            product = self.db.query(Product).filter(
                Product.id == product_data['product_id']
            ).first()
            
            if product:
                html += f"""
                <div style="width: 200px; margin: 10px; text-align: center;">
                    <img src="{product.image_url}" style="width: 100%; height: 200px; object-fit: cover;">
                    <h4>{product.name}</h4>
                    <p>{product.price:,}원</p>
                    <small>조회 {product_data['view_count']}회</small>
                </div>
                """
        html += '</div>'
        return html
    
    def _generate_recommendations_html(self, recommendations: List[Dict[str, Any]]) -> str:
        """추천 상품 HTML 생성"""
        html = '<div style="display: flex; flex-wrap: wrap;">'
        for rec in recommendations:
            html += f"""
            <div style="width: 200px; margin: 10px; text-align: center;">
                <img src="#" style="width: 100%; height: 200px; object-fit: cover;">
                <h4>{rec['product_name']}</h4>
                <p>{rec.get('price', 0):,}원</p>
                <small>{rec.get('reason', '')}</small>
            </div>
            """
        html += '</div>'
        return html
    
    def _generate_purchased_products_html(self, products: List[Dict[str, Any]]) -> str:
        """구매한 상품 HTML 생성"""
        html = '<div style="margin: 20px 0;">'
        for product in products:
            html += f"""
            <div style="border-bottom: 1px solid #eee; padding: 10px 0;">
                <h4>{product['product_name']}</h4>
                <p>구매일: {product['purchase_date'].strftime('%Y년 %m월 %d일')}</p>
            </div>
            """
        html += '</div>'
        return html
    
    def _identify_campaign_type(self, campaign: MarketingCampaign) -> str:
        """캠페인 유형 식별"""
        name_lower = campaign.name.lower()
        
        if '장바구니' in name_lower or 'cart' in name_lower:
            return 'cart_abandonment'
        elif '조회' in name_lower or 'browse' in name_lower:
            return 'browse_abandonment'
        elif '재활성' in name_lower or 'winback' in name_lower:
            return 'customer_winback'
        elif '구매' in name_lower or 'purchase' in name_lower:
            return 'post_purchase'
        else:
            return 'other'
    
    def _generate_retargeting_insights(self, campaigns: List[MarketingCampaign], 
                                     performance_by_type: Dict[str, Any]) -> List[str]:
        """리타겟팅 인사이트 생성"""
        insights = []
        
        # 가장 효과적인 캠페인 유형
        if performance_by_type:
            best_type = max(performance_by_type.items(), 
                          key=lambda x: x[1]['revenue'] / x[1]['sent'] if x[1]['sent'] > 0 else 0)
            insights.append(f"{best_type[0]} 캠페인이 가장 높은 ROI를 보이고 있습니다.")
        
        # 전환율 트렌드
        recent_campaigns = sorted(campaigns, key=lambda c: c.created_at)[-5:]
        if len(recent_campaigns) >= 3:
            recent_avg = sum(c.conversion_rate or 0 for c in recent_campaigns[-3:]) / 3
            older_avg = sum(c.conversion_rate or 0 for c in recent_campaigns[:2]) / 2
            
            if recent_avg > older_avg * 1.1:
                insights.append("최근 캠페인의 전환율이 개선되고 있습니다.")
            elif recent_avg < older_avg * 0.9:
                insights.append("최근 캠페인의 전환율이 하락하고 있습니다. 전략 재검토가 필요합니다.")
        
        # 시간대별 권장사항
        insights.append("장바구니 이탈 캠페인은 이탈 후 2-4시간 내에 발송할 때 가장 효과적입니다.")
        
        return insights