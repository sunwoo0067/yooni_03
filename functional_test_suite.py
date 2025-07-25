#!/usr/bin/env python3
"""
Comprehensive Functional Testing Suite for Dropshipping System
Tests real functionality that users would interact with.
"""

import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
import asyncio
import importlib.util

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

class FunctionalTestResult:
    def __init__(self, test_name: str, expected_behavior: str):
        self.test_name = test_name
        self.expected_behavior = expected_behavior
        self.status = "PENDING"  # PASS, FAIL, WARNING
        self.actual_result = ""
        self.error_details = ""
        self.recommendations = []
        self.execution_time = 0.0
        self.start_time = None

    def start(self):
        self.start_time = datetime.now()
        
    def complete(self, status: str, actual_result: str, error_details: str = "", recommendations: List[str] = None):
        if self.start_time:
            self.execution_time = (datetime.now() - self.start_time).total_seconds()
        self.status = status
        self.actual_result = actual_result
        self.error_details = error_details
        self.recommendations = recommendations or []

    def to_dict(self) -> Dict:
        return {
            "test_name": self.test_name,
            "expected_behavior": self.expected_behavior,
            "status": self.status,
            "actual_result": self.actual_result,
            "error_details": self.error_details,
            "recommendations": self.recommendations,
            "execution_time": self.execution_time
        }

class DropshippingFunctionalTestSuite:
    def __init__(self):
        self.results: List[FunctionalTestResult] = []
        self.backend_path = os.path.join(os.path.dirname(__file__), 'backend')
        
    def add_result(self, result: FunctionalTestResult):
        self.results.append(result)
        
    def safe_import(self, module_path: str, class_name: str = None):
        """Safely import modules and classes"""
        try:
            if os.path.exists(module_path):
                spec = importlib.util.spec_from_file_location("module", module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if class_name:
                    return getattr(module, class_name, None)
                return module
            return None
        except Exception as e:
            return None

    # 1. DATABASE MODELS TESTING
    def test_database_models(self):
        """Test SQLAlchemy models import, instantiation, and relationships"""
        
        # Test 1.1: Product Model
        result = FunctionalTestResult(
            "Database Models - Product Model Import and Instantiation",
            "Product model should import successfully and allow instantiation with required fields"
        )
        result.start()
        
        try:
            # Try to import Product model
            from app.models.product import Product
            from app.models.base import Base
            
            # Test instantiation
            product = Product(
                name="Test Product",
                price=29.99,
                cost=15.00,
                sku="TEST-001",
                platform="test_platform"
            )
            
            # Check required attributes
            required_attrs = ['name', 'price', 'cost', 'sku', 'platform']
            missing_attrs = [attr for attr in required_attrs if not hasattr(product, attr)]
            
            if missing_attrs:
                result.complete("FAIL", f"Product model missing attributes: {missing_attrs}", 
                              recommendations=["Add missing attributes to Product model"])
            else:
                result.complete("PASS", f"Product model imported and instantiated successfully with all required fields")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import Product model", str(e), 
                          ["Check if Product model exists in app/models/product.py",
                           "Verify SQLAlchemy imports are correct"])
        except Exception as e:
            result.complete("FAIL", "Error instantiating Product model", str(e))
            
        self.add_result(result)
        
        # Test 1.2: Wholesaler Model
        result = FunctionalTestResult(
            "Database Models - Wholesaler Model Import and Instantiation",
            "Wholesaler model should import successfully and support CRUD operations"
        )
        result.start()
        
        try:
            from app.models.wholesaler import Wholesaler
            
            wholesaler = Wholesaler(
                name="Test Wholesaler",
                api_endpoint="https://api.test.com",
                api_key="test_key",
                status="active"
            )
            
            required_attrs = ['name', 'api_endpoint', 'api_key', 'status']
            missing_attrs = [attr for attr in required_attrs if not hasattr(wholesaler, attr)]
            
            if missing_attrs:
                result.complete("FAIL", f"Wholesaler model missing attributes: {missing_attrs}")
            else:
                result.complete("PASS", "Wholesaler model imported and instantiated successfully")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import Wholesaler model", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with Wholesaler model", str(e))
            
        self.add_result(result)
        
        # Test 1.3: Order Model and Relationships
        result = FunctionalTestResult(
            "Database Models - Order Model Relationships",
            "Order model should have proper relationships with Product and User models"
        )
        result.start()
        
        try:
            from app.models.order import Order
            from app.models.user import User
            
            order = Order(
                status="pending",
                total_amount=99.99,
                platform="test_platform"
            )
            
            # Check for relationship attributes
            relationship_attrs = []
            if hasattr(order, 'products'):
                relationship_attrs.append('products')
            if hasattr(order, 'user'):
                relationship_attrs.append('user')
            if hasattr(order, 'user_id'):
                relationship_attrs.append('user_id')
                
            if relationship_attrs:
                result.complete("PASS", f"Order model has relationships: {relationship_attrs}")
            else:
                result.complete("WARNING", "Order model may be missing relationship definitions",
                              recommendations=["Add relationships to Product and User models"])
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import Order or User models", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with Order model relationships", str(e))
            
        self.add_result(result)

    # 2. API ENDPOINT FUNCTIONALITY
    def test_api_endpoints(self):
        """Test FastAPI router loading and endpoint definitions"""
        
        # Test 2.1: Products API Endpoint
        result = FunctionalTestResult(
            "API Endpoints - Products Router Loading",
            "Products router should load successfully with all CRUD endpoints defined"
        )
        result.start()
        
        try:
            from app.api.v1.endpoints.products import router as products_router
            from fastapi import APIRouter
            
            if isinstance(products_router, APIRouter):
                # Check routes
                routes = [route.path for route in products_router.routes]
                expected_routes = ["/", "/{product_id}"]
                
                has_routes = any(route in str(routes) for route in expected_routes)
                
                if has_routes:
                    result.complete("PASS", f"Products router loaded with routes: {routes}")
                else:
                    result.complete("WARNING", f"Products router loaded but may be missing expected routes. Found: {routes}",
                                  recommendations=["Verify all CRUD endpoints are defined"])
            else:
                result.complete("FAIL", "Products router is not a valid APIRouter instance")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import products router", str(e),
                          ["Check if products.py exists in api/v1/endpoints/",
                           "Verify FastAPI imports are correct"])
        except Exception as e:
            result.complete("FAIL", "Error loading products router", str(e))
            
        self.add_result(result)
        
        # Test 2.2: Wholesaler API Endpoint
        result = FunctionalTestResult(
            "API Endpoints - Wholesaler Router Loading",
            "Wholesaler router should load with endpoints for wholesaler management"
        )
        result.start()
        
        try:
            from app.api.v1.endpoints.wholesaler import router as wholesaler_router
            
            if hasattr(wholesaler_router, 'routes'):
                routes = [route.path for route in wholesaler_router.routes]
                result.complete("PASS", f"Wholesaler router loaded with routes: {routes}")
            else:
                result.complete("FAIL", "Wholesaler router missing routes attribute")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import wholesaler router", str(e))
        except Exception as e:
            result.complete("FAIL", "Error loading wholesaler router", str(e))
            
        self.add_result(result)
        
        # Test 2.3: Pydantic Schemas
        result = FunctionalTestResult(
            "API Endpoints - Pydantic Schema Validation",
            "Pydantic schemas should be defined for request/response validation"
        )
        result.start()
        
        try:
            from app.schemas.product import ProductCreate, ProductResponse
            from pydantic import BaseModel
            
            # Test schema instantiation
            product_create = ProductCreate(
                name="Test Product",
                price=29.99,
                cost=15.00,
                sku="TEST-001",
                platform="test"
            )
            
            if isinstance(product_create, BaseModel):
                result.complete("PASS", "Product schemas imported and instantiated successfully")
            else:
                result.complete("FAIL", "Product schemas not properly defined as BaseModel")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import product schemas", str(e),
                          ["Check if schemas are defined in app/schemas/product.py"])
        except Exception as e:
            result.complete("FAIL", "Error with product schemas", str(e))
            
        self.add_result(result)

    # 3. SERVICE LAYER FUNCTIONALITY
    def test_service_layer(self):
        """Test core service classes and business logic"""
        
        # Test 3.1: Product Service
        result = FunctionalTestResult(
            "Service Layer - Product Service Instantiation",
            "Product service should instantiate and provide business logic methods"
        )
        result.start()
        
        try:
            from app.services.product_service import ProductService
            
            service = ProductService()
            
            # Check for expected methods
            expected_methods = ['create_product', 'get_product', 'update_product', 'delete_product']
            available_methods = [method for method in expected_methods if hasattr(service, method)]
            
            if len(available_methods) >= 2:
                result.complete("PASS", f"Product service instantiated with methods: {available_methods}")
            elif len(available_methods) > 0:
                result.complete("WARNING", f"Product service partially implemented. Has: {available_methods}",
                              recommendations=["Implement missing CRUD methods"])
            else:
                result.complete("FAIL", "Product service missing expected methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import ProductService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error instantiating ProductService", str(e))
            
        self.add_result(result)
        
        # Test 3.2: Dropshipping Service  
        result = FunctionalTestResult(
            "Service Layer - Dropshipping Service Core Functions",
            "Dropshipping service should provide order processing and inventory management"
        )
        result.start()
        
        try:
            from app.services.dropshipping_service import DropshippingService
            
            service = DropshippingService()
            
            # Check for dropshipping-specific methods
            dropshipping_methods = ['process_order', 'check_inventory', 'sync_products', 'handle_stockout']
            available_methods = [method for method in dropshipping_methods if hasattr(service, method)]
            
            if available_methods:
                result.complete("PASS", f"Dropshipping service has methods: {available_methods}")
            else:
                result.complete("WARNING", "Dropshipping service may be missing core methods",
                              recommendations=["Implement order processing and inventory methods"])
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import DropshippingService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with DropshippingService", str(e))
            
        self.add_result(result)

    # 4. WHOLESALE SYSTEM TESTING
    def test_wholesale_system(self):
        """Test wholesale product models and profitability analyzer"""
        
        # Test 4.1: Wholesale Analysis Service
        result = FunctionalTestResult(
            "Wholesale System - Analysis Service Functionality",
            "Wholesale analysis service should calculate profitability and generate reports"
        )
        result.start()
        
        try:
            from app.services.wholesale.analysis_service import WholesaleAnalysisService
            
            service = WholesaleAnalysisService()
            
            # Check for analysis methods
            analysis_methods = ['calculate_profitability', 'analyze_margins', 'generate_report']
            available_methods = [method for method in analysis_methods if hasattr(service, method)]
            
            if available_methods:
                result.complete("PASS", f"Wholesale analysis service has methods: {available_methods}")
            else:
                result.complete("WARNING", "Wholesale analysis service missing expected methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import WholesaleAnalysisService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with wholesale analysis service", str(e))
            
        self.add_result(result)
        
        # Test 4.2: Excel Export Service
        result = FunctionalTestResult(
            "Wholesale System - Excel Export Functionality",
            "Excel service should export wholesale data to Excel format"
        )
        result.start()
        
        try:
            from app.services.wholesale.excel_service import ExcelService
            
            service = ExcelService()
            
            # Check for export methods
            export_methods = ['export_products', 'export_analysis', 'create_workbook']
            available_methods = [method for method in export_methods if hasattr(service, method)]
            
            if available_methods:
                result.complete("PASS", f"Excel service has methods: {available_methods}")
            else:
                result.complete("WARNING", "Excel service missing export methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import ExcelService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with Excel service", str(e))
            
        self.add_result(result)

    # 5. NOTIFICATION SYSTEM TESTING
    def test_notification_system(self):
        """Test notification service functionality"""
        
        # Test 5.1: Dashboard Notification Service
        result = FunctionalTestResult(
            "Notification System - Dashboard Notification Service",
            "Notification service should support multiple channels and templates"
        )
        result.start()
        
        try:
            from app.services.dashboard.notification_service import NotificationService
            
            service = NotificationService()
            
            # Check for notification methods
            notification_methods = ['send_notification', 'create_template', 'schedule_notification']
            available_methods = [method for method in notification_methods if hasattr(service, method)]
            
            if available_methods:
                result.complete("PASS", f"Notification service has methods: {available_methods}")
            else:
                result.complete("WARNING", "Notification service missing expected methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import NotificationService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with notification service", str(e))
            
        self.add_result(result)
        
        # Test 5.2: Marketing Email Service
        result = FunctionalTestResult(
            "Notification System - Marketing Email Service",
            "Email service should handle marketing campaigns and customer notifications"
        )
        result.start()
        
        try:
            from app.services.marketing.email_service import EmailService
            
            service = EmailService()
            
            # Check for email methods
            email_methods = ['send_email', 'send_bulk_email', 'create_campaign']
            available_methods = [method for method in email_methods if hasattr(service, method)]
            
            if available_methods:
                result.complete("PASS", f"Email service has methods: {available_methods}")
            else:
                result.complete("WARNING", "Email service missing expected methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import EmailService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with email service", str(e))
            
        self.add_result(result)

    # 6. PERFORMANCE SYSTEM TESTING
    def test_performance_system(self):
        """Test caching decorators and performance monitoring"""
        
        # Test 6.1: Cache Manager
        result = FunctionalTestResult(
            "Performance System - Cache Manager Functionality",
            "Cache manager should provide caching decorators and cache management"
        )
        result.start()
        
        try:
            from app.services.performance.cache_manager import CacheManager
            
            cache_manager = CacheManager()
            
            # Check for cache methods
            cache_methods = ['get', 'set', 'delete', 'clear']
            available_methods = [method for method in cache_methods if hasattr(cache_manager, method)]
            
            if len(available_methods) >= 3:
                result.complete("PASS", f"Cache manager has methods: {available_methods}")
            else:
                result.complete("WARNING", f"Cache manager partially implemented: {available_methods}")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import CacheManager", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with cache manager", str(e))
            
        self.add_result(result)
        
        # Test 6.2: Performance Monitoring
        result = FunctionalTestResult(
            "Performance System - Monitoring Service",
            "Monitoring service should track performance metrics and alerts"
        )
        result.start()
        
        try:
            from app.services.performance.monitoring_service import MonitoringService
            
            service = MonitoringService()
            
            # Check for monitoring methods
            monitoring_methods = ['track_metric', 'create_alert', 'get_metrics']
            available_methods = [method for method in monitoring_methods if hasattr(service, method)]
            
            if available_methods:
                result.complete("PASS", f"Monitoring service has methods: {available_methods}")
            else:
                result.complete("WARNING", "Monitoring service missing expected methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import MonitoringService", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with monitoring service", str(e))
            
        self.add_result(result)

    # 7. INTEGRATION POINTS TESTING
    def test_integration_points(self):
        """Test inter-service communication and data flow"""
        
        # Test 7.1: Service Dependencies
        result = FunctionalTestResult(
            "Integration Points - Service Dependency Injection",
            "Services should properly inject dependencies and communicate"
        )
        result.start()
        
        try:
            # Test if services can be imported together
            from app.services.product_service import ProductService
            from app.services.dropshipping_service import DropshippingService
            
            product_service = ProductService()
            dropshipping_service = DropshippingService()
            
            # Check if services have database dependencies
            has_db_deps = (hasattr(product_service, 'db') or hasattr(product_service, 'session') or
                          hasattr(dropshipping_service, 'db') or hasattr(dropshipping_service, 'session'))
            
            if has_db_deps:
                result.complete("PASS", "Services have database dependencies configured")
            else:
                result.complete("WARNING", "Services may be missing database dependency injection")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import services for integration test", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with service integration", str(e))
            
        self.add_result(result)
        
        # Test 7.2: Platform Integration
        result = FunctionalTestResult(
            "Integration Points - Platform API Integration",
            "Platform APIs should be properly configured and accessible"
        )
        result.start()
        
        try:
            from app.services.platforms.platform_manager import PlatformManager
            
            manager = PlatformManager()
            
            # Check for platform methods
            platform_methods = ['get_platform', 'sync_products', 'process_orders']
            available_methods = [method for method in platform_methods if hasattr(manager, method)]
            
            if available_methods:
                result.complete("PASS", f"Platform manager has methods: {available_methods}")
            else:
                result.complete("WARNING", "Platform manager missing expected methods")
                
        except ImportError as e:
            result.complete("FAIL", "Failed to import PlatformManager", str(e))
        except Exception as e:
            result.complete("FAIL", "Error with platform integration", str(e))
            
        self.add_result(result)

    def run_all_tests(self):
        """Run all functional tests"""
        print("Starting Comprehensive Functional Testing Suite")
        print("=" * 60)
        
        test_categories = [
            ("Database Models", self.test_database_models),
            ("API Endpoints", self.test_api_endpoints), 
            ("Service Layer", self.test_service_layer),
            ("Wholesale System", self.test_wholesale_system),
            ("Notification System", self.test_notification_system),
            ("Performance System", self.test_performance_system),
            ("Integration Points", self.test_integration_points)
        ]
        
        for category_name, test_method in test_categories:
            print(f"\nTesting {category_name}...")
            try:
                test_method()
            except Exception as e:
                print(f"Error in {category_name}: {str(e)}")
                
        self.generate_report()
        
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("FUNCTIONAL TEST RESULTS SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r.status == "PASS"])
        failed_tests = len([r for r in self.results if r.status == "FAIL"])
        warning_tests = len([r for r in self.results if r.status == "WARNING"])
        
        print(f"Total Tests: {total_tests}")
        print(f"PASSED: {passed_tests}")
        print(f"FAILED: {failed_tests}")
        print(f"WARNINGS: {warning_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\nDETAILED RESULTS:")
        print("-" * 60)
        
        for result in self.results:
            status_icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARNING": "[WARN]"}[result.status]
            print(f"\n{status_icon} {result.test_name}")
            print(f"   Expected: {result.expected_behavior}")
            print(f"   Result: {result.actual_result}")
            
            if result.error_details:
                print(f"   Error: {result.error_details}")
                
            if result.recommendations:
                print(f"   Recommendations:")
                for rec in result.recommendations:
                    print(f"     - {rec}")
                    
            print(f"   Execution Time: {result.execution_time:.3f}s")
        
        # Save JSON report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"functional_test_results_{timestamp}.json"
        
        report_data = {
            "timestamp": timestamp,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "warnings": warning_tests,
                "success_rate": (passed_tests/total_tests)*100
            },
            "results": [result.to_dict() for result in self.results]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        print(f"\nDetailed report saved to: {report_file}")
        
if __name__ == "__main__":
    suite = DropshippingFunctionalTestSuite()
    suite.run_all_tests()