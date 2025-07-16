from django.db import models
from django.contrib.auth.models import User
from source_data.models import SourceData


class ConversationContext(models.Model):
    """AI 대화 컨텍스트 저장"""
    
    CONTEXT_TYPES = [
        ('workflow', '워크플로우 실행'),
        ('market_chat', '마켓 관리 대화'),
        ('product_analysis', '상품 분석'),
        ('support', '고객 지원'),
        ('system', '시스템 대화'),
    ]
    
    # 기본 정보
    context_id = models.CharField(max_length=100, unique=True, db_index=True)
    context_type = models.CharField(max_length=20, choices=CONTEXT_TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # 대화 데이터
    messages = models.JSONField(default=list, help_text="대화 메시지 리스트")
    metadata = models.JSONField(default=dict, help_text="추가 메타데이터")
    
    # 관련 데이터
    related_source_data = models.ManyToManyField(
        SourceData, 
        blank=True,
        help_text="이 대화와 관련된 소스 데이터"
    )
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(auto_now=True)
    
    # 상태
    is_active = models.BooleanField(default=True)
    ttl_seconds = models.IntegerField(
        default=86400 * 30,  # 30일
        help_text="Time to live in seconds"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['context_type', 'created_at']),
            models.Index(fields=['user', 'is_active']),
        ]
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.context_type} - {self.context_id}"


class MemorySnapshot(models.Model):
    """AI 메모리 스냅샷 - 중요한 정보 요약"""
    
    conversation = models.ForeignKey(
        ConversationContext, 
        on_delete=models.CASCADE,
        related_name='memory_snapshots'
    )
    
    # 메모리 내용
    summary = models.TextField(help_text="대화 요약")
    key_facts = models.JSONField(default=list, help_text="핵심 사실들")
    decisions = models.JSONField(default=list, help_text="내려진 결정사항들")
    action_items = models.JSONField(default=list, help_text="액션 아이템들")
    
    # 벡터 임베딩 정보
    embedding_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Upstash Vector DB의 임베딩 ID"
    )
    
    # 메타데이터
    importance_score = models.FloatField(
        default=0.5,
        help_text="중요도 점수 (0-1)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['importance_score', 'created_at']),
        ]
        ordering = ['-importance_score', '-created_at']


class WorkflowContext(models.Model):
    """워크플로우 실행 컨텍스트"""
    
    workflow_id = models.CharField(max_length=100, db_index=True)
    workflow_name = models.CharField(max_length=100)
    
    # 실행 컨텍스트
    input_context = models.JSONField(default=dict, help_text="입력 컨텍스트")
    execution_context = models.JSONField(default=dict, help_text="실행 중 컨텍스트")
    output_context = models.JSONField(default=dict, help_text="출력 컨텍스트")
    
    # 학습된 패턴
    learned_patterns = models.JSONField(
        default=dict, 
        help_text="이 워크플로우에서 학습된 패턴들"
    )
    
    # 성능 메트릭
    performance_metrics = models.JSONField(
        default=dict,
        help_text="실행 성능 메트릭"
    )
    
    # 관련 대화
    conversation = models.ForeignKey(
        ConversationContext,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='workflow_contexts'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['workflow_name', 'created_at']),
        ]
        ordering = ['-created_at']