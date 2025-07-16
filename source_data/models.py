from django.db import models
from django.contrib.postgres.indexes import GinIndex, BTreeIndex


class SourceData(models.Model):
    """모든 데이터의 근원 테이블 - 이벤트 소싱 패턴"""
    
    SOURCE_TYPE_CHOICES = [
        ('supplier_product', '공급사 상품'),
        ('market_listing', '마켓 리스팅'),
        ('order', '주문'),
        ('inventory', '재고'),
        ('pricing', '가격'),
        ('customer', '고객'),
        ('analytics', '분석'),
    ]
    
    PROCESSING_STATUS_CHOICES = [
        ('raw', '원본'),
        ('processing', '처리중'),
        ('processed', '처리완료'),
        ('error', '오류'),
        ('archived', '보관됨'),
    ]
    
    # 메타데이터
    id = models.BigAutoField(primary_key=True)
    source_type = models.CharField(
        max_length=50, 
        choices=SOURCE_TYPE_CHOICES,
        db_index=True
    )
    
    source_id = models.CharField(max_length=100, db_index=True)  # 외부 시스템 ID
    source_system = models.CharField(max_length=50, db_index=True)  # 'ownerclan', 'smartstore' 등
    
    # 근원 데이터 (JSONB)
    raw_data = models.JSONField(default=dict, help_text="원본 데이터 그대로")
    
    # 정규화된 데이터 (JSONB)
    normalized_data = models.JSONField(default=dict, help_text="정규화된 구조화 데이터")
    
    # 마켓별 데이터 (JSONB) - 핵심!
    market_data = models.JSONField(default=dict, help_text="""
    마켓별 특화 데이터:
    {
        'smartstore': {
            'category_id': '...',
            'title': '...',
            'price': 15000,
            'status': 'active',
            'listing_id': '...',
            'last_sync': '2025-01-01T00:00:00Z'
        },
        'coupang': {
            'vendor_item_id': '...',
            'item_name': '...',
            'original_price': 15000,
            'sale_price': 13500,
            'approval_status': 'approved'
        },
        'gmarket': {
            'goods_no': '...',
            'goods_nm': '...',
            'sell_price': 14000,
            'display_yn': 'Y'
        }
    }
    """)
    
    # AI 처리 데이터 (JSONB)
    ai_data = models.JSONField(default=dict, help_text="""
    AI 처리 결과:
    {
        'processed_title': '...',
        'optimized_description': '...',
        'extracted_keywords': [...],
        'category_predictions': {...},
        'pricing_recommendations': {...},
        'quality_score': 0.85
    }
    """)
    
    # 메타정보
    version = models.PositiveIntegerField(default=1)  # 데이터 버전
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    
    # 오케스트레이션 정보
    workflow_id = models.CharField(max_length=100, blank=True, db_index=True)
    processing_status = models.CharField(
        max_length=20, 
        choices=PROCESSING_STATUS_CHOICES,
        default='raw',
        db_index=True
    )
    
    class Meta:
        indexes = [
            # 복합 인덱스들
            BTreeIndex(fields=['source_type', 'source_system']),
            BTreeIndex(fields=['source_system', 'source_id']),
            BTreeIndex(fields=['processing_status', 'created_at']),
            BTreeIndex(fields=['workflow_id', 'processing_status']),
            
            # JSONB GIN 인덱스들
            GinIndex(fields=['raw_data']),
            GinIndex(fields=['normalized_data']),
            GinIndex(fields=['market_data']),
            GinIndex(fields=['ai_data']),
        ]
        
        unique_together = ['source_system', 'source_id', 'version']


class DataLineage(models.Model):
    """데이터 계보 추적"""
    parent = models.ForeignKey(
        SourceData, 
        on_delete=models.CASCADE, 
        related_name='children'
    )
    child = models.ForeignKey(
        SourceData, 
        on_delete=models.CASCADE, 
        related_name='parents'
    )
    transformation_type = models.CharField(max_length=50)
    transformation_metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)