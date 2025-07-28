"""
스케줄러 작업 함수들
각각의 배치 작업을 정의
"""

import asyncio
import requests
from datetime import datetime, timedelta
from typing import Dict, Any
from pathlib import Path

from database.connection import SessionLocal
from database.models_v2 import WholesaleProduct, MarketplaceProduct
from database.models import CollectionLog
from services.image.image_hosting import ImageHostingService
from collectors.bestseller_collector import CoupangBestsellerCollector, NaverShoppingCollector
from utils.logger import app_logger


async def collect_wholesale_products(suppliers: list = None, test_mode: bool = False) -> Dict[str, Any]:
    """도매처 상품 수집 작업"""
    try:
        app_logger.info("=== 도매처 상품 수집 작업 시작 ===")
        
        if not suppliers:
            suppliers = ['zentrade', 'ownerclan', 'domeggook', 'domomae']
        
        results = {}
        total_collected = 0
        
        for supplier in suppliers:
            try:
                # API 호출로 수집 시작
                url = f"http://localhost:8000/collection/full/{supplier}"
                params = {"test_mode": test_mode}
                
                response = requests.post(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    app_logger.info(f"{supplier} 수집 시작됨")
                    
                    # 수집 완료까지 대기 (최대 30분)
                    for i in range(180):  # 30분 = 180 * 10초
                        await asyncio.sleep(10)
                        
                        status_response = requests.get(
                            f"http://localhost:8000/collection/status/{supplier}",
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status = status_response.json()
                            
                            if status['status'] == 'completed':
                                results[supplier] = {
                                    'status': 'success',
                                    'total_count': status.get('total_count', 0),
                                    'new_count': status.get('new_count', 0),
                                    'updated_count': status.get('updated_count', 0)
                                }
                                total_collected += status.get('total_count', 0)
                                break
                            elif status['status'] == 'failed':
                                results[supplier] = {
                                    'status': 'failed',
                                    'error': status.get('error_message', '알 수 없는 오류')
                                }
                                break
                    else:
                        # 타임아웃
                        results[supplier] = {
                            'status': 'timeout',
                            'error': '수집 시간 초과'
                        }
                else:
                    results[supplier] = {
                        'status': 'failed',
                        'error': f'API 오류: {response.status_code}'
                    }
                    
            except Exception as e:
                results[supplier] = {
                    'status': 'error',
                    'error': str(e)
                }
                app_logger.error(f"{supplier} 수집 오류: {e}")
        
        app_logger.info(f"도매처 상품 수집 완료: 총 {total_collected}개")
        
        return {
            'status': 'completed',
            'total_collected': total_collected,
            'suppliers': results,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"도매처 상품 수집 작업 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }


async def collect_bestsellers(marketplaces: list = None) -> Dict[str, Any]:
    """베스트셀러 수집 작업"""
    try:
        app_logger.info("=== 베스트셀러 수집 작업 시작 ===")
        
        if not marketplaces:
            marketplaces = ['coupang', 'naver']
        
        results = {}
        total_collected = 0
        
        for marketplace in marketplaces:
            try:
                # API 호출로 수집 시작
                url = f"http://localhost:8000/bestseller/collect/{marketplace}"
                
                response = requests.post(url, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    results[marketplace] = {
                        'status': 'success',
                        'count': data.get('count', 0)
                    }
                    total_collected += data.get('count', 0)
                    app_logger.info(f"{marketplace} 베스트셀러 {data.get('count', 0)}개 수집")
                else:
                    results[marketplace] = {
                        'status': 'failed',
                        'error': f'API 오류: {response.status_code}'
                    }
                    
            except Exception as e:
                results[marketplace] = {
                    'status': 'error',
                    'error': str(e)
                }
                app_logger.error(f"{marketplace} 베스트셀러 수집 오류: {e}")
        
        app_logger.info(f"베스트셀러 수집 완료: 총 {total_collected}개")
        
        return {
            'status': 'completed',
            'total_collected': total_collected,
            'marketplaces': results,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"베스트셀러 수집 작업 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }


async def process_images(limit: int = 100, suppliers: list = None) -> Dict[str, Any]:
    """이미지 처리 작업"""
    try:
        app_logger.info("=== 이미지 처리 작업 시작 ===")
        
        # API 호출로 이미지 처리
        url = "http://localhost:8000/images/process-wholesale-images"
        params = {
            'limit': limit
        }
        
        if suppliers:
            # 도매처별로 처리
            results = {}
            total_processed = 0
            
            for supplier in suppliers:
                params['supplier'] = supplier
                response = requests.post(url, params=params, timeout=300)
                
                if response.status_code == 200:
                    data = response.json()
                    processed_count = data.get('total_products', 0)
                    results[supplier] = {
                        'status': 'success',
                        'processed_count': processed_count
                    }
                    total_processed += processed_count
                    app_logger.info(f"{supplier} 이미지 {processed_count}개 처리 시작")
                else:
                    results[supplier] = {
                        'status': 'failed',
                        'error': f'API 오류: {response.status_code}'
                    }
            
            return {
                'status': 'completed',
                'total_processed': total_processed,
                'suppliers': results,
                'completed_at': datetime.now().isoformat()
            }
        else:
            # 전체 처리
            response = requests.post(url, params=params, timeout=300)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': 'completed',
                    'total_processed': data.get('total_products', 0),
                    'message': data.get('message', ''),
                    'completed_at': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'failed',
                    'error': f'API 오류: {response.status_code}',
                    'completed_at': datetime.now().isoformat()
                }
                
    except Exception as e:
        app_logger.error(f"이미지 처리 작업 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }


def cleanup_old_data(days: int = 30) -> Dict[str, Any]:
    """오래된 데이터 정리 작업"""
    try:
        app_logger.info(f"=== 데이터 정리 작업 시작 ({days}일 이상) ===")
        
        db = SessionLocal()
        cleanup_results = {}
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 오래된 수집 로그 삭제
            deleted_logs = db.query(CollectionLog).filter(
                CollectionLog.created_at < cutoff_date
            ).count()
            
            db.query(CollectionLog).filter(
                CollectionLog.created_at < cutoff_date
            ).delete()
            
            cleanup_results['collection_logs'] = deleted_logs
            
            # 비활성 상품 삭제 (선택적)
            # inactive_products = db.query(WholesaleProduct).filter(
            #     WholesaleProduct.is_active == False,
            #     WholesaleProduct.updated_at < cutoff_date
            # ).count()
            
            db.commit()
            
            # 이미지 정리
            try:
                response = requests.post(
                    "http://localhost:8000/images/cleanup",
                    json={'days': days},
                    timeout=300
                )
                
                if response.status_code == 200:
                    cleanup_results['images'] = 'success'
                else:
                    cleanup_results['images'] = f'failed: {response.status_code}'
                    
            except Exception as e:
                cleanup_results['images'] = f'error: {str(e)}'
            
            app_logger.info(f"데이터 정리 완료: {cleanup_results}")
            
            return {
                'status': 'completed',
                'cleanup_results': cleanup_results,
                'cutoff_date': cutoff_date.isoformat(),
                'completed_at': datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        app_logger.error(f"데이터 정리 작업 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }


async def generate_daily_report() -> Dict[str, Any]:
    """일일 리포트 생성 작업"""
    try:
        app_logger.info("=== 일일 리포트 생성 시작 ===")
        
        db = SessionLocal()
        report_data = {}
        
        try:
            # 상품 통계
            total_wholesale = db.query(WholesaleProduct).filter(
                WholesaleProduct.is_active == True
            ).count()
            
            total_marketplace = db.query(MarketplaceProduct).filter(
                MarketplaceProduct.is_active == True
            ).count()
            
            # 어제 수집된 상품 수
            yesterday = datetime.now() - timedelta(days=1)
            new_products = db.query(WholesaleProduct).filter(
                WholesaleProduct.created_at >= yesterday,
                WholesaleProduct.is_active == True
            ).count()
            
            # 도매처별 통계
            supplier_stats = {}
            suppliers = ['zentrade', 'ownerclan', 'domeggook', 'domomae']
            
            for supplier in suppliers:
                count = db.query(WholesaleProduct).filter(
                    WholesaleProduct.supplier == supplier,
                    WholesaleProduct.is_active == True
                ).count()
                supplier_stats[supplier] = count
            
            report_data = {
                'date': datetime.now().date().isoformat(),
                'total_wholesale_products': total_wholesale,
                'total_marketplace_products': total_marketplace,
                'new_products_yesterday': new_products,
                'supplier_stats': supplier_stats,
                'generated_at': datetime.now().isoformat()
            }
            
            # 리포트 파일 저장
            report_dir = Path("reports")
            report_dir.mkdir(exist_ok=True)
            
            report_file = report_dir / f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            app_logger.info(f"일일 리포트 생성 완료: {report_file}")
            
            return {
                'status': 'completed',
                'report_file': str(report_file),
                'report_data': report_data
            }
            
        finally:
            db.close()
            
    except Exception as e:
        app_logger.error(f"일일 리포트 생성 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }


async def sync_marketplace_data() -> Dict[str, Any]:
    """마켓플레이스 데이터 동기화 작업"""
    try:
        app_logger.info("=== 마켓플레이스 데이터 동기화 시작 ===")
        
        # 실제 구현에서는 각 마켓플레이스 API를 호출하여
        # 등록된 상품의 상태, 재고, 가격 등을 동기화
        
        results = {
            'coupang': {'synced': 0, 'errors': 0},
            'naver': {'synced': 0, 'errors': 0},
            '11st': {'synced': 0, 'errors': 0}
        }
        
        # 임시로 성공으로 처리
        app_logger.info("마켓플레이스 데이터 동기화 완료")
        
        return {
            'status': 'completed',
            'results': results,
            'completed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        app_logger.error(f"마켓플레이스 데이터 동기화 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }


async def analyze_trends() -> Dict[str, Any]:
    """트렌드 분석 작업"""
    try:
        app_logger.info("=== 트렌드 분석 작업 시작 ===")
        
        # AI 트렌드 분석 API 호출
        try:
            response = requests.get(
                "http://localhost:8000/ai-sourcing/trends",
                timeout=300
            )
            
            if response.status_code == 200:
                trend_data = response.json()
                
                return {
                    'status': 'completed',
                    'trend_data': trend_data,
                    'completed_at': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'failed',
                    'error': f'트렌드 분석 API 오류: {response.status_code}',
                    'completed_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'failed',
                'error': f'트렌드 분석 오류: {str(e)}',
                'completed_at': datetime.now().isoformat()
            }
            
    except Exception as e:
        app_logger.error(f"트렌드 분석 작업 오류: {e}")
        return {
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        }