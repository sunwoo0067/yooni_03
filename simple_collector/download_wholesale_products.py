"""
도매처 상품 데이터 다운로드
- 엑셀 파일로 전체 상품 데이터 저장
- 마켓플레이스 업로드용 포맷 지원
"""

import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import json

# 프로젝트 루트 경로 추가
sys.path.append(str(Path(__file__).parent))

from database.connection import SessionLocal
from database.models_v2 import WholesaleProduct
from utils.logger import app_logger


def download_all_products(output_dir: str = "downloads"):
    """모든 도매처 상품 다운로드"""
    db = SessionLocal()
    
    try:
        # 출력 디렉토리 생성
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 타임스탬프
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 도매처별 다운로드
        suppliers = ['zentrade', 'ownerclan', 'domeggook', 'domomae']
        
        all_products_data = []
        
        for supplier in suppliers:
            app_logger.info(f"\n{supplier} 상품 추출 중...")
            
            # 상품 조회
            products = db.query(WholesaleProduct).filter(
                WholesaleProduct.supplier == supplier,
                WholesaleProduct.is_active == True
            ).all()
            
            if not products:
                app_logger.warning(f"{supplier}: 상품이 없습니다.")
                continue
            
            app_logger.info(f"{supplier}: {len(products)}개 상품")
            
            # 데이터 변환
            supplier_data = []
            
            for product in products:
                # 기본 정보
                row = {
                    '도매처': supplier,
                    '상품코드': product.product_code,
                    '상품명': product.product_name,
                    '카테고리': product.category,
                    '도매가': product.wholesale_price,
                    '재고수량': product.stock_quantity,
                    '최소주문수량': product.min_order_quantity,
                    '옵션': product.option_name,
                    '등록일': product.created_at.strftime("%Y-%m-%d"),
                    '최종수정일': product.updated_at.strftime("%Y-%m-%d"),
                }
                
                # 추가 정보 (product_info에서 추출)
                if product.product_info:
                    info = product.product_info
                    row.update({
                        '브랜드': info.get('brand', ''),
                        '제조사': info.get('manufacturer', ''),
                        '원산지': info.get('origin', ''),
                        '배송비': info.get('shipping_fee', 0),
                        '배송방법': info.get('shipping_method', ''),
                        '상품설명': info.get('description', '')[:200],  # 200자로 제한
                    })
                
                # 이미지 URL
                if product.images:
                    row['대표이미지'] = product.images[0] if product.images else ''
                    row['추가이미지'] = '|'.join(product.images[1:]) if len(product.images) > 1 else ''
                
                supplier_data.append(row)
                all_products_data.append(row)
            
            # 도매처별 엑셀 저장
            supplier_df = pd.DataFrame(supplier_data)
            supplier_file = output_path / f"{supplier}_products_{timestamp}.xlsx"
            
            with pd.ExcelWriter(supplier_file, engine='openpyxl') as writer:
                supplier_df.to_excel(writer, sheet_name='상품목록', index=False)
                
                # 요약 정보 시트
                summary_data = {
                    '항목': ['총 상품수', '평균 도매가', '최저 도매가', '최고 도매가'],
                    '값': [
                        len(supplier_data),
                        f"{int(supplier_df['도매가'].mean()):,}원",
                        f"{int(supplier_df['도매가'].min()):,}원",
                        f"{int(supplier_df['도매가'].max()):,}원"
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='요약', index=False)
            
            app_logger.info(f"저장됨: {supplier_file}")
        
        # 전체 상품 통합 파일
        if all_products_data:
            all_df = pd.DataFrame(all_products_data)
            all_file = output_path / f"all_wholesale_products_{timestamp}.xlsx"
            
            with pd.ExcelWriter(all_file, engine='openpyxl') as writer:
                # 전체 상품 시트
                all_df.to_excel(writer, sheet_name='전체상품', index=False)
                
                # 도매처별 요약 시트
                summary_by_supplier = all_df.groupby('도매처').agg({
                    '상품코드': 'count',
                    '도매가': ['mean', 'min', 'max']
                }).round(0)
                summary_by_supplier.columns = ['상품수', '평균가', '최저가', '최고가']
                summary_by_supplier.to_excel(writer, sheet_name='도매처별요약')
                
                # 카테고리별 요약 시트
                summary_by_category = all_df.groupby('카테고리').agg({
                    '상품코드': 'count',
                    '도매가': 'mean'
                }).round(0)
                summary_by_category.columns = ['상품수', '평균가']
                summary_by_category.to_excel(writer, sheet_name='카테고리별요약')
            
            app_logger.info(f"\n통합 파일 저장됨: {all_file}")
            app_logger.info(f"총 {len(all_products_data)}개 상품")
        
        # 마켓플레이스 업로드용 포맷
        create_marketplace_format(all_products_data, output_path, timestamp)
        
    except Exception as e:
        app_logger.error(f"다운로드 중 오류: {e}")
        
    finally:
        db.close()


def create_marketplace_format(products_data: list, output_path: Path, timestamp: str):
    """마켓플레이스 업로드용 포맷 생성"""
    
    # 쿠팡 업로드 포맷
    coupang_data = []
    for product in products_data:
        # 쿠팡 필수 필드 매핑
        coupang_row = {
            '상품명': product['상품명'],
            '브랜드': product.get('브랜드', '기타'),
            '제조사': product.get('제조사', '기타'),
            '카테고리': product['카테고리'],
            '판매가': int(product['도매가'] * 1.3),  # 30% 마진
            '원가': product['도매가'],
            '재고수량': product.get('재고수량', 100),
            '최소구매수량': product.get('최소주문수량', 1),
            '배송비': product.get('배송비', 0),
            '대표이미지URL': product.get('대표이미지', ''),
            '추가이미지URL': product.get('추가이미지', ''),
            '상품설명': product.get('상품설명', ''),
            '원산지': product.get('원산지', ''),
            '도매처': product['도매처'],
            '도매처상품코드': product['상품코드']
        }
        coupang_data.append(coupang_row)
    
    if coupang_data:
        coupang_df = pd.DataFrame(coupang_data)
        coupang_file = output_path / f"coupang_upload_format_{timestamp}.xlsx"
        coupang_df.to_excel(coupang_file, index=False)
        app_logger.info(f"\n쿠팡 업로드 포맷 저장됨: {coupang_file}")
    
    # 네이버 스마트스토어 포맷
    naver_data = []
    for product in products_data:
        naver_row = {
            '상품명': product['상품명'],
            '판매가': int(product['도매가'] * 1.3),
            '재고수량': product.get('재고수량', 100),
            '카테고리명': product['카테고리'],
            '브랜드': product.get('브랜드', ''),
            '제조사': product.get('제조사', ''),
            '원산지': product.get('원산지', '한국'),
            '상품주요정보': product.get('상품설명', ''),
            '대표이미지URL': product.get('대표이미지', ''),
            '추가이미지URL': product.get('추가이미지', ''),
            '배송비': product.get('배송비', 0),
            '도매처': product['도매처'],
            '도매처상품코드': product['상품코드']
        }
        naver_data.append(naver_row)
    
    if naver_data:
        naver_df = pd.DataFrame(naver_data)
        naver_file = output_path / f"naver_upload_format_{timestamp}.xlsx"
        naver_df.to_excel(naver_file, index=False)
        app_logger.info(f"네이버 업로드 포맷 저장됨: {naver_file}")


def download_filtered_products(filters: dict, output_file: str = None):
    """필터링된 상품 다운로드"""
    db = SessionLocal()
    
    try:
        query = db.query(WholesaleProduct).filter(
            WholesaleProduct.is_active == True
        )
        
        # 필터 적용
        if filters.get('supplier'):
            query = query.filter(WholesaleProduct.supplier == filters['supplier'])
        
        if filters.get('category'):
            query = query.filter(WholesaleProduct.category == filters['category'])
        
        if filters.get('min_price'):
            query = query.filter(WholesaleProduct.wholesale_price >= filters['min_price'])
        
        if filters.get('max_price'):
            query = query.filter(WholesaleProduct.wholesale_price <= filters['max_price'])
        
        products = query.all()
        
        if not products:
            app_logger.warning("필터 조건에 맞는 상품이 없습니다.")
            return
        
        app_logger.info(f"필터링된 상품: {len(products)}개")
        
        # 데이터 변환 및 저장
        data = []
        for product in products:
            row = {
                '도매처': product.supplier,
                '상품코드': product.product_code,
                '상품명': product.product_name,
                '카테고리': product.category,
                '도매가': product.wholesale_price,
                '재고수량': product.stock_quantity,
                '대표이미지': product.images[0] if product.images else ''
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"filtered_products_{timestamp}.xlsx"
        
        df.to_excel(output_file, index=False)
        app_logger.info(f"저장됨: {output_file}")
        
    except Exception as e:
        app_logger.error(f"필터링 다운로드 중 오류: {e}")
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='도매처 상품 다운로드')
    parser.add_argument('--all', action='store_true', help='전체 상품 다운로드')
    parser.add_argument('--supplier', type=str, help='특정 도매처만')
    parser.add_argument('--category', type=str, help='특정 카테고리만')
    parser.add_argument('--min-price', type=int, help='최소 가격')
    parser.add_argument('--max-price', type=int, help='최대 가격')
    parser.add_argument('--output', type=str, help='출력 파일명')
    
    args = parser.parse_args()
    
    if args.all or not any([args.supplier, args.category, args.min_price, args.max_price]):
        # 전체 다운로드
        download_all_products()
    else:
        # 필터링 다운로드
        filters = {}
        if args.supplier:
            filters['supplier'] = args.supplier
        if args.category:
            filters['category'] = args.category
        if args.min_price:
            filters['min_price'] = args.min_price
        if args.max_price:
            filters['max_price'] = args.max_price
        
        download_filtered_products(filters, args.output)