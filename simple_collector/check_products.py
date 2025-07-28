#!/usr/bin/env python3
"""
데이터베이스의 상품 데이터 확인
"""

import sys
from pathlib import Path
import json

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from database.connection import SessionLocal
from database.models import Product

def check_products():
    """상품 데이터 상세 확인"""
    db = SessionLocal()
    
    try:
        # 전체 상품 수
        total = db.query(Product).count()
        print(f"전체 상품 수: {total}개\n")
        
        # 공급사별로 상품 확인
        suppliers = ['zentrade', 'ownerclan', 'domeggook']
        
        for supplier in suppliers:
            print(f"\n{'='*50}")
            print(f"{supplier.upper()} 상품 목록")
            print(f"{'='*50}")
            
            products = db.query(Product).filter(
                Product.supplier == supplier
            ).order_by(Product.created_at.desc()).limit(5).all()
            
            for i, product in enumerate(products, 1):
                print(f"\n{i}. 상품코드: {product.product_code}")
                print(f"   공급사: {product.supplier}")
                print(f"   생성일: {product.created_at}")
                print(f"   수정일: {product.updated_at}")
                print(f"   상품정보:")
                
                # JSON 정보 출력
                if isinstance(product.product_info, dict):
                    for key, value in product.product_info.items():
                        if key != 'description':  # 설명은 너무 길어서 제외
                            print(f"     - {key}: {value}")
                else:
                    print(f"     {product.product_info}")
                    
            # 해당 공급사 총 상품 수
            count = db.query(Product).filter(
                Product.supplier == supplier
            ).count()
            print(f"\n{supplier} 총 상품 수: {count}개")
            
    finally:
        db.close()

def export_sample_data():
    """샘플 데이터 JSON으로 내보내기"""
    db = SessionLocal()
    
    try:
        print("\n\n샘플 데이터를 sample_products.json으로 내보내는 중...")
        
        sample_data = {}
        suppliers = ['zentrade', 'ownerclan', 'domeggook']
        
        for supplier in suppliers:
            products = db.query(Product).filter(
                Product.supplier == supplier
            ).limit(3).all()
            
            sample_data[supplier] = []
            for p in products:
                sample_data[supplier].append({
                    'product_code': p.product_code,
                    'product_info': p.product_info,
                    'created_at': p.created_at.isoformat(),
                    'updated_at': p.updated_at.isoformat()
                })
        
        with open('sample_products.json', 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
            
        print("샘플 데이터 내보내기 완료!")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_products()
    export_sample_data()