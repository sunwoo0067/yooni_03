"""
리포트 생성 서비스
대시보드 데이터 기반 리포트 생성
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import asyncio

from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.inventory import Inventory
from app.models.platform import Platform
from app.services.dashboard.dashboard_service import DashboardService
from app.services.dashboard.analytics_service import AnalyticsService
from app.services.cache_service import CacheService
from app.core.logging import logger
from app.core.performance import redis_cache, memory_cache, optimize_memory_usage


class ReportService:
    """리포트 생성 서비스"""
    
    def __init__(self):
        self.dashboard_service = DashboardService()
        self.analytics_service = AnalyticsService()
        self.cache = CacheService()
        
        # 차트 스타일 설정
        plt.style.use('seaborn-v0_8-darkgrid')
        sns.set_palette("husl")
        
    @redis_cache(expiration=300)
    async def generate_daily_report(
        self,
        db: Session,
        user_id: int,
        date: Optional[datetime] = None,
        platform_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """일일 리포트 생성"""
        try:
            # 날짜 설정
            if not date:
                date = datetime.now().date()
            else:
                date = date.date()
                
            # 캐시 확인
            cache_key = f"report:daily:{user_id}:{date}:{platform_ids}"
            cached_report = await self.cache.get(cache_key)
            if cached_report:
                return cached_report
                
            # 날짜 범위 설정
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date, datetime.max.time())
            date_range = {"start": start_date, "end": end_date}
            
            # 병렬로 데이터 수집
            tasks = [
                self.dashboard_service.get_overview(db, user_id, platform_ids, date_range),
                self._get_hourly_sales(db, user_id, platform_ids, date_range),
                self._get_top_performing_products(db, user_id, platform_ids, date_range),
                self._get_platform_comparison(db, user_id, platform_ids, date_range),
                self._get_order_fulfillment_stats(db, user_id, platform_ids, date_range)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 차트 생성
            charts = await self._generate_daily_charts(results[1], results[3])
            
            report = {
                "report_type": "daily",
                "date": date.isoformat(),
                "overview": results[0],
                "hourly_sales": results[1],
                "top_products": results[2],
                "platform_comparison": results[3],
                "fulfillment_stats": results[4],
                "charts": charts,
                "generated_at": datetime.now().isoformat()
            }
            
            # 캐시 저장
            await self.cache.set(cache_key, report, ttl=3600)  # 1시간
            
            return report
            
        except Exception as e:
            logger.error(f"일일 리포트 생성 실패: {str(e)}")
            raise
            
    @redis_cache(expiration=600)
    async def generate_weekly_report(
        self,
        db: Session,
        user_id: int,
        week_start: Optional[datetime] = None,
        platform_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """주간 리포트 생성"""
        try:
            # 주 시작일 설정
            if not week_start:
                today = datetime.now().date()
                week_start = today - timedelta(days=today.weekday())
            else:
                week_start = week_start.date()
                
            week_end = week_start + timedelta(days=6)
            
            # 날짜 범위 설정
            start_date = datetime.combine(week_start, datetime.min.time())
            end_date = datetime.combine(week_end, datetime.max.time())
            date_range = {"start": start_date, "end": end_date}
            
            # 데이터 수집
            tasks = [
                self.dashboard_service.get_overview(db, user_id, platform_ids, date_range),
                self._get_daily_sales_trend(db, user_id, platform_ids, date_range),
                self._get_weekly_product_performance(db, user_id, platform_ids, date_range),
                self._get_inventory_movement(db, user_id, platform_ids, date_range),
                self.analytics_service.get_ai_insights(db, user_id, platform_ids)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 차트 생성
            charts = await self._generate_weekly_charts(results[1], results[2])
            
            # 주간 성과 요약
            performance_summary = self._calculate_weekly_performance(results[0], results[1])
            
            report = {
                "report_type": "weekly",
                "period": {
                    "start": week_start.isoformat(),
                    "end": week_end.isoformat()
                },
                "overview": results[0],
                "daily_trend": results[1],
                "product_performance": results[2],
                "inventory_movement": results[3],
                "ai_insights": results[4],
                "performance_summary": performance_summary,
                "charts": charts,
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"주간 리포트 생성 실패: {str(e)}")
            raise
            
    @memory_cache(max_size=50, expiration=1800)
    async def generate_monthly_report(
        self,
        db: Session,
        user_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
        platform_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """월간 리포트 생성"""
        try:
            # 년월 설정
            now = datetime.now()
            if not year:
                year = now.year
            if not month:
                month = now.month
                
            # 월 시작일과 종료일
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
                
            date_range = {"start": month_start, "end": month_end}
            
            # 데이터 수집
            tasks = [
                self.dashboard_service.get_overview(db, user_id, platform_ids, date_range),
                self._get_monthly_sales_analysis(db, user_id, platform_ids, date_range),
                self._get_monthly_product_analysis(db, user_id, platform_ids, date_range),
                self._get_monthly_customer_analysis(db, user_id, platform_ids, date_range),
                self._get_monthly_financial_summary(db, user_id, platform_ids, date_range),
                self.analytics_service.predict_sales(db, user_id, platform_ids, days_ahead=30)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # 차트 생성
            charts = await self._generate_monthly_charts(results[1], results[2], results[3])
            
            # 월간 성과 평가
            performance_evaluation = self._evaluate_monthly_performance(results)
            
            report = {
                "report_type": "monthly",
                "period": {
                    "year": year,
                    "month": month,
                    "start": month_start.isoformat(),
                    "end": month_end.isoformat()
                },
                "overview": results[0],
                "sales_analysis": results[1],
                "product_analysis": results[2],
                "customer_analysis": results[3],
                "financial_summary": results[4],
                "sales_forecast": results[5],
                "performance_evaluation": performance_evaluation,
                "charts": charts,
                "generated_at": datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"월간 리포트 생성 실패: {str(e)}")
            raise
            
    @optimize_memory_usage
    async def generate_pdf_report(
        self,
        report_data: Dict[str, Any],
        user_name: str
    ) -> bytes:
        """PDF 리포트 생성"""
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # 제목 스타일
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#2E86AB'),
                spaceAfter=30,
                alignment=1  # 중앙 정렬
            )
            
            # 리포트 타입에 따른 제목
            report_type = report_data.get("report_type", "daily")
            if report_type == "daily":
                title = f"일일 판매 리포트 - {report_data.get('date')}"
            elif report_type == "weekly":
                period = report_data.get("period", {})
                title = f"주간 판매 리포트 ({period.get('start')} ~ {period.get('end')})"
            else:  # monthly
                period = report_data.get("period", {})
                title = f"{period.get('year')}년 {period.get('month')}월 판매 리포트"
                
            # 제목 추가
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(f"판매자: {user_name}", styles['Normal']))
            story.append(Spacer(1, 0.5*inch))
            
            # 개요 섹션
            story.append(Paragraph("1. 판매 개요", styles['Heading2']))
            overview = report_data.get("overview", {})
            sales = overview.get("sales", {})
            
            overview_data = [
                ["항목", "값"],
                ["총 매출", f"{sales.get('total_sales', 0):,.0f}원"],
                ["주문 건수", f"{sales.get('order_count', 0)}건"],
                ["평균 주문 금액", f"{sales.get('avg_order_value', 0):,.0f}원"],
                ["전일 대비 성장률", f"{sales.get('growth_rate', 0):+.1f}%"]
            ]
            
            overview_table = Table(overview_data, colWidths=[3*inch, 3*inch])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(overview_table)
            story.append(Spacer(1, 0.3*inch))
            
            # 차트 추가
            if "charts" in report_data:
                story.append(Paragraph("2. 판매 추이", styles['Heading2']))
                for chart_name, chart_data in report_data["charts"].items():
                    if chart_data:
                        img = Image(BytesIO(base64.b64decode(chart_data)), width=5*inch, height=3*inch)
                        story.append(img)
                        story.append(Spacer(1, 0.2*inch))
                        
            # 상품 성과
            if "top_products" in report_data:
                story.append(PageBreak())
                story.append(Paragraph("3. 상품별 성과", styles['Heading2']))
                
                products = report_data["top_products"][:10]  # 상위 10개
                product_data = [["순위", "상품명", "판매량", "매출"]]
                
                for i, product in enumerate(products):
                    product_data.append([
                        str(i + 1),
                        product.get("name", ""),
                        f"{product.get('quantity_sold', 0)}개",
                        f"{product.get('revenue', 0):,.0f}원"
                    ])
                    
                product_table = Table(product_data, colWidths=[0.8*inch, 3*inch, 1.2*inch, 1.5*inch])
                product_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(product_table)
                
            # AI 인사이트 (주간/월간 리포트)
            if "ai_insights" in report_data:
                story.append(PageBreak())
                story.append(Paragraph("4. AI 분석 및 제안", styles['Heading2']))
                
                insights = report_data["ai_insights"]
                action_items = insights.get("action_items", [])
                
                for item in action_items[:5]:  # 상위 5개
                    story.append(Paragraph(f"• {item.get('title')}", styles['Heading3']))
                    story.append(Paragraph(item.get('description', ''), styles['Normal']))
                    story.append(Spacer(1, 0.1*inch))
                    
            # 생성 정보
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph(
                f"리포트 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles['Normal']
            ))
            
            # PDF 생성
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF 리포트 생성 실패: {str(e)}")
            raise
            
    async def _get_hourly_sales(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """시간대별 매출 데이터"""
        try:
            query = db.query(
                func.extract('hour', Order.created_at).label('hour'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue'),
                func.count(Order.id).label('order_count')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by('hour').order_by('hour').all()
            
            hourly_data = []
            for r in results:
                hourly_data.append({
                    "hour": int(r.hour),
                    "revenue": float(r.revenue or 0),
                    "order_count": r.order_count
                })
                
            return hourly_data
            
        except Exception as e:
            logger.error(f"시간대별 매출 조회 실패: {str(e)}")
            return []
            
    async def _get_top_performing_products(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """최고 성과 상품"""
        try:
            return await self.dashboard_service._get_top_products(
                db, user_id, platform_ids, date_range, limit=20
            )
        except Exception as e:
            logger.error(f"최고 성과 상품 조회 실패: {str(e)}")
            return []
            
    async def _get_platform_comparison(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """플랫폼별 비교 데이터"""
        try:
            return await self.dashboard_service._get_platform_performance(
                db, user_id, platform_ids, date_range
            )
        except Exception as e:
            logger.error(f"플랫폼 비교 조회 실패: {str(e)}")
            return []
            
    async def _get_order_fulfillment_stats(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """주문 처리 통계"""
        try:
            # 상태별 주문 수
            status_query = db.query(
                Order.status,
                func.count(Order.id).label('count'),
                func.avg(
                    func.extract('epoch', Order.updated_at - Order.created_at)
                ).label('avg_processing_time')
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"]
            )
            
            if platform_ids:
                status_query = status_query.filter(Order.platform_id.in_(platform_ids))
                
            status_results = status_query.group_by(Order.status).all()
            
            fulfillment_stats = {
                "by_status": {},
                "average_processing_hours": 0,
                "fulfillment_rate": 0
            }
            
            total_orders = 0
            fulfilled_orders = 0
            total_processing_time = 0
            processing_count = 0
            
            for status, count, avg_time in status_results:
                fulfillment_stats["by_status"][status] = count
                total_orders += count
                
                if status in ['shipped', 'delivered']:
                    fulfilled_orders += count
                    
                if avg_time and status != 'pending':
                    total_processing_time += avg_time * count
                    processing_count += count
                    
            if total_orders > 0:
                fulfillment_stats["fulfillment_rate"] = (fulfilled_orders / total_orders) * 100
                
            if processing_count > 0:
                avg_hours = (total_processing_time / processing_count) / 3600
                fulfillment_stats["average_processing_hours"] = round(avg_hours, 1)
                
            return fulfillment_stats
            
        except Exception as e:
            logger.error(f"주문 처리 통계 조회 실패: {str(e)}")
            return {}
            
    async def _get_daily_sales_trend(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> List[Dict[str, Any]]:
        """일별 매출 추이"""
        try:
            query = db.query(
                func.date(Order.created_at).label('date'),
                func.sum(OrderItem.price * OrderItem.quantity).label('revenue'),
                func.count(Order.id).label('order_count')
            ).join(
                OrderItem, Order.id == OrderItem.order_id
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= date_range["start"],
                Order.created_at <= date_range["end"],
                Order.status.in_(['pending', 'processing', 'shipped', 'delivered'])
            )
            
            if platform_ids:
                query = query.filter(Order.platform_id.in_(platform_ids))
                
            results = query.group_by('date').order_by('date').all()
            
            daily_trend = []
            for r in results:
                daily_trend.append({
                    "date": r.date.isoformat(),
                    "revenue": float(r.revenue or 0),
                    "order_count": r.order_count
                })
                
            return daily_trend
            
        except Exception as e:
            logger.error(f"일별 매출 추이 조회 실패: {str(e)}")
            return []
            
    async def _get_weekly_product_performance(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """주간 상품 성과"""
        try:
            # 상품별 주간 판매 데이터
            products = await self.dashboard_service.get_product_performance(
                db, user_id, platform_ids, date_range, limit=50
            )
            
            # 카테고리별 성과 추가
            category_performance = products.get("categories", [])
            
            return {
                "top_products": products.get("products", []),
                "category_performance": category_performance,
                "total_products_sold": len(products.get("products", []))
            }
            
        except Exception as e:
            logger.error(f"주간 상품 성과 조회 실패: {str(e)}")
            return {}
            
    async def _get_inventory_movement(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """재고 이동 현황"""
        try:
            # 재고 입출고 내역
            # 실제로는 재고 이력 테이블에서 조회
            return {
                "stock_in": 0,
                "stock_out": 0,
                "adjustments": 0,
                "ending_inventory_value": 0
            }
            
        except Exception as e:
            logger.error(f"재고 이동 현황 조회 실패: {str(e)}")
            return {}
            
    async def _get_monthly_sales_analysis(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """월간 매출 분석"""
        try:
            # 일별 매출 추이
            daily_sales = await self._get_daily_sales_trend(db, user_id, platform_ids, date_range)
            
            # 주별 집계
            weekly_sales = self._aggregate_to_weekly(daily_sales)
            
            # 전월 대비 비교
            prev_month_start = date_range["start"] - timedelta(days=30)
            prev_month_end = date_range["start"] - timedelta(seconds=1)
            prev_date_range = {"start": prev_month_start, "end": prev_month_end}
            
            prev_overview = await self.dashboard_service.get_overview(
                db, user_id, platform_ids, prev_date_range
            )
            
            current_total = sum(d["revenue"] for d in daily_sales)
            prev_total = prev_overview.get("sales", {}).get("total_sales", 0)
            
            growth_rate = 0
            if prev_total > 0:
                growth_rate = ((current_total - prev_total) / prev_total) * 100
                
            return {
                "daily_sales": daily_sales,
                "weekly_sales": weekly_sales,
                "total_revenue": current_total,
                "previous_month_revenue": prev_total,
                "growth_rate": growth_rate,
                "best_day": max(daily_sales, key=lambda x: x["revenue"]) if daily_sales else None,
                "worst_day": min(daily_sales, key=lambda x: x["revenue"]) if daily_sales else None
            }
            
        except Exception as e:
            logger.error(f"월간 매출 분석 실패: {str(e)}")
            return {}
            
    async def _get_monthly_product_analysis(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """월간 상품 분석"""
        try:
            # 상품 성과
            product_performance = await self.dashboard_service.get_product_performance(
                db, user_id, platform_ids, date_range, limit=100
            )
            
            products = product_performance.get("products", [])
            
            # 신상품 vs 기존상품 비교
            # ABC 분석 (매출 기준)
            total_revenue = sum(p["revenue"] for p in products)
            cumulative_revenue = 0
            
            a_products = []
            b_products = []
            c_products = []
            
            for product in products:
                cumulative_revenue += product["revenue"]
                percentage = (cumulative_revenue / total_revenue * 100) if total_revenue > 0 else 0
                
                if percentage <= 70:
                    a_products.append(product)
                elif percentage <= 90:
                    b_products.append(product)
                else:
                    c_products.append(product)
                    
            return {
                "total_products": len(products),
                "product_performance": products[:20],  # 상위 20개
                "category_performance": product_performance.get("categories", []),
                "abc_analysis": {
                    "a_products": {"count": len(a_products), "revenue_share": 70},
                    "b_products": {"count": len(b_products), "revenue_share": 20},
                    "c_products": {"count": len(c_products), "revenue_share": 10}
                }
            }
            
        except Exception as e:
            logger.error(f"월간 상품 분석 실패: {str(e)}")
            return {}
            
    async def _get_monthly_customer_analysis(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """월간 고객 분석"""
        try:
            # 고객 구매 패턴 분석
            # 실제로는 고객 테이블과 조인하여 분석
            
            # 신규 vs 재구매 고객
            # 구매 빈도 분석
            # 고객 가치 분석
            
            return {
                "total_customers": 0,
                "new_customers": 0,
                "returning_customers": 0,
                "average_order_value": 0,
                "customer_retention_rate": 0
            }
            
        except Exception as e:
            logger.error(f"월간 고객 분석 실패: {str(e)}")
            return {}
            
    async def _get_monthly_financial_summary(
        self,
        db: Session,
        user_id: int,
        platform_ids: Optional[List[int]],
        date_range: Dict[str, datetime]
    ) -> Dict[str, Any]:
        """월간 재무 요약"""
        try:
            # 매출, 비용, 이익 계산
            # 실제로는 비용 데이터도 필요
            
            overview = await self.dashboard_service.get_overview(
                db, user_id, platform_ids, date_range
            )
            
            sales = overview.get("sales", {})
            
            return {
                "gross_revenue": sales.get("total_sales", 0),
                "total_orders": sales.get("order_count", 0),
                "average_order_value": sales.get("avg_order_value", 0),
                "estimated_profit_margin": 30,  # 예시값
                "estimated_profit": sales.get("total_sales", 0) * 0.3
            }
            
        except Exception as e:
            logger.error(f"월간 재무 요약 실패: {str(e)}")
            return {}
            
    async def _generate_daily_charts(
        self,
        hourly_sales: List[Dict[str, Any]],
        platform_comparison: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """일일 차트 생성"""
        try:
            charts = {}
            
            # 시간대별 매출 차트
            if hourly_sales:
                plt.figure(figsize=(10, 6))
                hours = [d["hour"] for d in hourly_sales]
                revenues = [d["revenue"] for d in hourly_sales]
                
                plt.bar(hours, revenues, color='skyblue', edgecolor='navy')
                plt.xlabel('시간')
                plt.ylabel('매출 (원)')
                plt.title('시간대별 매출 현황')
                plt.xticks(range(24))
                plt.grid(axis='y', alpha=0.3)
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                charts["hourly_sales"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            # 플랫폼별 매출 파이 차트
            if platform_comparison:
                plt.figure(figsize=(8, 8))
                labels = [p["name"] for p in platform_comparison]
                sizes = [p["revenue"] for p in platform_comparison]
                
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                plt.title('플랫폼별 매출 비중')
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                charts["platform_pie"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            return charts
            
        except Exception as e:
            logger.error(f"일일 차트 생성 실패: {str(e)}")
            return {}
            
    async def _generate_weekly_charts(
        self,
        daily_trend: List[Dict[str, Any]],
        product_performance: Dict[str, Any]
    ) -> Dict[str, str]:
        """주간 차트 생성"""
        try:
            charts = {}
            
            # 일별 매출 추이 차트
            if daily_trend:
                plt.figure(figsize=(12, 6))
                dates = [d["date"] for d in daily_trend]
                revenues = [d["revenue"] for d in daily_trend]
                
                plt.plot(dates, revenues, marker='o', linewidth=2, markersize=8)
                plt.xlabel('날짜')
                plt.ylabel('매출 (원)')
                plt.title('일별 매출 추이')
                plt.xticks(rotation=45)
                plt.grid(True, alpha=0.3)
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                charts["daily_trend"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            # 카테고리별 성과 차트
            categories = product_performance.get("category_performance", [])
            if categories:
                plt.figure(figsize=(10, 6))
                cat_names = [c["category"] for c in categories[:5]]
                cat_revenues = [c["revenue"] for c in categories[:5]]
                
                plt.barh(cat_names, cat_revenues, color='lightgreen', edgecolor='darkgreen')
                plt.xlabel('매출 (원)')
                plt.title('카테고리별 매출 TOP 5')
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                charts["category_performance"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            return charts
            
        except Exception as e:
            logger.error(f"주간 차트 생성 실패: {str(e)}")
            return {}
            
    async def _generate_monthly_charts(
        self,
        sales_analysis: Dict[str, Any],
        product_analysis: Dict[str, Any],
        customer_analysis: Dict[str, Any]
    ) -> Dict[str, str]:
        """월간 차트 생성"""
        try:
            charts = {}
            
            # 월간 매출 추이
            daily_sales = sales_analysis.get("daily_sales", [])
            if daily_sales:
                plt.figure(figsize=(14, 6))
                dates = [d["date"] for d in daily_sales]
                revenues = [d["revenue"] for d in daily_sales]
                
                plt.plot(dates, revenues, linewidth=2)
                plt.fill_between(range(len(dates)), revenues, alpha=0.3)
                plt.xlabel('날짜')
                plt.ylabel('매출 (원)')
                plt.title('월간 일별 매출 추이')
                plt.xticks(range(0, len(dates), 5), [dates[i] for i in range(0, len(dates), 5)], rotation=45)
                plt.grid(True, alpha=0.3)
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                charts["monthly_trend"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            # ABC 분석 차트
            abc = product_analysis.get("abc_analysis", {})
            if abc:
                plt.figure(figsize=(8, 8))
                labels = ['A그룹', 'B그룹', 'C그룹']
                sizes = [
                    abc.get("a_products", {}).get("count", 0),
                    abc.get("b_products", {}).get("count", 0),
                    abc.get("c_products", {}).get("count", 0)
                ]
                
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
                       colors=['gold', 'lightcoral', 'lightskyblue'])
                plt.title('상품 ABC 분석')
                
                buffer = BytesIO()
                plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
                buffer.seek(0)
                charts["abc_analysis"] = base64.b64encode(buffer.getvalue()).decode()
                plt.close()
                
            return charts
            
        except Exception as e:
            logger.error(f"월간 차트 생성 실패: {str(e)}")
            return {}
            
    def _calculate_weekly_performance(
        self,
        overview: Dict[str, Any],
        daily_trend: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """주간 성과 계산"""
        try:
            sales = overview.get("sales", {})
            
            # 일평균 계산
            total_days = len(daily_trend)
            if total_days > 0:
                avg_daily_revenue = sales.get("total_sales", 0) / total_days
                avg_daily_orders = sales.get("order_count", 0) / total_days
            else:
                avg_daily_revenue = 0
                avg_daily_orders = 0
                
            # 최고/최저 실적일
            if daily_trend:
                best_day = max(daily_trend, key=lambda x: x["revenue"])
                worst_day = min(daily_trend, key=lambda x: x["revenue"])
            else:
                best_day = None
                worst_day = None
                
            return {
                "total_revenue": sales.get("total_sales", 0),
                "total_orders": sales.get("order_count", 0),
                "average_daily_revenue": avg_daily_revenue,
                "average_daily_orders": avg_daily_orders,
                "best_performance_day": best_day,
                "worst_performance_day": worst_day,
                "growth_rate": sales.get("growth_rate", 0)
            }
            
        except Exception as e:
            logger.error(f"주간 성과 계산 실패: {str(e)}")
            return {}
            
    def _evaluate_monthly_performance(
        self,
        results: List[Any]
    ) -> Dict[str, Any]:
        """월간 성과 평가"""
        try:
            overview = results[0]
            sales_analysis = results[1]
            forecast = results[5]
            
            # 성과 점수 계산 (100점 만점)
            score = 0
            evaluation = {
                "score": 0,
                "grade": "C",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
            
            # 매출 성장률 평가 (30점)
            growth_rate = sales_analysis.get("growth_rate", 0)
            if growth_rate > 20:
                score += 30
                evaluation["strengths"].append("우수한 매출 성장률")
            elif growth_rate > 10:
                score += 20
            elif growth_rate > 0:
                score += 10
            else:
                evaluation["weaknesses"].append("매출 성장 정체")
                
            # 주문 처리율 평가 (20점)
            orders = overview.get("orders", {})
            processing_rate = orders.get("processing_rate", 0)
            if processing_rate > 95:
                score += 20
                evaluation["strengths"].append("높은 주문 처리율")
            elif processing_rate > 90:
                score += 15
            elif processing_rate > 80:
                score += 10
            else:
                evaluation["weaknesses"].append("주문 처리 개선 필요")
                
            # 재고 건전성 평가 (20점)
            inventory = overview.get("inventory", {})
            stock_health = inventory.get("stock_health_score", 0)
            if stock_health > 80:
                score += 20
            elif stock_health > 60:
                score += 15
            elif stock_health > 40:
                score += 10
            else:
                evaluation["weaknesses"].append("재고 관리 개선 필요")
                
            # 예측 정확도 평가 (30점)
            if forecast and "summary" in forecast:
                accuracy = forecast["summary"].get("model_accuracy", 0) * 100
                if accuracy > 80:
                    score += 30
                elif accuracy > 70:
                    score += 20
                elif accuracy > 60:
                    score += 10
                    
            # 등급 부여
            if score >= 90:
                evaluation["grade"] = "A"
            elif score >= 80:
                evaluation["grade"] = "B"
            elif score >= 70:
                evaluation["grade"] = "C"
            elif score >= 60:
                evaluation["grade"] = "D"
            else:
                evaluation["grade"] = "F"
                
            evaluation["score"] = score
            
            # 개선 제안
            if growth_rate < 10:
                evaluation["recommendations"].append("마케팅 강화 및 프로모션 전략 수립")
            if processing_rate < 90:
                evaluation["recommendations"].append("주문 처리 프로세스 개선")
            if stock_health < 60:
                evaluation["recommendations"].append("재고 관리 시스템 점검")
                
            return evaluation
            
        except Exception as e:
            logger.error(f"월간 성과 평가 실패: {str(e)}")
            return {
                "score": 0,
                "grade": "N/A",
                "strengths": [],
                "weaknesses": [],
                "recommendations": []
            }
            
    def _aggregate_to_weekly(
        self,
        daily_sales: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """일별 데이터를 주별로 집계"""
        try:
            if not daily_sales:
                return []
                
            # pandas 사용하여 주별 집계
            df = pd.DataFrame(daily_sales)
            df['date'] = pd.to_datetime(df['date'])
            df['week'] = df['date'].dt.isocalendar().week
            
            weekly = df.groupby('week').agg({
                'revenue': 'sum',
                'order_count': 'sum'
            }).reset_index()
            
            return weekly.to_dict('records')
            
        except Exception as e:
            logger.error(f"주별 집계 실패: {str(e)}")
            return []