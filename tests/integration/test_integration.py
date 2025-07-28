"""
Yooni Dropshipping System - 통합 기능 테스트
백엔드와 프론트엔드의 통합 동작을 테스트
"""
import asyncio
import json
import time
from datetime import datetime
import httpx
import subprocess
import os
from typing import Dict, List, Any

class IntegrationTestRunner:
    """통합 기능 테스트 실행기"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.frontend_url = "http://localhost:3002"
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
        color = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}.get(status, "")
        reset = "\033[0m"
        print(f"{color}[{status}] {category} - {test_name}{': ' + message if message else ''}{reset}")
    
    async def test_backend_health(self):
        """백엔드 서버 상태 확인"""
        try:
            response = await self.client.get(f"{self.backend_url}/health")
            if response.status_code == 200:
                self.log_test("백엔드", "서버 상태", "PASS")
                return True
            else:
                self.log_test("백엔드", "서버 상태", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("백엔드", "서버 상태", "FAIL", f"연결 실패: {str(e)}")
            return False
    
    async def test_frontend_health(self):
        """프론트엔드 서버 상태 확인"""
        try:
            response = await self.client.get(self.frontend_url)
            if response.status_code == 200:
                self.log_test("프론트엔드", "서버 상태", "PASS")
                return True
            else:
                self.log_test("프론트엔드", "서버 상태", "FAIL", f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("프론트엔드", "서버 상태", "FAIL", f"연결 실패: {str(e)}")
            return False
    
    async def test_api_cors(self):
        """CORS 설정 테스트"""
        try:
            headers = {
                "Origin": self.frontend_url,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
            response = await self.client.options(
                f"{self.backend_url}/api/v1/status",
                headers=headers
            )
            
            if response.status_code == 200:
                cors_headers = response.headers.get("access-control-allow-origin")
                if cors_headers:
                    self.log_test("통합", "CORS 설정", "PASS")
                else:
                    self.log_test("통합", "CORS 설정", "WARN", "CORS 헤더 없음")
            else:
                self.log_test("통합", "CORS 설정", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("통합", "CORS 설정", "FAIL", str(e))
    
    async def test_api_response_format(self):
        """API 응답 형식 테스트"""
        try:
            response = await self.client.get(f"{self.backend_url}/api/v1/status")
            if response.status_code == 200:
                data = response.json()
                if "status" in data and "version" in data:
                    self.log_test("API 형식", "응답 구조", "PASS")
                else:
                    self.log_test("API 형식", "응답 구조", "FAIL", "필수 필드 누락")
            else:
                self.log_test("API 형식", "응답 구조", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("API 형식", "응답 구조", "FAIL", str(e))
    
    async def test_database_consistency(self):
        """데이터베이스 일관성 테스트"""
        try:
            # 헬스 체크 엔드포인트를 통한 DB 상태 확인
            response = await self.client.get(f"{self.backend_url}/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("database", {}).get("status") == "connected":
                    self.log_test("데이터베이스", "연결 일관성", "PASS")
                else:
                    self.log_test("데이터베이스", "연결 일관성", "WARN", "DB 상태 확인 불가")
            else:
                self.log_test("데이터베이스", "연결 일관성", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("데이터베이스", "연결 일관성", "FAIL", str(e))
    
    async def test_performance_metrics(self):
        """성능 메트릭 테스트"""
        endpoints = [
            ("/health", "헬스체크", 100),
            ("/api/v1/status", "API 상태", 100),
            ("/api/v1/products", "상품 목록", 500),
        ]
        
        for endpoint, name, threshold_ms in endpoints:
            try:
                start_time = time.time()
                response = await self.client.get(f"{self.backend_url}{endpoint}")
                duration_ms = (time.time() - start_time) * 1000
                
                if response.status_code in [200, 401, 404]:  # 정상 응답 코드
                    if duration_ms < threshold_ms:
                        self.log_test("성능", f"{name} 응답시간", "PASS", f"{duration_ms:.1f}ms")
                    else:
                        self.log_test("성능", f"{name} 응답시간", "WARN", 
                                    f"{duration_ms:.1f}ms (임계값: {threshold_ms}ms)")
                else:
                    self.log_test("성능", f"{name} 응답시간", "FAIL", 
                                f"HTTP {response.status_code}")
            except Exception as e:
                self.log_test("성능", f"{name} 응답시간", "FAIL", str(e))
    
    async def test_error_handling(self):
        """에러 처리 테스트"""
        # 잘못된 엔드포인트
        try:
            response = await self.client.get(f"{self.backend_url}/api/v1/invalid-endpoint")
            if response.status_code == 404:
                self.log_test("에러 처리", "404 처리", "PASS")
            else:
                self.log_test("에러 처리", "404 처리", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("에러 처리", "404 처리", "FAIL", str(e))
        
        # 잘못된 메서드
        try:
            response = await self.client.post(f"{self.backend_url}/health")
            if response.status_code in [405, 404]:  # Method Not Allowed 또는 Not Found
                self.log_test("에러 처리", "메서드 검증", "PASS")
            else:
                self.log_test("에러 처리", "메서드 검증", "FAIL", f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("에러 처리", "메서드 검증", "FAIL", str(e))
    
    async def run_all_tests(self):
        """모든 통합 테스트 실행"""
        print("\n=== Yooni Dropshipping System 통합 기능 테스트 시작 ===\n")
        
        # 서버 상태 확인
        backend_ok = await self.test_backend_health()
        frontend_ok = await self.test_frontend_health()
        
        if not backend_ok:
            print("\n⚠️  백엔드 서버가 실행되지 않았습니다. 서버를 시작하세요.")
        
        if not frontend_ok:
            print("\n⚠️  프론트엔드 서버가 실행되지 않았습니다. 서버를 시작하세요.")
        
        # 통합 테스트 실행
        if backend_ok:
            await self.test_api_cors()
            await self.test_api_response_format()
            await self.test_database_consistency()
            await self.test_performance_metrics()
            await self.test_error_handling()
        
        # 결과 요약
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        warned = len([r for r in self.test_results if r["status"] == "WARN"])
        
        print("\n=== 테스트 결과 요약 ===")
        print(f"총 테스트: {total}")
        print(f"\033[92m성공: {passed}\033[0m")
        print(f"\033[91m실패: {failed}\033[0m")
        print(f"\033[93m경고: {warned}\033[0m")
        if total > 0:
            print(f"성공률: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n실패한 테스트:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['category']}: {result['test_name']} - {result['message']}")
    
    def save_results(self):
        """테스트 결과를 파일로 저장"""
        filename = f"integration_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "test_run": datetime.now().isoformat(),
                "backend_url": self.backend_url,
                "frontend_url": self.frontend_url,
                "results": self.test_results,
                "summary": {
                    "total": len(self.test_results),
                    "passed": len([r for r in self.test_results if r["status"] == "PASS"]),
                    "failed": len([r for r in self.test_results if r["status"] == "FAIL"]),
                    "warned": len([r for r in self.test_results if r["status"] == "WARN"])
                }
            }, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장됨: {filepath}")


async def main():
    """메인 실행 함수"""
    runner = IntegrationTestRunner()
    try:
        await runner.run_all_tests()
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())