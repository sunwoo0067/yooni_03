# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
이 파일은 이 저장소에서 코드 작업을 할 때 Claude Code(claude.ai/code)에 대한 가이드를 제공합니다.

## Quick Start Checklist / 빠른 시작 체크리스트

1. [ ] Install dependencies / 의존성 설치: `pip install -r requirements.txt`
2. [ ] Setup environment / 환경 설정: `cp .env.example .env` (create if needed)
3. [ ] Setup database / 데이터베이스 설정: `docker-compose up -d db redis`
4. [ ] Run migrations / 마이그레이션 실행: `python manage.py migrate`
5. [ ] Create superuser / 관리자 생성: `python manage.py createsuperuser`
6. [ ] Start Celery / Celery 시작: `celery -A config worker -l info`
7. [ ] Run server / 서버 실행: `python manage.py runserver`

## Project Overview / 프로젝트 개요

This is a Django-based orchestration and source data-centric dropshipping system designed with an event-driven architecture. The system focuses on data orchestration between suppliers and marketplaces, with AI-powered processing and market management.

이것은 이벤트 기반 아키텍처로 설계된 Django 기반 오케스트레이션 및 소스 데이터 중심 드롭쉬핑 시스템입니다. 공급업체와 마켓플레이스 간의 데이터 오케스트레이션에 중점을 두며, AI 기반 처리 및 마켓 관리 기능을 제공합니다.

## Development Commands / 개발 명령어

### Environment Setup / 환경 설정

```bash
# Docker services (PostgreSQL, Redis) / Docker 서비스 실행
docker-compose up -d

# Stop services / 서비스 중지
docker-compose down

# View logs / 로그 확인
docker-compose logs -f

# Environment variables / 환경 변수 설정
cp .env.example .env  # Edit with your settings / 설정값 편집 필요
```

### Database Setup / 데이터베이스 설정

```bash
# Create database (if not using Docker) / 데이터베이스 생성
createdb yooini_03

# Make migrations / 마이그레이션 생성
python manage.py makemigrations

# Apply migrations / 마이그레이션 적용
python manage.py migrate

# Create indexes / 인덱스 생성
python scripts/database/create_indexes.py

# Optimize JSONB / JSONB 최적화
python scripts/database/optimize_jsonb.py
```

### Running the Application / 애플리케이션 실행

```bash
# Development server / 개발 서버
python manage.py runserver

# Celery worker / Celery 워커
celery -A config worker -l info

# Celery beat (scheduler) / Celery 스케줄러
celery -A config beat -l info

# Celery flower (monitoring) / Celery 모니터링
celery -A config flower

# All in one (development) / 개발용 통합 실행
honcho start  # or use Procfile
```

### Testing / 테스트

```bash
# Run all tests / 전체 테스트
python manage.py test

# Run specific app tests / 특정 앱 테스트
python manage.py test source_data
python manage.py test orchestration
python manage.py test ai_agents

# With coverage / 커버리지 포함
coverage run --source='.' manage.py test
coverage report
coverage html  # HTML report / HTML 리포트 생성

# Run specific test / 특정 테스트 실행
python manage.py test source_data.tests.test_models.SourceDataModelTest
```

### Workflow Management / 워크플로우 관리

```bash
# Setup initial workflows / 초기 워크플로우 설정
python scripts/orchestration/setup_workflows.py

# Deploy AI agents / AI 에이전트 배포
python scripts/orchestration/deploy_agents.py

# Monitor system / 시스템 모니터링
python scripts/orchestration/monitor_system.py

# Execute specific workflow / 특정 워크플로우 실행
python manage.py shell
>>> from core.orchestrator.engine import OrchestrationEngine
>>> engine = OrchestrationEngine()
>>> engine.execute_workflow('product_sync', {'suppliers': ['ownerclan']})
```

## High-Level Architecture / 고수준 아키텍처

### Core Components / 핵심 컴포넌트

1. **Source Data Model (`source_data/`)** / **소스 데이터 모델**
   - Central data storage using event sourcing pattern / 이벤트 소싱 패턴을 사용한 중앙 데이터 저장소
   - All data flows through the `SourceData` model with JSONB fields / 모든 데이터는 JSONB 필드를 가진 `SourceData` 모델을 통해 흐름
   - Tracks data lineage and transformations / 데이터 계보 및 변환 추적
   - Market-specific data stored in `market_data` JSONB field / 마켓별 데이터는 `market_data` JSONB 필드에 저장

2. **Orchestration Engine (`core/orchestrator/`)** / **오케스트레이션 엔진**
   - Central workflow orchestration system / 중앙 워크플로우 오케스트레이션 시스템
   - Manages workflow execution, scheduling, and monitoring / 워크플로우 실행, 스케줄링, 모니터링 관리
   - Event-driven architecture with event bus / 이벤트 버스를 통한 이벤트 기반 아키텍처
   - Handles failure recovery and retries / 장애 복구 및 재시도 처리

3. **Workflow System (`orchestration/workflows/`)** / **워크플로우 시스템**
   - Defines reusable workflows / 재사용 가능한 워크플로우 정의
   - Step-based execution model / 단계 기반 실행 모델
   - Supports parallel and sequential execution / 병렬 및 순차 실행 지원
   - Celery-based task distribution / Celery 기반 작업 분산

4. **AI Orchestration (`ai_agents/orchestrator/`)** / **AI 오케스트레이션**
   - AI Conductor manages multiple AI agents / AI Conductor가 여러 AI 에이전트 관리
   - Coordinates market analysis, pricing, inventory, and promotions / 시장 분석, 가격 책정, 재고, 프로모션 조정
   - Asynchronous task distribution / 비동기 작업 분산

### Data Flow Architecture / 데이터 흐름 아키텍처

1. **Data Collection / 데이터 수집**: Suppliers → Connectors → SourceData (raw_data)
2. **AI Processing / AI 처리**: SourceData → AI Agents → SourceData (ai_data)
3. **Market Distribution / 마켓 배포**: SourceData → Market Connectors → SourceData (market_data)
4. **Analytics Pipeline / 분석 파이프라인**: SourceData → Analytics Engine → Dashboards

### Working with JSONB Data / JSONB 데이터 작업

```python
# Query examples / 쿼리 예시
from source_data.models import SourceData

# Find products active in SmartStore / 스마트스토어에서 활성 상태인 상품 찾기
active_products = SourceData.objects.active_in_market('smartstore')

# Find products with high AI quality score / 높은 AI 품질 점수를 가진 상품
quality_products = SourceData.objects.with_ai_score_above(0.8)

# Access market-specific data / 마켓별 데이터 접근
product = SourceData.objects.get(id=1)
smartstore_data = product.market_data.get('smartstore', {})
price = smartstore_data.get('price')

# Update market data / 마켓 데이터 업데이트
product.market_data['smartstore']['price'] = 15000
product.save(update_fields=['market_data'])
```

### Workflow Examples / 워크플로우 예시

```python
# Product sync workflow / 상품 동기화 워크플로우
from orchestration.workflows.product_sync import ProductSyncWorkflow

workflow = ProductSyncWorkflow({
    'suppliers': ['ownerclan', 'domeggook'],
    'markets': ['smartstore', 'coupang'],
    'sync_mode': 'full'  # or 'incremental'
})
result = await workflow.execute()

# Market management workflow / 마켓 관리 워크플로우
from orchestration.workflows.market_management import MarketManagementWorkflow

workflow = MarketManagementWorkflow({
    'markets': ['smartstore'],
    'tasks': ['price_optimization', 'inventory_sync']
})
result = await workflow.execute()
```

### Key Design Patterns / 주요 디자인 패턴

- **Event Sourcing / 이벤트 소싱**: All data changes tracked as events / 모든 데이터 변경사항을 이벤트로 추적
- **JSONB Storage / JSONB 저장소**: Flexible schema for diverse data sources / 다양한 데이터 소스를 위한 유연한 스키마
- **Orchestration Pattern / 오케스트레이션 패턴**: Workflows coordinate complex processes / 워크플로우가 복잡한 프로세스 조정
- **Market Abstraction / 마켓 추상화**: Each market has its own data structure / 각 마켓은 고유한 데이터 구조 보유
- **AI Pipeline / AI 파이프라인**: Separate AI processing layer / 분리된 AI 처리 레이어

## Debugging Tips / 디버깅 팁

### JSONB Field Debugging / JSONB 필드 디버깅

```python
# Pretty print JSONB data / JSONB 데이터 예쁘게 출력
import json
product = SourceData.objects.get(id=1)
print(json.dumps(product.market_data, indent=2, ensure_ascii=False))

# Check data structure / 데이터 구조 확인
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT jsonb_pretty(market_data) 
        FROM source_data_sourcedata 
        WHERE id = %s
    """, [1])
    print(cursor.fetchone()[0])
```

### Workflow Debugging / 워크플로우 디버깅

```python
# Enable detailed logging / 상세 로깅 활성화
import logging
logging.getLogger('orchestration').setLevel(logging.DEBUG)

# Check workflow status / 워크플로우 상태 확인
from core.orchestrator.engine import OrchestrationEngine
engine = OrchestrationEngine()
status = engine.get_execution_status(execution_id)
print(f"Status: {status['status']}")
print(f"Steps completed: {status['steps_completed']}/{status['total_steps']}")
```

### Celery Task Debugging / Celery 작업 디버깅

```bash
# Monitor tasks in real-time / 실시간 작업 모니터링
celery -A config events

# Inspect active tasks / 활성 작업 검사
celery -A config inspect active

# Purge all tasks / 모든 작업 제거
celery -A config purge
```

## Performance Optimization / 성능 최적화

### JSONB Query Optimization / JSONB 쿼리 최적화

```python
# Use indexes effectively / 인덱스 효과적 사용
# Good - uses GIN index / 좋음 - GIN 인덱스 사용
SourceData.objects.filter(market_data__smartstore__status='active')

# Bad - full table scan / 나쁨 - 전체 테이블 스캔
SourceData.objects.filter(market_data__contains={'smartstore': {'status': 'active'}})

# Bulk updates / 대량 업데이트
from django.db.models import F
SourceData.objects.filter(
    source_type='supplier_product'
).update(
    market_data=F('market_data').bitand({'processed': True})
)
```

### Workflow Optimization / 워크플로우 최적화

- Use parallel execution for independent tasks / 독립적인 작업은 병렬 실행 사용
- Batch database operations / 데이터베이스 작업 일괄 처리
- Cache frequently accessed data / 자주 접근하는 데이터 캐싱
- Use task priorities in Celery / Celery에서 작업 우선순위 사용

## Common Issues and Solutions / 일반적인 문제 및 해결방법

### JSONB Migration Issues / JSONB 마이그레이션 문제

```bash
# If JSONB field migration fails / JSONB 필드 마이그레이션 실패 시
python manage.py migrate --fake source_data
python manage.py migrate source_data --run-syncdb
```

### Celery Connection Issues / Celery 연결 문제

```bash
# Check Redis connection / Redis 연결 확인
redis-cli ping

# Reset Celery / Celery 리셋
celery -A config purge
pkill -f celery
celery -A config worker -l info
```

## Security Considerations / 보안 고려사항

- Environment variables for sensitive configuration / 민감한 설정은 환경 변수 사용
- API authentication for external integrations / 외부 통합을 위한 API 인증
- Data encryption for sensitive information / 민감한 정보 암호화
- Audit logging for data changes / 데이터 변경사항 감사 로깅

## Integration Points / 통합 포인트

### Supplier Connectors / 공급업체 커넥터
- **API Connector**: RESTful API integration / RESTful API 통합
- **Excel Connector**: Excel file processing / 엑셀 파일 처리
- **Webhook Connector**: Real-time data updates / 실시간 데이터 업데이트

### Market Connectors / 마켓 커넥터
- **SmartStore**: Naver SmartStore API / 네이버 스마트스토어 API
- **Coupang**: Coupang Wing API / 쿠팡 윙 API
- **Gmarket**: Gmarket ESM API / 지마켓 ESM API

### AI Services / AI 서비스
- **OpenAI**: GPT models for text processing / 텍스트 처리를 위한 GPT 모델
- **Anthropic**: Claude for complex analysis / 복잡한 분석을 위한 Claude
- **Upstash Redis**: AI memory and conversation history / AI 메모리 및 대화 기록
- **Upstash Vector**: Semantic search and embeddings / 의미 기반 검색 및 임베딩

### Monitoring / 모니터링
- **Prometheus**: Metrics collection / 메트릭 수집
- **Sentry**: Error tracking / 오류 추적

## AI Memory Management / AI 메모리 관리

### Context Management (`context_management/`)
AI 대화 컨텍스트와 메모리를 관리하는 핵심 모듈:

- **ConversationContext**: 대화 컨텍스트 저장 및 관리
- **MemorySnapshot**: 중요 정보 요약 및 스냅샷
- **WorkflowContext**: 워크플로우 실행 컨텍스트 추적

### Memory Storage / 메모리 저장소

```python
# Upstash Redis를 사용한 대화 기록 저장
from context_management.memory_store import UpstashMemoryStore

memory_store = UpstashMemoryStore()
await memory_store.add_message(
    context_id="ctx_123",
    role="human",
    content="상품 가격을 업데이트해주세요"
)

# 대화 기록 조회
messages = await memory_store.get_messages("ctx_123", limit=50)
```

### Semantic Memory / 의미 기반 메모리

```python
# Upstash Vector를 사용한 의미 검색
from context_management.vector_store import UpstashVectorMemory

vector_memory = UpstashVectorMemory()

# 유사한 메모리 검색
similar = await vector_memory.search_similar_memories(
    query="스마트스토어 상품 등록 방법",
    k=5
)

# 관련 컨텍스트 찾기
related = await vector_memory.find_related_contexts(
    query="가격 최적화",
    current_context_id="ctx_123"
)
```

### AI Agent Memory / AI 에이전트 메모리

```python
# 에이전트별 메모리 관리
from ai_agents.memory.chat_memory import AgentChatMemory

chat_memory = AgentChatMemory(
    agent_name="market_manager",
    context_id="ctx_123"
)

# 상호작용 추가
await chat_memory.add_interaction(
    human_input="스마트스토어 수수료는 얼마인가요?",
    ai_response="스마트스토어 기본 수수료는 5.6%입니다.",
    metadata={"market": "smartstore", "topic": "commission"}
)

# 관련 컨텍스트 조회
context = await chat_memory.get_relevant_context(
    query="수수료",
    include_summary=True
)
```

### Memory Retrieval / 메모리 검색

```python
# 통합 메모리 검색
from ai_agents.memory.retrieval import MemoryRetrieval

retrieval = MemoryRetrieval(agent_name="market_manager")

# 관련 메모리 종합 검색
memories = await retrieval.retrieve_relevant_memories(
    query="쿠팡 상품 등록",
    context_id="ctx_123",
    memory_types=["chat", "semantic", "workflow"],
    limit=10
)
```

### Upstash Configuration / Upstash 설정

환경 변수 설정 (.env):
```bash
# Upstash Redis (for AI Memory)
UPSTASH_REDIS_REST_URL=https://your-redis-endpoint.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-redis-token

# Upstash Vector (for Semantic Search)
UPSTASH_VECTOR_REST_URL=https://your-vector-endpoint.upstash.io
UPSTASH_VECTOR_REST_TOKEN=your-vector-token
```