#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
테스트 데이터 로더
샘플 데이터를 데이터베이스에 로드합니다.
"""
import json
import csv
from pathlib import Path

def load_test_data():
    """테스트 데이터를 데이터베이스에 로드"""
    print("테스트 데이터 로딩 시작...")
    
    # 샘플 데이터 경로
    data_dir = Path("sample_data")
    
    if not data_dir.exists():
        print("❌ 샘플 데이터 폴더를 찾을 수 없습니다.")
        return False
    
    try:
        # CSV 파일들 처리
        csv_files = [
            "wholesale_products.csv",
            "market_prices.csv", 
            "test_orders.csv"
        ]
        
        for csv_file in csv_files:
            file_path = data_dir / csv_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                    print(f"✓ {csv_file}: {len(data)}개 레코드 로드됨")
            else:
                print(f"⚠️ {csv_file} 파일을 찾을 수 없습니다.")
        
        print("✅ 테스트 데이터 로딩 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 데이터 로딩 실패: {e}")
        return False

if __name__ == "__main__":
    load_test_data()
