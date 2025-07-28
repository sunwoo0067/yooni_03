"""
Automatic settlement service
자동 정산 시스템
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
import pandas as pd
from io import BytesIO

from app.models.order_core import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.order_automation import (
    WholesaleOrder, Settlement, SettlementStatus,
    OrderProcessingLog
)
from app.models.platform_account import PlatformAccount
from app.services.realtime.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class AutoSettlement:
    """자동 정산 시스템"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.websocket_manager = WebSocketManager()
        self.settlement_active = False
        self.settlement_tasks = {}
        
        # 정산 설정
        self.config = {
            'vat_rate': Decimal('0.10'),  # 부가세율 10%
            'income_tax_rate': Decimal('0.033'),  # 소득세율 3.3%
            'platform_fees': {
                'coupang': Decimal('0.09'),  # 쿠팡 수수료 9%
                'naver': Decimal('0.08'),    # 네이버 수수료 8%
                '11st': Decimal('0.07')      # 11번가 수수료 7%
            },
            'payment_gateway_fees': {
                'card': Decimal('0.025'),    # 카드 결제 수수료 2.5%
                'bank_transfer': Decimal('0.005'),  # 계좌이체 수수료 0.5%
                'mobile': Decimal('0.03')    # 모바일 결제 수수료 3%
            }
        }
    
    async def start_auto_settlement(self):
        """자동 정산 시작"""
        try:
            logger.info("자동 정산 시스템 시작")
            self.settlement_active = True
            
            # 정산 처리 태스크들 시작
            self.settlement_tasks["calculate_profit_margins"] = asyncio.create_task(
                self._calculate_profit_margins_continuously()
            )
            
            self.settlement_tasks["track_expenses"] = asyncio.create_task(
                self._track_expenses_continuously()
            )
            
            self.settlement_tasks["generate_settlements"] = asyncio.create_task(
                self._generate_settlements_continuously()
            )
            
            self.settlement_tasks["calculate_taxes"] = asyncio.create_task(
                self._calculate_taxes_continuously()
            )
            
            self.settlement_tasks["generate_reports"] = asyncio.create_task(
                self._generate_reports_continuously()
            )
            
            logger.info(f"자동 정산 시스템 {len(self.settlement_tasks)}개 태스크 시작됨")
            
        except Exception as e:
            logger.error(f"자동 정산 시스템 시작 실패: {e}")
            raise
    
    async def stop_auto_settlement(self):
        """자동 정산 중지"""
        try:
            logger.info("자동 정산 시스템 중지 시작")
            self.settlement_active = False
            
            # 모든 태스크 취소
            for task_name, task in self.settlement_tasks.items():
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.info(f"정산 태스크 {task_name} 취소됨")
            
            self.settlement_tasks.clear()
            logger.info("자동 정산 시스템 중지 완료")
            
        except Exception as e:
            logger.error(f"자동 정산 시스템 중지 실패: {e}")
    
    async def calculate_profit_margin(self, order_id: str) -> Dict[str, Any]:
        """마진 계산"""
        try:
            start_time = datetime.utcnow()
            
            # 주문 정보 조회
            order = await self._get_order_with_details(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 도매 주문 정보 조회
            wholesale_orders = await self._get_wholesale_orders_by_order_id(order_id)
            
            # 수익 계산
            revenue_calculation = await self._calculate_revenue(order)
            cost_calculation = await self._calculate_costs(order, wholesale_orders)
            
            # 마진 계산
            gross_revenue = revenue_calculation['gross_revenue']
            total_costs = cost_calculation['total_costs']
            net_profit = gross_revenue - total_costs
            
            profit_margin = Decimal('0')
            if gross_revenue > 0:
                profit_margin = (net_profit / gross_revenue * Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            
            # ROI 계산
            roi = Decimal('0')
            if total_costs > 0:
                roi = (net_profit / total_costs * Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            
            # 처리 시간 계산
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # 로그 기록
            await self._log_settlement_processing(
                order_id=order_id,
                step='profit_calculation',
                action='calculate_profit_margin',
                success=True,
                processing_time_ms=int(processing_time),
                output_data={
                    'gross_revenue': float(gross_revenue),
                    'total_costs': float(total_costs),
                    'net_profit': float(net_profit),
                    'profit_margin': float(profit_margin),
                    'roi': float(roi)
                }
            )
            
            return {
                'success': True,
                'order_id': order_id,
                'revenue': {
                    'gross_revenue': float(gross_revenue),
                    'customer_payment': float(revenue_calculation['customer_payment']),
                    'marketplace_fee': float(revenue_calculation['marketplace_fee']),
                    'payment_gateway_fee': float(revenue_calculation['payment_gateway_fee'])
                },
                'costs': {
                    'total_costs': float(total_costs),
                    'wholesale_cost': float(cost_calculation['wholesale_cost']),
                    'shipping_cost': float(cost_calculation['shipping_cost']),
                    'packaging_cost': float(cost_calculation['packaging_cost']),
                    'other_costs': float(cost_calculation['other_costs'])
                },
                'profit': {
                    'net_profit': float(net_profit),
                    'profit_margin': float(profit_margin),
                    'roi': float(roi)
                }
            }
            
        except Exception as e:
            logger.error(f"마진 계산 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def track_expenses(self, order_id: str) -> Dict[str, Any]:
        """비용 추적"""
        try:
            order = await self._get_order_with_details(order_id)
            if not order:
                return {
                    'success': False,
                    'error': '주문을 찾을 수 없습니다'
                }
            
            # 비용 항목별 추적
            expense_tracking = {
                'wholesale_costs': await self._track_wholesale_costs(order),
                'shipping_costs': await self._track_shipping_costs(order),
                'platform_fees': await self._track_platform_fees(order),
                'payment_fees': await self._track_payment_fees(order),
                'packaging_costs': await self._track_packaging_costs(order),
                'operational_costs': await self._track_operational_costs(order)
            }
            
            # 총 비용 계산
            total_expenses = sum(
                expense['amount'] for expense in expense_tracking.values()
            )
            
            # 비용 구조 분석
            cost_breakdown = await self._analyze_cost_structure(expense_tracking, total_expenses)
            
            return {
                'success': True,
                'order_id': order_id,
                'total_expenses': float(total_expenses),
                'expense_breakdown': {
                    key: {
                        'amount': float(value['amount']),
                        'percentage': float(value['percentage']),
                        'details': value['details']
                    }
                    for key, value in expense_tracking.items()
                },
                'cost_analysis': cost_breakdown
            }
            
        except Exception as e:
            logger.error(f"비용 추적 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_profit_report(self, start_date: datetime, end_date: datetime, 
                                   filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """수익 보고서 생성"""
        try:
            # 기간 내 주문 조회
            orders = await self._get_orders_in_period(start_date, end_date, filters)
            
            if not orders:
                return {
                    'success': True,
                    'message': '해당 기간에 주문이 없습니다',
                    'data': self._get_empty_report_structure()
                }
            
            # 정산 데이터 계산
            report_data = await self._calculate_period_profits(orders, start_date, end_date)
            
            # 추세 분석
            trend_analysis = await self._analyze_profit_trends(orders, start_date, end_date)
            
            # 상품별 수익성 분석
            product_profitability = await self._analyze_product_profitability(orders)
            
            # 플랫폼별 수익성 분석
            platform_profitability = await self._analyze_platform_profitability(orders)
            
            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': report_data['summary'],
                'detailed_metrics': report_data['detailed_metrics'],
                'trend_analysis': trend_analysis,
                'product_profitability': product_profitability,
                'platform_profitability': platform_profitability,
                'recommendations': await self._generate_profit_recommendations(report_data)
            }
            
        except Exception as e:
            logger.error(f"수익 보고서 생성 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def calculate_taxes(self, order_id: str) -> Dict[str, Any]:
        """세금 계산"""
        try:
            # 정산 데이터 조회
            settlement = await self._get_settlement_by_order_id(order_id)
            if not settlement:
                return {
                    'success': False,
                    'error': '정산 데이터를 찾을 수 없습니다'
                }
            
            # 부가세 계산
            vat_calculation = await self._calculate_vat(settlement)
            
            # 소득세 계산
            income_tax_calculation = await self._calculate_income_tax(settlement)
            
            # 지방소득세 계산
            local_tax_calculation = await self._calculate_local_tax(income_tax_calculation['amount'])
            
            # 총 세금 합계
            total_tax = (
                vat_calculation['amount'] +
                income_tax_calculation['amount'] +
                local_tax_calculation['amount']
            )
            
            # 세후 순이익 계산
            net_profit_after_tax = settlement.net_profit - total_tax
            
            # 세금 정보 업데이트
            settlement.vat_amount = vat_calculation['amount']
            settlement.income_tax = (
                income_tax_calculation['amount'] + local_tax_calculation['amount']
            )
            
            await self.db.commit()
            
            return {
                'success': True,
                'order_id': order_id,
                'tax_breakdown': {
                    'vat': {
                        'amount': float(vat_calculation['amount']),
                        'rate': float(vat_calculation['rate']),
                        'taxable_amount': float(vat_calculation['taxable_amount'])
                    },
                    'income_tax': {
                        'amount': float(income_tax_calculation['amount']),
                        'rate': float(income_tax_calculation['rate']),
                        'taxable_income': float(income_tax_calculation['taxable_income'])
                    },
                    'local_tax': {
                        'amount': float(local_tax_calculation['amount']),
                        'rate': float(local_tax_calculation['rate'])
                    }
                },
                'total_tax': float(total_tax),
                'net_profit_before_tax': float(settlement.net_profit),
                'net_profit_after_tax': float(net_profit_after_tax)
            }
            
        except Exception as e:
            logger.error(f"세금 계산 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_settlement(self, order_id: str) -> Dict[str, Any]:
        """정산 데이터 생성"""
        try:
            # 기존 정산 데이터 확인
            existing_settlement = await self._get_settlement_by_order_id(order_id)
            if existing_settlement and existing_settlement.status == SettlementStatus.COMPLETED:
                return {
                    'success': False,
                    'error': '이미 완료된 정산입니다'
                }
            
            # 마진 계산 실행
            profit_result = await self.calculate_profit_margin(order_id)
            if not profit_result['success']:
                return {
                    'success': False,
                    'error': f"마진 계산 실패: {profit_result['error']}"
                }
            
            # 정산 데이터 생성 또는 업데이트
            if existing_settlement:
                settlement = await self._update_settlement_data(existing_settlement, profit_result)
            else:
                settlement = await self._create_settlement_data(order_id, profit_result)
            
            # 세금 계산
            tax_result = await self.calculate_taxes(order_id)
            if not tax_result['success']:
                logger.warning(f"세금 계산 실패: {tax_result['error']}")
            
            # 정산 상태 업데이트
            settlement.status = SettlementStatus.CALCULATED
            settlement.calculation_date = datetime.utcnow()
            
            await self.db.commit()
            
            # 정산 완료 알림
            await self._send_settlement_notification(settlement)
            
            return {
                'success': True,
                'settlement_id': str(settlement.id),
                'order_id': order_id,
                'gross_revenue': float(settlement.gross_revenue),
                'total_costs': float(settlement.total_costs),
                'net_profit': float(settlement.net_profit),
                'profit_margin': float(settlement.profit_margin),
                'status': settlement.status.value
            }
            
        except Exception as e:
            logger.error(f"정산 데이터 생성 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def export_accounting_data(self, start_date: datetime, end_date: datetime,
                                   format_type: str = 'excel') -> Dict[str, Any]:
        """회계 데이터 내보내기"""
        try:
            # 정산 데이터 조회
            settlements = await self._get_settlements_in_period(start_date, end_date)
            
            if not settlements:
                return {
                    'success': False,
                    'error': '해당 기간에 정산 데이터가 없습니다'
                }
            
            # 회계 데이터 변환
            accounting_data = await self._convert_to_accounting_format(settlements)
            
            if format_type.lower() == 'excel':
                # Excel 파일 생성
                file_data = await self._create_excel_report(accounting_data, start_date, end_date)
                file_extension = 'xlsx'
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif format_type.lower() == 'csv':
                # CSV 파일 생성
                file_data = await self._create_csv_report(accounting_data)
                file_extension = 'csv'
                content_type = 'text/csv'
            else:
                return {
                    'success': False,
                    'error': f'지원하지 않는 파일 형식: {format_type}'
                }
            
            # 파일명 생성
            filename = f"accounting_data_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{file_extension}"
            
            return {
                'success': True,
                'filename': filename,
                'file_data': file_data,
                'content_type': content_type,
                'records_count': len(settlements),
                'total_revenue': float(sum(s.gross_revenue for s in settlements)),
                'total_profit': float(sum(s.net_profit for s in settlements))
            }
            
        except Exception as e:
            logger.error(f"회계 데이터 내보내기 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 백그라운드 태스크들
    async def _calculate_profit_margins_continuously(self):
        """지속적인 마진 계산"""
        while self.settlement_active:
            try:
                # 마진 계산이 필요한 주문들 조회
                orders = await self._get_orders_needing_profit_calculation()
                
                for order in orders:
                    try:
                        await self.calculate_profit_margin(str(order.id))
                    except Exception as e:
                        logger.error(f"주문 {order.id} 마진 계산 실패: {e}")
                        continue
                
                # 30분마다 실행
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"마진 계산 태스크 오류: {e}")
                await asyncio.sleep(300)
    
    async def _track_expenses_continuously(self):
        """지속적인 비용 추적"""
        while self.settlement_active:
            try:
                # 비용 추적이 필요한 주문들 조회
                orders = await self._get_orders_needing_expense_tracking()
                
                for order in orders:
                    try:
                        await self.track_expenses(str(order.id))
                    except Exception as e:
                        logger.error(f"주문 {order.id} 비용 추적 실패: {e}")
                        continue
                
                # 1시간마다 실행
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"비용 추적 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _generate_settlements_continuously(self):
        """지속적인 정산 생성"""
        while self.settlement_active:
            try:
                # 정산 생성이 필요한 주문들 조회
                orders = await self._get_orders_needing_settlement()
                
                for order in orders:
                    try:
                        await self.generate_settlement(str(order.id))
                    except Exception as e:
                        logger.error(f"주문 {order.id} 정산 생성 실패: {e}")
                        continue
                
                # 2시간마다 실행
                await asyncio.sleep(7200)
                
            except Exception as e:
                logger.error(f"정산 생성 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _calculate_taxes_continuously(self):
        """지속적인 세금 계산"""
        while self.settlement_active:
            try:
                # 세금 계산이 필요한 정산들 조회
                settlements = await self._get_settlements_needing_tax_calculation()
                
                for settlement in settlements:
                    try:
                        await self.calculate_taxes(str(settlement.order_id))
                    except Exception as e:
                        logger.error(f"정산 {settlement.id} 세금 계산 실패: {e}")
                        continue
                
                # 4시간마다 실행
                await asyncio.sleep(14400)
                
            except Exception as e:
                logger.error(f"세금 계산 태스크 오류: {e}")
                await asyncio.sleep(600)
    
    async def _generate_reports_continuously(self):
        """지속적인 보고서 생성"""
        while self.settlement_active:
            try:
                # 일일 보고서 생성
                yesterday = datetime.utcnow().date() - timedelta(days=1)
                start_date = datetime.combine(yesterday, datetime.min.time())
                end_date = datetime.combine(yesterday, datetime.max.time())
                
                await self.generate_profit_report(start_date, end_date)
                
                # 하루에 한 번 실행 (새벽 2시)
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"보고서 생성 태스크 오류: {e}")
                await asyncio.sleep(3600)
    
    # 헬퍼 메서드들
    async def _calculate_revenue(self, order: Order) -> Dict[str, Decimal]:
        """수익 계산"""
        customer_payment = order.total_amount
        
        # 마켓플레이스 수수료 계산
        platform = order.platform_account.platform
        marketplace_fee_rate = self.config['platform_fees'].get(platform, Decimal('0.08'))
        marketplace_fee = customer_payment * marketplace_fee_rate
        
        # 결제 수수료 계산
        payment_method = 'card'  # 실제로는 주문의 결제 방법에서 가져와야 함
        payment_fee_rate = self.config['payment_gateway_fees'].get(payment_method, Decimal('0.025'))
        payment_gateway_fee = customer_payment * payment_fee_rate
        
        gross_revenue = customer_payment - marketplace_fee - payment_gateway_fee
        
        return {
            'customer_payment': customer_payment,
            'marketplace_fee': marketplace_fee,
            'payment_gateway_fee': payment_gateway_fee,
            'gross_revenue': gross_revenue
        }
    
    async def _calculate_costs(self, order: Order, wholesale_orders: List[WholesaleOrder]) -> Dict[str, Decimal]:
        """비용 계산"""
        wholesale_cost = sum(wo.total_amount for wo in wholesale_orders)
        
        # 기본 배송비 (실제로는 더 정교한 계산 필요)
        shipping_cost = Decimal('3000')  # 기본 배송비 3,000원
        
        # 포장비 (실제로는 상품별로 다를 수 있음)
        packaging_cost = Decimal('500') * len(order.order_items)
        
        # 기타 비용
        other_costs = Decimal('0')
        
        total_costs = wholesale_cost + shipping_cost + packaging_cost + other_costs
        
        return {
            'wholesale_cost': wholesale_cost,
            'shipping_cost': shipping_cost,
            'packaging_cost': packaging_cost,
            'other_costs': other_costs,
            'total_costs': total_costs
        }
    
    async def _calculate_vat(self, settlement: Settlement) -> Dict[str, Decimal]:
        """부가세 계산"""
        # 부가세 대상 금액 (매출액)
        taxable_amount = settlement.gross_revenue
        vat_amount = taxable_amount * self.config['vat_rate']
        
        return {
            'amount': vat_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
            'rate': self.config['vat_rate'],
            'taxable_amount': taxable_amount
        }
    
    async def _calculate_income_tax(self, settlement: Settlement) -> Dict[str, Decimal]:
        """소득세 계산"""
        # 소득세 대상 소득 (순이익)
        taxable_income = settlement.net_profit
        if taxable_income <= 0:
            return {
                'amount': Decimal('0'),
                'rate': Decimal('0'),
                'taxable_income': taxable_income
            }
        
        income_tax_amount = taxable_income * self.config['income_tax_rate']
        
        return {
            'amount': income_tax_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
            'rate': self.config['income_tax_rate'],
            'taxable_income': taxable_income
        }
    
    async def _calculate_local_tax(self, income_tax_amount: Decimal) -> Dict[str, Decimal]:
        """지방소득세 계산 (소득세의 10%)"""
        local_tax_rate = Decimal('0.10')
        local_tax_amount = income_tax_amount * local_tax_rate
        
        return {
            'amount': local_tax_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
            'rate': local_tax_rate
        }
    
    async def _create_excel_report(self, accounting_data: List[Dict], start_date: datetime, end_date: datetime) -> bytes:
        """Excel 보고서 생성"""
        # pandas DataFrame 생성
        df = pd.DataFrame(accounting_data)
        
        # Excel 파일 생성
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='정산데이터', index=False)
            
            # 요약 시트 추가
            summary_data = {
                '항목': ['총 주문 수', '총 매출', '총 비용', '총 순이익', '평균 마진율'],
                '값': [
                    len(df),
                    df['총매출'].sum(),
                    df['총비용'].sum(), 
                    df['순이익'].sum(),
                    df['마진율'].mean()
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='요약', index=False)
        
        output.seek(0)
        return output.getvalue()
    
    # 추가 헬퍼 메서드들 (실제 구현에서 완성 필요)
    async def _get_order_with_details(self, order_id: str) -> Optional[Order]:
        pass
    
    async def _get_wholesale_orders_by_order_id(self, order_id: str) -> List[WholesaleOrder]:
        pass
    
    async def _log_settlement_processing(self, order_id: str, step: str, action: str, 
                                       success: bool, processing_time_ms: int = None,
                                       output_data: Dict = None):
        pass
    
    async def _send_settlement_notification(self, settlement: Settlement):
        pass
    
    # 추가 구현 필요한 메서드들...
    async def _track_wholesale_costs(self, order: Order) -> Dict[str, Any]:
        pass
    
    async def _track_shipping_costs(self, order: Order) -> Dict[str, Any]:
        pass
    
    async def _track_platform_fees(self, order: Order) -> Dict[str, Any]:
        pass