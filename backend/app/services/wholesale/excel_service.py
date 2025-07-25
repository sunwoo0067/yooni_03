"""
엑셀 파일 처리 서비스
도매처 상품 엑셀 파일을 업로드하고 처리하는 기능을 제공합니다.
"""
import hashlib
import io
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union
import logging

import pandas as pd
from difflib import SequenceMatcher
from sqlalchemy.orm import Session

from app.models.wholesaler import (
    ExcelUploadLog, 
    WholesalerProduct, 
    WholesalerAccount,
    CollectionStatus
)
from app.utils.encryption import encrypt_data, decrypt_data
from app.core.performance import redis_cache, memory_cache, batch_process, optimize_memory_usage

logger = logging.getLogger(__name__)


class ExcelColumnMapper:
    """엑셀 컬럼 자동 매핑 클래스"""
    
    # 표준 컬럼 매핑 템플릿
    COLUMN_MAPPINGS = {
        'name': ['상품명', '제품명', 'name', 'product_name', '품명', '상품이름'],
        'price': ['가격', '판매가', 'price', '판매가격', '소매가', '정가'],
        'wholesale_price': ['도매가', '원가', '매입가', '공급가', 'wholesale_price', '도매'],
        'category': ['카테고리', '분류', 'category', '카테고리명', '상품분류'],
        'stock': ['재고', '수량', 'stock', 'quantity', '재고수량', '보유수량'],
        'sku': ['SKU', 'sku', '상품코드', '품번', '상품번호', '제품코드'],
        'description': ['설명', '상품설명', 'description', '제품설명', '상세설명'],
        'brand': ['브랜드', '제조사', 'brand', 'manufacturer', '브랜드명'],
        'origin': ['원산지', 'origin', '제조국', '원산국'],
        'weight': ['무게', '중량', 'weight', '무게(g)', '무게(kg)', '중량(g)'],
        'size': ['크기', '사이즈', 'size', '규격', '치수'],
        'color': ['색상', '컬러', 'color', '색깔'],
        'material': ['재질', '소재', 'material', '재료'],
        'model': ['모델', 'model', '모델명', '품번'],
        'barcode': ['바코드', 'barcode', 'UPC', 'EAN'],
        'image_url': ['이미지', '사진', 'image', 'image_url', '이미지URL', '메인이미지']
    }
    
    @classmethod
    def find_best_match(cls, column_name: str, threshold: float = 0.6) -> Optional[str]:
        """컬럼명에 가장 적합한 표준 필드를 찾습니다."""
        best_match = None
        best_score = 0
        
        column_name_lower = column_name.lower().strip()
        
        for standard_field, possible_names in cls.COLUMN_MAPPINGS.items():
            for possible_name in possible_names:
                # 정확한 매치 우선
                if column_name_lower == possible_name.lower():
                    return standard_field
                
                # 부분 매치 확인
                if possible_name.lower() in column_name_lower or column_name_lower in possible_name.lower():
                    score = 0.8
                    if score > best_score:
                        best_score = score
                        best_match = standard_field
                
                # 유사도 매치
                similarity = SequenceMatcher(None, column_name_lower, possible_name.lower()).ratio()
                if similarity > threshold and similarity > best_score:
                    best_score = similarity
                    best_match = standard_field
        
        return best_match if best_score > threshold else None
    
    @classmethod
    def auto_map_columns(cls, columns: List[str]) -> Dict[str, str]:
        """컬럼 목록을 자동으로 매핑합니다."""
        mapping = {}
        used_fields = set()
        
        for column in columns:
            if not column or pd.isna(column):
                continue
                
            best_match = cls.find_best_match(str(column))
            if best_match and best_match not in used_fields:
                mapping[column] = best_match
                used_fields.add(best_match)
            else:
                mapping[column] = 'unmapped'
        
        return mapping


class ExcelProcessor:
    """엑셀 파일 처리 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.mapper = ExcelColumnMapper()
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """파일 해시를 계산합니다."""
        return hashlib.sha256(file_content).hexdigest()
    
    @optimize_memory_usage
    def read_excel_file(self, file_content: bytes, filename: str) -> Tuple[pd.DataFrame, Dict]:
        """엑셀 파일을 읽고 기본 정보를 반환합니다."""
        try:
            # 다양한 인코딩 시도
            encodings = ['utf-8', 'cp949', 'euc-kr', 'utf-8-sig']
            
            df = None
            file_info = {
                'filename': filename,
                'file_size': len(file_content),
                'sheets': [],
                'encoding': None
            }
            
            # BytesIO로 파일 내용 변환
            file_buffer = io.BytesIO(file_content)
            
            # 엑셀 파일 읽기 시도
            try:
                if filename.endswith('.xlsx') or filename.endswith('.xls'):
                    # 모든 시트 정보 먼저 확인
                    excel_file = pd.ExcelFile(file_buffer)
                    file_info['sheets'] = excel_file.sheet_names
                    
                    # 첫 번째 시트 읽기
                    df = pd.read_excel(file_buffer, sheet_name=0, engine='openpyxl')
                    file_info['encoding'] = 'excel'
                
                elif filename.endswith('.csv'):
                    # CSV 파일 처리
                    for encoding in encodings:
                        try:
                            file_buffer.seek(0)
                            df = pd.read_csv(file_buffer, encoding=encoding)
                            file_info['encoding'] = encoding
                            break
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    
                    if df is None:
                        raise ValueError("지원하지 않는 인코딩입니다.")
                
                else:
                    raise ValueError("지원하지 않는 파일 형식입니다. (.xlsx, .xls, .csv만 지원)")
                
                # 데이터 기본 정보 추가
                file_info.update({
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'columns': df.columns.tolist(),
                    'sample_data': df.head(3).to_dict('records') if len(df) > 0 else []
                })
                
                return df, file_info
                
            except Exception as e:
                logger.error(f"파일 읽기 실패: {str(e)}")
                raise ValueError(f"파일을 읽을 수 없습니다: {str(e)}")
                
        except Exception as e:
            logger.error(f"엑셀 파일 처리 실패: {str(e)}")
            raise ValueError(f"파일 처리 중 오류 발생: {str(e)}")
    
    def validate_data(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> Dict:
        """데이터 유효성을 검증합니다."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {
                'total_rows': len(df),
                'valid_rows': 0,
                'invalid_rows': 0,
                'missing_required_fields': 0
            }
        }
        
        # 필수 필드 확인
        required_fields = ['name']  # 최소한 상품명은 필요
        mapped_fields = set(column_mapping.values())
        
        missing_required = set(required_fields) - mapped_fields
        if missing_required:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"필수 필드가 누락되었습니다: {', '.join(missing_required)}")
        
        # 행별 데이터 검증
        for idx, row in df.iterrows():
            row_errors = []
            
            # 상품명 확인
            if 'name' in mapped_fields:
                name_column = next((k for k, v in column_mapping.items() if v == 'name'), None)
                if name_column and (pd.isna(row[name_column]) or str(row[name_column]).strip() == ''):
                    row_errors.append(f"행 {idx + 2}: 상품명이 비어있습니다.")
            
            # 가격 정보 확인
            price_fields = ['price', 'wholesale_price']
            for field in price_fields:
                if field in mapped_fields:
                    price_column = next((k for k, v in column_mapping.items() if v == field), None)
                    if price_column and not pd.isna(row[price_column]):
                        try:
                            price_value = float(str(row[price_column]).replace(',', ''))
                            if price_value < 0:
                                row_errors.append(f"행 {idx + 2}: {field} 값이 음수입니다.")
                        except (ValueError, TypeError):
                            row_errors.append(f"행 {idx + 2}: {field} 값이 올바르지 않습니다.")
            
            # 재고 수량 확인
            if 'stock' in mapped_fields:
                stock_column = next((k for k, v in column_mapping.items() if v == 'stock'), None)
                if stock_column and not pd.isna(row[stock_column]):
                    try:
                        stock_value = int(float(str(row[stock_column])))
                        if stock_value < 0:
                            row_errors.append(f"행 {idx + 2}: 재고 수량이 음수입니다.")
                    except (ValueError, TypeError):
                        row_errors.append(f"행 {idx + 2}: 재고 수량이 올바르지 않습니다.")
            
            if row_errors:
                validation_result['invalid_rows'] += 1
                validation_result['errors'].extend(row_errors)
            else:
                validation_result['valid_rows'] += 1
        
        validation_result['stats']['invalid_rows'] = validation_result['invalid_rows']
        validation_result['stats']['valid_rows'] = validation_result['valid_rows']
        
        # 경고 메시지 추가
        if validation_result['invalid_rows'] > 0:
            validation_result['warnings'].append(f"{validation_result['invalid_rows']}개 행에 오류가 있습니다.")
        
        return validation_result
    
    @batch_process(batch_size=100)
    def process_excel_data(self, df: pd.DataFrame, column_mapping: Dict[str, str], 
                          wholesaler_account_id: int) -> List[Dict]:
        """엑셀 데이터를 처리하여 상품 정보로 변환합니다."""
        products = []
        
        for idx, row in df.iterrows():
            try:
                product_data = {
                    'wholesaler_account_id': wholesaler_account_id,
                    'name': '',
                    'description': None,
                    'category_path': None,
                    'wholesale_price': 0,
                    'retail_price': None,
                    'stock_quantity': 0,
                    'is_in_stock': True,
                    'raw_data': row.to_dict()
                }
                
                # 매핑된 컬럼에서 데이터 추출
                for excel_column, standard_field in column_mapping.items():
                    if standard_field == 'unmapped':
                        continue
                    
                    value = row.get(excel_column)
                    if pd.isna(value):
                        continue
                    
                    # 필드별 데이터 처리
                    if standard_field == 'name':
                        product_data['name'] = str(value).strip()
                    elif standard_field == 'description':
                        product_data['description'] = str(value).strip()
                    elif standard_field == 'category':
                        product_data['category_path'] = str(value).strip()
                    elif standard_field == 'price':
                        try:
                            product_data['retail_price'] = int(float(str(value).replace(',', '')))
                        except (ValueError, TypeError):
                            pass
                    elif standard_field == 'wholesale_price':
                        try:
                            product_data['wholesale_price'] = int(float(str(value).replace(',', '')))
                        except (ValueError, TypeError):
                            pass
                    elif standard_field == 'stock':
                        try:
                            stock_value = int(float(str(value)))
                            product_data['stock_quantity'] = max(0, stock_value)
                            product_data['is_in_stock'] = stock_value > 0
                        except (ValueError, TypeError):
                            pass
                    elif standard_field == 'sku':
                        product_data['wholesaler_sku'] = str(value).strip()
                    elif standard_field == 'image_url':
                        product_data['main_image_url'] = str(value).strip()
                
                # 필수 데이터 확인
                if not product_data['name']:
                    continue
                
                # 기본값 설정
                if not product_data.get('wholesaler_sku'):
                    product_data['wholesaler_sku'] = f"EXCEL_{idx + 1}"
                
                if not product_data.get('wholesaler_product_id'):
                    product_data['wholesaler_product_id'] = f"EXCEL_{wholesaler_account_id}_{idx + 1}"
                
                products.append(product_data)
                
            except Exception as e:
                logger.error(f"행 {idx + 2} 처리 실패: {str(e)}")
                continue
        
        return products


class ExcelService:
    """엑셀 처리 메인 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.processor = ExcelProcessor(db)
    
    def upload_excel_file(self, file_content: bytes, filename: str, 
                         wholesaler_account_id: int) -> Dict:
        """엑셀 파일을 업로드하고 분석합니다."""
        try:
            # 파일 해시 계산
            file_hash = self.processor.calculate_file_hash(file_content)
            
            # 이미 처리된 파일인지 확인
            existing_log = self.db.query(ExcelUploadLog).filter(
                ExcelUploadLog.file_hash == file_hash,
                ExcelUploadLog.wholesaler_account_id == wholesaler_account_id
            ).first()
            
            if existing_log:
                return {
                    'success': False,
                    'message': '이미 업로드된 파일입니다.',
                    'upload_log_id': existing_log.id
                }
            
            # 엑셀 파일 읽기
            df, file_info = self.processor.read_excel_file(file_content, filename)
            
            # 컬럼 자동 매핑
            column_mapping = self.processor.mapper.auto_map_columns(df.columns.tolist())
            
            # 업로드 로그 생성
            upload_log = ExcelUploadLog(
                wholesaler_account_id=wholesaler_account_id,
                filename=filename,
                file_size=len(file_content),
                file_hash=file_hash,
                total_rows=len(df),
                status=CollectionStatus.PENDING
            )
            
            self.db.add(upload_log)
            self.db.commit()
            self.db.refresh(upload_log)
            
            return {
                'success': True,
                'upload_log_id': upload_log.id,
                'file_info': file_info,
                'column_mapping': column_mapping,
                'preview_data': df.head(5).to_dict('records') if len(df) > 0 else []
            }
            
        except Exception as e:
            logger.error(f"엑셀 파일 업로드 실패: {str(e)}")
            return {
                'success': False,
                'message': f"파일 업로드 실패: {str(e)}"
            }
    
    def process_uploaded_file(self, upload_log_id: int, column_mapping: Dict[str, str],
                            file_content: bytes) -> Dict:
        """업로드된 파일을 처리하여 상품을 등록합니다."""
        try:
            # 업로드 로그 조회
            upload_log = self.db.query(ExcelUploadLog).filter(
                ExcelUploadLog.id == upload_log_id
            ).first()
            
            if not upload_log:
                return {'success': False, 'message': '업로드 로그를 찾을 수 없습니다.'}
            
            # 파일 다시 읽기
            df, _ = self.processor.read_excel_file(file_content, upload_log.filename)
            
            # 데이터 검증
            validation_result = self.processor.validate_data(df, column_mapping)
            
            if not validation_result['is_valid']:
                upload_log.status = CollectionStatus.FAILED
                upload_log.error_message = '; '.join(validation_result['errors'])
                upload_log.failed_rows_detail = validation_result
                self.db.commit()
                
                return {
                    'success': False,
                    'message': '데이터 검증 실패',
                    'validation_result': validation_result
                }
            
            # 상품 데이터 처리
            upload_log.status = CollectionStatus.RUNNING
            self.db.commit()
            
            products_data = self.processor.process_excel_data(
                df, column_mapping, upload_log.wholesaler_account_id
            )
            
            # 상품 등록
            success_count = 0
            failed_count = 0
            processing_log = []
            
            for idx, product_data in enumerate(products_data):
                try:
                    # 기존 상품 확인 (SKU 기준)
                    existing_product = self.db.query(WholesalerProduct).filter(
                        WholesalerProduct.wholesaler_account_id == upload_log.wholesaler_account_id,
                        WholesalerProduct.wholesaler_sku == product_data.get('wholesaler_sku')
                    ).first()
                    
                    if existing_product:
                        # 기존 상품 업데이트
                        for key, value in product_data.items():
                            if hasattr(existing_product, key) and value is not None:
                                setattr(existing_product, key, value)
                        existing_product.last_updated_at = datetime.utcnow()
                    else:
                        # 새 상품 생성
                        new_product = WholesalerProduct(**product_data)
                        self.db.add(new_product)
                    
                    success_count += 1
                    processing_log.append({
                        'row': idx + 2,
                        'product_name': product_data.get('name', ''),
                        'status': 'success'
                    })
                    
                except Exception as e:
                    failed_count += 1
                    processing_log.append({
                        'row': idx + 2,
                        'product_name': product_data.get('name', ''),
                        'status': 'failed',
                        'error': str(e)
                    })
                    logger.error(f"상품 등록 실패 (행 {idx + 2}): {str(e)}")
            
            # 업로드 로그 업데이트
            upload_log.processed_rows = len(products_data)
            upload_log.success_rows = success_count
            upload_log.failed_rows = failed_count
            upload_log.status = CollectionStatus.COMPLETED if failed_count == 0 else CollectionStatus.FAILED
            upload_log.processed_at = datetime.utcnow()
            upload_log.processing_log = processing_log
            
            self.db.commit()
            
            return {
                'success': True,
                'message': f'처리 완료: 성공 {success_count}개, 실패 {failed_count}개',
                'stats': {
                    'total_processed': len(products_data),
                    'success_count': success_count,
                    'failed_count': failed_count
                },
                'processing_log': processing_log
            }
            
        except Exception as e:
            logger.error(f"엑셀 파일 처리 실패: {str(e)}")
            if 'upload_log' in locals():
                upload_log.status = CollectionStatus.FAILED
                upload_log.error_message = str(e)
                self.db.commit()
            
            return {
                'success': False,
                'message': f"파일 처리 실패: {str(e)}"
            }
    
    @memory_cache(max_size=50, expiration=600)
    def get_upload_history(self, wholesaler_account_id: int, 
                          limit: int = 50, offset: int = 0) -> List[Dict]:
        """업로드 이력을 조회합니다."""
        try:
            logs = self.db.query(ExcelUploadLog).filter(
                ExcelUploadLog.wholesaler_account_id == wholesaler_account_id
            ).order_by(ExcelUploadLog.uploaded_at.desc()).offset(offset).limit(limit).all()
            
            return [
                {
                    'id': log.id,
                    'filename': log.filename,
                    'file_size': log.file_size,
                    'total_rows': log.total_rows,
                    'processed_rows': log.processed_rows,
                    'success_rows': log.success_rows,
                    'failed_rows': log.failed_rows,
                    'status': log.status.value,
                    'uploaded_at': log.uploaded_at.isoformat() if log.uploaded_at else None,
                    'processed_at': log.processed_at.isoformat() if log.processed_at else None,
                    'error_message': log.error_message
                } for log in logs
            ]
            
        except Exception as e:
            logger.error(f"업로드 이력 조회 실패: {str(e)}")
            return []
    
    @redis_cache(expiration=1800)
    def get_upload_detail(self, upload_log_id: int) -> Optional[Dict]:
        """업로드 상세 정보를 조회합니다."""
        try:
            log = self.db.query(ExcelUploadLog).filter(
                ExcelUploadLog.id == upload_log_id
            ).first()
            
            if not log:
                return None
            
            return {
                'id': log.id,
                'filename': log.filename,
                'file_size': log.file_size,
                'file_hash': log.file_hash,
                'total_rows': log.total_rows,
                'processed_rows': log.processed_rows,
                'success_rows': log.success_rows,
                'failed_rows': log.failed_rows,
                'status': log.status.value,
                'uploaded_at': log.uploaded_at.isoformat() if log.uploaded_at else None,
                'processed_at': log.processed_at.isoformat() if log.processed_at else None,
                'error_message': log.error_message,
                'processing_log': log.processing_log,
                'failed_rows_detail': log.failed_rows_detail
            }
            
        except Exception as e:
            logger.error(f"업로드 상세 정보 조회 실패: {str(e)}")
            return None