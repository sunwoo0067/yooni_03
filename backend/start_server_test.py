"""
서버 시작 및 기본 테스트
"""

import subprocess
import time
import requests
import sys
import os

def start_server():
    """백그라운드에서 FastAPI 서버 시작"""
    print("[INFO] FastAPI 서버 시작 중...")
    
    # 서버 프로세스 시작
    server_process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    
    # 서버 시작 대기
    print("[INFO] 서버 시작 대기 중...")
    time.sleep(5)
    
    # 서버 상태 확인
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("[OK] 서버가 정상적으로 시작되었습니다.")
            print(f"  - PID: {server_process.pid}")
            print(f"  - 상태: {response.json().get('status')}")
            return server_process
        else:
            print(f"[FAIL] 서버 응답 오류: {response.status_code}")
            server_process.terminate()
            return None
    except Exception as e:
        print(f"[FAIL] 서버 연결 실패: {str(e)}")
        server_process.terminate()
        return None


def test_api_routes():
    """API 라우트 테스트"""
    print("\n[INFO] API 라우트 테스트 시작...")
    
    routes_to_test = [
        ("/", "루트"),
        ("/health", "헬스체크"),
        ("/api/v1/status", "API 상태"),
        ("/api/v1/platform-accounts", "플랫폼 계정"),
        ("/api/v1/products", "상품"),
        ("/api/v1/ai/status", "AI 상태"),
        ("/api/v1/dashboard/summary", "대시보드"),
        ("/docs", "Swagger UI"),
        ("/redoc", "ReDoc")
    ]
    
    success_count = 0
    
    for route, description in routes_to_test:
        try:
            response = requests.get(f"http://localhost:8000{route}")
            if response.status_code in [200, 307, 422]:  # 307은 리다이렉트, 422는 파라미터 필요
                print(f"  [OK] {description} ({route}) - {response.status_code}")
                success_count += 1
            else:
                print(f"  [FAIL] {description} ({route}) - {response.status_code}")
        except Exception as e:
            print(f"  [FAIL] {description} ({route}) - 오류: {str(e)}")
    
    print(f"\n총 {len(routes_to_test)}개 라우트 중 {success_count}개 성공")
    
    return success_count == len(routes_to_test)


def check_api_documentation():
    """API 문서 확인"""
    print("\n[INFO] API 문서 확인...")
    
    try:
        # OpenAPI 스키마 가져오기
        response = requests.get("http://localhost:8000/openapi.json")
        if response.status_code == 200:
            openapi_data = response.json()
            paths = openapi_data.get('paths', {})
            
            print(f"[OK] OpenAPI 문서 로드 성공")
            print(f"  - API 버전: {openapi_data.get('info', {}).get('version')}")
            print(f"  - 등록된 경로 수: {len(paths)}")
            
            # 주요 경로 출력
            print("\n등록된 API 경로:")
            for i, path in enumerate(list(paths.keys())[:10], 1):
                print(f"  {i}. {path}")
            
            if len(paths) > 10:
                print(f"  ... 외 {len(paths) - 10}개")
            
            return True
        else:
            print(f"[FAIL] OpenAPI 문서 로드 실패: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FAIL] 오류 발생: {str(e)}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("Yooni 드랍쉬핑 시스템 - 서버 테스트")
    print("="*60)
    
    # 기존 서버가 실행 중인지 확인
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("\n[INFO] 서버가 이미 실행 중입니다.")
            server_process = None
        else:
            server_process = start_server()
    except:
        server_process = start_server()
    
    if server_process or response.status_code == 200:
        # API 라우트 테스트
        test_api_routes()
        
        # API 문서 확인
        check_api_documentation()
        
        # 서버 종료 (테스트용으로 시작한 경우)
        if server_process:
            print("\n[INFO] 테스트 완료. 서버를 종료합니다.")
            server_process.terminate()
            server_process.wait()
    else:
        print("\n[ERROR] 서버를 시작할 수 없습니다.")