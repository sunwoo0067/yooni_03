"""Alert management and notification system"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
import structlog

from ..database.models import (
    Product, ProductPerformance, Alert,
    Review, MarketplaceProduct
)

logger = structlog.get_logger()


class AlertType(Enum):
    """Alert types"""
    SALES_DROP = "sales_drop"
    REVIEW_ALERT = "review_alert"
    INVENTORY_LOW = "inventory_low"
    RANKING_DROP = "ranking_drop"
    PRICE_ALERT = "price_alert"
    COMPETITOR_ALERT = "competitor_alert"
    PERFORMANCE_ANOMALY = "performance_anomaly"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertManager:
    """Manages system alerts and notifications"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.alert_config = config['monitoring']['alerts']
        self.notification_config = config['monitoring']['notification']
    
    async def check_all_alerts(self) -> List[Alert]:
        """Run all alert checks"""
        alerts = []
        
        # Sales drop alerts
        sales_alerts = await self.check_sales_drop_alerts()
        alerts.extend(sales_alerts)
        
        # Review score alerts
        review_alerts = await self.check_review_alerts()
        alerts.extend(review_alerts)
        
        # Inventory alerts
        inventory_alerts = await self.check_inventory_alerts()
        alerts.extend(inventory_alerts)
        
        # Ranking drop alerts
        ranking_alerts = await self.check_ranking_alerts()
        alerts.extend(ranking_alerts)
        
        # Performance anomaly alerts
        anomaly_alerts = await self.check_performance_anomalies()
        alerts.extend(anomaly_alerts)
        
        # Send notifications for new critical/high alerts
        await self.send_notifications(alerts)
        
        return alerts
    
    async def check_sales_drop_alerts(self) -> List[Alert]:
        """Check for significant sales drops"""
        alerts = []
        threshold = self.alert_config['sales_drop_threshold']
        
        # Compare last 7 days to previous 7 days
        current_end = datetime.utcnow().date()
        current_start = current_end - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=7)
        
        # Get products with sales data
        stmt = select(
            ProductPerformance.product_id,
            ProductPerformance.marketplace,
            func.sum(
                case(
                    (and_(
                        ProductPerformance.date >= current_start,
                        ProductPerformance.date <= current_end
                    ), ProductPerformance.sales_volume),
                    else_=0
                )
            ).label('current_sales'),
            func.sum(
                case(
                    (and_(
                        ProductPerformance.date >= previous_start,
                        ProductPerformance.date <= previous_end
                    ), ProductPerformance.sales_volume),
                    else_=0
                )
            ).label('previous_sales')
        ).group_by(
            ProductPerformance.product_id,
            ProductPerformance.marketplace
        ).having(
            func.sum(
                case(
                    (and_(
                        ProductPerformance.date >= previous_start,
                        ProductPerformance.date <= previous_end
                    ), ProductPerformance.sales_volume),
                    else_=0
                )
            ) > 0  # Only check products that had sales
        )
        
        result = await self.session.execute(stmt)
        
        for row in result:
            if row.previous_sales > 0:
                change_rate = (row.current_sales - row.previous_sales) / row.previous_sales
                
                if change_rate < threshold:
                    # Get product info
                    product = await self._get_product(row.product_id)
                    
                    severity = self._calculate_sales_drop_severity(change_rate)
                    
                    alert = await self.create_alert(
                        alert_type=AlertType.SALES_DROP,
                        severity=severity,
                        product_id=row.product_id,
                        marketplace=row.marketplace,
                        message=f"Sales dropped by {abs(change_rate)*100:.1f}% for {product.name}",
                        details={
                            'current_sales': row.current_sales,
                            'previous_sales': row.previous_sales,
                            'change_rate': change_rate
                        }
                    )
                    
                    alerts.append(alert)
        
        return alerts
    
    async def check_review_alerts(self) -> List[Alert]:
        """Check for review score drops or negative review patterns"""
        alerts = []
        threshold = self.alert_config['review_score_threshold']
        
        # Check recent reviews
        recent_date = datetime.utcnow() - timedelta(days=7)
        
        stmt = select(
            Review.product_id,
            Review.marketplace,
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('review_count'),
            func.sum(case((Review.rating <= 2, 1), else_=0)).label('negative_count')
        ).where(
            Review.created_at >= recent_date
        ).group_by(
            Review.product_id,
            Review.marketplace
        ).having(
            or_(
                func.avg(Review.rating) < threshold,
                func.sum(case((Review.rating <= 2, 1), else_=0)) >= 5  # 5+ negative reviews
            )
        )
        
        result = await self.session.execute(stmt)
        
        for row in result:
            product = await self._get_product(row.product_id)
            
            if row.avg_rating < threshold:
                severity = AlertSeverity.HIGH if row.avg_rating < 3.0 else AlertSeverity.MEDIUM
                
                alert = await self.create_alert(
                    alert_type=AlertType.REVIEW_ALERT,
                    severity=severity,
                    product_id=row.product_id,
                    marketplace=row.marketplace,
                    message=f"Low review score ({row.avg_rating:.1f}) for {product.name}",
                    details={
                        'average_rating': float(row.avg_rating),
                        'review_count': row.review_count,
                        'negative_count': row.negative_count
                    }
                )
                alerts.append(alert)
            
            elif row.negative_count >= 5:
                alert = await self.create_alert(
                    alert_type=AlertType.REVIEW_ALERT,
                    severity=AlertSeverity.MEDIUM,
                    product_id=row.product_id,
                    marketplace=row.marketplace,
                    message=f"Multiple negative reviews ({row.negative_count}) for {product.name}",
                    details={
                        'average_rating': float(row.avg_rating),
                        'review_count': row.review_count,
                        'negative_count': row.negative_count
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    async def check_inventory_alerts(self) -> List[Alert]:
        """Check for low inventory levels"""
        alerts = []
        threshold = self.alert_config['inventory_threshold']
        
        # This would integrate with actual inventory system
        # For now, simulate based on sales velocity
        
        stmt = select(
            ProductPerformance.product_id,
            ProductPerformance.marketplace,
            func.avg(ProductPerformance.sales_volume).label('avg_daily_sales')
        ).where(
            ProductPerformance.date >= datetime.utcnow().date() - timedelta(days=7)
        ).group_by(
            ProductPerformance.product_id,
            ProductPerformance.marketplace
        ).having(
            func.avg(ProductPerformance.sales_volume) > 0
        )
        
        result = await self.session.execute(stmt)
        
        for row in result:
            # Simulate inventory check
            estimated_inventory = 100  # Would come from inventory system
            days_of_stock = estimated_inventory / row.avg_daily_sales if row.avg_daily_sales > 0 else float('inf')
            
            if days_of_stock < threshold:
                product = await self._get_product(row.product_id)
                
                severity = AlertSeverity.CRITICAL if days_of_stock < 3 else AlertSeverity.HIGH
                
                alert = await self.create_alert(
                    alert_type=AlertType.INVENTORY_LOW,
                    severity=severity,
                    product_id=row.product_id,
                    marketplace=row.marketplace,
                    message=f"Low inventory for {product.name} - {days_of_stock:.1f} days remaining",
                    details={
                        'estimated_inventory': estimated_inventory,
                        'avg_daily_sales': float(row.avg_daily_sales),
                        'days_of_stock': days_of_stock
                    }
                )
                alerts.append(alert)
        
        return alerts
    
    async def check_ranking_alerts(self) -> List[Alert]:
        """Check for significant ranking drops"""
        alerts = []
        threshold = self.alert_config['ranking_drop_threshold']
        
        # Compare today's ranking with 7 days ago
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        
        stmt = select(
            ProductPerformance.product_id,
            ProductPerformance.marketplace,
            func.first_value(ProductPerformance.category_ranking).over(
                partition_by=[ProductPerformance.product_id, ProductPerformance.marketplace],
                order_by=ProductPerformance.date.desc()
            ).label('current_rank'),
            func.first_value(ProductPerformance.category_ranking).over(
                partition_by=[ProductPerformance.product_id, ProductPerformance.marketplace],
                order_by=ProductPerformance.date
            ).label('previous_rank')
        ).where(
            ProductPerformance.date.in_([today, week_ago])
        ).distinct()
        
        result = await self.session.execute(stmt)
        
        for row in result:
            if row.current_rank and row.previous_rank:
                rank_drop = row.current_rank - row.previous_rank
                
                if rank_drop >= threshold:
                    product = await self._get_product(row.product_id)
                    
                    severity = AlertSeverity.HIGH if rank_drop >= 50 else AlertSeverity.MEDIUM
                    
                    alert = await self.create_alert(
                        alert_type=AlertType.RANKING_DROP,
                        severity=severity,
                        product_id=row.product_id,
                        marketplace=row.marketplace,
                        message=f"Ranking dropped by {rank_drop} positions for {product.name}",
                        details={
                            'current_rank': row.current_rank,
                            'previous_rank': row.previous_rank,
                            'rank_change': rank_drop
                        }
                    )
                    alerts.append(alert)
        
        return alerts
    
    async def check_performance_anomalies(self) -> List[Alert]:
        """Check for unusual performance patterns"""
        alerts = []
        
        # Check for sudden spikes or drops in metrics
        today = datetime.utcnow().date()
        
        # Get average metrics for last 30 days
        stmt = select(
            ProductPerformance.product_id,
            ProductPerformance.marketplace,
            func.avg(ProductPerformance.views).label('avg_views'),
            func.stddev(ProductPerformance.views).label('stddev_views'),
            func.avg(ProductPerformance.conversions).label('avg_conversions'),
            func.stddev(ProductPerformance.conversions).label('stddev_conversions')
        ).where(
            and_(
                ProductPerformance.date >= today - timedelta(days=30),
                ProductPerformance.date < today
            )
        ).group_by(
            ProductPerformance.product_id,
            ProductPerformance.marketplace
        )
        
        result = await self.session.execute(stmt)
        baselines = {
            (row.product_id, row.marketplace): {
                'avg_views': row.avg_views or 0,
                'stddev_views': row.stddev_views or 1,
                'avg_conversions': row.avg_conversions or 0,
                'stddev_conversions': row.stddev_conversions or 1
            }
            for row in result
        }
        
        # Check today's performance against baselines
        stmt = select(ProductPerformance).where(
            ProductPerformance.date == today
        )
        
        result = await self.session.execute(stmt)
        
        for perf in result.scalars():
            key = (perf.product_id, perf.marketplace)
            if key in baselines:
                baseline = baselines[key]
                
                # Check for anomalies (3 standard deviations)
                views_zscore = abs((perf.views - baseline['avg_views']) / baseline['stddev_views']) if baseline['stddev_views'] > 0 else 0
                conv_zscore = abs((perf.conversions - baseline['avg_conversions']) / baseline['stddev_conversions']) if baseline['stddev_conversions'] > 0 else 0
                
                if views_zscore > 3 or conv_zscore > 3:
                    product = await self._get_product(perf.product_id)
                    
                    alert = await self.create_alert(
                        alert_type=AlertType.PERFORMANCE_ANOMALY,
                        severity=AlertSeverity.MEDIUM,
                        product_id=perf.product_id,
                        marketplace=perf.marketplace,
                        message=f"Unusual performance detected for {product.name}",
                        details={
                            'views': perf.views,
                            'avg_views': baseline['avg_views'],
                            'views_zscore': views_zscore,
                            'conversions': perf.conversions,
                            'avg_conversions': baseline['avg_conversions'],
                            'conversions_zscore': conv_zscore
                        }
                    )
                    alerts.append(alert)
        
        return alerts
    
    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        product_id: Optional[int] = None,
        marketplace: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert if it doesn't already exist"""
        
        # Check if similar alert already exists and is active
        stmt = select(Alert).where(
            and_(
                Alert.alert_type == alert_type.value,
                Alert.product_id == product_id,
                Alert.marketplace == marketplace,
                Alert.status == 'active',
                Alert.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
        )
        
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing alert
            existing.message = message
            existing.details = details
            await self.session.commit()
            return existing
        
        # Create new alert
        alert = Alert(
            alert_type=alert_type.value,
            severity=severity.value,
            product_id=product_id,
            marketplace=marketplace,
            message=message,
            details=details,
            status='active',
            created_at=datetime.utcnow()
        )
        
        self.session.add(alert)
        await self.session.commit()
        
        logger.info(
            "alert_created",
            alert_id=alert.id,
            type=alert_type.value,
            severity=severity.value,
            product_id=product_id
        )
        
        return alert
    
    async def send_notifications(self, alerts: List[Alert]):
        """Send notifications for critical/high alerts"""
        
        # Filter for new critical and high alerts
        critical_alerts = [
            a for a in alerts 
            if a.severity in ['critical', 'high'] and not a.notifications_sent
        ]
        
        if not critical_alerts:
            return
        
        # Send email notifications
        if self.notification_config['email']['enabled']:
            await self.send_email_notifications(critical_alerts)
        
        # Send Slack notifications
        if self.notification_config['slack']['enabled']:
            await self.send_slack_notifications(critical_alerts)
        
        # Mark alerts as notified
        for alert in critical_alerts:
            alert.notifications_sent = {
                'email': self.notification_config['email']['enabled'],
                'slack': self.notification_config['slack']['enabled']
            }
        
        await self.session.commit()
    
    async def send_email_notifications(self, alerts: List[Alert]):
        """Send email notifications"""
        try:
            smtp_config = self.notification_config['email']
            
            # Create email content
            subject = f"Dropship AI Alert: {len(alerts)} Critical Issues"
            
            html_content = "<h2>Dropship AI System Alerts</h2>"
            html_content += f"<p>{len(alerts)} critical alerts require your attention:</p>"
            html_content += "<ul>"
            
            for alert in alerts:
                product_name = "N/A"
                if alert.product_id:
                    product = await self._get_product(alert.product_id)
                    product_name = product.name if product else "Unknown"
                
                html_content += f"""
                <li>
                    <strong>[{alert.severity.upper()}] {alert.alert_type}</strong><br>
                    Product: {product_name}<br>
                    Marketplace: {alert.marketplace or 'All'}<br>
                    Message: {alert.message}<br>
                    Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
                </li>
                """
            
            html_content += "</ul>"
            
            # Send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_config['from_email']
            msg['To'] = ', '.join(smtp_config['to_emails'])
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port']) as server:
                server.starttls()
                # Note: In production, use proper authentication
                server.send_message(msg)
            
            logger.info(f"Email notifications sent for {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Failed to send email notifications: {str(e)}")
    
    async def send_slack_notifications(self, alerts: List[Alert]):
        """Send Slack notifications"""
        try:
            webhook_url = self.notification_config['slack']['webhook_url']
            
            # Create Slack message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Dropship AI: {len(alerts)} Critical Alerts"
                    }
                }
            ]
            
            for alert in alerts:
                severity_emoji = {
                    'critical': '🔴',
                    'high': '🟠',
                    'medium': '🟡',
                    'low': '🟢'
                }
                
                product_name = "N/A"
                if alert.product_id:
                    product = await self._get_product(alert.product_id)
                    product_name = product.name if product else "Unknown"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{severity_emoji.get(alert.severity, '⚪')} *{alert.alert_type}*\n"
                                f"Product: {product_name}\n"
                                f"Marketplace: {alert.marketplace or 'All'}\n"
                                f"_{alert.message}_"
                    }
                })
            
            # Send to Slack
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json={"blocks": blocks}
                )
                response.raise_for_status()
            
            logger.info(f"Slack notifications sent for {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notifications: {str(e)}")
    
    async def _get_product(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def _calculate_sales_drop_severity(self, change_rate: float) -> AlertSeverity:
        """Calculate severity based on sales drop percentage"""
        if change_rate <= -0.5:  # 50% or more drop
            return AlertSeverity.CRITICAL
        elif change_rate <= -0.3:  # 30% or more drop
            return AlertSeverity.HIGH
        elif change_rate <= -0.2:  # 20% or more drop
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW
    
    async def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert"""
        stmt = select(Alert).where(Alert.id == alert_id)
        result = await self.session.execute(stmt)
        alert = result.scalar_one_or_none()
        
        if alert:
            alert.status = 'acknowledged'
            alert.acknowledged_at = datetime.utcnow()
            await self.session.commit()
    
    async def resolve_alert(self, alert_id: int):
        """Resolve an alert"""
        stmt = select(Alert).where(Alert.id == alert_id)
        result = await self.session.execute(stmt)
        alert = result.scalar_one_or_none()
        
        if alert:
            alert.status = 'resolved'
            alert.resolved_at = datetime.utcnow()
            await self.session.commit()