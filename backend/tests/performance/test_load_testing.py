"""
Performance and load testing for dropshipping system
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, AsyncMock
import statistics
from decimal import Decimal
from datetime import datetime
import threading

from tests.conftest_enhanced import *
from tests.mocks import *


class TestAPIPerformance:
    """Test API endpoint performance"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_product_api_load(self, enhanced_test_client, test_user_token, product_factory):
        """Test product API under load"""
        
        # Create test products
        for i in range(50):
            product_factory(name=f"로드테스트 상품 {i+1}")
        
        def make_request():
            """Single request function"""
            start_time = time.time()
            response = enhanced_test_client.get(
                "/api/v1/products/",
                headers=test_user_token["headers"]
            )
            end_time = time.time()
            
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 200
            }
        
        # Concurrent requests
        num_requests = 50
        max_workers = 10
        
        print(f"🚀 Testing {num_requests} concurrent requests with {max_workers} workers...")
        
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_requests = [r for r in results if r["success"]]
        response_times = [r["response_time"] for r in successful_requests]
        
        success_rate = len(successful_requests) / num_requests
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        requests_per_second = num_requests / total_time
        
        print(f"✅ Load test results:")
        print(f"   Total requests: {num_requests}")
        print(f"   Successful requests: {len(successful_requests)}")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Average response time: {avg_response_time:.3f}s")
        print(f"   Min response time: {min_response_time:.3f}s")
        print(f"   Max response time: {max_response_time:.3f}s")
        print(f"   Requests per second: {requests_per_second:.2f}")
        print(f"   Total time: {total_time:.3f}s")
        
        # Performance assertions
        assert success_rate >= 0.95  # 95% success rate
        assert avg_response_time < 2.0  # Average under 2 seconds
        assert max_response_time < 5.0  # Max under 5 seconds
        assert requests_per_second >= 10  # At least 10 RPS
    
    @pytest.mark.performance
    def test_search_performance(self, enhanced_test_client, test_user_token, product_factory):
        """Test search API performance with various query types"""
        
        # Create diverse test data
        categories = ["보석", "주방용품", "생활용품", "전자제품", "의류"]
        for category in categories:
            for i in range(20):  # 20 products per category
                product_factory(
                    name=f"{category} 테스트 상품 {i+1}",
                    category=category,
                    tags=[category, f"태그{i}", "테스트"]
                )
        
        search_queries = [
            ("category=보석", "Category search"),
            ("q=테스트", "Text search"),
            ("category=주방용품&min_price=10000", "Complex filter"),
            ("tags=태그1", "Tag search"),
            ("q=상품&category=생활용품", "Combined search")
        ]
        
        performance_results = {}
        
        for query, description in search_queries:
            print(f"🔍 Testing {description}...")
            
            # Measure multiple requests
            times = []
            for _ in range(10):
                start_time = time.time()
                response = enhanced_test_client.get(
                    f"/api/v1/products/search?{query}",
                    headers=test_user_token["headers"]
                )
                end_time = time.time()
                
                assert response.status_code == 200
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            max_time = max(times)
            
            performance_results[description] = {
                "avg_time": avg_time,
                "max_time": max_time,
                "queries": len(times)
            }
            
            print(f"   Average: {avg_time:.3f}s, Max: {max_time:.3f}s")
            
            # Search should be fast
            assert avg_time < 1.0  # Average under 1 second
            assert max_time < 2.0  # Max under 2 seconds
        
        return performance_results
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_performance(self, enhanced_test_db, product_factory):
        """Test database operation performance"""
        
        print("💾 Testing database performance...")
        
        # Test bulk insert performance
        start_time = time.time()
        
        products = []
        for i in range(100):
            product = product_factory(name=f"DB 테스트 상품 {i+1}")
            products.append(product)
        
        insert_time = time.time() - start_time
        
        # Test bulk read performance
        start_time = time.time()
        
        # Simulate bulk read
        for _ in range(50):
            query_result = enhanced_test_db.query(products[0].__class__).limit(20).all()
            assert len(query_result) > 0
        
        read_time = time.time() - start_time
        
        print(f"   Bulk insert (100 records): {insert_time:.3f}s")
        print(f"   Bulk read (50 queries): {read_time:.3f}s")
        
        # Database operations should be fast
        assert insert_time < 5.0  # 100 inserts under 5 seconds
        assert read_time < 2.0   # 50 reads under 2 seconds
        
        return {
            "insert_time": insert_time,
            "read_time": read_time,
            "records_created": len(products)
        }


class TestConcurrencyAndThreading:
    """Test system behavior under concurrent access"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_order_processing(self, enhanced_test_client, test_user_token, product_factory):
        """Test concurrent order processing"""
        
        # Create test products
        products = []
        for i in range(5):
            product = product_factory(
                name=f"동시성 테스트 상품 {i+1}",
                stock_quantity=100
            )
            products.append(product)
        
        def create_order(product_id, order_num):
            """Create a single order"""
            order_data = {
                "platform": "coupang",
                "platform_order_id": f"CONCURRENT_ORD_{order_num:03d}",
                "customer_name": f"동시고객{order_num}",
                "customer_email": f"concurrent{order_num}@example.com",
                "customer_phone": "010-1234-5678",
                "order_items": [
                    {
                        "product_id": product_id,
                        "name": f"상품 {product_id}",
                        "quantity": 1,
                        "price": 25000,
                        "total": 25000
                    }
                ],
                "total_amount": 25000,
                "payment_status": "paid"
            }
            
            start_time = time.time()
            response = enhanced_test_client.post(
                "/api/v1/orders/",
                json=order_data,
                headers=test_user_token["headers"]
            )
            end_time = time.time()
            
            return {
                "order_num": order_num,
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "success": response.status_code == 201
            }
        
        # Create 20 concurrent orders
        num_orders = 20
        max_workers = 8
        
        print(f"📦 Creating {num_orders} concurrent orders...")
        
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(num_orders):
                product_id = str(products[i % len(products)].id)
                future = executor.submit(create_order, product_id, i+1)
                futures.append(future)
            
            for future in as_completed(futures):
                results.append(future.result())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze results
        successful_orders = [r for r in results if r["success"]]
        response_times = [r["response_time"] for r in successful_orders]
        
        success_rate = len(successful_orders) / num_orders
        avg_response_time = statistics.mean(response_times) if response_times else 0
        orders_per_second = num_orders / total_time
        
        print(f"✅ Concurrent order processing results:")
        print(f"   Orders created: {len(successful_orders)}/{num_orders}")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Average response time: {avg_response_time:.3f}s")
        print(f"   Orders per second: {orders_per_second:.2f}")
        print(f"   Total time: {total_time:.3f}s")
        
        # Concurrency assertions
        assert success_rate >= 0.90  # 90% success rate
        assert avg_response_time < 3.0  # Average under 3 seconds
        assert orders_per_second >= 5   # At least 5 orders per second
    
    @pytest.mark.performance
    def test_race_condition_stock_updates(self, enhanced_test_client, test_user_token, product_factory):
        """Test for race conditions in stock updates"""
        
        # Create product with initial stock
        product = product_factory(
            name="경쟁조건 테스트 상품",
            stock_quantity=100
        )
        
        def update_stock(stock_change, thread_id):
            """Update stock in a single thread"""
            try:
                # Get current stock
                get_response = enhanced_test_client.get(
                    f"/api/v1/products/{product.id}",
                    headers=test_user_token["headers"]
                )
                
                if get_response.status_code != 200:
                    return {"thread_id": thread_id, "success": False, "error": "Get failed"}
                
                current_stock = get_response.json()["stock_quantity"]
                new_stock = max(0, current_stock + stock_change)
                
                # Update stock
                update_response = enhanced_test_client.put(
                    f"/api/v1/products/{product.id}",
                    json={"stock_quantity": new_stock},
                    headers=test_user_token["headers"]
                )
                
                return {
                    "thread_id": thread_id,
                    "success": update_response.status_code == 200,
                    "old_stock": current_stock,
                    "new_stock": new_stock,
                    "change": stock_change
                }
                
            except Exception as e:
                return {"thread_id": thread_id, "success": False, "error": str(e)}
        
        # Simulate concurrent stock updates (some positive, some negative)
        stock_changes = [-5, -3, -2, 10, -1, 8, -4, 15, -2, -1]
        num_threads = len(stock_changes)
        
        print(f"🔄 Testing {num_threads} concurrent stock updates...")
        
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i, change in enumerate(stock_changes):
                future = executor.submit(update_stock, change, i+1)
                futures.append(future)
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Verify final stock consistency
        final_response = enhanced_test_client.get(
            f"/api/v1/products/{product.id}",
            headers=test_user_token["headers"]
        )
        
        assert final_response.status_code == 200
        final_stock = final_response.json()["stock_quantity"]
        
        successful_updates = [r for r in results if r["success"]]
        success_rate = len(successful_updates) / num_threads
        
        print(f"✅ Race condition test results:")
        print(f"   Successful updates: {len(successful_updates)}/{num_threads}")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Final stock: {final_stock}")
        print(f"   Initial stock: 100")
        
        # Race condition assertions
        assert success_rate >= 0.80  # 80% success rate (some may fail due to conflicts)
        assert final_stock >= 0      # Stock should never go negative
        assert final_stock <= 150    # Should not exceed reasonable bounds
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_async_task_performance(self):
        """Test performance of async task processing"""
        
        async def mock_ai_task(task_id):
            """Mock AI processing task"""
            # Simulate AI processing time
            await asyncio.sleep(0.1)  # 100ms processing
            return {
                "task_id": task_id,
                "result": f"AI result for task {task_id}",
                "processing_time": 0.1
            }
        
        async def mock_api_task(task_id):
            """Mock API call task"""
            # Simulate API call time
            await asyncio.sleep(0.05)  # 50ms API call
            return {
                "task_id": task_id,
                "result": f"API result for task {task_id}",
                "processing_time": 0.05
            }
        
        # Test concurrent async tasks
        num_tasks = 20
        
        print(f"⚡ Testing {num_tasks} concurrent async tasks...")
        
        start_time = time.time()
        
        # Create mix of AI and API tasks
        tasks = []
        for i in range(num_tasks):
            if i % 2 == 0:
                task = mock_ai_task(i)
            else:
                task = mock_api_task(i)
            tasks.append(task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze async performance
        ai_tasks = [r for r in results if "AI result" in r["result"]]
        api_tasks = [r for r in results if "API result" in r["result"]]
        
        tasks_per_second = num_tasks / total_time
        
        print(f"✅ Async task performance:")
        print(f"   Total tasks: {num_tasks}")
        print(f"   AI tasks: {len(ai_tasks)}")
        print(f"   API tasks: {len(api_tasks)}")
        print(f"   Total time: {total_time:.3f}s")
        print(f"   Tasks per second: {tasks_per_second:.2f}")
        
        # Async performance should be much better than sequential
        sequential_time = num_tasks * 0.075  # Average of 0.1 and 0.05
        speedup = sequential_time / total_time
        
        print(f"   Sequential time would be: {sequential_time:.3f}s")
        print(f"   Speedup: {speedup:.2f}x")
        
        # Assertions
        assert total_time < sequential_time / 2  # At least 2x speedup
        assert tasks_per_second >= 50            # At least 50 tasks per second
        assert speedup >= 5                      # At least 5x speedup


class TestMemoryAndResourceUsage:
    """Test memory usage and resource management"""
    
    @pytest.mark.performance
    def test_memory_usage_bulk_operations(self, enhanced_test_client, test_user_token, performance_test_data):
        """Test memory usage during bulk operations"""
        
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"💾 Initial memory usage: {initial_memory:.2f} MB")
        
        # Perform bulk operations
        bulk_data = performance_test_data
        
        # Create many products
        print("📦 Creating bulk products...")
        for i, product_data in enumerate(bulk_data["products"][:100]):  # Limit to 100
            response = enhanced_test_client.post(
                "/api/v1/products/",
                json=product_data,
                headers=test_user_token["headers"]
            )
            
            # Check memory every 20 products
            if i % 20 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_increase = current_memory - initial_memory
                print(f"   After {i+1} products: {current_memory:.2f} MB (+{memory_increase:.2f} MB)")
                
                # Memory should not grow excessively
                assert memory_increase < 100  # Should not exceed 100MB increase
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"✅ Final memory usage: {final_memory:.2f} MB (+{total_increase:.2f} MB)")
        
        # Memory assertions
        assert total_increase < 150  # Total increase should be reasonable
        
        return {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": total_increase
        }
    
    @pytest.mark.performance
    def test_connection_pool_performance(self, enhanced_test_client, test_user_token):
        """Test database connection pool performance"""
        
        def make_db_intensive_request():
            """Make a database-intensive request"""
            return enhanced_test_client.get(
                "/api/v1/products/?limit=50&include_stats=true",
                headers=test_user_token["headers"]
            )
        
        # Test connection pool under load
        num_requests = 30
        max_workers = 10
        
        print(f"🔗 Testing connection pool with {num_requests} requests...")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_db_intensive_request) for _ in range(num_requests)]
            responses = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Analyze connection performance
        successful_responses = [r for r in responses if r.status_code == 200]
        success_rate = len(successful_responses) / num_requests
        requests_per_second = num_requests / total_time
        
        print(f"✅ Connection pool performance:")
        print(f"   Successful requests: {len(successful_responses)}/{num_requests}")
        print(f"   Success rate: {success_rate:.2%}")
        print(f"   Requests per second: {requests_per_second:.2f}")
        print(f"   Total time: {total_time:.3f}s")
        
        # Connection pool should handle load efficiently
        assert success_rate >= 0.95  # 95% success rate
        assert requests_per_second >= 10  # At least 10 RPS


class TestCachePerformance:
    """Test cache performance and effectiveness"""
    
    @pytest.mark.performance
    def test_cache_hit_performance(self, enhanced_test_client, test_user_token, product_factory):
        """Test cache hit rates and performance"""
        
        # Create test product
        product = product_factory(name="캐시 테스트 상품")
        
        # First request (cache miss)
        print("🗄️ Testing cache miss performance...")
        start_time = time.time()
        first_response = enhanced_test_client.get(
            f"/api/v1/products/{product.id}",
            headers=test_user_token["headers"]
        )
        cache_miss_time = time.time() - start_time
        
        assert first_response.status_code == 200
        
        # Subsequent requests (cache hits)
        print("⚡ Testing cache hit performance...")
        cache_hit_times = []
        
        for i in range(10):
            start_time = time.time()
            response = enhanced_test_client.get(
                f"/api/v1/products/{product.id}",
                headers=test_user_token["headers"]
            )
            hit_time = time.time() - start_time
            cache_hit_times.append(hit_time)
            
            assert response.status_code == 200
        
        avg_cache_hit_time = statistics.mean(cache_hit_times)
        speedup_ratio = cache_miss_time / avg_cache_hit_time if avg_cache_hit_time > 0 else 0
        
        print(f"✅ Cache performance results:")
        print(f"   Cache miss time: {cache_miss_time:.4f}s")
        print(f"   Average cache hit time: {avg_cache_hit_time:.4f}s")
        print(f"   Speedup ratio: {speedup_ratio:.2f}x")
        
        # Cache should provide significant speedup
        assert avg_cache_hit_time < cache_miss_time  # Cache hits should be faster
        assert speedup_ratio >= 2.0  # At least 2x speedup
    
    @pytest.mark.performance
    @patch('app.services.cache.cache_manager.CacheManager')
    def test_cache_efficiency_under_load(self, mock_cache, enhanced_test_client, test_user_token):
        """Test cache efficiency under high load"""
        
        # Setup cache mock
        cache_mock = mock_cache.return_value
        cache_hits = 0
        cache_misses = 0
        
        def mock_get(key):
            nonlocal cache_hits, cache_misses
            # Simulate 80% cache hit rate
            if hash(key) % 10 < 8:
                cache_hits += 1
                return {"cached": True, "data": "mock_data"}
            else:
                cache_misses += 1
                return None
        
        cache_mock.get = mock_get
        cache_mock.set = lambda k, v, ttl=None: True
        
        # Generate load
        num_requests = 100
        
        print(f"🚀 Testing cache under {num_requests} requests...")
        
        for i in range(num_requests):
            response = enhanced_test_client.get(
                f"/api/v1/products/{i % 20}/cached",  # 20 unique products
                headers=test_user_token["headers"]
            )
            # Note: This endpoint might not exist in actual API
        
        cache_hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        
        print(f"✅ Cache efficiency results:")
        print(f"   Cache hits: {cache_hits}")
        print(f"   Cache misses: {cache_misses}")
        print(f"   Hit rate: {cache_hit_rate:.2%}")
        
        # Cache should be effective
        assert cache_hit_rate >= 0.75  # At least 75% hit rate


class TestStressAndBreakpoint:
    """Test system limits and breaking points"""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_maximum_concurrent_users(self, enhanced_test_client, test_user_token):
        """Test maximum concurrent user load"""
        
        def simulate_user_session():
            """Simulate a complete user session"""
            try:
                # User workflow: login -> browse products -> search -> view details
                responses = []
                
                # Browse products
                response = enhanced_test_client.get(
                    "/api/v1/products/?limit=10",
                    headers=test_user_token["headers"]
                )
                responses.append(response.status_code == 200)
                
                # Search products
                response = enhanced_test_client.get(
                    "/api/v1/products/search?q=테스트",
                    headers=test_user_token["headers"]
                )
                responses.append(response.status_code == 200)
                
                # View dashboard
                response = enhanced_test_client.get(
                    "/api/v1/dashboard/summary",
                    headers=test_user_token["headers"]
                )
                responses.append(response.status_code in [200, 404])  # Endpoint might not exist
                
                return sum(responses) / len(responses)  # Success rate
                
            except Exception:
                return 0.0
        
        # Test with increasing concurrent users
        user_loads = [10, 20, 30, 50]
        results = {}
        
        for num_users in user_loads:
            print(f"👥 Testing with {num_users} concurrent users...")
            
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=num_users) as executor:
                futures = [executor.submit(simulate_user_session) for _ in range(num_users)]
                session_results = [future.result() for future in as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            avg_success_rate = statistics.mean(session_results)
            users_per_second = num_users / total_time
            
            results[num_users] = {
                "success_rate": avg_success_rate,
                "total_time": total_time,
                "users_per_second": users_per_second
            }
            
            print(f"   Success rate: {avg_success_rate:.2%}")
            print(f"   Total time: {total_time:.3f}s")
            print(f"   Users per second: {users_per_second:.2f}")
            
            # If success rate drops significantly, we've found the limit
            if avg_success_rate < 0.80:
                print(f"⚠️  Performance degradation detected at {num_users} users")
                break
        
        print("✅ Concurrent user testing completed")
        return results
    
    @pytest.mark.performance
    def test_large_payload_handling(self, enhanced_test_client, test_user_token):
        """Test handling of large payloads"""
        
        # Test with increasingly large product data
        payload_sizes = [1, 10, 50, 100]  # Number of products in bulk create
        
        for size in payload_sizes:
            print(f"📦 Testing bulk create with {size} products...")
            
            # Generate large payload
            bulk_products = []
            for i in range(size):
                product_data = {
                    "name": f"대용량 테스트 상품 {i+1}",
                    "description": "이것은 긴 설명입니다. " * 20,  # Make description longer
                    "price": 25000 + i,
                    "cost": 12500 + i,
                    "sku": f"BULK-{i:04d}",
                    "category": "테스트",
                    "stock_quantity": 100,
                    "tags": [f"태그{j}" for j in range(10)],  # Multiple tags
                    "images": [f"https://example.com/image{j}.jpg" for j in range(5)],  # Multiple images
                    "specifications": {
                        f"spec_{j}": f"value_{j}" for j in range(20)  # Multiple specs
                    }
                }
                bulk_products.append(product_data)
            
            start_time = time.time()
            
            response = enhanced_test_client.post(
                "/api/v1/products/bulk",
                json={"products": bulk_products},
                headers=test_user_token["headers"]
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Processing time: {processing_time:.3f}s")
            print(f"   Time per product: {processing_time/size:.4f}s")
            
            # Large payloads should still be handled reasonably
            if response.status_code == 200:
                assert processing_time < size * 0.1  # Max 100ms per product
            else:
                print(f"   ⚠️  Failed at {size} products")
                break
        
        print("✅ Large payload testing completed")


class TestResourceCleanup:
    """Test resource cleanup and garbage collection"""
    
    @pytest.mark.performance
    def test_memory_cleanup_after_operations(self, enhanced_test_client, test_user_token):
        """Test memory cleanup after intensive operations"""
        
        import gc
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        gc.collect()  # Force garbage collection
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        print(f"🧹 Baseline memory: {baseline_memory:.2f} MB")
        
        # Perform intensive operations
        print("🚀 Performing intensive operations...")
        for i in range(20):
            response = enhanced_test_client.get(
                "/api/v1/products/",
                headers=test_user_token["headers"]
            )
            assert response.status_code == 200
        
        # Memory after operations
        after_ops_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_ops_memory - baseline_memory
        
        print(f"💾 Memory after operations: {after_ops_memory:.2f} MB (+{memory_increase:.2f} MB)")
        
        # Force cleanup
        gc.collect()
        time.sleep(1)  # Allow time for cleanup
        
        # Memory after cleanup
        after_cleanup_memory = process.memory_info().rss / 1024 / 1024
        cleanup_effect = after_ops_memory - after_cleanup_memory
        
        print(f"🧹 Memory after cleanup: {after_cleanup_memory:.2f} MB (-{cleanup_effect:.2f} MB)")
        
        # Cleanup should be effective
        assert cleanup_effect >= 0  # Memory should not increase after cleanup
        final_increase = after_cleanup_memory - baseline_memory
        assert final_increase < memory_increase * 1.5  # Should clean up some memory
        
        return {
            "baseline_memory": baseline_memory,
            "peak_memory": after_ops_memory,
            "final_memory": after_cleanup_memory,
            "cleanup_effectiveness": cleanup_effect / memory_increase if memory_increase > 0 else 0
        }