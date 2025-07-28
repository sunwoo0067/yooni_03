"""
Service performance benchmarks.
서비스 성능 벤치마크.
"""
import pytest
import asyncio
from decimal import Decimal
from pathlib import Path

from tests.benchmarks.benchmark_framework import (
    Benchmark, BenchmarkSuite, MemoryBenchmark
)
from app.services.product.product_service_v2 import ProductServiceV2
from app.services.order_processing.order_processor_v2 import OrderProcessorV2
from app.services.ai.ai_service_v2 import AIServiceV2
from app.core.cache_utils import CacheService


@pytest.mark.benchmark
class TestServiceBenchmarks:
    """서비스 벤치마크 테스트"""
    
    @pytest.fixture
    def benchmark_suite(self):
        """벤치마크 스위트"""
        return BenchmarkSuite("Service Performance")
        
    async def test_product_service_benchmarks(
        self,
        async_session,
        cache_service,
        benchmark_suite,
        test_data_factory
    ):
        """상품 서비스 벤치마크"""
        # 서비스 초기화
        service = ProductServiceV2(async_session, cache_service)
        
        # 테스트 데이터 준비
        products = []
        for i in range(100):
            product_data = test_data_factory.create_product_data(
                sku=f"BENCH-{i:04d}",
                name=f"Benchmark Product {i}",
                price=Decimal(f"{100 + i}.00")
            )
            product = await service.create_product(product_data)
            products.append(product)
            
        # 1. 단일 상품 조회 벤치마크 (캐시 없음)
        bench_get_no_cache = Benchmark("get_product_no_cache")
        result1 = await bench_get_no_cache.run_async(
            service.get_product_detail,
            iterations=1000,
            product_id=str(products[0].id),
            use_cache=False
        )
        benchmark_suite.add_benchmark(bench_get_no_cache)
        
        # 2. 단일 상품 조회 벤치마크 (캐시 있음)
        bench_get_with_cache = Benchmark("get_product_with_cache")
        
        # 캐시 워밍업
        await service.get_product_detail(str(products[0].id), use_cache=True)
        
        result2 = await bench_get_with_cache.run_async(
            service.get_product_detail,
            iterations=1000,
            product_id=str(products[0].id),
            use_cache=True
        )
        benchmark_suite.add_benchmark(bench_get_with_cache)
        
        # 3. 상품 검색 벤치마크
        bench_search = Benchmark("search_products")
        result3 = await bench_search.run_async(
            service.search_products,
            iterations=100,
            category="TestCategory",
            page=1,
            per_page=20
        )
        benchmark_suite.add_benchmark(bench_search)
        
        # 4. 재고 업데이트 벤치마크
        bench_update_stock = Benchmark("update_stock")
        
        async def update_stock_test():
            # 순환하며 재고 업데이트
            for i in range(10):
                await service.update_stock(
                    str(products[i % len(products)].id),
                    quantity_change=1
                )
                
        result4 = await bench_update_stock.run_async(
            update_stock_test,
            iterations=10
        )
        benchmark_suite.add_benchmark(bench_update_stock)
        
        # 5. 동시성 벤치마크
        bench_concurrent = Benchmark("concurrent_product_operations")
        
        async def mixed_operations():
            tasks = []
            # 다양한 작업 혼합
            for i in range(5):
                if i % 3 == 0:
                    # 조회
                    task = service.get_product_detail(
                        str(products[i % len(products)].id)
                    )
                elif i % 3 == 1:
                    # 검색
                    task = service.search_products(page=1, per_page=10)
                else:
                    # 재고 업데이트
                    task = service.update_stock(
                        str(products[i % len(products)].id),
                        quantity_change=1
                    )
                tasks.append(task)
                
            await asyncio.gather(*tasks)
            
        result5 = await bench_concurrent.run_concurrent(
            mixed_operations,
            iterations=50,
            concurrency=10
        )
        benchmark_suite.add_benchmark(bench_concurrent)
        
        # 결과 비교
        comparison = bench_get_with_cache.compare(bench_get_no_cache)
        print(f"\n캐시 성능 개선: {comparison['improvement_percent']:.2f}%")
        print(f"속도 향상: {comparison['speedup']:.2f}x")
        
    async def test_order_processor_benchmarks(
        self,
        async_session,
        benchmark_suite,
        test_data_factory,
        integration_helper
    ):
        """주문 처리 벤치마크"""
        # 서비스 초기화
        processor = OrderProcessorV2(async_session)
        
        # 테스트 데이터 준비
        user = await integration_helper.create_test_user()
        products = []
        for i in range(10):
            product = await integration_helper.create_test_product(
                price=Decimal("100.00"),
                stock_quantity=1000
            )
            products.append(product)
            
        # 1. 주문 생성 벤치마크
        bench_create = Benchmark("create_order")
        
        async def create_order_test():
            order_data = test_data_factory.create_order_data(
                user_id=str(user.id),
                items=[
                    {
                        "product_id": str(products[i % len(products)].id),
                        "quantity": 2,
                        "price": "100.00"
                    }
                    for i in range(3)
                ]
            )
            return await processor.create_order(order_data)
            
        result1 = await bench_create.run_async(
            create_order_test,
            iterations=100
        )
        benchmark_suite.add_benchmark(bench_create)
        
        # 2. 주문 검증 벤치마크
        bench_validate = Benchmark("validate_order")
        
        order_data = test_data_factory.create_order_data(
            user_id=str(user.id),
            items=[{"product_id": str(products[0].id), "quantity": 1}]
        )
        
        result2 = await bench_validate.run_async(
            processor.validate_order,
            iterations=1000,
            order_data=order_data
        )
        benchmark_suite.add_benchmark(bench_validate)
        
        # 3. 총액 계산 벤치마크
        bench_calculate = Benchmark("calculate_order_total")
        
        items = [
            {
                "product_id": str(p.id),
                "quantity": 2,
                "price": Decimal("100.00")
            }
            for p in products[:5]
        ]
        
        result3 = await bench_calculate.run_async(
            processor.calculate_order_total,
            iterations=1000,
            items=items,
            apply_margin=True
        )
        benchmark_suite.add_benchmark(bench_calculate)
        
    async def test_ai_service_benchmarks(
        self,
        ai_service_v2,
        benchmark_suite,
        cache_service
    ):
        """AI 서비스 벤치마크"""
        # 1. 텍스트 생성 벤치마크 (캐시 없음)
        bench_generate_no_cache = Benchmark("ai_generate_no_cache")
        
        result1 = await bench_generate_no_cache.run_async(
            ai_service_v2.generate_text,
            iterations=50,
            prompt="Generate a product description",
            max_tokens=100,
            use_cache=False
        )
        benchmark_suite.add_benchmark(bench_generate_no_cache)
        
        # 2. 텍스트 생성 벤치마크 (캐시 있음)
        bench_generate_with_cache = Benchmark("ai_generate_with_cache")
        
        # 캐시 워밍업
        await ai_service_v2.generate_text(
            "Cached prompt",
            use_cache=True
        )
        
        result2 = await bench_generate_with_cache.run_async(
            ai_service_v2.generate_text,
            iterations=50,
            prompt="Cached prompt",
            use_cache=True
        )
        benchmark_suite.add_benchmark(bench_generate_with_cache)
        
        # 3. 배치 상품 분석 벤치마크
        bench_batch_analysis = Benchmark("ai_batch_product_analysis")
        
        products = [
            {"id": f"prod-{i}", "name": f"Product {i}", "price": 100 + i}
            for i in range(20)
        ]
        
        result3 = await bench_batch_analysis.run_async(
            ai_service_v2.batch_analyze_products,
            iterations=5,
            products=products,
            batch_size=5
        )
        benchmark_suite.add_benchmark(bench_batch_analysis)
        
    async def test_memory_benchmarks(
        self,
        async_session,
        cache_service,
        test_data_factory
    ):
        """메모리 사용량 벤치마크"""
        memory_bench = MemoryBenchmark()
        
        # 1. 대량 상품 생성 메모리 테스트
        service = ProductServiceV2(async_session, cache_service)
        
        async def create_many_products():
            products = []
            for i in range(1000):
                product_data = test_data_factory.create_product_data(
                    sku=f"MEM-{i:05d}"
                )
                product = await service.create_product(product_data)
                products.append(product)
            return products
            
        memory_result = memory_bench.measure(create_many_products)
        
        print(f"\n메모리 사용량:")
        print(f"시작: {memory_result['start_memory_mb']:.2f} MB")
        print(f"종료: {memory_result['end_memory_mb']:.2f} MB")
        print(f"증가: {memory_result['memory_increase_mb']:.2f} MB")
        
    @pytest.mark.slow
    async def test_load_benchmarks(
        self,
        async_session,
        cache_service,
        benchmark_suite
    ):
        """부하 테스트 벤치마크"""
        service = ProductServiceV2(async_session, cache_service)
        
        # 동시 사용자 시뮬레이션
        bench_load = Benchmark("load_test_concurrent_users")
        
        async def simulate_user():
            # 사용자 행동 시뮬레이션
            # 1. 상품 검색
            await service.search_products(page=1, per_page=20)
            
            # 2. 상품 상세 조회
            # (실제로는 검색 결과에서 선택)
            
            # 3. 짧은 대기
            await asyncio.sleep(0.1)
            
        # 100명의 동시 사용자
        result = await bench_load.run_concurrent(
            simulate_user,
            iterations=1000,  # 총 1000개 요청
            concurrency=100   # 100명 동시
        )
        
        benchmark_suite.add_benchmark(bench_load)
        
        print(f"\n부하 테스트 결과:")
        print(f"총 처리 시간: {result.metadata['total_wall_time']:.2f}초")
        print(f"처리량: {result.metadata['concurrent_throughput']:.2f} ops/sec")
        
    async def test_generate_benchmark_report(
        self,
        benchmark_suite,
        tmp_path
    ):
        """벤치마크 보고서 생성"""
        # JSON 보고서
        report_path = tmp_path / "benchmark_report.json"
        benchmark_suite.generate_report(report_path)
        
        # CSV 내보내기
        csv_path = tmp_path / "benchmark_results.csv"
        benchmark_suite.export_csv(csv_path)
        
        print(f"\n보고서 생성:")
        print(f"JSON: {report_path}")
        print(f"CSV: {csv_path}")


# 벤치마크 비교 도구
class BenchmarkComparison:
    """V1 vs V2 성능 비교"""
    
    @staticmethod
    async def compare_services(v1_service, v2_service, test_data):
        """서비스 버전 비교"""
        suite = BenchmarkSuite("V1 vs V2 Comparison")
        
        # V1 벤치마크
        bench_v1 = Benchmark("Service V1")
        result_v1 = await bench_v1.run_async(
            v1_service.process,
            iterations=100,
            data=test_data
        )
        suite.add_benchmark(bench_v1)
        
        # V2 벤치마크
        bench_v2 = Benchmark("Service V2")
        result_v2 = await bench_v2.run_async(
            v2_service.process,
            iterations=100,
            data=test_data
        )
        suite.add_benchmark(bench_v2)
        
        # 비교 결과
        comparison = bench_v2.compare(bench_v1)
        
        print("\n=== 성능 비교 결과 ===")
        print(f"V1 평균 시간: {result_v1.avg_time * 1000:.2f}ms")
        print(f"V2 평균 시간: {result_v2.avg_time * 1000:.2f}ms")
        print(f"개선율: {comparison['improvement_percent']:.2f}%")
        print(f"속도 향상: {comparison['speedup']:.2f}x")
        
        return comparison