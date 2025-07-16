"""
오케스트레이션 + 근원 데이터 중심 드랍쉬핑 시스템 설계
Claude Code로 개발 시작 가능한 구조
"""

# 프로젝트 구조
yooini_03
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── .env
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
│
├── core/                       # 핵심 오케스트레이션
│   ├── models.py              # 근원 데이터 모델
│   ├── orchestrator/          # 오케스트레이션 엔진
│   │   ├── __init__.py
│   │   ├── engine.py         # 메인 오케스트레이션 엔진
│   │   ├── workflow.py       # 워크플로우 정의
│   │   ├── scheduler.py      # 작업 스케줄러
│   │   ├── monitor.py        # 실행 모니터링
│   │   └── recovery.py       # 장애 복구
│   ├── events/                # 이벤트 시스템
│   │   ├── __init__.py
│   │   ├── bus.py           # 이벤트 버스
│   │   ├── handlers.py      # 이벤트 핸들러
│   │   └── listeners.py     # 이벤트 리스너
│   └── storage/               # 데이터 저장소
│       ├── __init__.py
│       ├── source_store.py  # 근원 데이터 저장소
│       ├── cache_store.py   # 캐시 저장소
│       └── analytics_store.py # 분석 데이터 저장소
│
├── orchestration/              # 오케스트레이션 워크플로우들
│   ├── __init__.py
│   ├── models.py              # 워크플로우 모델들
│   ├── admin.py
│   │
│   ├── workflows/             # 워크플로우 정의들
│   │   ├── __init__.py
│   │   ├── base.py           # 기본 워크플로우 클래스
│   │   ├── product_sync.py   # 상품 동기화 워크플로우
│   │   ├── market_management.py # 마켓 관리 워크플로우
│   │   ├── order_processing.py # 주문 처리 워크플로우
│   │   ├── inventory_sync.py # 재고 동기화 워크플로우
│   │   └── analytics_pipeline.py # 분석 파이프라인
│   │
│   ├── steps/                 # 워크플로우 스텝들
│   │   ├── __init__.py
│   │   ├── base_step.py      # 기본 스텝 클래스
│   │   ├── data_collection.py # 데이터 수집 스텝들
│   │   ├── ai_processing.py  # AI 처리 스텝들
│   │   ├── market_operations.py # 마켓 작업 스텝들
│   │   └── notifications.py  # 알림 스텝들
│   │
│   └── tasks.py               # Celery 오케스트레이션 작업
│
├── source_data/                # 근원 데이터 앱
│   ├── __init__.py
│   ├── models.py              # 모든 근원 데이터 테이블
│   ├── admin.py               # 근원 데이터 관리
│   ├── managers.py            # JSONB 쿼리 최적화
│   ├── serializers.py         # API 시리얼라이저
│   └── views.py               # 근원 데이터 API
│
├── suppliers/                  # 공급사 (데이터 소스)
│   ├── models.py              # 공급사 설정만
│   ├── admin.py
│   ├── connectors/            # 데이터 커넥터들
│   │   ├── __init__.py
│   │   ├── base_connector.py # 기본 커넥터
│   │   ├── api_connector.py  # API 커넥터
│   │   ├── excel_connector.py # 엑셀 커넥터
│   │   └── webhook_connector.py # 웹훅 커넥터
│   └── tasks.py
│
├── markets/                    # 마켓 (데이터 싱크)
│   ├── models.py              # 마켓 설정만
│   ├── admin.py
│   ├── connectors/            # 마켓 커넥터들
│   │   ├── __init__.py
│   │   ├── base_connector.py
│   │   ├── smartstore.py
│   │   ├── coupang.py
│   │   └── gmarket.py
│   └── tasks.py
│
├── ai_agents/                  # AI 오케스트레이션
│   ├── __init__.py
│   ├── models.py
│   ├── admin.py
│   ├── orchestrator/          # AI 오케스트레이션
│   │   ├── __init__.py
│   │   ├── ai_conductor.py   # AI 오케스트레이터
│   │   ├── agent_manager.py  # 에이전트 관리자
│   │   └── task_distributor.py # 작업 분배기
│   └── agents/                # 실제 AI 에이전트들
│       ├── market_manager.py
│       ├── product_processor.py
│       ├── pricing_optimizer.py
│       └── order_handler.py
│
├── analytics/                  # 분석 오케스트레이션
│   ├── models.py
│   ├── admin.py
│   ├── pipelines/             # 분석 파이프라인
│   └── dashboards/            # 대시보드
│
└── scripts/                    # Claude Code 스크립트들
    ├── orchestration/
    │   ├── setup_workflows.py
    │   ├── deploy_agents.py
    │   └── monitor_system.py
    ├── database/
    │   ├── optimize_jsonb.py
    │   ├── create_indexes.py
    │   └── migrate_data.py
    └── ai/
        ├── train_agents.py
        ├── optimize_prompts.py
        └── evaluate_performance.py

# 근원 데이터 중심 모델 설계

# source_data/models.py
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GinIndex, BTreeIndex

class SourceData(models.Model):
    """모든 데이터의 근원 테이블 - 이벤트 소싱 패턴"""
    
    # 메타데이터
    id = models.BigAutoField(primary_key=True)
    source_type = models.CharField(max_length=50, choices=[
        ('supplier_product', '공급사 상품'),
        ('market_listing', '마켓 리스팅'),
        ('order', '주문'),
        ('inventory', '재고'),
        ('pricing', '가격'),
        ('customer', '고객'),
        ('analytics', '분석'),
    ], db_index=True)
    
    source_id = models.CharField(max_length=100, db_index=True)  # 외부 시스템 ID
    source_system = models.CharField(max_length=50, db_index=True)  # 'ownerclan', 'smartstore' 등
    
    # 근원 데이터 (JSONB)
    raw_data = JSONField(default=dict, help_text="원본 데이터 그대로")
    
    # 정규화된 데이터 (JSONB)
    normalized_data = JSONField(default=dict, help_text="정규화된 구조화 데이터")
    
    # 마켓별 데이터 (JSONB) - 핵심!
    market_data = JSONField(default=dict, help_text="""
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
    ai_data = JSONField(default=dict, help_text="""
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
    processing_status = models.CharField(max_length=20, choices=[
        ('raw', '원본'),
        ('processing', '처리중'),
        ('processed', '처리완료'),
        ('error', '오류'),
        ('archived', '보관됨'),
    ], default='raw', db_index=True)
    
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
    parent = models.ForeignKey(SourceData, on_delete=models.CASCADE, related_name='children')
    child = models.ForeignKey(SourceData, on_delete=models.CASCADE, related_name='parents')
    transformation_type = models.CharField(max_length=50)
    transformation_metadata = JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

# core/orchestrator/engine.py
from typing import Dict, List, Any
import asyncio
from celery import group, chain, chord
from .workflow import BaseWorkflow

class OrchestrationEngine:
    """메인 오케스트레이션 엔진"""
    
    def __init__(self):
        self.workflows = {}
        self.active_executions = {}
        self.event_bus = EventBus()
    
    def register_workflow(self, workflow_class: BaseWorkflow):
        """워크플로우 등록"""
        self.workflows[workflow_class.name] = workflow_class
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> str:
        """워크플로우 실행"""
        if workflow_name not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        workflow = self.workflows[workflow_name](input_data)
        execution_id = workflow.generate_execution_id()
        
        # 실행 상태 추적
        self.active_executions[execution_id] = {
            'workflow': workflow,
            'status': 'running',
            'started_at': timezone.now(),
            'steps_completed': 0,
            'total_steps': len(workflow.steps)
        }
        
        try:
            # 워크플로우 실행
            result = await workflow.execute()
            
            # 완료 상태 업데이트
            self.active_executions[execution_id]['status'] = 'completed'
            self.active_executions[execution_id]['result'] = result
            
            return execution_id
            
        except Exception as e:
            # 오류 상태 업데이트
            self.active_executions[execution_id]['status'] = 'failed'
            self.active_executions[execution_id]['error'] = str(e)
            
            # 복구 시도
            await self.attempt_recovery(execution_id, e)
            
            raise

# orchestration/workflows/product_sync.py
from .base import BaseWorkflow
from ..steps import DataCollectionStep, AIProcessingStep, MarketSyncStep

class ProductSyncWorkflow(BaseWorkflow):
    """상품 동기화 워크플로우"""
    
    name = "product_sync"
    description = "공급사에서 상품을 수집하고 AI 처리 후 마켓에 동기화"
    
    def define_steps(self):
        return [
            DataCollectionStep("collect_supplier_products"),
            AIProcessingStep("process_with_ai"),
            MarketSyncStep("sync_to_markets"),
        ]
    
    async def execute(self):
        """실행 로직"""
        # 1. 공급사 데이터 수집
        supplier_data = await self.steps[0].execute(self.input_data)
        
        # SourceData에 저장
        source_records = []
        for product in supplier_data:
            source_record = SourceData.objects.create(
                source_type='supplier_product',
                source_system=product['supplier'],
                source_id=product['external_id'],
                raw_data=product,
                processing_status='raw'
            )
            source_records.append(source_record)
        
        # 2. AI 처리 (병렬)
        ai_tasks = group([
            process_with_ai.s(record.id) for record in source_records
        ])
        ai_results = ai_tasks.apply_async()
        
        # 3. 마켓 동기화 (병렬)
        sync_tasks = group([
            sync_to_market.s(record.id, market) 
            for record in source_records 
            for market in ['smartstore', 'coupang', 'gmarket']
        ])
        sync_results = sync_tasks.apply_async()
        
        return {
            'products_processed': len(source_records),
            'ai_results': ai_results.get(),
            'sync_results': sync_results.get()
        }

# orchestration/workflows/market_management.py
class MarketManagementWorkflow(BaseWorkflow):
    """AI 기반 마켓 관리 워크플로우"""
    
    name = "market_management"
    
    async def execute(self):
        """마켓 자동 관리"""
        
        # 1. 시장 분석
        market_analysis = await self.analyze_market_conditions()
        
        # 2. 가격 최적화
        pricing_job = chain(
            analyze_competitor_prices.s(),
            calculate_optimal_prices.s(),
            update_market_prices.s()
        )
        
        # 3. 재고 관리
        inventory_job = chain(
            check_inventory_levels.s(),
            predict_demand.s(),
            optimize_inventory.s()
        )
        
        # 4. 성과 분석
        analytics_job = chain(
            collect_sales_data.s(),
            analyze_performance.s(),
            generate_recommendations.s()
        )
        
        # 병렬 실행
        management_workflow = chord([
            pricing_job,
            inventory_job,
            analytics_job
        ])(consolidate_results.s())
        
        return management_workflow.get()

# source_data/managers.py
from django.db import models
from django.contrib.postgres.aggregates import JSONBAgg

class SourceDataManager(models.Manager):
    """JSONB 쿼리 최적화된 매니저"""
    
    def by_market(self, market_name: str):
        """특정 마켓 데이터 조회"""
        return self.filter(
            market_data__has_key=market_name
        ).extra(
            select={
                'market_info': f"market_data->>'{market_name}'"
            }
        )
    
    def with_ai_score_above(self, score: float):
        """AI 품질 점수 이상인 데이터"""
        return self.filter(
            ai_data__quality_score__gte=score
        )
    
    def active_in_market(self, market_name: str):
        """특정 마켓에서 활성 상태인 상품들"""
        return self.filter(
            **{f"market_data__{market_name}__status": "active"}
        )
    
    def need_price_update(self, market_name: str):
        """가격 업데이트가 필요한 상품들"""
        from django.db.models import F
        from django.utils import timezone
        from datetime import timedelta
        
        return self.filter(
            **{f"market_data__{market_name}__last_sync__lt": 
               timezone.now() - timedelta(hours=6)}
        )
    
    def aggregate_by_market(self):
        """마켓별 집계"""
        return self.values('source_system').annotate(
            market_stats=JSONBAgg('market_data')
        )

# ai_agents/orchestrator/ai_conductor.py
class AIConductor:
    """AI 에이전트들을 오케스트레이션하는 지휘자"""
    
    def __init__(self):
        self.agents = {}
        self.task_queue = asyncio.Queue()
        self.result_store = {}
    
    async def conduct_market_management(self):
        """마켓 관리 AI 오케스트레이션"""
        
        # 1. 시장 상황 파악
        market_analysis = await self.agents['market_analyzer'].analyze()
        
        # 2. 에이전트별 작업 할당
        tasks = {
            'pricing': self.agents['pricing_optimizer'].optimize_prices(market_analysis),
            'inventory': self.agents['inventory_manager'].manage_stock(market_analysis),
            'listing': self.agents['listing_optimizer'].optimize_listings(market_analysis),
            'promotion': self.agents['promotion_manager'].plan_promotions(market_analysis)
        }
        
        # 3. 병렬 실행
        results = await asyncio.gather(*tasks.values())
        
        # 4. 결과 통합 및 실행
        integrated_plan = await self.integrate_results(results)
        execution_result = await self.execute_plan(integrated_plan)
        
        return execution_result

# Claude Code 시작 스크립트들

# scripts/orchestration/setup_workflows.py
"""
Claude Code로 실행할 워크플로우 설정 스크립트
"""

def setup_initial_workflows():
    """초기 워크플로우들 설정"""
    
    # 1. 기본 워크플로우 등록
    engine = OrchestrationEngine()
    engine.register_workflow(ProductSyncWorkflow)
    engine.register_workflow(MarketManagementWorkflow)
    engine.register_workflow(OrderProcessingWorkflow)
    
    # 2. 스케줄 설정
    scheduler = WorkflowScheduler()
    scheduler.schedule_workflow(
        'product_sync', 
        cron='0 */6 * * *',  # 6시간마다
        input_data={'suppliers': ['ownerclan', 'domeggook']}
    )
    
    scheduler.schedule_workflow(
        'market_management',
        cron='0 9 * * *',   # 매일 오전 9시
        input_data={'markets': ['smartstore', 'coupang', 'gmarket']}
    )
    
    print("✅ 워크플로우 설정 완료")

if __name__ == "__main__":
    setup_initial_workflows()

# requirements.txt
Django==4.2.0
psycopg2-binary==2.9.5
celery==5.3.0
redis==4.5.0
django-environ==0.10.0
djangorestframework==3.14.0
django-cors-headers==4.0.0

# AI 관련
openai==1.0.0
anthropic==0.8.0

# 데이터 처리
pandas==2.0.0
openpyxl==3.1.0
Pillow==9.5.0

# 오케스트레이션
prefect==2.10.0  # 또는 airflow
dramatiq==1.14.0

# 모니터링
prometheus-client==0.16.0
sentry-sdk==1.20.0