import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import pandas as pd

from database.connection import SessionLocal
from database.models import Product, ExcelUpload
from utils.logger import app_logger

class ExcelProcessor:
    """엑셀 파일 업로드 및 처리"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.logger = app_logger
        
    def process_excel_file(self, 
                         file_path: str, 
                         supplier: str,
                         file_name: str = None) -> Dict[str, Any]:
        """엑셀 파일 처리"""
        
        result = {
            'success': False,
            'file_name': file_name or os.path.basename(file_path),
            'supplier': supplier,
            'total_rows': 0,
            'processed_rows': 0,
            'error_rows': 0,
            'new_products': 0,
            'updated_products': 0,
            'errors': []
        }
        
        db = SessionLocal()
        
        try:
            # 엑셀 파일 읽기
            self.logger.info(f"엑셀 파일 읽기 시작: {file_path}")
            df = self._read_excel_file(file_path)
            
            if df is None or df.empty:
                result['errors'].append("엑셀 파일이 비어있거나 읽을 수 없습니다")
                return result
                
            result['total_rows'] = len(df)
            
            # 업로드 기록 생성
            upload_record = ExcelUpload(
                supplier=supplier,
                filename=result['file_name'],
                file_path=file_path,
                total_rows=result['total_rows'],
                status='processing'
            )
            db.add(upload_record)
            db.commit()
            
            # 각 행 처리
            for index, row in df.iterrows():
                try:
                    product_data = self._parse_row(row, supplier)
                    
                    if product_data:
                        # DB에 저장
                        saved, is_new = self._save_product(db, product_data, supplier)
                        
                        if saved:
                            result['processed_rows'] += 1
                            if is_new:
                                result['new_products'] += 1
                            else:
                                result['updated_products'] += 1
                        else:
                            result['error_rows'] += 1
                            result['errors'].append(f"행 {index + 2}: 저장 실패")
                    else:
                        result['error_rows'] += 1
                        result['errors'].append(f"행 {index + 2}: 데이터 파싱 실패")
                        
                except Exception as e:
                    result['error_rows'] += 1
                    result['errors'].append(f"행 {index + 2}: {str(e)}")
                    self.logger.error(f"행 {index + 2} 처리 중 오류: {e}")
                    
                # 진행 상황 로그 (100행마다)
                if (index + 1) % 100 == 0:
                    self.logger.info(f"진행 상황: {index + 1}/{result['total_rows']} 행 처리")
            
            # 커밋
            db.commit()
            
            # 업로드 기록 업데이트
            upload_record.processed_rows = result['processed_rows']
            upload_record.error_rows = result['error_rows']
            upload_record.status = 'completed'
            upload_record.process_time = datetime.now()
            db.commit()
            
            result['success'] = True
            self.logger.info(f"엑셀 처리 완료: {result['processed_rows']}/{result['total_rows']} 행 성공")
            
        except Exception as e:
            db.rollback()
            result['errors'].append(f"처리 중 오류: {str(e)}")
            self.logger.error(f"엑셀 파일 처리 실패: {e}")
            
            # 업로드 기록 실패 상태로 업데이트
            if 'upload_record' in locals():
                upload_record.status = 'failed'
                upload_record.process_time = datetime.now()
                db.commit()
                
        finally:
            db.close()
            
        return result
        
    def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """엑셀 파일 읽기"""
        try:
            # 여러 형식 시도
            try:
                # Excel 파일
                df = pd.read_excel(file_path)
            except:
                # CSV 파일
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                
            return df
            
        except Exception as e:
            self.logger.error(f"엑셀 파일 읽기 실패: {e}")
            return None
            
    def _parse_row(self, row: pd.Series, supplier: str) -> Optional[Dict[str, Any]]:
        """엑셀 행을 상품 데이터로 변환"""
        try:
            # 필수 필드 확인
            product_code = self._get_value(row, ['상품코드', 'product_code', 'code', '코드'])
            
            if not product_code:
                return None
                
            # 공급사별 파싱 규칙
            if supplier == 'zentrade':
                return self._parse_zentrade_row(row, product_code)
            elif supplier == 'ownerclan':
                return self._parse_ownerclan_row(row, product_code)
            elif supplier == 'domeggook':
                return self._parse_domeggook_row(row, product_code)
            else:
                # 기본 파싱
                return self._parse_default_row(row, product_code)
                
        except Exception as e:
            self.logger.error(f"행 파싱 오류: {e}")
            return None
            
    def _parse_default_row(self, row: pd.Series, product_code: str) -> Dict[str, Any]:
        """기본 파싱 규칙"""
        return {
            'product_code': str(product_code),
            'product_name': self._get_value(row, ['상품명', 'product_name', 'name', '이름']),
            'price': self._get_value(row, ['가격', 'price', '판매가']),
            'supply_price': self._get_value(row, ['공급가', 'supply_price', '도매가']),
            'category': self._get_value(row, ['카테고리', 'category', '분류']),
            'brand': self._get_value(row, ['브랜드', 'brand', '제조사']),
            'description': self._get_value(row, ['설명', 'description', '상세설명']),
            'stock': self._get_value(row, ['재고', 'stock', '재고수량']),
            'collected_at': datetime.now().isoformat(),
            'source': 'excel_upload'
        }
        
    def _parse_zentrade_row(self, row: pd.Series, product_code: str) -> Dict[str, Any]:
        """젠트레이드 전용 파싱"""
        data = self._parse_default_row(row, product_code)
        
        # 젠트레이드 특수 필드
        data.update({
            'model': self._get_value(row, ['모델명', 'model']),
            'shipping_fee': self._get_value(row, ['배송비', 'shipping_fee']),
            'return_fee': self._get_value(row, ['반품비', 'return_fee']),
        })
        
        return data
        
    def _parse_ownerclan_row(self, row: pd.Series, product_code: str) -> Dict[str, Any]:
        """오너클랜 전용 파싱"""
        data = self._parse_default_row(row, product_code)
        
        # 오너클랜 특수 필드
        data.update({
            'brand_name': self._get_value(row, ['브랜드명', 'brand_name']),
            'stock_quantity': self._get_value(row, ['재고수량', 'stock_quantity']),
            'product_status': self._get_value(row, ['상품상태', 'product_status']),
        })
        
        # 옵션 정보 파싱
        options_str = self._get_value(row, ['옵션', 'options'])
        if options_str:
            try:
                data['options'] = json.loads(options_str) if isinstance(options_str, str) else options_str
            except:
                data['options'] = []
                
        return data
        
    def _parse_domeggook_row(self, row: pd.Series, product_code: str) -> Dict[str, Any]:
        """도매꾹 전용 파싱"""
        data = self._parse_default_row(row, product_code)
        
        # 도매꾹 특수 필드
        data.update({
            'category_code': self._get_value(row, ['카테고리코드', 'category_code']),
            'vendor_code': self._get_value(row, ['벤더코드', 'vendor_code']),
            'min_order_qty': self._get_value(row, ['최소주문수량', 'min_order_qty']),
            'consumer_price': self._get_value(row, ['소비자가', 'consumer_price']),
        })
        
        return data
        
    def _get_value(self, row: pd.Series, columns: List[str]) -> Any:
        """여러 컬럼명 중 존재하는 값 찾기"""
        for col in columns:
            if col in row.index and pd.notna(row[col]):
                return row[col]
        return None
        
    def _save_product(self, db, product_data: Dict[str, Any], supplier: str) -> Tuple[bool, bool]:
        """상품 데이터 저장"""
        try:
            product_code = product_data.get('product_code')
            
            # 기존 상품 확인
            existing = db.query(Product).filter(
                Product.product_code == product_code
            ).first()
            
            if existing:
                # 업데이트
                existing.product_info = product_data
                existing.supplier = supplier
                return True, False
            else:
                # 신규 생성
                new_product = Product(
                    product_code=product_code,
                    product_info=product_data,
                    supplier=supplier
                )
                db.add(new_product)
                return True, True
                
        except Exception as e:
            self.logger.error(f"상품 저장 오류: {e}")
            return False, False
            
    def get_template(self, supplier: str = 'default') -> pd.DataFrame:
        """공급사별 엑셀 템플릿 생성"""
        
        if supplier == 'zentrade':
            columns = [
                '상품코드', '상품명', '가격', '공급가', '카테고리', 
                '브랜드', '모델명', '설명', '재고', '배송비', '반품비'
            ]
        elif supplier == 'ownerclan':
            columns = [
                '상품코드', '상품명', '가격', '공급가', '카테고리',
                '브랜드명', '재고수량', '상품상태', '옵션', '설명'
            ]
        elif supplier == 'domeggook':
            columns = [
                '상품코드', '상품명', '공급가', '소비자가', '카테고리코드',
                '카테고리', '벤더코드', '최소주문수량', '재고', '설명'
            ]
        else:
            # 기본 템플릿
            columns = [
                '상품코드', '상품명', '가격', '공급가', '카테고리',
                '브랜드', '설명', '재고'
            ]
            
        # 빈 데이터프레임 생성
        df = pd.DataFrame(columns=columns)
        
        # 샘플 데이터 추가 (1행)
        sample_data = {col: f'샘플_{col}' for col in columns}
        df = pd.concat([df, pd.DataFrame([sample_data])], ignore_index=True)
        
        return df