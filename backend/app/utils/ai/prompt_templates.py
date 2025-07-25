"""Prompt templates for AI services."""

from typing import Dict, List, Any
from enum import Enum


class PromptCategory(str, Enum):
    """프롬프트 카테고리"""
    PRODUCT_OPTIMIZATION = "product_optimization"
    MARKET_ANALYSIS = "market_analysis"
    PRICING_STRATEGY = "pricing_strategy"
    CONTENT_GENERATION = "content_generation"
    CUSTOMER_ANALYSIS = "customer_analysis"
    DEMAND_PREDICTION = "demand_prediction"


class PromptTemplates:
    """AI 서비스용 프롬프트 템플릿 관리"""
    
    # 상품 최적화 템플릿
    PRODUCT_TITLE_OPTIMIZATION = """
    당신은 온라인 쇼핑몰 SEO 전문가입니다. 다음 상품명을 최적화해주세요.
    
    현재 상품명: {current_title}
    카테고리: {category}
    주요 키워드: {keywords}
    타겟 플랫폼: {platform}
    최대 길이: {max_length}자
    
    최적화 기준:
    1. 주요 키워드를 자연스럽게 포함
    2. 클릭률을 높일 수 있는 매력적인 표현
    3. 모바일 화면에서 잘림 없이 핵심 정보 전달
    4. 플랫폼별 특성 고려
    5. 불필요한 특수문자 제거
    
    3개의 개선안을 제시하고 각각의 장점을 설명해주세요.
    """
    
    PRODUCT_DESCRIPTION_GENERATION = """
    전문 카피라이터로서 다음 상품의 설명을 작성해주세요.
    
    상품 정보:
    - 상품명: {product_name}
    - 카테고리: {category}
    - 주요 특징: {features}
    - 타겟 고객: {target_audience}
    - 가격대: {price_range}
    - 차별화 포인트: {unique_points}
    
    작성 스타일: {style}
    
    구성:
    1. 한 줄 요약 (구매 욕구 자극)
    2. 핵심 특징 (불릿 포인트 5개)
    3. 상세 설명 (스토리텔링)
    4. 사용 시나리오
    5. 구매 혜택
    
    SEO 키워드를 자연스럽게 포함하고, 감성적 어필과 이성적 정보를 균형있게 작성해주세요.
    """
    
    KEYWORD_EXTRACTION = """
    SEO 전문가로서 다음 정보에서 효과적인 키워드를 추출해주세요.
    
    분석 대상:
    {text}
    
    카테고리: {category}
    경쟁 강도: {competition_level}
    
    추출 기준:
    1. 검색량이 높을 것으로 예상되는 키워드
    2. 구매 의도가 명확한 키워드
    3. 롱테일 키워드 포함
    4. 카테고리 특화 키워드
    5. 트렌드 키워드
    
    각 키워드에 대해:
    - 키워드
    - 예상 검색량 (높음/중간/낮음)
    - 경쟁도 (높음/중간/낮음)
    - 추천 이유
    - 활용 방법
    
    총 {max_keywords}개의 키워드를 JSON 형식으로 제공해주세요.
    """
    
    # 시장 분석 템플릿
    MARKET_TREND_ANALYSIS = """
    시장 분석 전문가로서 다음 카테고리의 트렌드를 분석해주세요.
    
    분석 대상:
    - 카테고리: {category}
    - 기간: {period}
    - 지역: {region}
    - 타겟층: {target_demographic}
    
    분석 항목:
    1. 현재 인기 상품/브랜드 Top 10
    2. 급상승 검색어
    3. 계절적 요인 분석
    4. 소비자 선호 변화
    5. 가격대별 수요 분포
    6. 신규 진입 기회
    7. 향후 3-6개월 전망
    
    데이터 기반의 구체적인 인사이트와 실행 가능한 전략을 제시해주세요.
    """
    
    COMPETITOR_ANALYSIS = """
    경쟁 분석 전문가로서 다음 상품의 경쟁 환경을 분석해주세요.
    
    분석 대상:
    - 상품: {product_name}
    - 카테고리: {category}
    - 가격대: {price_range}
    - 주요 특징: {key_features}
    
    경쟁사 분석 (상위 5개):
    1. 브랜드/상품명
    2. 가격 전략
    3. 마케팅 포인트
    4. 강점과 약점
    5. 고객 반응
    
    차별화 전략:
    1. 가격 포지셔닝
    2. USP (Unique Selling Proposition)
    3. 타겟 고객 세분화
    4. 마케팅 메시지
    5. 판매 채널 전략
    
    구체적인 액션 플랜을 포함해주세요.
    """
    
    # 가격 전략 템플릿
    PRICING_STRATEGY = """
    가격 전략 전문가로서 최적의 가격 정책을 수립해주세요.
    
    상품 정보:
    - 카테고리: {category}
    - 원가: {cost}
    - 경쟁사 가격: {competitor_prices}
    - 품질 등급: {quality_grade}
    - 브랜드 가치: {brand_value}
    - 목표 마진: {target_margin}
    
    시장 환경:
    - 수요 탄력성: {demand_elasticity}
    - 시장 성장률: {market_growth}
    - 경쟁 강도: {competition_intensity}
    
    가격 전략 제안:
    1. 초기 진입 가격
    2. 정상 판매 가격
    3. 프로모션 가격
    4. 번들 가격
    5. 시즌별 가격
    
    각 전략별로:
    - 추천 가격
    - 예상 마진율
    - 예상 판매량
    - 리스크 요인
    - 실행 타이밍
    """
    
    DYNAMIC_PRICING = """
    동적 가격 전략을 수립해주세요.
    
    현재 상황:
    - 재고 수준: {inventory_level}
    - 판매 속도: {sales_velocity}
    - 계절 요인: {seasonal_factor}
    - 경쟁사 동향: {competitor_movement}
    
    가격 조정 제안:
    1. 즉시 적용 가격
    2. 시간대별 가격
    3. 재고 기반 가격
    4. 고객 세그먼트별 가격
    5. 이벤트 가격
    
    자동화 규칙도 함께 제시해주세요.
    """
    
    # 콘텐츠 생성 템플릿
    SOCIAL_MEDIA_CONTENT = """
    소셜 미디어 마케팅 전문가로서 다음 상품의 SNS 콘텐츠를 작성해주세요.
    
    상품 정보:
    - 상품명: {product_name}
    - 핵심 특징: {key_features}
    - 타겟 고객: {target_audience}
    - 캠페인 목표: {campaign_goal}
    
    플랫폼: {platform}
    
    콘텐츠 요구사항:
    1. 어텐션 그래빙 헤드라인
    2. 스토리텔링 본문
    3. 해시태그 (10-15개)
    4. CTA (Call-to-Action)
    5. 이모지 활용
    
    플랫폼별 특성과 알고리즘을 고려하여 최적화해주세요.
    """
    
    EMAIL_MARKETING = """
    이메일 마케팅 전문가로서 다음 상품의 프로모션 이메일을 작성해주세요.
    
    캠페인 정보:
    - 상품: {product_name}
    - 프로모션: {promotion_type}
    - 할인율: {discount_rate}
    - 기간: {promotion_period}
    - 타겟: {target_segment}
    
    이메일 구성:
    1. 제목 (오픈율 최적화)
    2. 프리헤더
    3. 인사말
    4. 핵심 메시지
    5. 상품 소개
    6. 혜택 강조
    7. 긴급성 어필
    8. CTA 버튼
    9. 추가 정보
    
    A/B 테스트용 2가지 버전을 제공해주세요.
    """
    
    # 고객 분석 템플릿
    CUSTOMER_PERSONA = """
    고객 분석 전문가로서 다음 데이터를 기반으로 고객 페르소나를 작성해주세요.
    
    데이터:
    - 구매 이력: {purchase_history}
    - 인구통계: {demographics}
    - 행동 패턴: {behavior_patterns}
    - 선호도: {preferences}
    
    페르소나 구성:
    1. 기본 정보 (나이, 성별, 직업 등)
    2. 라이프스타일
    3. 쇼핑 행동
    4. 구매 동기
    5. 페인 포인트
    6. 선호 채널
    7. 가격 민감도
    8. 브랜드 충성도
    
    마케팅 전략 제안도 포함해주세요.
    """
    
    REVIEW_ANALYSIS = """
    리뷰 분석 전문가로서 다음 고객 리뷰들을 분석해주세요.
    
    리뷰 데이터:
    {reviews}
    
    분석 항목:
    1. 전체 감성 분석 (긍정/부정/중립)
    2. 주요 긍정 요인 Top 5
    3. 주요 불만 사항 Top 5
    4. 자주 언급되는 키워드
    5. 고객 세그먼트별 반응
    6. 시간대별 트렌드
    7. 경쟁 제품 대비 평가
    
    개선 방안:
    1. 제품 개선점
    2. 서비스 개선점
    3. 마케팅 메시지 조정
    4. 고객 응대 전략
    """
    
    # 수요 예측 템플릿
    DEMAND_FORECAST = """
    수요 예측 전문가로서 다음 데이터를 분석하여 판매량을 예측해주세요.
    
    과거 데이터:
    - 판매 이력: {sales_history}
    - 계절 패턴: {seasonal_patterns}
    - 프로모션 효과: {promotion_effects}
    - 외부 요인: {external_factors}
    
    예측 기간: {forecast_period}
    
    예측 결과:
    1. 일별 예상 판매량
    2. 주별 예상 판매량
    3. 월별 예상 판매량
    4. 신뢰 구간
    5. 시나리오별 예측 (낙관/중립/비관)
    
    재고 관리 제안:
    1. 최적 재고 수준
    2. 재주문 시점
    3. 안전 재고
    4. 시즌별 조정
    """
    
    @classmethod
    def get_template(cls, category: PromptCategory, template_name: str) -> str:
        """카테고리와 템플릿 이름으로 프롬프트 템플릿 가져오기"""
        template_map = {
            PromptCategory.PRODUCT_OPTIMIZATION: {
                "title": cls.PRODUCT_TITLE_OPTIMIZATION,
                "description": cls.PRODUCT_DESCRIPTION_GENERATION,
                "keywords": cls.KEYWORD_EXTRACTION
            },
            PromptCategory.MARKET_ANALYSIS: {
                "trends": cls.MARKET_TREND_ANALYSIS,
                "competition": cls.COMPETITOR_ANALYSIS
            },
            PromptCategory.PRICING_STRATEGY: {
                "static": cls.PRICING_STRATEGY,
                "dynamic": cls.DYNAMIC_PRICING
            },
            PromptCategory.CONTENT_GENERATION: {
                "social": cls.SOCIAL_MEDIA_CONTENT,
                "email": cls.EMAIL_MARKETING
            },
            PromptCategory.CUSTOMER_ANALYSIS: {
                "persona": cls.CUSTOMER_PERSONA,
                "reviews": cls.REVIEW_ANALYSIS
            },
            PromptCategory.DEMAND_PREDICTION: {
                "forecast": cls.DEMAND_FORECAST
            }
        }
        
        category_templates = template_map.get(category, {})
        return category_templates.get(template_name, "")
    
    @classmethod
    def format_template(cls, template: str, **kwargs) -> str:
        """템플릿에 변수 값 채우기"""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required parameter: {e}")
    
    @classmethod
    def create_custom_template(cls, base_template: str, 
                             modifications: Dict[str, Any]) -> str:
        """기존 템플릿을 수정하여 커스텀 템플릿 생성"""
        custom_template = base_template
        
        # 추가 지시사항
        if "additional_instructions" in modifications:
            custom_template += f"\n\n추가 지시사항:\n{modifications['additional_instructions']}"
        
        # 제외 항목
        if "exclude_sections" in modifications:
            for section in modifications["exclude_sections"]:
                # 간단한 구현: 섹션 제목을 찾아 제거
                custom_template = custom_template.replace(section, "")
        
        # 강조 사항
        if "emphasis" in modifications:
            custom_template += f"\n\n특별히 강조할 사항:\n{modifications['emphasis']}"
        
        return custom_template
    
    @classmethod
    def get_platform_specific_template(cls, base_template: str, 
                                     platform: str) -> str:
        """플랫폼별 특화 템플릿 생성"""
        platform_instructions = {
            "coupang": "\n\n쿠팡 최적화:\n- 로켓배송 강조\n- 쿠팡 랭킹 고려\n- 리뷰 평점 중요",
            "naver": "\n\n네이버 쇼핑 최적화:\n- 네이버 SEO 키워드\n- 스토어팜 특성\n- 톡톡 응대 고려",
            "gmarket": "\n\nG마켓 최적화:\n- 파워클릭 광고 고려\n- 스마일배송\n- 할인 쿠폰 전략",
            "11st": "\n\n11번가 최적화:\n- 십일절 프로모션\n- OK캐쉬백\n- 셀러 등급 고려"
        }
        
        if platform in platform_instructions:
            return base_template + platform_instructions[platform]
        
        return base_template