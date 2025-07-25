"""
Yooni Dropshipping System - 기능 테스트 스위트
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
import httpx
from colorama import init, Fore, Style

init(autoreset=True)

class FunctionalTestRunner:
    """시스템 전체 기능 테스트 실행기"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_v1 = f"{base_url}/api/v1"
        self.test_results = []
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        await self.client.aclose()
        
    def log_test(self, category: str, test_name: str, status: str, message: str = "", duration: float = 0):
        """테스트 결과 로깅"""
        result = {
            "category": category,
            "test_name": test_name,
            "status": status,
            "message": message,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # 콘솔 출력
        if status == "PASS":
            print(f"{Fore.GREEN}[PASS] {category} - {test_name}{Style.RESET_ALL}")
        elif status == "FAIL":
            print(f"{Fore.RED}[FAIL] {category} - {test_name}: {message}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}[WARN] {category} - {test_name}: {message}{Style.RESET_ALL}")
    
    async def test_health_check(self):
        """헬스 체크 테스트"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("시스템", "헬스 체크", "PASS")
                else:
                    self.log_test("시스템", "헬스 체크", "FAIL", f"상태: {data.get('status')}")
            else:
                self.log_test("시스템", "헬스 체크", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("시스템", "헬스 체크", "FAIL", str(e))
    
    async def test_api_status(self):
        """API 상태 테스트"""
        try:
            response = await self.client.get(f"{self.api_v1}/status")
            if response.status_code == 200:
                self.log_test("API", "상태 확인", "PASS")
            else:
                self.log_test("API", "상태 확인", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("API", "상태 확인", "FAIL", str(e))
    
    async def test_platform_accounts(self):
        """플랫폼 계정 관리 테스트"""
        # 플랫폼 계정 목록 조회
        try:
            response = await self.client.get(f"{self.api_v1}/platform-accounts")
            if response.status_code in [200, 401]:  # 인증 없이 401 예상
                self.log_test("플랫폼 계정", "목록 조회 API", "PASS")
            else:
                self.log_test("플랫폼 계정", "목록 조회 API", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("플랫폼 계정", "목록 조회 API", "FAIL", str(e))
    
    async def test_products_api(self):
        """상품 관리 API 테스트"""
        # 상품 목록 조회
        try:
            response = await self.client.get(f"{self.api_v1}/products")
            if response.status_code in [200, 401]:
                self.log_test("상품 관리", "상품 목록 조회", "PASS")
            else:
                self.log_test("상품 관리", "상품 목록 조회", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("상품 관리", "상품 목록 조회", "FAIL", str(e))
        
        # 상품 검색
        try:
            params = {"query": "test", "page": 1, "page_size": 10}
            response = await self.client.get(f"{self.api_v1}/products/search", params=params)
            if response.status_code in [200, 401]:
                self.log_test("상품 관리", "상품 검색", "PASS")
            else:
                self.log_test("상품 관리", "상품 검색", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("상품 관리", "상품 검색", "FAIL", str(e))
    
    async def test_orders_api(self):
        """주문 관리 API 테스트"""
        try:
            response = await self.client.get(f"{self.api_v1}/orders")
            if response.status_code in [200, 401]:
                self.log_test("주문 관리", "주문 목록 조회", "PASS")
            else:
                self.log_test("주문 관리", "주문 목록 조회", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("주문 관리", "주문 목록 조회", "FAIL", str(e))
    
    async def test_wholesalers_api(self):
        """도매처 관리 API 테스트"""
        try:
            response = await self.client.get(f"{self.api_v1}/wholesalers")
            if response.status_code in [200, 401]:
                self.log_test("도매처 관리", "도매처 목록 조회", "PASS")
            else:
                self.log_test("도매처 관리", "도매처 목록 조회", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("도매처 관리", "도매처 목록 조회", "FAIL", str(e))
    
    async def test_analytics_api(self):
        """분석 API 테스트"""
        try:
            response = await self.client.get(f"{self.api_v1}/analytics/dashboard")
            if response.status_code in [200, 401]:
                self.log_test("분석", "대시보드 데이터", "PASS")
            else:
                self.log_test("분석", "대시보드 데이터", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("분석", "대시보드 데이터", "FAIL", str(e))
    
    async def test_ai_services(self):
        """AI 서비스 테스트"""
        try:
            # AI 서비스 상태 확인
            response = await self.client.get(f"{self.api_v1}/ai/status")
            if response.status_code in [200, 401]:
                self.log_test("AI 서비스", "상태 확인", "PASS")
            else:
                self.log_test("AI 서비스", "상태 확인", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("AI 서비스", "상태 확인", "FAIL", str(e))
    
    async def test_database_connection(self):
        """데이터베이스 연결 테스트"""
        try:
            response = await self.client.get(f"{self.api_v1}/health/database")
            if response.status_code == 200:
                self.log_test("데이터베이스", "연결 상태", "PASS")
            else:
                self.log_test("데이터베이스", "연결 상태", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("데이터베이스", "연결 상태", "FAIL", str(e))
    
    async def run_all_tests(self):
        """모든 기능 테스트 실행"""
        print(f"\n{Fore.CYAN}=== Yooni Dropshipping System 기능 테스트 시작 ==={Style.RESET_ALL}\n")
        
        # 시스템 기본 테스트
        await self.test_health_check()
        await self.test_api_status()
        await self.test_database_connection()
        
        # API 기능 테스트
        await self.test_platform_accounts()
        await self.test_products_api()
        await self.test_orders_api()
        await self.test_wholesalers_api()
        await self.test_analytics_api()
        await self.test_ai_services()
        
        # 결과 요약
        self.print_summary()
        
        # 결과 저장
        self.save_results()
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        
        print(f"\n{Fore.CYAN}=== 테스트 결과 요약 ==={Style.RESET_ALL}")
        print(f"총 테스트: {total}")
        print(f"{Fore.GREEN}성공: {passed}{Style.RESET_ALL}")
        print(f"{Fore.RED}실패: {failed}{Style.RESET_ALL}")
        print(f"성공률: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print(f"\n{Fore.RED}실패한 테스트:{Style.RESET_ALL}")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['category']}: {result['test_name']} - {result['message']}")
    
    def save_results(self):
        """테스트 결과를 파일로 저장"""
        filename = f"functional_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "test_run": datetime.now().isoformat(),
                "base_url": self.base_url,
                "results": self.test_results,
                "summary": {
                    "total": len(self.test_results),
                    "passed": len([r for r in self.test_results if r["status"] == "PASS"]),
                    "failed": len([r for r in self.test_results if r["status"] == "FAIL"])
                }
            }, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장됨: {filename}")


async def main():
    """메인 실행 함수"""
    runner = FunctionalTestRunner()
    try:
        await runner.run_all_tests()
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())