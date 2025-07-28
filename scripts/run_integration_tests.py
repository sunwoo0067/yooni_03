#!/usr/bin/env python3
"""
드랍쉬핑 자동화 시스템 통합 테스트 실행 스크립트
"""

import asyncio
import sys
import os
import argparse
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 디렉토리를 파이썬 패스에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.test_integration import DropshippingSystemTest
from src.monitoring.telegram_notifier import TelegramNotifier
from src.config.settings import get_settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class TestRunner:
    """통합 테스트 실행기"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.test_suite = None
        self.notifier = None
        self.start_time = None
        self.end_time = None
        
    async def setup(self):
        """테스트 환경 설정"""
        logger.info("=== 통합 테스트 환경 설정 시작 ===")
        
        # 설정 로드
        settings = get_settings()
        
        # 텔레그램 알림 설정 (선택사항)
        if settings.get('telegram_bot_token') and settings.get('telegram_chat_id'):
            self.notifier = TelegramNotifier(
                settings['telegram_bot_token'],
                settings['telegram_chat_id']
            )
        
        # 테스트 스위트 초기화
        self.test_suite = DropshippingSystemTest()
        await self.test_suite.setup()
        
        logger.info("✅ 테스트 환경 설정 완료")
    
    async def run_all_tests(self):
        """전체 테스트 실행"""
        self.start_time = datetime.now()
        
        try:
            logger.info("=== 전체 통합 테스트 시작 ===")
            
            if self.notifier:
                await self.notifier.send_message("🧪 드랍쉬핑 시스템 통합 테스트를 시작합니다.")
            
            # 1. 기본 워크플로우 테스트
            await self.test_suite.test_complete_workflow()
            
            # 2. 예외 상황 테스트
            await self.test_suite.test_exception_cases()
            
            # 3. 성능 부하 테스트
            await self.test_suite.test_performance_load()
            
            # 4. 보안 테스트
            await self.test_suite.test_security_measures()
            
            self.end_time = datetime.now()
            
            # 테스트 결과 분석
            await self.analyze_results()
            
            logger.info("=== 모든 통합 테스트 완료 ===")
            
        except Exception as e:
            logger.error(f"통합 테스트 실행 중 오류 발생: {str(e)}")
            
            if self.notifier:
                await self.notifier.send_alert(
                    'critical',
                    '통합 테스트 실패',
                    f"오류: {str(e)}"
                )
            
            raise
    
    async def run_smoke_tests(self):
        """스모크 테스트 실행 (핵심 기능만)"""
        logger.info("=== 스모크 테스트 시작 ===")
        
        try:
            # 기본 연결 테스트
            await self.test_basic_connectivity()
            
            # 핵심 API 테스트
            await self.test_core_apis()
            
            # 데이터베이스 연결 테스트
            await self.test_database_connectivity()
            
            logger.info("✅ 스모크 테스트 완료")
            
        except Exception as e:
            logger.error(f"스모크 테스트 실패: {str(e)}")
            raise
    
    async def test_basic_connectivity(self):
        """기본 연결성 테스트"""
        logger.info("기본 연결성 테스트 중...")
        
        # 웹 서버 상태 확인
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/health') as response:
                    assert response.status == 200
                    logger.info("✅ 웹 서버 연결 성공")
        except Exception as e:
            logger.error(f"❌ 웹 서버 연결 실패: {str(e)}")
            raise
    
    async def test_core_apis(self):
        """핵심 API 테스트"""
        logger.info("핵심 API 테스트 중...")
        
        # API 엔드포인트 테스트
        core_apis = [
            '/api/v1/products/collect',
            '/api/v1/ai/analyze',
            '/api/v1/marketplace/register',
            '/api/v1/orders/monitor'
        ]
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for api_endpoint in core_apis:
                try:
                    async with session.get(f'http://localhost:8000{api_endpoint}') as response:
                        # 401(인증 필요)이나 200(성공)이면 API가 살아있음
                        assert response.status in [200, 401]
                        logger.info(f"✅ API {api_endpoint} 응답 정상")
                except Exception as e:
                    logger.error(f"❌ API {api_endpoint} 테스트 실패: {str(e)}")
                    raise
    
    async def test_database_connectivity(self):
        """데이터베이스 연결 테스트"""
        logger.info("데이터베이스 연결 테스트 중...")
        
        try:
            from src.database.db_manager import DatabaseManager
            
            db = DatabaseManager()
            result = await db.execute_query("SELECT 1 as test")
            assert result is not None
            
            logger.info("✅ 데이터베이스 연결 성공")
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {str(e)}")
            raise
    
    async def analyze_results(self):
        """테스트 결과 분석"""
        if not self.start_time or not self.end_time:
            return
        
        duration = self.end_time - self.start_time
        
        # 결과 요약
        results_summary = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'test_results': self.test_suite.test_results,
            'overall_status': self.determine_overall_status()
        }
        
        # 결과 출력
        self.print_results_summary(results_summary)
        
        # 결과 파일 저장
        await self.save_results(results_summary)
        
        # 알림 발송
        if self.notifier:
            await self.send_results_notification(results_summary)
    
    def determine_overall_status(self):
        """전체 테스트 상태 결정"""
        if not self.test_suite.test_results:
            return 'UNKNOWN'
        
        failed_tests = [
            name for name, result in self.test_suite.test_results.items()
            if result != 'PASS'
        ]
        
        if not failed_tests:
            return 'ALL_PASS'
        elif len(failed_tests) <= 2:
            return 'MOSTLY_PASS'
        else:
            return 'MULTIPLE_FAILURES'
    
    def print_results_summary(self, results):
        """결과 요약 출력"""
        print("\n" + "="*60)
        print("           통합 테스트 결과 요약")
        print("="*60)
        
        print(f"시작 시간: {results['start_time']}")
        print(f"종료 시간: {results['end_time']}")
        print(f"실행 시간: {results['duration_seconds']:.2f}초")
        print(f"전체 상태: {results['overall_status']}")
        
        print("\n테스트별 결과:")
        for test_name, result in results['test_results'].items():
            status_icon = "✅" if result == "PASS" else "❌"
            print(f"  {status_icon} {test_name}: {result}")
        
        print("="*60)
    
    async def save_results(self, results):
        """결과를 파일로 저장"""
        import json
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"test_results_{timestamp}.json"
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"테스트 결과가 {results_file}에 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"결과 저장 실패: {str(e)}")
    
    async def send_results_notification(self, results):
        """결과 알림 발송"""
        if not self.notifier:
            return
        
        status_emoji = {
            'ALL_PASS': '✅',
            'MOSTLY_PASS': '⚠️',
            'MULTIPLE_FAILURES': '❌',
            'UNKNOWN': '❓'
        }
        
        emoji = status_emoji.get(results['overall_status'], '❓')
        
        message = f"""
{emoji} **통합 테스트 완료**

**전체 상태**: {results['overall_status']}
**실행 시간**: {results['duration_seconds']:.1f}초

**테스트 결과**:
"""
        
        for test_name, result in results['test_results'].items():
            result_emoji = "✅" if result == "PASS" else "❌"
            message += f"{result_emoji} {test_name}\n"
        
        await self.notifier.send_message(message)


async def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='드랍쉬핑 시스템 통합 테스트')
    parser.add_argument(
        '--mode',
        choices=['full', 'smoke'],
        default='full',
        help='테스트 모드 (full: 전체 테스트, smoke: 스모크 테스트)'
    )
    parser.add_argument(
        '--config',
        help='설정 파일 경로'
    )
    parser.add_argument(
        '--notify',
        action='store_true',
        help='텔레그램 알림 활성화'
    )
    
    args = parser.parse_args()
    
    # 테스트 러너 초기화
    test_runner = TestRunner()
    
    try:
        # 설정
        await test_runner.setup()
        
        # 테스트 실행
        if args.mode == 'smoke':
            await test_runner.run_smoke_tests()
        else:
            await test_runner.run_all_tests()
        
        logger.info("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        logger.error(f"💥 테스트 실행 실패: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # 이벤트 루프 실행
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("사용자에 의해 테스트가 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        sys.exit(1)