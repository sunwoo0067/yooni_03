"""
Yooni 드롭쉬핑 시스템 - 개인 사용자용 메인 애플리케이션 진입점
간소화된 설정을 지원하는 버전
"""

import os
import sys
from pathlib import Path

import uvicorn

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_personal_app():
    """개인 사용자용 앱 인스턴스를 반환"""
    try:
        from backend.configs.environments.personal_simple import app
        return app, "personal"
    except Exception as e:
        print(f"⚠️ 개인 사용자 모드 실행 실패: {e}")
        # 실패 시 기본 simple 모드로 대체
        from backend.configs.environments.main_simple import app  
        return app, "simple (personal 대체)"

# 앱 인스턴스 생성
app, current_mode = get_personal_app()

if __name__ == "__main__":
    print(f"🚀 Yooni 드롭쉬핑 시스템 시작 (모드: {current_mode})")
    print(f"💡 개인 사용자 모드: YOONI_ENV_MODE=personal")
    
    # 개인 사용자용 기본 설정
    host = os.getenv("APP_HOST", "127.0.0.1")  # 외부 접근 차단
    port = int(os.getenv("APP_PORT", "8000"))
    reload = os.getenv("DEBUG", "true").lower() == "true"
    
    uvicorn.run(
        "backend.main_personal:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True,
        workers=1  # 개인 사용자용으로 단일 워커만 사용
    )