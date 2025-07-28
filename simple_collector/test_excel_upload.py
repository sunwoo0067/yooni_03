#!/usr/bin/env python3
"""
엑셀 업로드 기능 테스트
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# 현재 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from processors.excel_processor import ExcelProcessor
from database.connection import SessionLocal
from database.models import Product, ExcelUpload
from utils.logger import app_logger

def create_test_excel_files():
    """테스트용 엑셀 파일 생성"""
    print("=== 테스트용 엑셀 파일 생성 ===")
    
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    
    test_files = []
    
    # 1. 젠트레이드 테스트 파일
    zentrade_data = pd.DataFrame([
        {
            '상품코드': 'ZT_EXCEL_001',
            '상품명': '엑셀 업로드 테스트 상품 1',
            '가격': 20000,
            '공급가': 15000,
            '카테고리': '의류/남성의류',
            '브랜드': '엑셀브랜드',
            '모델명': 'EXCEL-001',
            '설명': '엑셀에서 업로드한 첫 번째 상품',
            '재고': 150,
            '배송비': 3000,
            '반품비': 3000
        },
        {
            '상품코드': 'ZT_EXCEL_002',
            '상품명': '엑셀 업로드 테스트 상품 2',
            '가격': 35000,
            '공급가': 28000,
            '카테고리': '전자제품/액세서리',
            '브랜드': '엑셀브랜드',
            '모델명': 'EXCEL-002',
            '설명': '엑셀에서 업로드한 두 번째 상품',
            '재고': 80,
            '배송비': 0,
            '반품비': 3000
        }
    ])
    
    zentrade_file = upload_dir / 'test_zentrade.xlsx'
    zentrade_data.to_excel(zentrade_file, index=False)
    test_files.append(('zentrade', zentrade_file))
    print(f"[OK] 젠트레이드 테스트 파일 생성: {zentrade_file}")
    
    # 2. 오너클랜 테스트 파일
    ownerclan_data = pd.DataFrame([
        {
            '상품코드': 'OC_EXCEL_001',
            '상품명': '오너클랜 엑셀 테스트 상품',
            '가격': 45000,
            '공급가': 35000,
            '카테고리': '패션/여성의류',
            '브랜드명': '오너엑셀',
            '재고수량': 250,
            '상품상태': 'active',
            '옵션': '[{"name":"사이즈","values":["S","M","L"]},{"name":"색상","values":["블랙","네이비"]}]',
            '설명': '오너클랜 엑셀 업로드 테스트'
        }
    ])
    
    ownerclan_file = upload_dir / 'test_ownerclan.xlsx'
    ownerclan_data.to_excel(ownerclan_file, index=False)
    test_files.append(('ownerclan', ownerclan_file))
    print(f"[OK] 오너클랜 테스트 파일 생성: {ownerclan_file}")
    
    # 3. 도매꾹 테스트 파일
    domeggook_data = pd.DataFrame([
        {
            '상품코드': 'DG_EXCEL_001',
            '상품명': '도매꾹 엑셀 테스트 상품 1',
            '공급가': 12000,
            '소비자가': 20000,
            '카테고리코드': '02_01_00_00_00',
            '카테고리': '가방',
            '벤더코드': 'V_EXCEL_01',
            '최소주문수량': 10,
            '재고': 500,
            '설명': '도매꾹 엑셀 업로드 테스트 상품'
        },
        {
            '상품코드': 'DG_EXCEL_002',
            '상품명': '도매꾹 엑셀 테스트 상품 2',
            '공급가': 8000,
            '소비자가': 15000,
            '카테고리코드': '02_02_00_00_00',
            '카테고리': '액세서리',
            '벤더코드': 'V_EXCEL_02',
            '최소주문수량': 5,
            '재고': 300,
            '설명': '도매꾹 두 번째 테스트 상품'
        }
    ])
    
    domeggook_file = upload_dir / 'test_domeggook.xlsx'
    domeggook_data.to_excel(domeggook_file, index=False)
    test_files.append(('domeggook', domeggook_file))
    print(f"[OK] 도매꾹 테스트 파일 생성: {domeggook_file}")
    
    return test_files

def test_excel_processing(test_files):
    """엑셀 파일 처리 테스트"""
    print("\n=== 엑셀 파일 처리 테스트 ===")
    
    processor = ExcelProcessor()
    results = []
    
    for supplier, file_path in test_files:
        print(f"\n### {supplier} 엑셀 처리 ###")
        
        result = processor.process_excel_file(
            file_path=str(file_path),
            supplier=supplier,
            file_name=file_path.name
        )
        
        results.append(result)
        
        # 결과 출력
        if result['success']:
            print(f"[OK] 처리 완료")
            print(f"  - 총 행수: {result['total_rows']}")
            print(f"  - 처리된 행: {result['processed_rows']}")
            print(f"  - 신규 상품: {result['new_products']}")
            print(f"  - 업데이트: {result['updated_products']}")
            print(f"  - 오류 행: {result['error_rows']}")
        else:
            print(f"[FAIL] 처리 실패")
            print(f"  - 오류: {result['errors']}")
    
    return results

def test_template_generation():
    """템플릿 생성 테스트"""
    print("\n=== 템플릿 생성 테스트 ===")
    
    processor = ExcelProcessor()
    template_dir = Path("uploads/templates")
    template_dir.mkdir(exist_ok=True)
    
    suppliers = ['zentrade', 'ownerclan', 'domeggook', 'default']
    
    for supplier in suppliers:
        try:
            template_df = processor.get_template(supplier)
            template_file = template_dir / f"{supplier}_template.xlsx"
            template_df.to_excel(template_file, index=False)
            print(f"[OK] {supplier} 템플릿 생성: {template_file}")
            print(f"  - 컬럼: {', '.join(template_df.columns)}")
        except Exception as e:
            print(f"[FAIL] {supplier} 템플릿 생성 실패: {e}")

def check_database_results():
    """데이터베이스 결과 확인"""
    print("\n=== 데이터베이스 결과 확인 ===")
    
    db = SessionLocal()
    
    try:
        # 업로드 기록 확인
        uploads = db.query(ExcelUpload).order_by(ExcelUpload.upload_time.desc()).limit(5).all()
        print(f"\n최근 업로드 기록 ({len(uploads)}개):")
        for upload in uploads:
            print(f"  - [{upload.supplier}] {upload.filename}")
            print(f"    상태: {upload.status}, 처리: {upload.processed_rows}/{upload.total_rows}")
            
        # 엑셀로 업로드된 상품 확인
        excel_products = db.query(Product).filter(
            Product.product_info['source'].astext == 'excel_upload'
        ).all()
        
        print(f"\n엑셀로 업로드된 상품 ({len(excel_products)}개):")
        for product in excel_products[:5]:  # 처음 5개만
            info = product.product_info
            print(f"  - [{product.supplier}] {product.product_code}: {info.get('product_name', 'N/A')}")
            
        # 공급사별 통계
        print("\n공급사별 엑셀 업로드 상품 수:")
        for supplier in ['zentrade', 'ownerclan', 'domeggook']:
            count = db.query(Product).filter(
                Product.supplier == supplier,
                Product.product_info['source'].astext == 'excel_upload'
            ).count()
            print(f"  - {supplier}: {count}개")
            
    except Exception as e:
        print(f"[ERROR] 데이터베이스 확인 중 오류: {e}")
        
    finally:
        db.close()

def test_error_handling():
    """오류 처리 테스트"""
    print("\n=== 오류 처리 테스트 ===")
    
    processor = ExcelProcessor()
    
    # 1. 잘못된 형식의 파일
    print("\n1. 잘못된 데이터 테스트")
    bad_data = pd.DataFrame([
        {
            '잘못된컬럼': 'TEST001',
            '상품명': '테스트 상품'
        }
    ])
    
    bad_file = Path("uploads/bad_data.xlsx")
    bad_data.to_excel(bad_file, index=False)
    
    result = processor.process_excel_file(
        file_path=str(bad_file),
        supplier='zentrade',
        file_name='bad_data.xlsx'
    )
    
    print(f"  - 성공 여부: {result['success']}")
    print(f"  - 오류 수: {result['error_rows']}")
    print(f"  - 오류 메시지: {result['errors'][:2] if result['errors'] else 'None'}")
    
    # 정리
    bad_file.unlink()

def main():
    """메인 테스트 함수"""
    print("엑셀 업로드 기능 통합 테스트")
    print("=" * 50)
    
    # 1. 테스트 파일 생성
    test_files = create_test_excel_files()
    
    # 2. 엑셀 처리 테스트
    results = test_excel_processing(test_files)
    
    # 3. 템플릿 생성 테스트
    test_template_generation()
    
    # 4. 데이터베이스 결과 확인
    check_database_results()
    
    # 5. 오류 처리 테스트
    test_error_handling()
    
    print("\n" + "=" * 50)
    print("[SUCCESS] 엑셀 업로드 테스트 완료!")
    
    # 성공/실패 통계
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count
    
    print(f"\n테스트 결과:")
    print(f"- 성공: {success_count}개")
    print(f"- 실패: {fail_count}개")

if __name__ == "__main__":
    main()