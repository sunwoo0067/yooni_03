#!/usr/bin/env python3
"""
전체 상품 자동 수집 스크립트
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database.connection import SessionLocal
from database.models import Product, CollectionLog
from collectors.zentrade_collector_simple import ZentradeCollector
from collectors.ownerclan_collector_simple import OwnerClanCollector
from collectors.domeggook_collector_simple import DomeggookCollector

def collect_all(limit_per_supplier=100):
    """모든 공급사 상품 수집"""
    print(f"전체 상품 수집 시작 (공급사당 {limit_per_supplier}개)")
    print("=" * 50)
    
    # 수집 전 상태
    db = SessionLocal()
    before_total = db.query(Product).count()
    print(f"\n수집 전 총 상품 수: {before_total}개")
    db.close()
    
    # 공급사별 수집
    suppliers = [
        ('zentrade', ZentradeCollector({
            'api_id': 'test_id',
            'api_key': 'test_key',
            'base_url': 'https://www.zentrade.co.kr/shop/proc'
        })),
        ('ownerclan', OwnerClanCollector({
            'username': 'test_user',
            'password': 'test_password',
            'api_url': 'https://api.ownerclan.com/v1/graphql',
            'auth_url': 'https://auth.ownerclan.com/auth'
        })),
        ('domeggook', DomeggookCollector({
            'api_key': 'test_key',
            'base_url': 'https://openapi.domeggook.com'
        }))
    ]
    
    total_collected = 0
    total_new = 0
    total_updated = 0
    
    for supplier_name, collector in suppliers:
        print(f"\n{'='*30}")
        print(f"{supplier_name.upper()} 수집 시작")
        print(f"{'='*30}")
        
        db = SessionLocal()
        
        # 수집 로그 생성
        log = CollectionLog(
            supplier=supplier_name,
            collection_type='full',
            status='running',
            start_time=datetime.now()
        )
        db.add(log)
        db.commit()
        
        try:
            # 테스트 모드 설정
            collector.test_mode = True
            
            # 인증
            if not collector.authenticate():
                print(f"[{supplier_name}] 인증 실패")
                log.status = 'failed'
                log.error_message = '인증 실패'
                continue
                
            print(f"[{supplier_name}] 인증 성공")
            
            # 수집
            count = 0
            new_count = 0
            update_count = 0
            
            for product_data in collector.collect_products():
                count += 1
                
                # 기존 상품 확인
                existing = db.query(Product).filter(
                    Product.product_code == product_data.product_code
                ).first()
                
                if existing:
                    existing.product_info = product_data.product_info
                    existing.updated_at = datetime.now()
                    update_count += 1
                else:
                    new_product = Product(
                        product_code=product_data.product_code,
                        product_info=product_data.product_info,
                        supplier=product_data.supplier
                    )
                    db.add(new_product)
                    new_count += 1
                
                # 진행 상황
                if count % 50 == 0:
                    db.commit()
                    print(f"  {count}개 처리 중...")
                    
                # 제한 확인
                if limit_per_supplier and count >= limit_per_supplier:
                    break
                    
            db.commit()
            
            # 로그 업데이트
            log.end_time = datetime.now()
            log.status = 'completed'
            log.total_count = count
            log.new_count = new_count
            log.updated_count = update_count
            
            duration = (log.end_time - log.start_time).total_seconds()
            print(f"\n[{supplier_name}] 완료!")
            print(f"  - 처리: {count}개")
            print(f"  - 신규: {new_count}개")
            print(f"  - 업데이트: {update_count}개")
            print(f"  - 소요시간: {duration:.1f}초")
            
            total_collected += count
            total_new += new_count
            total_updated += update_count
            
        except Exception as e:
            print(f"[{supplier_name}] 오류 발생: {e}")
            log.status = 'failed'
            log.error_message = str(e)
            log.end_time = datetime.now()
            
        finally:
            db.commit()
            db.close()
            time.sleep(1)  # 잠시 대기
    
    # 수집 후 상태
    db = SessionLocal()
    after_total = db.query(Product).count()
    
    print(f"\n{'='*50}")
    print("전체 수집 완료!")
    print(f"{'='*50}")
    print(f"수집 전 상품 수: {before_total}개")
    print(f"수집 후 상품 수: {after_total}개")
    print(f"\n수집 결과:")
    print(f"  - 총 처리: {total_collected}개")
    print(f"  - 신규 추가: {total_new}개")
    print(f"  - 업데이트: {total_updated}개")
    
    # 공급사별 최종 상태
    print(f"\n공급사별 상품 수:")
    for supplier in ['zentrade', 'ownerclan', 'domeggook']:
        count = db.query(Product).filter(Product.supplier == supplier).count()
        print(f"  - {supplier}: {count}개")
        
    db.close()

if __name__ == "__main__":
    # 각 공급사당 100개씩 수집
    collect_all(limit_per_supplier=100)