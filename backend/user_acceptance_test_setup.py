# -*- coding: utf-8 -*-
"""
사용자 인수 테스트(UAT) 환경 구축
실제 사용자가 시스템을 테스트할 수 있는 환경과 도구 제공
"""
import os
import json
import csv
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

def create_user_test_environment():
    """사용자 테스트 환경 구축"""
    
    print("="*60)
    print("드롭시핑 시스템 사용자 테스트 환경 구축")
    print("="*60)
    print(f"구축 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 환경 디렉토리 생성
    test_env_dir = Path("user_test_environment")
    test_env_dir.mkdir(exist_ok=True)
    
    # 1. 테스트 데이터 생성
    create_test_data(test_env_dir)
    
    # 2. 사용자 가이드 생성
    create_user_guide(test_env_dir)
    
    # 3. 테스트 시나리오 생성
    create_test_scenarios(test_env_dir)
    
    # 4. 테스트 결과 양식 생성
    create_test_result_forms(test_env_dir)
    
    # 5. 테스트 환경 설정 파일 생성
    create_test_config(test_env_dir)
    
    # 6. 실행 스크립트 생성
    create_execution_scripts(test_env_dir)
    
    print(f"[완료] 사용자 테스트 환경이 '{test_env_dir}' 디렉토리에 구축되었습니다.")
    print(f"구축 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

def create_test_data(test_dir: Path):
    """테스트용 샘플 데이터 생성"""
    print("1. 테스트 데이터 생성 중...")
    
    data_dir = test_dir / "sample_data"
    data_dir.mkdir(exist_ok=True)
    
    # 도매상품 데이터
    wholesale_products = [
        {
            "상품명": "블루투스 무선 이어폰 프리미엄",
            "도매가": 18000,
            "재고수량": 200,
            "카테고리": "전자기기",
            "브랜드": "TechSound",
            "모델번호": "TS-TWS-2024",
            "설명": "노이즈 캔슬링 기능이 있는 고급 무선 이어폰",
            "무게": "45g",
            "크기": "6x4x3cm"
        },
        {
            "상품명": "여성 트렌치 코트",
            "도매가": 55000,
            "재고수량": 120,
            "카테고리": "의류",
            "브랜드": "StyleWear",
            "모델번호": "SW-TC-F24",
            "설명": "클래식한 디자인의 여성용 트렌치 코트",
            "무게": "800g",
            "크기": "프리사이즈"
        },
        {
            "상품명": "고속 무선충전패드 15W",
            "도매가": 28000,
            "재고수량": 180,
            "카테고리": "전자기기",
            "브랜드": "PowerCharge",
            "모델번호": "PC-WC-15W",
            "설명": "모든 스마트폰 호환 고속 무선 충전기",
            "무게": "280g",
            "크기": "10x10x1.5cm"
        },
        {
            "상품명": "프리미엄 캠핑 텐트 4인용",
            "도매가": 95000,
            "재고수량": 50,
            "카테고리": "레저용품",
            "브랜드": "OutdoorPro",
            "모델번호": "OP-TENT-4P",
            "설명": "방수 기능이 뛰어난 4인용 가족 텐트",
            "무게": "3.2kg",
            "크기": "40x30x15cm"
        },
        {
            "상품명": "스마트워치 건강관리형",
            "도매가": 42000,
            "재고수량": 150,
            "카테고리": "전자기기",
            "브랜드": "HealthTech",
            "모델번호": "HT-SW-2024",
            "설명": "심박수, 산소포화도 측정 가능한 스마트워치",
            "무게": "65g",
            "크기": "4.5x3.8x1.2cm"
        }
    ]
    
    # CSV 파일로 저장
    with open(data_dir / "wholesale_products.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=wholesale_products[0].keys())
        writer.writeheader()
        writer.writerows(wholesale_products)
    
    # 시장 가격 데이터
    market_prices = [
        {"상품명": "블루투스 무선 이어폰 프리미엄", "쿠팡": 35900, "네이버": 34500, "11번가": 36800},
        {"상품명": "여성 트렌치 코트", "쿠팡": 98000, "네이버": 95000, "11번가": 99900},
        {"상품명": "고속 무선충전패드 15W", "쿠팡": 48000, "네이버": 45900, "11번가": 47500},
        {"상품명": "프리미엄 캠핑 텐트 4인용", "쿠팡": 169000, "네이버": 165000, "11번가": 172000},
        {"상품명": "스마트워치 건강관리형", "쿠팡": 78000, "네이버": 75900, "11번가": 79900}
    ]
    
    with open(data_dir / "market_prices.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=market_prices[0].keys())
        writer.writeheader()
        writer.writerows(market_prices)
    
    # 테스트 주문 데이터
    test_orders = [
        {
            "주문번호": "TEST-001",
            "상품명": "블루투스 무선 이어폰 프리미엄",
            "수량": 2,
            "고객명": "김테스트",
            "연락처": "010-1234-5678",
            "주문금액": 71800,
            "배송지": "서울시 강남구 테스트로 123",
            "플랫폼": "쿠팡",
            "주문일시": (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "주문번호": "TEST-002",
            "상품명": "여성 트렌치 코트",
            "수량": 1,
            "고객명": "이사용자",
            "연락처": "010-9876-5432",
            "주문금액": 98000,
            "배송지": "부산시 해운대구 사용자길 456",
            "플랫폼": "네이버",
            "주문일시": (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    with open(data_dir / "test_orders.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=test_orders[0].keys())
        writer.writeheader()
        writer.writerows(test_orders)
    
    # JSON 형태로도 저장
    test_data = {
        "wholesale_products": wholesale_products,
        "market_prices": market_prices,
        "test_orders": test_orders,
        "generated_at": datetime.now().isoformat()
    }
    
    with open(data_dir / "all_test_data.json", "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print("  [OK] 테스트 데이터 생성 완료")

def create_user_guide(test_dir: Path):
    """사용자 가이드 생성"""
    print("2. 사용자 가이드 생성 중...")
    
    guide_content = """# 드롭시핑 시스템 사용자 테스트 가이드

## 📋 테스트 개요

이 문서는 드롭시핑 시스템의 사용자 인수 테스트(UAT)를 위한 가이드입니다.
실제 비즈니스 환경에서 시스템이 어떻게 작동하는지 테스트해보실 수 있습니다.

## 🎯 테스트 목표

1. **기능 검증**: 모든 핵심 기능이 예상대로 작동하는지 확인
2. **사용성 평가**: 사용자 인터페이스가 직관적이고 사용하기 쉬운지 평가
3. **성능 확인**: 시스템이 실제 업무 환경에서 충분한 성능을 보이는지 확인
4. **안정성 검증**: 오류 상황에서도 시스템이 안정적으로 작동하는지 확인

## 🚀 시작하기

### 1단계: 환경 설정
```bash
# Python 가상환경 활성화 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate     # Windows

# 필요한 패키지 설치
pip install -r requirements.txt
```

### 2단계: 테스트 데이터 확인
- `sample_data/` 폴더에서 테스트용 데이터를 확인하세요
- 5개의 샘플 상품과 시장 가격 정보가 준비되어 있습니다

### 3단계: 시스템 시작
```bash
# API 서버 시작
python main.py

# 또는 uvicorn 사용
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📝 주요 테스트 시나리오

### 🛍️ 시나리오 1: 도매상품 관리
**목적**: 도매상품 등록, 수정, 삭제 기능 테스트

**단계**:
1. 도매상품 목록 조회 (`GET /api/wholesaler/products`)
2. 새 상품 등록 (`POST /api/wholesaler/products`)
3. 상품 정보 수정 (`PUT /api/wholesaler/products/{id}`)
4. 상품 삭제 (`DELETE /api/wholesaler/products/{id}`)

**예상 결과**: 모든 CRUD 작업이 정상 동작

### 📊 시나리오 2: 수익성 분석
**목적**: 상품별 수익성 분석 기능 테스트

**단계**:
1. 수익성 분석 실행 (`POST /api/analysis/profitability`)
2. 분석 결과 조회 (`GET /api/analysis/results`)
3. 수익률 기준 상품 필터링
4. 분석 리포트 내보내기

**예상 결과**: 정확한 마진율과 수익 계산

### 🚚 시나리오 3: 주문 처리
**목적**: 주문 접수부터 처리까지 전체 워크플로우 테스트

**단계**:
1. 테스트 주문 생성
2. 주문 상태 확인
3. 배송 정보 업데이트
4. 주문 완료 처리

**예상 결과**: 주문 상태가 정확히 추적되고 업데이트됨

### 📈 시나리오 4: 대시보드 및 리포트
**목적**: 비즈니스 인사이트 제공 기능 테스트

**단계**:
1. 대시보드 데이터 조회
2. 일일/주간/월간 리포트 생성
3. 성과 메트릭 확인
4. 리포트 내보내기 (Excel, PDF)

**예상 결과**: 정확하고 유용한 비즈니스 데이터 제공

## 🔧 테스트 도구

### API 테스트
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Postman Collection**: `test_collections/` 폴더 참조

### 데이터베이스 확인
```sql
-- 상품 테이블 확인
SELECT * FROM products LIMIT 10;

-- 주문 테이블 확인  
SELECT * FROM orders WHERE created_at >= CURRENT_DATE;
```

## 📊 성능 기준

### 응답 시간 기준
- API 조회: < 500ms
- 데이터 등록: < 1초
- 리포트 생성: < 3초
- 대용량 처리: < 10초

### 처리량 기준
- 동시 사용자: 50명
- 초당 요청: 100건
- 일일 주문: 1,000건

## ❗ 문제 발생 시

### 일반적인 문제 해결
1. **연결 오류**: 서버가 실행 중인지 확인
2. **데이터 오류**: 테스트 데이터 초기화 실행
3. **성능 문제**: 시스템 리소스 확인

### 로그 확인
```bash
# 애플리케이션 로그
tail -f logs/app.log

# 에러 로그  
tail -f logs/error.log
```

## 📞 지원 및 피드백

테스트 중 문제가 발생하거나 개선사항이 있으시면:
- 이슈 트래커: GitHub Issues
- 이메일: [개발팀 이메일]
- 슬랙: #dropshipping-support 채널

## ✅ 테스트 완료 체크리스트

- [ ] 모든 API 엔드포인트 테스트 완료
- [ ] 주요 비즈니스 시나리오 검증 완료
- [ ] 성능 기준 만족 확인
- [ ] 오류 처리 테스트 완료
- [ ] 사용성 평가 완료
- [ ] 테스트 결과 보고서 작성 완료

테스트를 완료하신 후, `test_results/` 폴더의 양식을 작성해 주세요.
여러분의 피드백은 시스템 개선에 소중한 자료가 됩니다.

감사합니다! 🙏
"""
    
    with open(test_dir / "USER_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide_content)
    
    print("  [OK] 사용자 가이드 생성 완료")

def create_test_scenarios(test_dir: Path):
    """테스트 시나리오 생성"""
    print("3. 테스트 시나리오 생성 중...")
    
    scenarios_dir = test_dir / "test_scenarios"
    scenarios_dir.mkdir(exist_ok=True)
    
    # 기본 시나리오들
    scenarios = [
        {
            "id": "TS-001",
            "name": "도매상품 관리 테스트",
            "description": "도매상품의 등록, 조회, 수정, 삭제 기능을 테스트합니다.",
            "priority": "HIGH",
            "estimated_time": "30분",
            "prerequisites": ["테스트 데이터 준비", "API 서버 실행"],
            "steps": [
                {
                    "step": 1,
                    "action": "도매상품 목록 조회",
                    "method": "GET",
                    "endpoint": "/api/wholesaler/products",
                    "expected_result": "상품 목록이 JSON 형태로 반환됨"
                },
                {
                    "step": 2,
                    "action": "새 상품 등록",
                    "method": "POST", 
                    "endpoint": "/api/wholesaler/products",
                    "payload": {
                        "name": "테스트 상품",
                        "wholesale_price": 10000,
                        "stock_quantity": 100
                    },
                    "expected_result": "상품이 성공적으로 등록되고 ID가 반환됨"
                },
                {
                    "step": 3,
                    "action": "상품 정보 수정",
                    "method": "PUT",
                    "endpoint": "/api/wholesaler/products/{id}",
                    "expected_result": "상품 정보가 업데이트됨"
                },
                {
                    "step": 4,
                    "action": "상품 삭제",
                    "method": "DELETE",
                    "endpoint": "/api/wholesaler/products/{id}",
                    "expected_result": "상품이 삭제됨"
                }
            ],
            "acceptance_criteria": [
                "모든 CRUD 작업이 정상 동작",
                "응답 시간이 1초 이내",
                "적절한 HTTP 상태 코드 반환"
            ]
        },
        {
            "id": "TS-002", 
            "name": "수익성 분석 테스트",
            "description": "상품별 수익성 분석 및 리포트 생성 기능을 테스트합니다.",
            "priority": "HIGH",
            "estimated_time": "45분",
            "prerequisites": ["상품 데이터 등록", "시장 가격 데이터 준비"],
            "steps": [
                {
                    "step": 1,
                    "action": "수익성 분석 실행",
                    "method": "POST",
                    "endpoint": "/api/analysis/profitability",
                    "expected_result": "분석이 성공적으로 시작됨"
                },
                {
                    "step": 2,
                    "action": "분석 결과 조회",
                    "method": "GET",
                    "endpoint": "/api/analysis/results",
                    "expected_result": "상품별 수익률, 마진, 추천 여부가 반환됨"
                },
                {
                    "step": 3,
                    "action": "수익률 필터링",
                    "method": "GET",
                    "endpoint": "/api/analysis/results?min_margin=20",
                    "expected_result": "20% 이상 마진 상품만 반환됨"
                }
            ],
            "acceptance_criteria": [
                "정확한 수익률 계산",
                "실용적인 비즈니스 인사이트 제공",
                "분석 결과를 다양한 형태로 내보내기 가능"
            ]
        },
        {
            "id": "TS-003",
            "name": "주문 처리 워크플로우 테스트", 
            "description": "주문 접수부터 완료까지의 전체 프로세스를 테스트합니다.",
            "priority": "HIGH",
            "estimated_time": "60분",
            "prerequisites": ["상품 등록", "고객 정보 준비"],
            "steps": [
                {
                    "step": 1,
                    "action": "테스트 주문 생성",
                    "method": "POST",
                    "endpoint": "/api/orders",
                    "expected_result": "주문이 생성되고 주문번호가 발급됨"
                },
                {
                    "step": 2,
                    "action": "주문 상태 조회",
                    "method": "GET", 
                    "endpoint": "/api/orders/{order_id}",
                    "expected_result": "주문 상세 정보와 현재 상태가 반환됨"
                },
                {
                    "step": 3,
                    "action": "배송 정보 업데이트",
                    "method": "PUT",
                    "endpoint": "/api/orders/{order_id}/shipping",
                    "expected_result": "배송 정보가 업데이트됨"
                },
                {
                    "step": 4,
                    "action": "주문 완료 처리",
                    "method": "PUT",
                    "endpoint": "/api/orders/{order_id}/complete",
                    "expected_result": "주문 상태가 '완료'로 변경됨"
                }
            ],
            "acceptance_criteria": [
                "주문 상태가 정확히 추적됨",
                "재고가 자동으로 차감됨",
                "고객에게 알림이 발송됨"
            ]
        }
    ]
    
    # 각 시나리오를 개별 파일로 저장
    for scenario in scenarios:
        filename = f"scenario_{scenario['id'].lower()}.json"
        with open(scenarios_dir / filename, "w", encoding="utf-8") as f:
            json.dump(scenario, f, ensure_ascii=False, indent=2)
    
    # 전체 시나리오 인덱스 파일
    scenario_index = {
        "total_scenarios": len(scenarios),
        "scenarios": [
            {
                "id": s["id"],
                "name": s["name"], 
                "priority": s["priority"],
                "estimated_time": s["estimated_time"]
            } for s in scenarios
        ],
        "created_at": datetime.now().isoformat()
    }
    
    with open(scenarios_dir / "scenario_index.json", "w", encoding="utf-8") as f:
        json.dump(scenario_index, f, ensure_ascii=False, indent=2)
    
    print("  [OK] 테스트 시나리오 생성 완료")

def create_test_result_forms(test_dir: Path):
    """테스트 결과 양식 생성"""
    print("4. 테스트 결과 양식 생성 중...")
    
    forms_dir = test_dir / "test_results"
    forms_dir.mkdir(exist_ok=True)
    
    # 기능 테스트 결과 양식
    functional_test_form = {
        "test_session": {
            "tester_name": "",
            "test_date": "",
            "test_environment": "UAT",
            "browser": "",
            "os": ""
        },
        "test_results": [
            {
                "scenario_id": "TS-001",
                "scenario_name": "도매상품 관리 테스트",
                "status": "",  # PASS/FAIL/SKIP
                "execution_time": "",
                "issues_found": [],
                "comments": "",
                "evidence": []  # 스크린샷, 로그 파일 등
            },
            {
                "scenario_id": "TS-002", 
                "scenario_name": "수익성 분석 테스트",
                "status": "",
                "execution_time": "",
                "issues_found": [],
                "comments": "",
                "evidence": []
            },
            {
                "scenario_id": "TS-003",
                "scenario_name": "주문 처리 워크플로우 테스트", 
                "status": "",
                "execution_time": "",
                "issues_found": [],
                "comments": "",
                "evidence": []
            }
        ],
        "overall_assessment": {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "success_rate": 0,
            "overall_rating": "",  # Excellent/Good/Fair/Poor
            "ready_for_production": "",  # Yes/No/With_Conditions
            "major_issues": [],
            "recommendations": []
        }
    }
    
    with open(forms_dir / "functional_test_results.json", "w", encoding="utf-8") as f:
        json.dump(functional_test_form, f, ensure_ascii=False, indent=2)
    
    # 사용성 테스트 결과 양식
    usability_test_form = {
        "test_session": {
            "tester_name": "",
            "role": "",  # Business_Owner/Manager/Developer/End_User
            "experience_level": "",  # Beginner/Intermediate/Expert
            "test_date": ""
        },
        "usability_metrics": {
            "ease_of_use": {
                "rating": 0,  # 1-5 scale
                "comments": ""
            },
            "navigation": {
                "rating": 0,
                "comments": ""
            },
            "visual_design": {
                "rating": 0,
                "comments": ""
            },
            "response_time": {
                "rating": 0,
                "comments": ""
            },
            "error_handling": {
                "rating": 0,
                "comments": ""
            }
        },
        "feature_feedback": [
            {
                "feature": "상품 관리",
                "usefulness": 0,  # 1-5 scale
                "ease_of_use": 0,
                "suggestions": ""
            },
            {
                "feature": "수익성 분석",
                "usefulness": 0,
                "ease_of_use": 0,
                "suggestions": ""
            },
            {
                "feature": "주문 처리",
                "usefulness": 0,
                "ease_of_use": 0,
                "suggestions": ""
            },
            {
                "feature": "리포트 생성",
                "usefulness": 0,
                "ease_of_use": 0,
                "suggestions": ""
            }
        ],
        "general_feedback": {
            "most_liked_features": [],
            "most_problematic_features": [],
            "missing_features": [],
            "overall_satisfaction": 0,
            "recommendation_score": 0,  # NPS: 0-10
            "would_use_in_production": ""  # Yes/No/Maybe
        }
    }
    
    with open(forms_dir / "usability_test_results.json", "w", encoding="utf-8") as f:
        json.dump(usability_test_form, f, ensure_ascii=False, indent=2)
    
    # 성능 테스트 결과 양식
    performance_test_form = {
        "test_environment": {
            "hardware": "",
            "os": "",
            "memory": "",
            "cpu": "",
            "network": ""
        },
        "load_test_results": [
            {
                "test_name": "정상 부하 테스트",
                "concurrent_users": 10,
                "test_duration": "10분",
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "average_response_time": 0,
                "max_response_time": 0,
                "throughput": 0,
                "error_rate": 0
            },
            {
                "test_name": "스트레스 테스트",
                "concurrent_users": 50,
                "test_duration": "5분",
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "average_response_time": 0,
                "max_response_time": 0,
                "throughput": 0,
                "error_rate": 0
            }
        ],
        "performance_benchmarks": {
            "api_response_time": {
                "target": "< 500ms",
                "actual": "",
                "status": ""  # PASS/FAIL
            },
            "database_query_time": {
                "target": "< 100ms",
                "actual": "",
                "status": ""
            },
            "file_upload_time": {
                "target": "< 5s",
                "actual": "",
                "status": ""
            }
        }
    }
    
    with open(forms_dir / "performance_test_results.json", "w", encoding="utf-8") as f:
        json.dump(performance_test_form, f, ensure_ascii=False, indent=2)
    
    print("  [OK] 테스트 결과 양식 생성 완료")

def create_test_config(test_dir: Path):
    """테스트 환경 설정 파일 생성"""
    print("5. 테스트 환경 설정 생성 중...")
    
    config_dir = test_dir / "config"
    config_dir.mkdir(exist_ok=True)
    
    # 테스트 환경 설정
    test_config = {
        "environment": "UAT",
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "dropshipping_test",
            "user": "test_user",
            "password": "test_password"
        },
        "api": {
            "base_url": "http://localhost:8000",
            "timeout": 30,
            "retry_count": 3
        },
        "test_data": {
            "cleanup_after_test": True,
            "use_sample_data": True,
            "data_seed": 12345
        },
        "notifications": {
            "email_enabled": False,
            "slack_enabled": False,
            "webhook_url": ""
        },
        "logging": {
            "level": "INFO",
            "file": "logs/test.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    with open(config_dir / "test_config.json", "w", encoding="utf-8") as f:
        json.dump(test_config, f, ensure_ascii=False, indent=2)
    
    # 환경 변수 템플릿
    env_template = """# 드롭시핑 시스템 테스트 환경 변수

# 데이터베이스 설정
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/dropshipping_test

# API 설정
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# JWT 설정 (테스트용)
JWT_SECRET_KEY=test_jwt_secret_key_for_testing_only
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Redis 설정
REDIS_URL=redis://localhost:6379/1

# 로깅 설정
LOG_LEVEL=DEBUG
LOG_FILE=logs/test.log

# 외부 API 설정 (테스트 모드)
COUPANG_API_KEY=test_coupang_key
NAVER_API_KEY=test_naver_key
MARKET11_API_KEY=test_11st_key

# 알림 설정
SMTP_SERVER=smtp.test.com
SMTP_PORT=587
SMTP_USER=test@test.com
SMTP_PASSWORD=test_password

SLACK_WEBHOOK_URL=https://hooks.slack.com/test/webhook
"""
    
    with open(config_dir / "test.env", "w", encoding="utf-8") as f:
        f.write(env_template)
    
    print("  [OK] 테스트 환경 설정 생성 완료")

def create_execution_scripts(test_dir: Path):
    """실행 스크립트 생성"""
    print("6. 실행 스크립트 생성 중...")
    
    scripts_dir = test_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    # 테스트 시작 스크립트 (Windows)
    start_test_bat = """@echo off
echo ========================================
echo 드롭시핑 시스템 사용자 테스트 시작
echo ========================================

echo 1. 가상환경 활성화...
call venv\\Scripts\\activate.bat

echo 2. 환경 변수 설정...
copy config\\test.env .env

echo 3. 데이터베이스 초기화...
python scripts\\init_test_db.py

echo 4. 테스트 데이터 로드...
python scripts\\load_test_data.py

echo 5. API 서버 시작...
echo 서버가 시작됩니다. 브라우저에서 http://localhost:8000/docs 를 열어주세요.
echo 테스트를 중단하려면 Ctrl+C를 누르세요.
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
"""
    
    with open(scripts_dir / "start_test.bat", "w", encoding="utf-8") as f:
        f.write(start_test_bat)
    
    # 테스트 시작 스크립트 (Linux/Mac)
    start_test_sh = """#!/bin/bash
echo "========================================"
echo "드롭시핑 시스템 사용자 테스트 시작"
echo "========================================"

echo "1. 가상환경 활성화..."
source venv/bin/activate

echo "2. 환경 변수 설정..."
cp config/test.env .env

echo "3. 데이터베이스 초기화..."
python scripts/init_test_db.py

echo "4. 테스트 데이터 로드..."  
python scripts/load_test_data.py

echo "5. API 서버 시작..."
echo "서버가 시작됩니다. 브라우저에서 http://localhost:8000/docs 를 열어주세요."
echo "테스트를 중단하려면 Ctrl+C를 누르세요."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
    
    with open(scripts_dir / "start_test.sh", "w", encoding="utf-8") as f:
        f.write(start_test_sh)
    
    # 실행 권한 부여 (Linux/Mac)
    import stat
    os.chmod(scripts_dir / "start_test.sh", stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    
    # 테스트 데이터 로더 스크립트
    load_test_data_py = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
테스트 데이터 로더
샘플 데이터를 데이터베이스에 로드합니다.
\"\"\"
import json
import csv
from pathlib import Path

def load_test_data():
    \"\"\"테스트 데이터를 데이터베이스에 로드\"\"\"
    print("테스트 데이터 로딩 시작...")
    
    # 샘플 데이터 경로
    data_dir = Path("sample_data")
    
    if not data_dir.exists():
        print("❌ 샘플 데이터 폴더를 찾을 수 없습니다.")
        return False
    
    try:
        # CSV 파일들 처리
        csv_files = [
            "wholesale_products.csv",
            "market_prices.csv", 
            "test_orders.csv"
        ]
        
        for csv_file in csv_files:
            file_path = data_dir / csv_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                    print(f"✓ {csv_file}: {len(data)}개 레코드 로드됨")
            else:
                print(f"⚠️ {csv_file} 파일을 찾을 수 없습니다.")
        
        print("✅ 테스트 데이터 로딩 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 데이터 로딩 실패: {e}")
        return False

if __name__ == "__main__":
    load_test_data()
"""
    
    with open(scripts_dir / "load_test_data.py", "w", encoding="utf-8") as f:
        f.write(load_test_data_py)
    
    # 테스트 완료 후 정리 스크립트
    cleanup_py = """#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
테스트 정리 스크립트
테스트 완료 후 임시 데이터와 로그를 정리합니다.
\"\"\"
import os
import shutil
from pathlib import Path

def cleanup_test_environment():
    \"\"\"테스트 환경 정리\"\"\"
    print("테스트 환경 정리 시작...")
    
    # 정리할 항목들
    cleanup_items = [
        "logs/test.log",
        "test_temp/",
        ".env",
        "__pycache__/",
    ]
    
    for item in cleanup_items:
        item_path = Path(item)
        try:
            if item_path.is_file():
                item_path.unlink()
                print(f"✓ 파일 삭제: {item}")
            elif item_path.is_dir():
                shutil.rmtree(item_path)
                print(f"✓ 폴더 삭제: {item}")
        except Exception as e:
            print(f"⚠️ {item} 삭제 실패: {e}")
    
    print("✅ 테스트 환경 정리 완료!")

if __name__ == "__main__":
    cleanup_test_environment()
"""
    
    with open(scripts_dir / "cleanup.py", "w", encoding="utf-8") as f:
        f.write(cleanup_py)
    
    print("  [OK] 실행 스크립트 생성 완료")

if __name__ == "__main__":
    create_user_test_environment()