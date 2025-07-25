#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
테스트 정리 스크립트
테스트 완료 후 임시 데이터와 로그를 정리합니다.
"""
import os
import shutil
from pathlib import Path

def cleanup_test_environment():
    """테스트 환경 정리"""
    print("테스트 환경 정리 시작...")
    
    # 정리할 항목들
    cleanup_items = [
        "logs/test.log",
        "test_temp/",
        ".env",
        "__pycache__/",
    ]
    
    for item in cleanup_items:
        item_path = Path(item)
        try:
            if item_path.is_file():
                item_path.unlink()
                print(f"✓ 파일 삭제: {item}")
            elif item_path.is_dir():
                shutil.rmtree(item_path)
                print(f"✓ 폴더 삭제: {item}")
        except Exception as e:
            print(f"⚠️ {item} 삭제 실패: {e}")
    
    print("✅ 테스트 환경 정리 완료!")

if __name__ == "__main__":
    cleanup_test_environment()
