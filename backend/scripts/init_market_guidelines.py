"""
마켓 가이드라인 초기화 스크립트

기본 마켓플레이스 가이드라인을 데이터베이스에 설정
"""

import sys
import os
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.services.database.database import get_db
from app.models.product_processing import MarketGuideline


def init_market_guidelines():
    """마켓 가이드라인 초기화"""
    
    db = next(get_db())
    
    try:
        # 기존 가이드라인 제거
        db.query(MarketGuideline).delete()
        
        # 쿠팡 가이드라인
        coupang_guideline = MarketGuideline(
            marketplace="coupang",
            image_specs={
                "width": 780,
                "height": 780,
                "format": ["jpg", "png"],
                "max_size_mb": 10,
                "min_size_mb": 0.1,
                "dpi": 72,
                "color_mode": "RGB",
                "aspect_ratio": "1:1",
                "background": "white_preferred"
            },
            naming_rules={
                "max_length": 40,
                "min_length": 10,
                "required_elements": ["제품명"],
                "forbidden_chars": ["♥", "★", "◆", "♦", "♠", "♣"],
                "forbidden_patterns": [r'\d+원', r'무료배송', r'당일배송'],
                "preferred_patterns": ["프리미엄", "고품질", "추천"],
                "case_sensitivity": False
            },
            description_rules={
                "max_length": 2000,
                "min_length": 100,
                "required_sections": ["제품소개", "주요특징"],
                "forbidden_content": ["타 쇼핑몰 언급", "연락처", "외부링크"],
                "html_allowed": True,
                "image_in_description": True
            },
            prohibited_keywords=[
                "최저가", "덤핑", "짝퉁", "가품", "B급", "하자상품",
                "중고", "리퍼", "전시상품"
            ],
            required_fields={
                "brand": True,
                "model_number": False,
                "manufacturer": True,
                "origin_country": True,
                "warranty": False
            },
            guidelines_version="1.0",
            is_active=True,
            created_at=datetime.now()
        )
        
        # 네이버 가이드라인
        naver_guideline = MarketGuideline(
            marketplace="naver",
            image_specs={
                "width": 640,
                "height": 640,
                "format": ["jpg", "png", "gif"],
                "max_size_mb": 20,
                "min_size_mb": 0.1,
                "dpi": 72,
                "color_mode": "RGB",
                "aspect_ratio": ["1:1", "4:3"],
                "background": "any"
            },
            naming_rules={
                "max_length": 50,
                "min_length": 15,
                "required_elements": ["제품명", "브랜드"],
                "forbidden_chars": ["※", "◎", "●", "■"],
                "forbidden_patterns": [r'가짜', r'모조품'],
                "preferred_patterns": ["정품", "국내배송", "브랜드"],
                "case_sensitivity": False
            },
            description_rules={
                "max_length": 3000,
                "min_length": 200,
                "required_sections": ["상품정보", "배송정보", "교환반품"],
                "forbidden_content": ["과장광고", "의료효능"],
                "html_allowed": True,
                "image_in_description": True
            },
            prohibited_keywords=[
                "가짜", "모조", "임의", "복제품", "불법"
            ],
            required_fields={
                "brand": True,
                "model_number": True,
                "manufacturer": True,
                "origin_country": True,
                "warranty": True
            },
            guidelines_version="1.0",
            is_active=True,
            created_at=datetime.now()
        )
        
        # 11번가 가이드라인
        eleventh_guideline = MarketGuideline(
            marketplace="11st",
            image_specs={
                "width": 1000,
                "height": 1000,
                "format": ["jpg", "png"],
                "max_size_mb": 5,
                "min_size_mb": 0.1,
                "dpi": 96,
                "color_mode": "RGB",
                "aspect_ratio": "1:1",
                "background": "white_preferred"
            },
            naming_rules={
                "max_length": 35,
                "min_length": 10,
                "required_elements": ["제품명"],
                "forbidden_chars": ["♣", "♠", "◐", "◑"],
                "forbidden_patterns": [r'복제품', r'불법'],
                "preferred_patterns": ["혜택", "적립", "무료", "빠른"],
                "case_sensitivity": False
            },
            description_rules={
                "max_length": 1500,
                "min_length": 100,
                "required_sections": ["상품설명"],
                "forbidden_content": ["허위정보", "과대광고"],
                "html_allowed": False,
                "image_in_description": False
            },
            prohibited_keywords=[
                "복제품", "불법", "해적판"
            ],
            required_fields={
                "brand": False,
                "model_number": False,
                "manufacturer": False,
                "origin_country": True,
                "warranty": False
            },
            guidelines_version="1.0",
            is_active=True,
            created_at=datetime.now()
        )
        
        # 데이터베이스에 저장
        db.add(coupang_guideline)
        db.add(naver_guideline)
        db.add(eleventh_guideline)
        
        db.commit()
        
        print("✅ 마켓 가이드라인 초기화 완료")
        print("   - 쿠팡 가이드라인 생성")
        print("   - 네이버 가이드라인 생성")
        print("   - 11번가 가이드라인 생성")
        
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_market_guidelines()