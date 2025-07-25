"""
주문처리 시스템 유닛 테스트
- 주문 모니터링 테스트
- 자동 발주 테스트
- 배송 추적 테스트
- 정산 시스템 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any

from app.services.order_automation.order_monitor import OrderMonitor
from app.services.order_automation.auto_order_system import AutoOrderSystem
from app.services.order_automation.shipping_tracker import ShippingTracker
from app.services.order_automation.auto_settlement import AutoSettlement
from app.services.ordering.order_manager import OrderManager
from app.services.ordering.zentrade_ordering import ZentradeOrdering
from app.services.ordering.ownerclan_ordering import OwnerClanOrdering
from app.services.ordering.domeggook_ordering import DomeggookOrdering


class TestOrderMonitor:
    """주문 모니터링 테스트"""
    
    @pytest.fixture
    def order_monitor(self):
        return OrderMonitor()
    
    @patch('app.services.platforms.coupang_api.CoupangAPI.get_new_orders')
    def test_monitor_coupang_orders(self, mock_get_orders, order_monitor):
        """쿠팡 주문 모니터링 테스트"""
        mock_get_orders.return_value = [
            {
                "orderId": "C123456",
                "orderDate": "2025-01-25T10:00:00",
                "customerName": "테스트고객",
                "productName": "테스트 상품",
                "quantity": 2,
                "totalPrice": 50000,
                "status": "PAYMENT_COMPLETE"
            }
        ]
        
        new_orders = order_monitor.check_coupang_orders()
        
        assert len(new_orders) == 1
        assert new_orders[0]["orderId"] == "C123456"
        assert new_orders[0]["platform"] == "coupang"
        mock_get_orders.assert_called_once()
    
    @patch('app.services.platforms.naver_api.NaverAPI.get_orders')
    def test_monitor_naver_orders(self, mock_get_orders, order_monitor):
        """네이버 주문 모니터링 테스트"""
        mock_get_orders.return_value = {
            "orders": [
                {
                    "orderNo": "N789012",
                    "orderDate": "2025-01-25T11:00:00",
                    "ordererName": "네이버고객",
                    "productOrderList": [{
                        "productName": "네이버 상품",
                        "quantity": 1,
                        "unitPrice": 30000
                    }],
                    "orderStatus": "PAYED"
                }
            ]
        }
        
        new_orders = order_monitor.check_naver_orders()
        
        assert len(new_orders) == 1
        assert new_orders[0]["orderId"] == "N789012"
        assert new_orders[0]["platform"] == "naver"
    
    def test_filter_duplicate_orders(self, order_monitor):
        """중복 주문 필터링 테스트"""
        orders = [
            {"orderId": "O1", "platform": "coupang"},
            {"orderId": "O2", "platform": "naver"},
            {"orderId": "O1", "platform": "coupang"},  # 중복
            {"orderId": "O3", "platform": "11st"}
        ]
        
        # 첫 번째 실행
        unique_orders = order_monitor.filter_duplicates(orders)
        assert len(unique_orders) == 3
        
        # 두 번째 실행 (모두 중복)
        duplicate_check = order_monitor.filter_duplicates(orders)
        assert len(duplicate_check) == 0
    
    @pytest.mark.asyncio
    async def test_real_time_monitoring(self, order_monitor):
        """실시간 모니터링 테스트"""
        mock_callback = Mock()
        
        with patch.object(order_monitor, 'check_all_platforms') as mock_check:
            mock_check.side_effect = [
                [{"orderId": "RT1", "platform": "coupang"}],
                [{"orderId": "RT2", "platform": "naver"}],
                []  # 종료 조건
            ]
            
            await order_monitor.start_monitoring(
                callback=mock_callback,
                interval=0.1,  # 빠른 테스트를 위해
                max_iterations=3
            )
        
        assert mock_callback.call_count == 2
        mock_callback.assert_any_call({"orderId": "RT1", "platform": "coupang"})
        mock_callback.assert_any_call({"orderId": "RT2", "platform": "naver"})
    
    def test_order_status_tracking(self, order_monitor):
        """주문 상태 추적 테스트"""
        order_id = "TEST123"
        
        # 상태 변경 시뮬레이션
        statuses = ["PAYMENT_COMPLETE", "PREPARING", "SHIPPING", "DELIVERED"]
        
        for status in statuses:
            order_monitor.update_status(order_id, status)
            current_status = order_monitor.get_status(order_id)
            assert current_status == status
        
        # 상태 이력 확인
        history = order_monitor.get_status_history(order_id)
        assert len(history) == 4
        assert history[-1]["status"] == "DELIVERED"


class TestAutoOrderSystem:
    """자동 발주 시스템 테스트"""
    
    @pytest.fixture
    def auto_order_system(self):
        return AutoOrderSystem()
    
    def test_process_new_order(self, auto_order_system):
        """신규 주문 처리 테스트"""
        order = {
            "orderId": "AO123",
            "productId": "P123",
            "quantity": 3,
            "customerInfo": {
                "name": "테스트고객",
                "phone": "010-1234-5678",
                "address": "서울시 강남구"
            }
        }
        
        with patch.object(auto_order_system, '_find_supplier') as mock_find:
            mock_find.return_value = {
                "supplier": "zentrade",
                "supplier_product_id": "Z123",
                "price": 15000
            }
            
            result = auto_order_system.process_order(order)
        
        assert result["status"] == "processing"
        assert result["supplier"] == "zentrade"
        assert result["total_cost"] == 45000
    
    def test_supplier_selection(self, auto_order_system):
        """공급업체 선택 테스트"""
        product_id = "P456"
        quantity = 5
        
        suppliers = [
            {"name": "zentrade", "price": 10000, "stock": 10, "reliability": 0.95},
            {"name": "ownerclan", "price": 9500, "stock": 3, "reliability": 0.90},
            {"name": "domeggook", "price": 11000, "stock": 20, "reliability": 0.98}
        ]
        
        with patch.object(auto_order_system, '_get_supplier_options', return_value=suppliers):
            selected = auto_order_system.select_best_supplier(product_id, quantity)
        
        # 재고가 충분하고 신뢰도가 높은 공급업체 선택
        assert selected["name"] in ["zentrade", "domeggook"]
        assert selected["stock"] >= quantity
    
    @patch.object(ZentradeOrdering, 'place_order')
    def test_place_wholesale_order(self, mock_place_order, auto_order_system):
        """도매 주문 발주 테스트"""
        mock_place_order.return_value = {
            "wholesale_order_id": "WO123",
            "status": "confirmed",
            "estimated_delivery": "2025-01-27"
        }
        
        order_details = {
            "supplier": "zentrade",
            "product_id": "Z789",
            "quantity": 2,
            "shipping_address": {
                "name": "고객명",
                "address": "배송주소"
            }
        }
        
        result = auto_order_system.place_wholesale_order(order_details)
        
        assert result["wholesale_order_id"] == "WO123"
        assert result["status"] == "confirmed"
        mock_place_order.assert_called_once()
    
    def test_order_failure_handling(self, auto_order_system):
        """주문 실패 처리 테스트"""
        order = {
            "orderId": "FAIL123",
            "productId": "P999",
            "quantity": 1
        }
        
        with patch.object(auto_order_system, '_find_supplier') as mock_find:
            mock_find.return_value = None  # 공급업체 없음
            
            result = auto_order_system.process_order(order)
        
        assert result["status"] == "failed"
        assert "reason" in result
        assert "대체 공급업체" in result["reason"]
    
    def test_bulk_order_processing(self, auto_order_system):
        """대량 주문 처리 테스트"""
        orders = [
            {"orderId": f"BO{i}", "productId": f"P{i}", "quantity": i}
            for i in range(1, 6)
        ]
        
        with patch.object(auto_order_system, 'process_order') as mock_process:
            mock_process.return_value = {"status": "processing"}
            
            results = auto_order_system.process_bulk_orders(orders)
        
        assert len(results) == 5
        assert mock_process.call_count == 5
        assert all(r["status"] == "processing" for r in results)


class TestShippingTracker:
    """배송 추적 시스템 테스트"""
    
    @pytest.fixture
    def shipping_tracker(self):
        return ShippingTracker()
    
    @patch('requests.get')
    def test_track_cj_logistics(self, mock_get, shipping_tracker):
        """CJ대한통운 배송 추적 테스트"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tracking_number": "123456789",
            "status": "배송중",
            "history": [
                {"time": "2025-01-25 10:00", "location": "서울 집하장", "status": "집하"},
                {"time": "2025-01-25 14:00", "location": "경기 허브", "status": "이동중"}
            ]
        }
        mock_get.return_value = mock_response
        
        tracking_info = shipping_tracker.track_shipment("123456789", "cj")
        
        assert tracking_info["status"] == "배송중"
        assert len(tracking_info["history"]) == 2
        mock_get.assert_called_once()
    
    def test_parse_tracking_status(self, shipping_tracker):
        """배송 상태 파싱 테스트"""
        test_cases = [
            ("상품준비중", "preparing"),
            ("집하완료", "collected"),
            ("배송중", "in_transit"),
            ("배송완료", "delivered"),
            ("반송", "returned")
        ]
        
        for korean_status, expected_status in test_cases:
            parsed = shipping_tracker.parse_status(korean_status)
            assert parsed == expected_status
    
    def test_estimate_delivery_date(self, shipping_tracker):
        """예상 배송일 계산 테스트"""
        # 일반 배송 (2-3일)
        order_date = datetime.now()
        estimated = shipping_tracker.estimate_delivery(order_date, "standard")
        
        expected_min = order_date + timedelta(days=2)
        expected_max = order_date + timedelta(days=3)
        
        assert expected_min <= estimated <= expected_max
        
        # 당일 배송
        estimated_today = shipping_tracker.estimate_delivery(order_date, "same_day")
        assert estimated_today.date() == order_date.date()
    
    @pytest.mark.asyncio
    async def test_auto_tracking_update(self, shipping_tracker):
        """자동 배송 추적 업데이트 테스트"""
        tracking_numbers = ["TN001", "TN002", "TN003"]
        
        with patch.object(shipping_tracker, 'track_shipment') as mock_track:
            mock_track.side_effect = [
                {"tracking_number": "TN001", "status": "in_transit"},
                {"tracking_number": "TN002", "status": "delivered"},
                {"tracking_number": "TN003", "status": "preparing"}
            ]
            
            updates = await shipping_tracker.batch_update_tracking(tracking_numbers)
        
        assert len(updates) == 3
        assert updates["TN002"]["status"] == "delivered"
        assert mock_track.call_count == 3
    
    def test_delivery_notification(self, shipping_tracker):
        """배송 완료 알림 테스트"""
        mock_notifier = Mock()
        
        tracking_update = {
            "tracking_number": "TN123",
            "status": "delivered",
            "delivered_at": "2025-01-25 15:30",
            "recipient": "테스트고객"
        }
        
        shipping_tracker.notify_delivery(tracking_update, mock_notifier)
        
        mock_notifier.send_notification.assert_called_once()
        call_args = mock_notifier.send_notification.call_args[0][0]
        assert "배송완료" in call_args["message"]
        assert "TN123" in call_args["message"]


class TestAutoSettlement:
    """자동 정산 시스템 테스트"""
    
    @pytest.fixture
    def auto_settlement(self):
        return AutoSettlement()
    
    def test_calculate_settlement_amount(self, auto_settlement):
        """정산 금액 계산 테스트"""
        order = {
            "orderId": "S123",
            "sales_price": 50000,
            "wholesale_cost": 30000,
            "platform_fee": 5000,
            "shipping_cost": 2500,
            "additional_costs": 1000
        }
        
        settlement = auto_settlement.calculate_settlement(order)
        
        assert settlement["gross_profit"] == 20000  # 50000 - 30000
        assert settlement["net_profit"] == 11500   # 20000 - 5000 - 2500 - 1000
        assert settlement["profit_margin"] == 0.23  # 11500 / 50000
    
    def test_batch_settlement_processing(self, auto_settlement):
        """일괄 정산 처리 테스트"""
        orders = [
            {
                "orderId": f"S{i}",
                "sales_price": 30000 + (i * 5000),
                "wholesale_cost": 20000 + (i * 2000),
                "platform_fee": 3000 + (i * 500)
            }
            for i in range(5)
        ]
        
        settlements = auto_settlement.process_batch_settlement(orders)
        
        assert len(settlements) == 5
        assert all("net_profit" in s for s in settlements)
        assert sum(s["net_profit"] for s in settlements) > 0
    
    def test_platform_fee_calculation(self, auto_settlement):
        """플랫폼 수수료 계산 테스트"""
        test_cases = [
            ("coupang", 100000, 0.11, 11000),  # 쿠팡 11%
            ("naver", 100000, 0.05, 5000),     # 네이버 5%
            ("11st", 100000, 0.13, 13000)     # 11번가 13%
        ]
        
        for platform, amount, fee_rate, expected_fee in test_cases:
            fee = auto_settlement.calculate_platform_fee(platform, amount)
            assert fee == expected_fee
    
    def test_settlement_report_generation(self, auto_settlement):
        """정산 리포트 생성 테스트"""
        period_start = datetime(2025, 1, 1)
        period_end = datetime(2025, 1, 31)
        
        with patch.object(auto_settlement, 'get_orders_for_period') as mock_get:
            mock_get.return_value = [
                {"orderId": "R1", "net_profit": 10000, "platform": "coupang"},
                {"orderId": "R2", "net_profit": 15000, "platform": "naver"},
                {"orderId": "R3", "net_profit": 12000, "platform": "coupang"}
            ]
            
            report = auto_settlement.generate_report(period_start, period_end)
        
        assert report["total_orders"] == 3
        assert report["total_profit"] == 37000
        assert report["by_platform"]["coupang"]["count"] == 2
        assert report["by_platform"]["coupang"]["profit"] == 22000
    
    def test_refund_processing(self, auto_settlement):
        """환불 처리 테스트"""
        original_order = {
            "orderId": "REF123",
            "sales_price": 50000,
            "wholesale_cost": 30000,
            "platform_fee": 5000,
            "status": "delivered"
        }
        
        refund_request = {
            "orderId": "REF123",
            "refund_amount": 50000,
            "refund_shipping": 2500,
            "reason": "단순변심"
        }
        
        refund_result = auto_settlement.process_refund(
            original_order, refund_request
        )
        
        assert refund_result["refund_amount"] == 50000
        assert refund_result["loss_amount"] == 37500  # 원가 + 수수료 + 반품배송비
        assert refund_result["status"] == "refunded"


class TestOrderIntegration:
    """주문 처리 통합 테스트"""
    
    def test_end_to_end_order_flow(self):
        """전체 주문 플로우 테스트"""
        # 1. 주문 감지
        order_monitor = OrderMonitor()
        with patch.object(order_monitor, 'check_coupang_orders') as mock_check:
            mock_check.return_value = [{
                "orderId": "INT123",
                "productId": "P123",
                "quantity": 2,
                "customerInfo": {
                    "name": "통합테스트",
                    "address": "서울시"
                }
            }]
            new_orders = order_monitor.check_coupang_orders()
        
        # 2. 자동 발주
        auto_order = AutoOrderSystem()
        with patch.object(auto_order, 'place_wholesale_order') as mock_place:
            mock_place.return_value = {
                "wholesale_order_id": "WO123",
                "tracking_number": "TN123"
            }
            order_result = auto_order.process_order(new_orders[0])
        
        # 3. 배송 추적
        shipping_tracker = ShippingTracker()
        with patch.object(shipping_tracker, 'track_shipment') as mock_track:
            mock_track.return_value = {
                "status": "delivered",
                "delivered_at": "2025-01-27"
            }
            tracking = shipping_tracker.track_shipment("TN123")
        
        # 4. 정산 처리
        auto_settlement = AutoSettlement()
        settlement = auto_settlement.calculate_settlement({
            "orderId": "INT123",
            "sales_price": 60000,
            "wholesale_cost": 40000,
            "platform_fee": 6000
        })
        
        # 검증
        assert new_orders[0]["orderId"] == "INT123"
        assert order_result["wholesale_order_id"] == "WO123"
        assert tracking["status"] == "delivered"
        assert settlement["net_profit"] == 14000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])