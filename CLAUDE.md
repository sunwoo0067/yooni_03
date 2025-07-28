# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

완전 자동화된 드롭쉬핑 비즈니스를 위한 종합 솔루션입니다. AI 기반 상품 소싱부터 멀티 플랫폼 등록, 주문 처리, 성과 분석까지 모든 과정을 자동화하는 엔터프라이즈급 시스템입니다.

**Core Business Flow:**
1. **Product Sourcing** → Wholesaler APIs (Ownerclan, Zentrade, Domeggook)
2. **AI Processing** → Product analysis, pricing optimization, description generation
3. **Multi-Platform Registration** → Coupang, Naver, 11st marketplaces
4. **Order Automation** → Real-time order processing, inventory sync, shipping tracking
5. **Analytics & Monitoring** → Performance tracking, profit analysis, demand forecasting

## Technology Stack

**Backend:**
- FastAPI (Python 3.11+)
- SQLAlchemy ORM with async support
- PostgreSQL (production), SQLite (development)
- Redis for caching and task queues
- Alembic for database migrations

**Frontend:**
- React 18 with TypeScript
- Vite build system
- Material-UI (MUI) for components
- React Query for server state caching
- Redux Toolkit for global state
- Vitest for testing

**AI Integration:**
- LangChain framework
- Google Gemini API
- Ollama for local LLM
- Support for OpenAI and Anthropic Claude

**Infrastructure:**
- Docker containers
- Nginx reverse proxy
- Prometheus/Grafana monitoring
- Automated backup systems

## Development Commands

### Backend Development

```bash
# Development environment setup
make setup-dev

# Run development server
cd backend && python main.py

# Database migrations
make db-migrate                    # Apply migrations
make db-migration                  # Create new migration
alembic revision --autogenerate -m "description"  # Direct migration creation
alembic upgrade head              # Apply migrations directly

# Testing
make test                         # Run all tests
make test-unit                    # Unit tests only
make test-integration             # Integration tests
make test-e2e                     # End-to-end tests
make test-security                # Security tests
pytest tests/ -v                  # Direct pytest execution
pytest tests/ --cov=app --cov-report=html  # With coverage
pytest -m unit                    # Run tests by marker
pytest -m "not slow"              # Skip slow tests
python run_tests.py --parallel    # Run tests in parallel
python run_tests.py --module api  # Test specific module

# Code quality
make lint-fix                     # Fix linting issues
make format                       # Format code
black app/                        # Format Python code
flake8 app/                      # Lint Python code
mypy app/                        # Type checking
```

### Frontend Development

```bash
# Install dependencies
cd frontend && npm install

# Development server
npm run dev                       # Start dev server at localhost:3000

# Testing
npm run test                      # Run unit tests
npm run test:coverage             # Run with coverage
npm run test:ui                   # Interactive test UI

# Build and deployment
npm run build                     # Production build
npm run preview                   # Preview production build
npm run lint                      # ESLint
npm run lint:fix                  # Fix linting issues
```

### Docker Environment

```bash
# Development
make dev-start                    # Start all services
make dev-stop                     # Stop all services
make dev-logs                     # View logs
make dev-restart                  # Restart services

# Production
make prod-start                   # Start production environment
make prod-stop                    # Stop production environment
make prod-logs                    # View production logs

# Staging
make staging-start                # Start staging environment
make staging-stop                 # Stop staging environment

# Database operations
make db-reset                     # Reset development database
```

### Additional Make Commands

```bash
# Health and monitoring
make health                       # Check system health
make monitoring-start             # Start Prometheus/Grafana
make monitoring-stop              # Stop monitoring services

# Maintenance
make backup                       # Create database backup
make clean                        # Clean up containers and images
make clean-all                    # Remove ALL containers, images, volumes

# Logs
make logs-backend                 # View backend logs
make logs-frontend                # View frontend logs
make logs-db                      # View database logs
make logs-nginx                   # View nginx logs

# Development tools
make shell-backend                # Open bash shell in backend container
make shell-db                     # Open PostgreSQL shell
make shell-redis                  # Open Redis CLI
```

## Architecture Overview

### High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Wholesalers   │     │   Marketplaces  │     │     Frontend    │
│  (APIs/Scraping)│     │  (APIs/OAuth)   │     │   (React/MUI)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         └───────────┬───────────┘                        │
                     ▼                                     ▼
         ┌───────────────────────────────────┐  ┌─────────────────┐
         │        FastAPI Backend            │  │   WebSocket     │
         │  ┌─────────────────────────────┐  │  │   (Real-time)   │
         │  │    Service Layer (DDD)      │  │  └─────────────────┘
         │  │  • AI Services              │  │
         │  │  • Sourcing Engine          │  │
         │  │  • Order Processing         │  │
         │  │  • Platform Integration     │  │
         │  └─────────────────────────────┘  │
         │  ┌─────────────────────────────┐  │
         │  │    Repository Layer         │  │
         │  │  (SQLAlchemy + Async)       │  │
         │  └─────────────────────────────┘  │
         └───────────────┬───────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
    ┌─────────┐                    ┌─────────┐
    │PostgreSQL│                    │  Redis  │
    │(SQLite) │                    │ (Cache) │
    └─────────┘                    └─────────┘
```

### Service Layer Architecture

The backend follows Domain-Driven Design with services organized by business capabilities:

- **`app/services/ai/`** - AI integration services (Gemini, Ollama, LangChain)
- **`app/services/sourcing/`** - Smart sourcing engine and market data collection
- **`app/services/platforms/`** - Multi-platform API integration (Coupang, Naver, 11st)
- **`app/services/order_processing/`** - Order processing and automation
- **`app/services/dropshipping/`** - Dropshipping-specific features
- **`app/services/wholesalers/`** - Wholesale supplier integrations
- **`app/services/marketing/`** - Marketing automation and A/B testing
- **`app/services/analytics/`** - Data analysis and performance monitoring
- **`app/services/monitoring/`** - System monitoring and metrics collection
- **`app/services/sync/`** - Data synchronization services
- **`app/services/tasks/`** - Background task processing

### Key Architectural Patterns

1. **Async/Await Pattern**: All I/O operations use async/await for performance
2. **Dependency Injection**: FastAPI's Depends system for service injection
3. **Repository/CRUD Pattern**: Generic CRUD base classes with type safety
4. **Manager/Service Pattern**: Complex business logic encapsulated in manager classes
5. **Middleware Chain**: Cross-cutting concerns (logging, monitoring, rate limiting)
6. **Abstract Base Classes**: Common interfaces for integrations (e.g., BaseWholesaler)
7. **Service Locator Pattern**: Dynamic service registration and retrieval

### Database Architecture

**Base Model System:**
All models inherit from `BaseModel` with mixins:
- `TimestampMixin` - Created/updated timestamps
- `SoftDeleteMixin` - Soft delete functionality
- `UUIDMixin` - UUID primary keys
- `MetadataMixin` - Flexible JSONB metadata storage

**Core Entity Relationships:**
- **User** → PlatformAccount, Product, Order (1:N relationships)
- **Product** → ProductVariant, PlatformListing, PriceHistory (1:N relationships)
- **Order** → OrderItem, OrderPayment, OrderShipment (1:N relationships)
- **CollectedProduct** → CollectedProductHistory (versioning pattern)

**Database Compatibility:**
The system automatically handles both SQLite (development) and PostgreSQL (production) using conditional JSON/JSONB types.

### API Structure

RESTful API with consistent patterns:
```
/api/v1/
├── /platform-accounts    # Platform account management
├── /products            # Product management
├── /ai                  # AI services
├── /sourcing            # Sourcing management
├── /orders              # Order processing
├── /dropshipping        # Dropshipping features
├── /marketing           # Marketing automation
├── /analytics           # Analytics and reports
├── /monitoring          # System monitoring
├── /product-collector   # Product collection services
├── /wholesaler-sync     # Wholesale supplier sync
└── /websocket           # Real-time communication
```

Note: Some endpoints may be temporarily disabled during development (check `backend/app/api/v1/__init__.py`).

### Middleware Stack

1. **CORS**: Configurable origins with development-friendly defaults
2. **GZip Compression**: Automatic response compression
3. **Trusted Host**: Security middleware for host validation
4. **Rate Limiting**: Redis-based sliding window rate limiter
   - Per-endpoint configuration
   - User vs anonymous differentiation
   - Rate limit headers (X-RateLimit-*)
5. **Logging**: Request/response logging with correlation IDs

### Background Task Architecture

Custom lightweight task queue implementation:
- Priority-based queue with Redis backend
- Automatic retries with exponential backoff
- Task status tracking (PENDING, RUNNING, COMPLETED, FAILED)
- Configurable worker pool
- Result storage and error tracking

## Configuration Management

### Environment Variables

The system uses environment-specific configuration:
- `.env.development` - Development settings
- `.env.production` - Production settings (copy and configure)
- `backend/app/core/config.py` - Unified configuration with V1/V2 merger

Key configuration areas:
- Database connections (supports both SQLite and PostgreSQL)
- AI service API keys (Gemini, OpenAI, Anthropic)
- Marketplace API credentials
- Wholesale supplier settings
- Security settings (JWT, encryption keys)
- Redis configuration
- Monitoring and logging settings

### Running Different Environments

```bash
# Development
cp .env.development .env
make dev-start

# Staging
make staging-start

# Production
cp .env.production .env
# Edit .env with production values
make prod-start
```

## Testing Strategy

### Test Organization
- **`tests/unit/`** - Fast, isolated unit tests
- **`tests/integration/`** - Component integration tests
- **`tests/e2e/`** - End-to-end workflow tests

### Test Markers
Use pytest markers for test categorization:
```bash
pytest -m unit                   # Unit tests only
pytest -m integration           # Integration tests only
pytest -m "not slow"            # Skip slow tests
pytest -m requires_db           # Database-dependent tests
pytest -m requires_redis        # Redis-dependent tests
pytest -m requires_api_key      # External API tests
pytest -m performance           # Performance tests
pytest -m security              # Security tests
```

### Coverage Requirements
- Minimum 80% code coverage
- Reports generated in `htmlcov/`
- Coverage config in `pyproject.toml` and `.coveragerc`

### Frontend Testing
Vitest with coverage thresholds:
- Lines: 80%
- Functions: 75%
- Branches: 70%
- Statements: 80%

## External Service Integration

### Marketplace APIs
- **Coupang**: Partner API for product listing and order management
- **Naver**: Smart Store API for e-commerce operations
- **11st**: Open Market API for multi-platform selling

### Wholesale Suppliers
All suppliers implement the `BaseWholesaler` abstract class:
- **Ownerclan**: GraphQL API for product sourcing
- **Domeggook**: REST API for wholesale products
- **Zentrade**: Custom API for B2B sourcing

### AI Services
Multi-provider support with automatic fallback:
- **Google Gemini**: Primary AI for product analysis
- **Ollama**: Local LLM for privacy-sensitive operations
- **OpenAI/Anthropic**: Additional providers with fallback

## Database Operations

### Migration Workflow
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### Database Access Patterns
- Use async sessions: `AsyncSession`
- CRUD operations through repository pattern
- Bulk operations for performance-critical code
- Connection pooling configured in settings
- Automatic retry on connection failures

## Monitoring and Logging

### Health Checks
```bash
curl http://localhost:8000/health    # Application health
make health                          # Comprehensive system check
```

### Logging
- Structured JSON logging in production
- Debug logging in development
- Separate log levels by environment
- Log rotation and retention configured
- Correlation IDs for request tracing

### Metrics
- Prometheus metrics collection
- Grafana dashboards for visualization
- Custom business metrics tracking
- Performance monitoring for all external API calls
- Resource usage monitoring (CPU, memory, connections)

## Security Best Practices

### API Security
- JWT token authentication with refresh tokens
- Per-endpoint rate limiting
- Input validation with Pydantic
- SQL injection protection via ORM
- Request size limits

### Data Protection
- Encrypted storage for sensitive data
- API keys stored as SecretStr
- Database connection encryption
- CORS properly configured
- Secure password hashing (bcrypt)

## Performance Optimization

### Caching Strategy
- Redis for session and API response caching
- Database query result caching
- AI response caching to reduce API costs
- CDN integration for static assets
- Browser caching headers

### Async Operations
- All I/O operations use async/await
- Connection pooling for databases
- Batch processing for bulk operations
- Background tasks for heavy computations
- Concurrent request handling

## Common Development Workflows

### Adding New Marketplace Integration
1. Create new API class in `app/services/platforms/`
2. Implement base marketplace interface
3. Add platform type to enums
4. Create API credentials configuration
5. Add integration tests
6. Update documentation

### Adding New AI Service
1. Create service class in `app/services/ai/`
2. Implement AI service interface
3. Add configuration for API keys
4. Implement fallback mechanism
5. Add caching for responses
6. Create performance tests

### Database Schema Changes
1. Modify models in `app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration
4. Test migration on development database
5. Apply to staging/production environments

### Running Single Test
```bash
# Backend
pytest tests/test_api/test_products.py::test_create_product -v

# Frontend
npm run test -- ProductList.test.tsx
```

### Working with Wholesaler APIs
```bash
# Test individual wholesaler API
python backend/test_wholesaler_fixed.py

# Collect products from all wholesalers
python backend/collect_all_wholesalers.py

# Test marketplace integration
python backend/integrated_marketplace_system.py
```

### Quick Development Cycle
```bash
# 1. Start development environment
make dev-start

# 2. Watch backend logs
make logs-backend

# 3. Run specific service
cd backend && python main.py

# 4. Test API endpoint
curl http://localhost:8000/api/v1/health

# 5. Run tests while developing
pytest -xvs tests/unit/ --lf  # Run last failed
```

## Frontend Architecture

### Build Configuration
- **Vite** optimizes dependencies and chunks
- Path aliases configured: `@components`, `@pages`, `@hooks`, `@utils`, `@services`, `@store`, `@types`, `@assets`
- API proxy configured for development
- Manual chunking for optimal bundle sizes

### State Management
- **Redux Toolkit** for global state
- **React Query** for server state caching
- **React Hook Form** for form state
- **Socket.io** for real-time updates

## Performance Targets

- API response time: < 200ms average
- Product processing: 1,000/hour
- AI analysis: 50 products/second
- System uptime: 99.9%
- Database query time: < 50ms
- Cache hit rate: > 80%

## Deployment

### Environment Setup
```bash
# Development
make setup-dev

# Production deployment
make deploy
```

### Docker Commands
```bash
# Build containers
make prod-build

# Start production environment
make prod-start

# View logs
make prod-logs

# Database backup
make backup
```

### SSL Certificate Management
```bash
# Generate self-signed certificate
make ssl-cert

# Use Let's Encrypt
make ssl-letsencrypt
```

## Troubleshooting

### Common Issues

**Database Connection Issues:**
- Check DATABASE_URL in .env
- Verify database server is running
- Check connection pool settings
- Review firewall rules

**AI Service Failures:**
- Verify API keys are configured
- Check service-specific rate limits
- Review fallback service configuration
- Monitor API usage quotas

**Performance Issues:**
- Monitor Redis cache hit rates
- Check database query performance
- Review async operation bottlenecks
- Analyze slow query logs

### Debug Mode
Set `DEBUG=True` in environment for:
- Detailed error messages
- Auto-reload on code changes
- Enhanced logging output
- API documentation at `/docs`
- SQL query logging

### Log Analysis
```bash
# View application logs
make logs-backend

# Database logs
make logs-db

# System health check
make health

# Redis monitoring
make shell-redis
redis-cli MONITOR
```

## Project-Specific Notes

- Some services may be temporarily disabled during development (check comments in `main.py`)
- The system supports both SQLite (development) and PostgreSQL (production)
- Frontend runs on port 3000, backend on port 8000
- API documentation available at http://localhost:8000/docs
- Additional development services: MailHog (8025), pgAdmin (5050)

## Windows-Specific Development Notes

When developing on Windows:
- Use `python` instead of `python3` in commands
- Ensure Docker Desktop is running for Docker commands
- Use Git Bash or WSL for better Unix command compatibility
- Path separators in Python code are handled automatically by pathlib

## Environment Dependencies

### Required Services
- **PostgreSQL 13+** (or SQLite for development)
- **Redis 6+** for caching and task queues
- **Docker** for containerized deployment
- **Node.js 16+** for frontend development

### External API Requirements
- **Google Gemini API Key** for AI features
- **Wholesaler Credentials** (OwnerClan, Zentrade, Domeggook)
- **Marketplace API Keys** (Coupang, Naver, 11st)

### Development Ports
- Backend API: `http://localhost:8000`
- Frontend Dev: `http://localhost:3000`
- API Documentation: `http://localhost:8000/docs`
- MailHog (email testing): `http://localhost:8025`
- pgAdmin: `http://localhost:5050`

## Critical Files and Entry Points

### Backend
- **`backend/main.py`** - FastAPI application entry point with lifespan management
- **`backend/app/core/config.py`** - Core configuration management (V1/V2 merger)
- **`backend/app/api/v1/__init__.py`** - API router configuration and endpoint management
- **`backend/app/services/database/database.py`** - Database connection management
- **`backend/app/models/base.py`** - Base model with all mixins
- **`backend/app/middleware/rate_limit.py`** - Custom rate limiting implementation

### Frontend
- **`frontend/src/main.tsx`** - React application entry point
- **`frontend/src/App.tsx`** - Main application component
- **`frontend/vite.config.ts`** - Build configuration and path aliases
- **`frontend/src/store/index.ts`** - Redux store configuration
- **`frontend/src/services/api.ts`** - API client configuration

## Testing Quick Reference

```bash
# Run specific test file
pytest tests/test_api/test_products.py -v

# Run tests with specific marker
pytest -m unit -v

# Run tests in parallel (using pytest-xdist)
pytest -n auto

# Run with coverage report
pytest --cov=app --cov-report=html

# Skip slow tests
pytest -m "not slow"

# Run tests for specific module
python run_tests.py --module products

# Run only failed tests from last run
pytest --lf

# Run tests with detailed output
pytest -vvs

# Run tests matching keyword
pytest -k "test_create"
```

## 📚 Claude Code 서브에이전트 완벽 활용 가이드

### 🎯 서브에이전트 활용 철학
Claude Code의 서브에이전트는 단순한 도구가 아닌, 특정 작업에 최적화된 전문가입니다. awesome-claude-agents 패턴을 기반으로, 우리 프로젝트에서는 다음과 같이 활용합니다:

1. **자동 에이전트 선택**: 작업의 성격에 따라 Claude Code가 자동으로 최적의 에이전트를 선택
2. **병렬 처리**: 여러 에이전트가 동시에 작업하여 속도 향상
3. **컨텍스트 전달**: 에이전트 간 작업 결과를 자동으로 공유

### 🤖 내장 서브에이전트 목록 및 활용법

#### 1. **general-purpose** - 만능 작업 처리자
**자동 실행 조건:**
- 3개 이상의 파일을 검색해야 할 때
- 복잡한 리팩토링이 필요할 때
- 프로젝트 전체 구조를 파악해야 할 때

**활용 예시:**
```
"주문 처리 로직이 어떻게 구성되어 있는지 전체적으로 분석해줘"
"모든 API 엔드포인트에서 인증 체크가 제대로 되고 있는지 확인해줘"
"상품 가격 계산하는 모든 부분을 찾아서 마진율 30%로 통일해줘"
```

#### 2. **code-reviewer** - 코드 품질 검토 전문가
**자동 실행 조건:**
- 새로운 기능 구현 완료 시
- 100줄 이상의 코드 수정 시
- 보안 관련 코드 작성 시

**활용 예시:**
```
"방금 작성한 주문 처리 코드를 검토해줘"
"이 API가 SQL 인젝션에 안전한지 확인해줘"
"성능상 병목이 될 수 있는 부분을 찾아줘"
```

#### 3. **test-automator** - 테스트 자동화 전문가
**자동 실행 조건:**
- 새로운 기능 추가 시
- 테스트 커버리지가 80% 미만일 때
- CI/CD 파이프라인 설정 시

**활용 예시:**
```
"상품 등록 API에 대한 통합 테스트를 작성해줘"
"주문 처리 전체 플로우에 대한 E2E 테스트를 만들어줘"
"테스트 커버리지를 90%까지 올려줘"
```

#### 4. **security-auditor** - 보안 검토 전문가
**활용 예시:**
```
"JWT 토큰 인증이 모든 API에 적용되었는지 확인해줘"
"환경 변수에 노출된 시크릿이 있는지 검사해줘"
"OWASP Top 10 기준으로 보안 취약점을 점검해줘"
```

#### 5. **performance-engineer** - 성능 최적화 전문가
**활용 예시:**
```
"상품 검색 API의 응답 시간을 200ms 이하로 최적화해줘"
"데이터베이스 쿼리 중 N+1 문제가 있는지 찾아줘"
"Redis 캐싱을 적용해서 API 성능을 개선해줘"
```

### 🚀 드롭쉬핑 프로젝트 특화 활용법

#### 상품 관리 작업
```
# 복잡한 상품 검색 로직이 필요한 경우
"모든 도매처 API에서 마진 40% 이상인 상품을 찾는 로직을 구현해줘"
→ general-purpose가 자동으로 모든 wholesaler API 파일을 분석하고 통합 로직 구현

# 성능이 중요한 경우
"상품 목록 조회 API가 너무 느려. 1초 이내로 응답하도록 최적화해줘"
→ performance-engineer가 자동으로 쿼리 분석, 인덱스 추가, 캐싱 적용
```

#### 주문 처리 작업
```
# 복잡한 비즈니스 로직
"주문이 들어오면 재고 확인 → 도매처 주문 → 배송 추적까지 자동화해줘"
→ general-purpose가 전체 플로우 설계 후 구현

# 보안이 중요한 경우  
"결제 정보 처리 부분의 보안을 강화해줘"
→ security-auditor가 PCI DSS 기준으로 검토 및 개선
```

### 📋 서브에이전트 활용 모범 사례

#### 1. **명확한 목표 제시**
```
❌ 나쁜 예: "코드 개선해줘"
✅ 좋은 예: "상품 등록 API의 응답 시간을 500ms 이하로 개선해줘"
```

#### 2. **컨텍스트 제공**
```
❌ 나쁜 예: "버그 고쳐줘"
✅ 좋은 예: "쿠팡 API 호출 시 401 에러가 발생해. 인증 토큰 관련 문제인 것 같아"
```

#### 3. **단계별 접근**
```
1단계: "현재 주문 처리 시스템의 구조를 분석해줘"
2단계: "병목 지점을 찾아서 개선 방안을 제시해줘"
3단계: "제시한 방안을 구현해줘"
```

### 🔄 서브에이전트 자동 활용 시나리오

#### 시나리오 1: 새 기능 개발
```
User: "네이버 스마트스토어 상품 동기화 기능을 추가해줘"

자동 실행되는 에이전트:
1. general-purpose: 기존 동기화 로직 분석
2. general-purpose: 네이버 API 통합 구현
3. test-automator: 테스트 코드 자동 생성
4. code-reviewer: 최종 코드 검토
```

#### 시나리오 2: 버그 수정
```
User: "상품 가격이 음수로 표시되는 버그를 고쳐줘"

자동 실행되는 에이전트:
1. general-purpose: 버그 원인 분석
2. general-purpose: 수정 사항 구현
3. test-automator: 회귀 테스트 추가
4. code-reviewer: 수정 사항 검토
```

#### 시나리오 3: 성능 최적화
```
User: "대시보드 로딩이 5초나 걸려. 1초 이내로 줄여줘"

자동 실행되는 에이전트:
1. performance-engineer: 성능 병목 분석
2. performance-engineer: 쿼리 최적화 및 캐싱 적용
3. general-purpose: 프론트엔드 레이지 로딩 구현
4. test-automator: 성능 테스트 추가
```

### 💡 프로 팁: 서브에이전트 활용 극대화

1. **병렬 작업 요청**
   ```
   "상품 등록 API를 만들면서 동시에 테스트 코드도 작성하고, 
   API 문서도 업데이트해줘"
   ```

2. **조건부 작업**
   ```
   "이 코드를 리팩토링하되, 테스트가 모두 통과하는 것을 확인하면서 진행해줘"
   ```

3. **반복 작업 자동화**
   ```
   "모든 API 엔드포인트에 rate limiting을 추가하고, 
   각각에 대한 테스트도 작성해줘"
   ```

### 🎮 드롭쉬핑 프로젝트 전용 서브에이전트 커스터마이징

우리 프로젝트를 위해 특별히 커스터마이징된 서브에이전트 프롬프트가 준비되어 있습니다:

1. **`.claude/agent-prompts/dropshipping-general-purpose.md`**
   - 도매처/마켓플레이스 API 전문 지식 내장
   - 프로젝트 구조 완벽 이해
   - 복잡한 통합 작업 최적화

2. **`.claude/agent-prompts/dropshipping-code-reviewer.md`**
   - 드롭쉬핑 특화 보안 체크리스트
   - 금융 계산 정확성 검증
   - API 통합 모범 사례 적용

3. **`.claude/agent-prompts/dropshipping-test-automator.md`**
   - 외부 API 모킹 전략
   - 주문 플로우 E2E 테스트
   - 플랫폼별 특수 요구사항 테스트

### 🚨 자동 트리거 규칙

자세한 트리거 규칙은 `.claude/agent-prompts/agent-triggers.md`에 정의되어 있습니다.

**주요 자동 실행 패턴:**
- 도매처 API 작업 → general-purpose + test-automator
- 금융 관련 코드 → code-reviewer + security-auditor
- 성능 이슈 언급 → performance-engineer 자동 실행
- 새 기능 구현 → 구현 → 테스트 → 리뷰 순차 실행

### 비개발자를 위한 활용 예시

**프로젝트 이해하기:**
```
"이 프로젝트의 주요 기능들을 설명해줘"
"상품 관리 시스템이 어떻게 구성되어 있는지 알려줘"
```

**기능 찾기 및 수정:**
```
"로그인 기능이 어디에 있는지 찾아줘"
"상품 가격을 자동으로 10% 할인하는 기능을 추가해줘"
```

**문제 해결:**
```
"주문이 실패하는 원인을 찾아서 해결해줘"
"이 에러 메시지가 왜 나오는지 분석해줘"
```

**코드 개선:**
```
"이 기능을 더 빠르게 만들 수 있는 방법을 찾아줘"
"보안상 위험한 코드가 있는지 검사해줘"
```

### 서브에이전트 자동 활용

Claude Code는 작업의 복잡도에 따라 자동으로 적절한 서브에이전트를 선택합니다:
- 여러 파일 검색이 필요한 경우 → general-purpose 자동 실행
- 코드 작성 후 → code-review-expert 자동 실행
- 복잡한 디버깅 → general-purpose로 원인 분석

### 팁: 자연스러운 한국어로 요청하세요

기술 용어를 몰라도 괜찮습니다. 하고 싶은 작업을 일상적인 언어로 설명하면 Claude Code가 이해하고 적절한 서브에이전트를 활용해 작업을 수행합니다.

예시:
- "손님이 물건을 살 때 포인트를 쌓을 수 있게 해줘"
- "매일 밤 12시에 재고를 확인하는 기능을 만들어줘"
- "관리자만 볼 수 있는 페이지를 추가해줘"

## 🚀 드롭쉬핑 특화 Claude 에이전트 시스템

프로젝트에 최적화된 드롭쉬핑 전문 에이전트들이 준비되어 있습니다. 각 에이전트는 특정 업무에 특화되어 있으며, 필요에 따라 자동으로 협업합니다.

### 사용 가능한 드롭쉬핑 에이전트

#### 1. 오케스트레이터 (전체 관리)
- **Dropship Manager**: 전체 비즈니스 워크플로우 조정
- **Market Analyst**: 시장 트렌드 분석 및 예측
- **Team Assembler**: 작업에 맞는 에이전트 자동 구성

#### 2. 비즈니스 전문가
- **Product Hunter**: AI 기반 수익성 높은 상품 발굴
- **Pricing Strategist**: 동적 가격 최적화 및 마진 관리
- **Listing Optimizer**: 플랫폼별 상품 설명 최적화
- **Order Processor**: 주문 자동화 및 재고 관리

#### 3. 플랫폼 전문가
- **Coupang Expert**: 쿠팡 로켓배송, SEO, 리뷰 관리
- **Naver Expert**: 네이버 스마트스토어 최적화
- **11st Expert**: 11번가 오픈마켓 전문 관리

#### 4. 기술 지원
- **API Integrator**: 도매처/마켓플레이스 API 통합
- **Performance Optimizer**: 시스템 성능 최적화
- **Data Analyst**: 판매 데이터 분석 및 인사이트

### 에이전트 활용 예시

#### 상품 소싱 및 등록 자동화
```
"패션 카테고리에서 마진 40% 이상인 상품 20개를 찾아서 모든 플랫폼에 등록해줘"
→ Product Hunter + Pricing Strategist + Platform Experts 자동 협업
```

#### 가격 최적화
```
"경쟁사보다 10% 저렴하면서도 마진 30%를 확보할 수 있는 가격 전략을 세워줘"
→ Pricing Strategist가 실시간 시장 분석 후 최적 가격 도출
```

#### 플랫폼별 최적화
```
"이 상품을 쿠팡 로켓배송 상품으로 등록하고 베스트셀러 전략을 세워줘"
→ Coupang Expert가 쿠팡 특화 전략 수립 및 실행
```

#### 성과 분석 및 개선
```
"지난 달 판매 데이터를 분석하고 수익률이 낮은 상품들의 개선 방안을 제시해줘"
→ Data Analyst + Market Analyst가 협업하여 인사이트 도출
```

### 에이전트 상세 정보

모든 에이전트의 상세 설명과 기술 구현은 `.claude/agents/` 디렉토리에서 확인할 수 있습니다:
- `.claude/agents/index.md` - 전체 에이전트 목록 및 가이드
- `.claude/agents/dropship-manager.md` - 메인 오케스트레이터
- `.claude/agents/product-hunter.md` - 상품 소싱 전문가
- `.claude/agents/pricing-strategist.md` - 가격 전략 전문가
- `.claude/agents/platform-coupang.md` - 쿠팡 플랫폼 전문가

### 워크플로우 자동화 예시

#### 일일 상품 업데이트 워크플로우
1. Market Analyst가 트렌드 분석
2. Product Hunter가 신상품 발굴
3. Pricing Strategist가 가격 최적화
4. Platform Experts가 각 플랫폼에 등록
5. Data Analyst가 성과 모니터링

이 모든 과정이 자동으로 진행되며, 각 단계의 결과는 실시간으로 확인할 수 있습니다.

## API Integration Status

### Wholesaler APIs (도매처)
- **OwnerClan**: GraphQL API - JWT authentication works, product query needs fixing (400 error)
- **Zentrade**: XML API (EUC-KR) - Previously working, currently 404 error
- **Domeggook**: REST API - Not activated, using sample data

### Marketplace APIs (마켓플레이스)
- **Coupang**: HMAC signature auth - Implementation complete, needs partner approval
- **Naver**: OAuth 2.0 - Implementation complete, needs OAuth flow setup
- **11st**: XML API - Implementation complete, needs API activation

### Data Collection
- PostgreSQL database with `simple_collected_products` table
- 15 products collected: 5 OwnerClan (jewelry), 5 Zentrade (kitchenware), 5 Domeggook (sample)
- Integrated marketplace system registers products with 30% default margin

## Key Workflows

### Collect Products from Wholesalers
```bash
cd backend
python collect_all_wholesalers.py          # Collect from all sources
python test_final_apis.py                   # Test individual APIs
python integrated_marketplace_system.py     # Register to marketplaces
python marketplace_dashboard.py             # View dashboard
```

### Test API Connections
```bash
python test_marketplace_apis.py            # Test marketplace APIs
python test_domeggook_simple.py           # Test Domeggook
python test_wholesaler_fixed.py           # Test all wholesalers
```

## Recent Implementation (2025-07-27)

### Completed Tasks
1. **Wholesaler API Integration**
   - Fixed OwnerClan JWT token handling (plain text response)
   - Fixed Zentrade XML parsing with EUC-KR encoding
   - Created Domeggook sample data fallback

2. **Marketplace API Integration**
   - Implemented Coupang Partners API client
   - Implemented Naver Smart Store API client
   - Implemented 11st Open Market API client

3. **Database Integration**
   - Created simplified product collection tables
   - Implemented product transformation and storage
   - Built integrated dashboard with analytics

4. **Documentation**
   - Created `WHOLESALER_API_SUMMARY.md`
   - Created `MARKETPLACE_API_SUMMARY.md`
   - Updated test scripts and collection tools

## Important Files Created Recently
- `backend/app/services/wholesalers/*_fixed.py` - Fixed API implementations
- `backend/test_*.py` - Various API test scripts
- `backend/collect_*.py` - Product collection scripts
- `backend/integrated_marketplace_system.py` - Main integration system
- `backend/marketplace_dashboard.py` - Analytics dashboard
- `.claude/agents/` - Dropshipping-specific AI agent definitions
- `.claude/agent-prompts/` - Custom subagent prompts for enhanced development

---

## AI Development Team Configuration
*Updated by team-configurator on 2025-07-28*

Your dropshipping e-commerce project uses: **FastAPI (Python 3.11+)**, **React 18 with TypeScript**, **PostgreSQL/SQLite**, **Redis**, **Material-UI**, **LangChain**, **Google Gemini API**, and **Docker**

### 🎯 Core Technical Specialists

#### Backend Excellence
- **@python-backend-expert** → FastAPI, SQLAlchemy, and async Python mastery
  - Complex dropshipping business logic and workflows
  - Database models with performance optimization
  - Async patterns for high-throughput operations
  - Service layer architecture (DDD patterns)
  
- **@api-integration-specialist** → External API integrations and design
  - Wholesaler APIs: OwnerClan (GraphQL), Zentrade (XML), Domeggook (REST)
  - Marketplace APIs: Coupang (HMAC), Naver (OAuth), 11st (XML)
  - Robust error handling, retries, and fallback strategies
  - RESTful API design and documentation

#### Frontend Mastery
- **@react-ui-architect** → React 18, TypeScript, and Material-UI expertise
  - Real-time dashboards with WebSocket integration
  - Complex data visualization and analytics interfaces
  - Component design patterns and reusable libraries
  - State management with Redux Toolkit and React Query
  
- **@frontend-performance-expert** → Client-side optimization and UX
  - Bundle optimization and code splitting
  - Progressive loading and caching strategies
  - Cross-browser compatibility and responsive design
  - Performance monitoring and Core Web Vitals

#### AI & Intelligence
- **@ai-dropshipping-specialist** → LangChain, Gemini API, and ML integration
  - Product analysis and automated description generation
  - Dynamic pricing optimization algorithms
  - Market trend analysis and demand forecasting
  - Multi-provider AI fallback strategies (Gemini, Ollama, OpenAI)
  
- **@data-pipeline-engineer** → ETL processes and real-time analytics
  - Wholesaler data collection and normalization
  - Real-time inventory synchronization
  - Sales analytics and performance metrics
  - Data quality validation and cleansing

#### Infrastructure & Security
- **@database-performance-optimizer** → PostgreSQL/SQLite optimization
  - Query performance tuning and indexing strategies
  - Redis caching for high-frequency operations
  - Database scaling and connection pooling
  - Migration strategies and data integrity
  
- **@security-compliance-auditor** → Security best practices for e-commerce
  - Financial data protection and PCI compliance
  - API security and authentication (JWT, OAuth)
  - Rate limiting and DDoS protection
  - Vulnerability assessment and penetration testing

### 🚀 Dropshipping Business Domain Specialists

#### E-commerce Operations
- **@dropshipping-workflow-expert** → End-to-end business process automation
  - Order processing: customer order → wholesaler purchase → fulfillment
  - Inventory synchronization across multiple platforms
  - Automated repricing based on supplier changes
  - Exception handling and manual intervention workflows

#### Multi-Platform Management
- **@marketplace-integration-expert** → Platform-specific optimizations
  - **Coupang**: Rocket Delivery optimization, keyword research, review management
  - **Naver**: Smart Store SEO, Shopping Search optimization
  - **11st**: Open Market strategies, promotional campaigns
  - Cross-platform inventory management and conflict resolution

#### Intelligent Automation
- **@ai-business-optimizer** → Machine learning for business optimization
  - Profit margin optimization with competitive analysis
  - Customer behavior analysis and segmentation
  - Automated A/B testing for listings and pricing
  - Predictive analytics for inventory management

### 🛠️ Development Quality & Operations

#### Code Excellence
- **@code-quality-guardian** → Architecture review and best practices
  - Code review with dropshipping business context
  - Performance impact analysis for financial calculations
  - Security review for payment and customer data handling
  - Maintainability and technical debt management
  
- **@test-automation-specialist** → Comprehensive testing strategies
  - Unit tests for business logic (pricing, margin calculations)
  - Integration tests for external API interactions
  - E2E tests for complete order workflows
  - Load testing for high-volume product processing

#### DevOps & Monitoring
- **@containerization-expert** → Docker, orchestration, and deployment
  - Multi-environment setup (dev, staging, production)
  - Automated CI/CD pipelines with quality gates
  - Infrastructure as code and environment management
  - Blue-green deployments and rollback strategies
  
- **@monitoring-analytics-expert** → System observability and business metrics
  - Application performance monitoring (APM)
  - Business KPI tracking and alerting
  - Error tracking and root cause analysis
  - Resource utilization and cost optimization

### 🎪 Orchestration & Project Management

- **@tech-lead-orchestrator** → Multi-phase project coordination
  - Research → Planning → Execution workflow
  - Cross-team coordination for complex features
  - Risk assessment and mitigation strategies
  - Human-in-the-loop approval gates for critical changes

- **@project-analyst** → Technology stack analysis and decision support
  - Codebase archaeology and documentation generation
  - Architecture decision records and technical debt assessment
  - Technology evaluation for new requirements
  - Performance benchmarking and optimization recommendations

### 🎯 Task Routing Intelligence

#### Automatic Specialist Assignment

**Product Management Tasks:**
```
"Implement automatic product collection from all wholesalers"
→ @python-backend-expert + @ai-dropshipping-specialist + @database-performance-optimizer
```

**Performance Critical Work:**
```
"Optimize product search API to respond under 200ms"
→ @database-performance-optimizer + @frontend-performance-expert + @monitoring-analytics-expert
```

**New Feature Development:**
```
"Add real-time inventory tracking with WebSocket updates"
→ @dropshipping-workflow-expert + @react-ui-architect + @containerization-expert
```

**Security & Compliance:**
```
"Implement secure payment processing with fraud detection"
→ @security-compliance-auditor + @ai-business-optimizer + @test-automation-specialist
```

**AI Enhancement:**
```
"Improve product description generation with competitor analysis"
→ @ai-dropshipping-specialist + @data-pipeline-engineer + @marketplace-integration-expert
```

### 🚀 Quick Commands for Domain-Specific Tasks

#### Business Operations
- **Product Sourcing**: "Find profitable products from OwnerClan with 40% margin"
- **Price Optimization**: "Adjust pricing strategy based on competitor analysis"
- **Inventory Management**: "Implement low-stock alerts and auto-reordering"
- **Order Automation**: "Automate order processing from Coupang to Zentrade"

#### Technical Development
- **API Integration**: "Fix Zentrade XML parsing for Korean product names"
- **Performance Tuning**: "Optimize database queries for product search"
- **Frontend Enhancement**: "Create real-time dashboard for order monitoring"
- **Security Hardening**: "Audit API endpoints for potential vulnerabilities"

#### Analytics & Intelligence
- **Market Analysis**: "Analyze sales trends for electronics category"
- **Customer Insights**: "Identify high-value customer segments"
- **Profitability Analysis**: "Calculate ROI for each marketplace platform"
- **Demand Forecasting**: "Predict inventory needs for next month"

### 🔄 Workflow Automation Patterns

#### Daily Operations Workflow
1. **@ai-dropshipping-specialist** analyzes market trends
2. **@python-backend-expert** processes new products from wholesalers
3. **@marketplace-integration-expert** optimizes listings across platforms
4. **@monitoring-analytics-expert** tracks performance metrics
5. **@data-pipeline-engineer** generates insights and reports

#### Feature Development Cycle
1. **@project-analyst** analyzes requirements and technical feasibility
2. **@tech-lead-orchestrator** coordinates development plan
3. **Specialist team** implements features with domain expertise
4. **@test-automation-specialist** ensures comprehensive testing
5. **@code-quality-guardian** reviews and validates implementation

### 💡 Advanced Integration Features

#### Custom Agent Prompts
Your project includes specialized agent prompts in `.claude/agent-prompts/` for enhanced development:
- `dropshipping-general-purpose.md` - Business context and API expertise
- `dropshipping-code-reviewer.md` - E-commerce security and financial accuracy
- `dropshipping-test-automator.md` - External API mocking and workflow testing

#### Intelligent Triggers
Auto-activation rules defined in `.claude/agent-prompts/agent-triggers.md`:
- **Wholesaler APIs** → @python-backend-expert + @test-automation-specialist
- **Financial Calculations** → @code-quality-guardian + @security-compliance-auditor
- **Performance Issues** → @database-performance-optimizer auto-activation
- **New Features** → Full development cycle with quality gates

### 🎯 Business Domain Expertise

Your AI team understands the complete dropshipping business model:
- **Supply Chain**: Wholesaler relationships and inventory management
- **Multi-Platform**: Marketplace-specific requirements and optimization
- **Financial**: Margin calculations, pricing strategies, and profitability
- **Customer Experience**: Order fulfillment, tracking, and support
- **Compliance**: Tax handling, return policies, and regulatory requirements

**Your specialized AI development team combines technical excellence with deep dropshipping business expertise, ensuring every solution is optimized for profitability, scalability, and operational efficiency.**