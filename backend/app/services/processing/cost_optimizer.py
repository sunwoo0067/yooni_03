"""
비용 최적화 전략

목표: AI 처리 비용 최적화
방법: 주간 GPT-4o-mini, 야간 Ollama 로컬 모델 활용
"""

import asyncio
import json
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.models.product_processing import ProcessingCostTracking
from app.services.ai.ai_manager import AIManager
from app.services.ai.ollama_service import OllamaService


class ProcessingPriority(Enum):
    """처리 우선순위"""
    HIGH = "high"      # 주력 계정, 즉시 처리
    MEDIUM = "medium"  # 일반 계정, 배치 처리
    LOW = "low"        # 테스트 계정, 야간 처리


class CostOptimizer:
    """AI 비용 최적화 관리자"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_manager = AIManager()
        self.ollama_service = OllamaService()
        
        # 비용 설정 (예상 비용, USD)
        self.model_costs = {
            "gpt-4o-mini": {
                "input_cost_per_1k_tokens": 0.00015,
                "output_cost_per_1k_tokens": 0.0006,
                "average_tokens_per_request": 1500
            },
            "gpt-4o": {
                "input_cost_per_1k_tokens": 0.005,
                "output_cost_per_1k_tokens": 0.015,
                "average_tokens_per_request": 1500
            },
            "ollama_llama3.1_8b": {
                "input_cost_per_1k_tokens": 0.0,
                "output_cost_per_1k_tokens": 0.0,
                "average_tokens_per_request": 1500
            },
            "ollama_llama3.1_70b": {
                "input_cost_per_1k_tokens": 0.0,
                "output_cost_per_1k_tokens": 0.0,
                "average_tokens_per_request": 1500
            }
        }
        
        # 시간대별 설정
        self.business_hours = {
            "start": time(9, 0),   # 오전 9시
            "end": time(18, 0)     # 오후 6시
        }
        
        self.night_hours = {
            "start": time(22, 0),  # 오후 10시
            "end": time(6, 0)      # 오전 6시
        }
    
    def get_optimal_model(
        self, 
        processing_type: str, 
        priority: ProcessingPriority,
        quality_requirement: str = "standard"  # high, standard, basic
    ) -> Dict[str, Any]:
        """최적 AI 모델 선택"""
        
        current_time = datetime.now().time()
        is_business_hours = self._is_business_hours(current_time)
        is_night_time = self._is_night_time(current_time)
        
        # 우선순위별 모델 선택
        if priority == ProcessingPriority.HIGH:
            # 주력 계정: 시간 무관하게 최고 품질
            if quality_requirement == "high":
                return {
                    "model": "gpt-4o",
                    "service": "openai",
                    "estimated_cost": self._calculate_estimated_cost("gpt-4o"),
                    "reason": "고품질 요구사항 + 주력 계정"
                }
            else:
                return {
                    "model": "gpt-4o-mini",
                    "service": "openai", 
                    "estimated_cost": self._calculate_estimated_cost("gpt-4o-mini"),
                    "reason": "주력 계정 표준 처리"
                }
        
        elif priority == ProcessingPriority.MEDIUM:
            # 일반 계정: 시간대별 최적화
            if is_business_hours:
                return {
                    "model": "gpt-4o-mini",
                    "service": "openai",
                    "estimated_cost": self._calculate_estimated_cost("gpt-4o-mini"),
                    "reason": "업무시간 중 일반 계정"
                }
            elif is_night_time:
                return {
                    "model": "llama3.1:8b",
                    "service": "ollama",
                    "estimated_cost": 0.0,
                    "reason": "야간 시간 비용 절약"
                }
            else:
                # 평상시
                return {
                    "model": "gpt-4o-mini",
                    "service": "openai",
                    "estimated_cost": self._calculate_estimated_cost("gpt-4o-mini"),
                    "reason": "평상시 일반 처리"
                }
        
        else:  # LOW priority
            # 테스트 계정: 야간 또는 로컬 모델 우선
            if is_night_time or not is_business_hours:
                return {
                    "model": "llama3.1:8b",
                    "service": "ollama",
                    "estimated_cost": 0.0,
                    "reason": "테스트 계정 비용 절약"
                }
            else:
                return {
                    "model": "gpt-4o-mini",
                    "service": "openai",
                    "estimated_cost": self._calculate_estimated_cost("gpt-4o-mini"),
                    "reason": "테스트 계정 최소 비용"
                }
    
    async def process_with_optimization(
        self,
        prompt: str,
        processing_type: str,
        priority: ProcessingPriority,
        quality_requirement: str = "standard",
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """비용 최적화된 AI 처리"""
        
        model_config = self.get_optimal_model(processing_type, priority, quality_requirement)
        
        start_time = datetime.now()
        
        for attempt in range(max_retries + 1):
            try:
                if model_config["service"] == "openai":
                    result = await self.ai_manager.generate_text(
                        prompt, 
                        model=model_config["model"]
                    )
                else:  # ollama
                    result = await self.ollama_service.generate_text(
                        prompt,
                        model=model_config["model"]
                    )
                
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                
                # 비용 추적
                await self._track_processing_cost(
                    processing_type=processing_type,
                    ai_model=f"{model_config['service']}_{model_config['model']}",
                    cost=model_config["estimated_cost"],
                    processing_time_ms=int(processing_time),
                    success=True
                )
                
                return {
                    "success": True,
                    "result": result,
                    "model_used": model_config["model"],
                    "service_used": model_config["service"],
                    "cost": model_config["estimated_cost"],
                    "processing_time_ms": int(processing_time),
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                print(f"AI 처리 시도 {attempt + 1} 실패: {e}")
                
                # 마지막 시도가 아니면 다른 모델로 재시도
                if attempt < max_retries:
                    model_config = self._get_fallback_model(model_config)
                    continue
                else:
                    # 최종 실패
                    await self._track_processing_cost(
                        processing_type=processing_type,
                        ai_model=f"{model_config['service']}_{model_config['model']}",
                        cost=model_config["estimated_cost"],
                        processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                        success=False,
                        error_message=str(e)
                    )
                    
                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1
                    }
    
    def schedule_batch_processing(
        self,
        processing_requests: List[Dict],
        target_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """배치 처리 스케줄링"""
        
        if not target_time:
            # 다음 야간 시간으로 설정
            target_time = self._get_next_night_time()
        
        # 우선순위별 그룹화
        grouped_requests = {
            "high": [],
            "medium": [],
            "low": []
        }
        
        for request in processing_requests:
            priority = request.get("priority", "medium")
            grouped_requests[priority].append(request)
        
        # 스케줄 계획
        schedule_plan = {
            "target_time": target_time.isoformat(),
            "total_requests": len(processing_requests),
            "grouped_counts": {k: len(v) for k, v in grouped_requests.items()},
            "estimated_cost": self._estimate_batch_cost(processing_requests),
            "estimated_duration": self._estimate_batch_duration(processing_requests)
        }
        
        return schedule_plan
    
    def get_cost_analytics(self, days: int = 30) -> Dict[str, Any]:
        """비용 분석"""
        
        start_date = datetime.now().date() - timedelta(days=days)
        
        # 기간별 비용 조회
        cost_data = self.db.query(
            ProcessingCostTracking.date,
            ProcessingCostTracking.processing_type,
            ProcessingCostTracking.ai_model,
            func.sum(ProcessingCostTracking.total_cost).label("total_cost"),
            func.sum(ProcessingCostTracking.total_requests).label("total_requests"),
            func.avg(ProcessingCostTracking.average_cost_per_request).label("avg_cost_per_request")
        ).filter(
            ProcessingCostTracking.date >= start_date
        ).group_by(
            ProcessingCostTracking.date,
            ProcessingCostTracking.processing_type,
            ProcessingCostTracking.ai_model
        ).all()
        
        # 분석 결과 구성
        total_cost = sum(float(row.total_cost) for row in cost_data)
        total_requests = sum(row.total_requests for row in cost_data)
        
        # 모델별 비용
        model_costs = {}
        for row in cost_data:
            model = row.ai_model
            if model not in model_costs:
                model_costs[model] = {"cost": 0, "requests": 0}
            model_costs[model]["cost"] += float(row.total_cost)
            model_costs[model]["requests"] += row.total_requests
        
        # 처리 타입별 비용
        type_costs = {}
        for row in cost_data:
            ptype = row.processing_type
            if ptype not in type_costs:
                type_costs[ptype] = {"cost": 0, "requests": 0}
            type_costs[ptype]["cost"] += float(row.total_cost)
            type_costs[ptype]["requests"] += row.total_requests
        
        # 일별 비용 추이
        daily_costs = {}
        for row in cost_data:
            date_str = row.date.strftime("%Y-%m-%d")
            if date_str not in daily_costs:
                daily_costs[date_str] = 0
            daily_costs[date_str] += float(row.total_cost)
        
        # 비용 절약 효과 계산
        savings = self._calculate_cost_savings(cost_data)
        
        return {
            "period": f"{days}일",
            "total_cost": round(total_cost, 4),
            "total_requests": total_requests,
            "average_cost_per_request": round(total_cost / total_requests if total_requests > 0 else 0, 6),
            "model_breakdown": model_costs,
            "type_breakdown": type_costs,
            "daily_trend": daily_costs,
            "cost_savings": savings,
            "recommendations": self._generate_cost_recommendations(cost_data)
        }
    
    def _is_business_hours(self, current_time: time) -> bool:
        """업무시간 여부 확인"""
        return self.business_hours["start"] <= current_time <= self.business_hours["end"]
    
    def _is_night_time(self, current_time: time) -> bool:
        """야간시간 여부 확인"""
        start = self.night_hours["start"]
        end = self.night_hours["end"]
        
        if start > end:  # 자정을 넘는 경우
            return current_time >= start or current_time <= end
        else:
            return start <= current_time <= end
    
    def _calculate_estimated_cost(self, model: str) -> float:
        """예상 비용 계산"""
        
        if model not in self.model_costs:
            return 0.0
        
        config = self.model_costs[model]
        avg_tokens = config["average_tokens_per_request"]
        
        # 입력과 출력을 50:50으로 가정
        input_tokens = avg_tokens * 0.5
        output_tokens = avg_tokens * 0.5
        
        input_cost = (input_tokens / 1000) * config["input_cost_per_1k_tokens"]
        output_cost = (output_tokens / 1000) * config["output_cost_per_1k_tokens"]
        
        return round(input_cost + output_cost, 6)
    
    def _get_fallback_model(self, failed_model_config: Dict) -> Dict[str, Any]:
        """실패 시 대체 모델 선택"""
        
        if failed_model_config["service"] == "openai":
            # OpenAI 실패 시 Ollama로 전환
            return {
                "model": "llama3.1:8b",
                "service": "ollama",
                "estimated_cost": 0.0,
                "reason": "OpenAI 실패로 인한 로컬 모델 대체"
            }
        else:
            # Ollama 실패 시 더 간단한 모델로
            return {
                "model": "gpt-4o-mini",
                "service": "openai",
                "estimated_cost": self._calculate_estimated_cost("gpt-4o-mini"),
                "reason": "Ollama 실패로 인한 OpenAI 대체"
            }
    
    def _get_next_night_time(self) -> datetime:
        """다음 야간 시간 계산"""
        
        now = datetime.now()
        today_night = datetime.combine(now.date(), self.night_hours["start"])
        
        if now < today_night:
            return today_night
        else:
            # 다음날 야간
            tomorrow = now.date() + timedelta(days=1)
            return datetime.combine(tomorrow, self.night_hours["start"])
    
    def _estimate_batch_cost(self, requests: List[Dict]) -> float:
        """배치 처리 비용 예상"""
        
        total_cost = 0.0
        
        for request in requests:
            priority = ProcessingPriority(request.get("priority", "medium"))
            quality = request.get("quality_requirement", "standard")
            processing_type = request.get("processing_type", "general")
            
            model_config = self.get_optimal_model(processing_type, priority, quality)
            total_cost += model_config["estimated_cost"]
        
        return round(total_cost, 4)
    
    def _estimate_batch_duration(self, requests: List[Dict]) -> int:
        """배치 처리 예상 소요시간 (분)"""
        
        # 평균 처리 시간: 2초/요청, 병렬 처리 고려
        avg_time_per_request = 2  # 초
        parallel_factor = 5  # 동시에 5개 처리
        
        total_time = (len(requests) / parallel_factor) * avg_time_per_request
        return int(total_time / 60)  # 분으로 변환
    
    def _calculate_cost_savings(self, cost_data: List) -> Dict[str, Any]:
        """비용 절약 효과 계산"""
        
        ollama_usage = sum(
            row.total_requests for row in cost_data 
            if "ollama" in row.ai_model
        )
        
        total_requests = sum(row.total_requests for row in cost_data)
        
        if total_requests == 0:
            return {"savings_amount": 0, "savings_percentage": 0}
        
        # Ollama 대신 GPT-4o-mini를 사용했다면의 비용 계산
        potential_cost = ollama_usage * self._calculate_estimated_cost("gpt-4o-mini")
        actual_cost = sum(float(row.total_cost) for row in cost_data)
        
        savings = potential_cost - actual_cost
        savings_percentage = (savings / potential_cost * 100) if potential_cost > 0 else 0
        
        return {
            "savings_amount": round(savings, 4),
            "savings_percentage": round(savings_percentage, 2),
            "ollama_usage_ratio": round(ollama_usage / total_requests * 100, 2)
        }
    
    def _generate_cost_recommendations(self, cost_data: List) -> List[str]:
        """비용 최적화 권장사항"""
        
        recommendations = []
        
        # 모델별 사용량 분석
        model_usage = {}
        for row in cost_data:
            model = row.ai_model
            if model not in model_usage:
                model_usage[model] = {"cost": 0, "requests": 0}
            model_usage[model]["cost"] += float(row.total_cost)
            model_usage[model]["requests"] += row.total_requests
        
        total_cost = sum(data["cost"] for data in model_usage.values())
        
        # GPT-4o 사용량이 높은 경우
        gpt4o_cost = model_usage.get("openai_gpt-4o", {}).get("cost", 0)
        if gpt4o_cost > total_cost * 0.3:
            recommendations.append("GPT-4o 사용을 줄이고 GPT-4o-mini로 대체 고려")
        
        # 야간 시간 활용도가 낮은 경우
        ollama_usage = sum(
            data["requests"] for model, data in model_usage.items() 
            if "ollama" in model
        )
        total_requests = sum(data["requests"] for data in model_usage.values())
        
        if ollama_usage < total_requests * 0.3:
            recommendations.append("야간 시간대 Ollama 활용도를 높여 비용 절약")
        
        # 배치 처리 권장
        if total_requests > 100:
            recommendations.append("대량 처리 시 배치 처리를 통한 비용 최적화 권장")
        
        return recommendations
    
    async def _track_processing_cost(
        self,
        processing_type: str,
        ai_model: str,
        cost: float,
        processing_time_ms: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """처리 비용 추적"""
        
        today = datetime.now().date()
        
        cost_tracking = self.db.query(ProcessingCostTracking).filter(
            and_(
                ProcessingCostTracking.date == today,
                ProcessingCostTracking.processing_type == processing_type,
                ProcessingCostTracking.ai_model == ai_model
            )
        ).first()
        
        if cost_tracking:
            cost_tracking.total_requests += 1
            cost_tracking.total_cost += Decimal(str(cost))
            cost_tracking.average_cost_per_request = (
                cost_tracking.total_cost / cost_tracking.total_requests
            )
            cost_tracking.cost_optimization_used = "ollama" in ai_model.lower()
        else:
            cost_tracking = ProcessingCostTracking(
                date=datetime.now(),
                processing_type=processing_type,
                ai_model=ai_model,
                total_requests=1,
                total_cost=Decimal(str(cost)),
                average_cost_per_request=Decimal(str(cost)),
                cost_optimization_used="ollama" in ai_model.lower()
            )
            self.db.add(cost_tracking)
        
        try:
            self.db.commit()
        except Exception as e:
            print(f"비용 추적 저장 오류: {e}")
            self.db.rollback()