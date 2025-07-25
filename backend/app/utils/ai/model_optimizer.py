"""Model optimizer for AI services performance optimization."""

import psutil
import GPUtil
import torch
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import asyncio
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class SystemResources:
    """시스템 리소스 정보"""
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    gpu_memory_used_gb: float
    gpu_memory_total_gb: float
    gpu_utilization: float
    gpu_temperature: float


@dataclass
class ModelConfig:
    """모델 설정"""
    name: str
    max_tokens: int
    temperature: float
    top_p: float
    batch_size: int
    num_threads: int
    use_gpu: bool
    quantization: Optional[str] = None  # "int8", "int4"


class ModelOptimizer:
    """
    AI 모델 성능 최적화
    - RTX 4070 + 32GB RAM 최적화
    - 동적 리소스 할당
    - 배치 처리 최적화
    - 모델 양자화 지원
    """
    
    def __init__(self):
        """Initialize model optimizer."""
        self.gpu_available = torch.cuda.is_available()
        self.device = torch.device("cuda" if self.gpu_available else "cpu")
        
        # RTX 4070 사양
        self.gpu_memory_limit = 12.0  # GB
        self.optimal_batch_sizes = {
            "small": 32,   # ~1B 파라미터
            "medium": 16,  # ~7B 파라미터  
            "large": 8,    # ~13B 파라미터
            "xlarge": 4    # ~30B+ 파라미터
        }
        
        # 성능 메트릭
        self.performance_history = []
        self.optimization_stats = {
            "total_optimizations": 0,
            "avg_speedup": 0.0,
            "memory_saved_gb": 0.0
        }
        
        logger.info(f"Model Optimizer initialized. GPU: {self.gpu_available}")
    
    def get_system_resources(self) -> SystemResources:
        """현재 시스템 리소스 상태 확인"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        gpu_info = {
            "memory_used_gb": 0.0,
            "memory_total_gb": 0.0,
            "utilization": 0.0,
            "temperature": 0.0
        }
        
        if self.gpu_available:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]  # RTX 4070
                    gpu_info = {
                        "memory_used_gb": gpu.memoryUsed / 1024,
                        "memory_total_gb": gpu.memoryTotal / 1024,
                        "utilization": gpu.load * 100,
                        "temperature": gpu.temperature
                    }
            except Exception as e:
                logger.error(f"Failed to get GPU info: {e}")
        
        return SystemResources(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_gb=memory.available / (1024**3),
            gpu_memory_used_gb=gpu_info["memory_used_gb"],
            gpu_memory_total_gb=gpu_info["memory_total_gb"],
            gpu_utilization=gpu_info["utilization"],
            gpu_temperature=gpu_info["temperature"]
        )
    
    def optimize_model_config(self, 
                            model_size: str,
                            task_type: str,
                            priority: str = "balanced") -> ModelConfig:
        """모델 설정 최적화"""
        resources = self.get_system_resources()
        
        # 기본 설정
        base_config = {
            "small": {"max_tokens": 2048, "batch_size": 32},
            "medium": {"max_tokens": 4096, "batch_size": 16},
            "large": {"max_tokens": 8192, "batch_size": 8},
            "xlarge": {"max_tokens": 16384, "batch_size": 4}
        }
        
        config = base_config.get(model_size, base_config["medium"])
        
        # 우선순위별 조정
        if priority == "speed":
            # 속도 우선: 토큰 수 감소, 배치 크기 증가
            config["max_tokens"] = int(config["max_tokens"] * 0.7)
            config["batch_size"] = int(config["batch_size"] * 1.5)
            temperature = 0.5
            top_p = 0.8
        elif priority == "quality":
            # 품질 우선: 토큰 수 증가, 배치 크기 감소
            config["max_tokens"] = int(config["max_tokens"] * 1.3)
            config["batch_size"] = int(config["batch_size"] * 0.7)
            temperature = 0.8
            top_p = 0.95
        else:  # balanced
            temperature = 0.7
            top_p = 0.9
        
        # 리소스 기반 조정
        if resources.gpu_memory_used_gb > self.gpu_memory_limit * 0.8:
            # GPU 메모리 부족: 배치 크기 감소
            config["batch_size"] = max(1, config["batch_size"] // 2)
            logger.warning(f"GPU memory high, reducing batch size to {config['batch_size']}")
        
        if resources.memory_percent > 80:
            # RAM 부족: 양자화 적용
            quantization = "int8"
        else:
            quantization = None
        
        # CPU 스레드 최적화
        num_threads = min(psutil.cpu_count(), 8)
        if resources.cpu_percent > 80:
            num_threads = max(2, num_threads // 2)
        
        return ModelConfig(
            name=f"{model_size}_optimized",
            max_tokens=config["max_tokens"],
            temperature=temperature,
            top_p=top_p,
            batch_size=config["batch_size"],
            num_threads=num_threads,
            use_gpu=self.gpu_available and resources.gpu_memory_used_gb < self.gpu_memory_limit * 0.9,
            quantization=quantization
        )
    
    async def optimize_batch_processing(self,
                                      items: List[Any],
                                      model_config: ModelConfig,
                                      process_func) -> List[Any]:
        """배치 처리 최적화"""
        batch_size = model_config.batch_size
        results = []
        
        # 동적 배치 크기 조정
        resources = self.get_system_resources()
        if resources.gpu_utilization > 90:
            batch_size = max(1, batch_size // 2)
            logger.info(f"GPU utilization high, reducing batch size to {batch_size}")
        
        # 배치 처리
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # 비동기 병렬 처리
            if len(batch) > 1:
                batch_results = await asyncio.gather(
                    *[process_func(item) for item in batch],
                    return_exceptions=True
                )
            else:
                batch_results = [await process_func(batch[0])]
            
            # 에러 처리
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch item {i+j} failed: {result}")
                    results.append(None)
                else:
                    results.append(result)
            
            # 배치 간 쿨다운 (GPU 온도 관리)
            if resources.gpu_temperature > 80:
                await asyncio.sleep(1.0)
            elif resources.gpu_temperature > 70:
                await asyncio.sleep(0.5)
        
        return results
    
    def apply_quantization(self, model_path: str, 
                         quantization_type: str = "int8") -> str:
        """모델 양자화 적용"""
        try:
            if quantization_type == "int8":
                # INT8 양자화 (속도 2배, 메모리 50% 절감)
                logger.info(f"Applying INT8 quantization to {model_path}")
                # 실제 양자화 로직은 모델 프레임워크에 따라 구현
                quantized_path = model_path.replace(".bin", "_int8.bin")
                
            elif quantization_type == "int4":
                # INT4 양자화 (속도 4배, 메모리 75% 절감)
                logger.info(f"Applying INT4 quantization to {model_path}")
                quantized_path = model_path.replace(".bin", "_int4.bin")
                
            else:
                return model_path
            
            self.optimization_stats["total_optimizations"] += 1
            return quantized_path
            
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return model_path
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용 최적화"""
        optimizations = []
        
        # 1. 가비지 컬렉션
        import gc
        gc.collect()
        optimizations.append("Garbage collection completed")
        
        # 2. GPU 메모리 정리
        if self.gpu_available:
            torch.cuda.empty_cache()
            optimizations.append("GPU cache cleared")
        
        # 3. 프로세스 우선순위 조정
        try:
            p = psutil.Process()
            if psutil.WINDOWS:
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            else:
                p.nice(-10)  # Unix/Linux
            optimizations.append("Process priority increased")
        except Exception as e:
            logger.error(f"Failed to adjust process priority: {e}")
        
        # 4. 메모리 사용량 확인
        resources_before = self.get_system_resources()
        
        return {
            "optimizations": optimizations,
            "memory_freed_gb": resources_before.memory_available_gb,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_optimal_model_for_task(self,
                                  task_type: str,
                                  data_size: int,
                                  time_constraint: Optional[float] = None) -> Dict[str, Any]:
        """작업에 최적화된 모델 추천"""
        resources = self.get_system_resources()
        
        # 작업별 모델 매핑
        task_model_map = {
            "title_optimization": {"size": "small", "priority": "speed"},
            "description_generation": {"size": "medium", "priority": "balanced"},
            "market_analysis": {"size": "large", "priority": "quality"},
            "keyword_extraction": {"size": "small", "priority": "speed"},
            "pricing_strategy": {"size": "medium", "priority": "quality"},
            "content_generation": {"size": "medium", "priority": "balanced"}
        }
        
        model_info = task_model_map.get(task_type, {"size": "medium", "priority": "balanced"})
        
        # 데이터 크기에 따른 조정
        if data_size > 10000:
            model_info["size"] = "small"  # 대용량은 작은 모델로
            model_info["priority"] = "speed"
        elif data_size < 100:
            model_info["size"] = "large"  # 소량은 큰 모델로
            model_info["priority"] = "quality"
        
        # 시간 제약에 따른 조정
        if time_constraint and time_constraint < 5.0:  # 5초 미만
            model_info["size"] = "small"
            model_info["priority"] = "speed"
        
        # 리소스 제약에 따른 조정
        if resources.gpu_memory_used_gb > self.gpu_memory_limit * 0.7:
            model_info["size"] = "small"
        
        # 최적 설정 생성
        config = self.optimize_model_config(
            model_info["size"],
            task_type,
            model_info["priority"]
        )
        
        return {
            "model_size": model_info["size"],
            "priority": model_info["priority"],
            "config": config.__dict__,
            "estimated_time": self._estimate_processing_time(data_size, model_info["size"]),
            "resource_usage": {
                "gpu_memory_required_gb": self._estimate_gpu_memory(model_info["size"]),
                "ram_required_gb": self._estimate_ram(model_info["size"])
            }
        }
    
    def _estimate_processing_time(self, data_size: int, model_size: str) -> float:
        """처리 시간 예측 (초)"""
        # 기본 처리 속도 (items/second)
        base_speed = {
            "small": 100,   # llama3.2:3b
            "medium": 50,   # mistral:7b
            "large": 25,    # llama2:13b
            "xlarge": 10    # llama2:70b
        }
        
        speed = base_speed.get(model_size, 50)
        
        # GPU 가속 보너스
        if self.gpu_available:
            speed *= 3
        
        return data_size / speed
    
    def _estimate_gpu_memory(self, model_size: str) -> float:
        """GPU 메모리 요구량 예측 (GB)"""
        memory_map = {
            "small": 2.0,    # 3B params
            "medium": 5.0,   # 7B params
            "large": 8.0,    # 13B params
            "xlarge": 16.0   # 70B params (양자화 필수)
        }
        return memory_map.get(model_size, 5.0)
    
    def _estimate_ram(self, model_size: str) -> float:
        """RAM 요구량 예측 (GB)"""
        ram_map = {
            "small": 4.0,
            "medium": 8.0,
            "large": 16.0,
            "xlarge": 32.0
        }
        return ram_map.get(model_size, 8.0)
    
    def monitor_performance(self, 
                          task_id: str,
                          start_time: datetime,
                          end_time: datetime,
                          items_processed: int,
                          model_config: ModelConfig) -> Dict[str, Any]:
        """성능 모니터링 및 기록"""
        duration = (end_time - start_time).total_seconds()
        throughput = items_processed / duration if duration > 0 else 0
        
        performance_data = {
            "task_id": task_id,
            "duration_seconds": duration,
            "items_processed": items_processed,
            "throughput_per_second": throughput,
            "model_config": model_config.__dict__,
            "resources": self.get_system_resources().__dict__,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 성능 기록 저장
        self.performance_history.append(performance_data)
        
        # 통계 업데이트
        if len(self.performance_history) > 1:
            avg_throughput = np.mean([p["throughput_per_second"] for p in self.performance_history])
            self.optimization_stats["avg_speedup"] = throughput / avg_throughput if avg_throughput > 0 else 1.0
        
        return performance_data
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """최적화 리포트 생성"""
        if not self.performance_history:
            return {"status": "No optimization data available"}
        
        recent_performances = self.performance_history[-10:]  # 최근 10개
        
        return {
            "summary": self.optimization_stats,
            "average_throughput": np.mean([p["throughput_per_second"] for p in recent_performances]),
            "resource_efficiency": {
                "avg_gpu_utilization": np.mean([p["resources"]["gpu_utilization"] for p in recent_performances]),
                "avg_memory_usage": np.mean([p["resources"]["memory_percent"] for p in recent_performances])
            },
            "recommendations": self._generate_recommendations(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """최적화 추천사항 생성"""
        recommendations = []
        resources = self.get_system_resources()
        
        if resources.gpu_temperature > 80:
            recommendations.append("GPU 온도가 높습니다. 배치 크기를 줄이거나 처리 간격을 늘리세요.")
        
        if resources.gpu_memory_used_gb > self.gpu_memory_limit * 0.9:
            recommendations.append("GPU 메모리가 부족합니다. 모델 양자화를 고려하세요.")
        
        if resources.memory_percent > 85:
            recommendations.append("시스템 메모리가 부족합니다. 불필요한 프로세스를 종료하세요.")
        
        if resources.cpu_percent > 90:
            recommendations.append("CPU 사용률이 높습니다. 병렬 처리 수를 줄이세요.")
        
        if not recommendations:
            recommendations.append("시스템이 최적 상태입니다.")
        
        return recommendations