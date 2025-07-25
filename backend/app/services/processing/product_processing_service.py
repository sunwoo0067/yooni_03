"""
통합 상품가공 서비스

목표: 모든 상품가공 기능을 통합하여 제공
방법: 각 가공 엔진을 조합하여 완전한 상품가공 워크플로우 제공
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_processing import ProductProcessingHistory
from app.services.processing.product_name_processor import ProductNameProcessor
from app.services.processing.image_processing_engine import ImageProcessingEngine
from app.services.processing.product_purpose_analyzer import ProductPurposeAnalyzer
from app.services.processing.market_guideline_manager import MarketGuidelineManager
from app.services.processing.cost_optimizer import CostOptimizer, ProcessingPriority


class ProductProcessingService:
    """통합 상품가공 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # 각 가공 엔진 초기화
        self.name_processor = ProductNameProcessor(db)
        self.image_processor = ImageProcessingEngine(db)
        self.purpose_analyzer = ProductPurposeAnalyzer(db)
        self.guideline_manager = MarketGuidelineManager(db)
        self.cost_optimizer = CostOptimizer(db)
    
    async def process_product_complete(
        self,
        product_id: int,
        marketplace: str,
        priority: ProcessingPriority = ProcessingPriority.MEDIUM,
        processing_options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """완전한 상품가공 프로세스"""
        
        start_time = datetime.now()
        
        try:
            # 상품 조회
            product = self.db.query(Product).filter(Product.id == product_id).first()
            if not product:
                return {"error": "상품을 찾을 수 없습니다"}
            
            processing_options = processing_options or {}
            
            results = {
                "product_id": product_id,
                "marketplace": marketplace,
                "processing_start": start_time.isoformat(),
                "steps": {}
            }
            
            # 1. 상품명 가공
            if processing_options.get("process_name", True):
                print(f"[{datetime.now()}] 상품명 가공 시작...")
                name_result = await self._process_product_name(
                    product, marketplace, priority
                )
                results["steps"]["name_processing"] = name_result
            
            # 2. 이미지 가공
            if processing_options.get("process_images", True):
                print(f"[{datetime.now()}] 이미지 가공 시작...")
                image_result = await self._process_product_images(
                    product, marketplace, priority
                )
                results["steps"]["image_processing"] = image_result
            
            # 3. 용도 분석 및 설명 가공
            if processing_options.get("process_purpose", True):
                print(f"[{datetime.now()}] 용도 분석 시작...")
                purpose_result = await self._process_product_purpose(
                    product, marketplace, priority
                )
                results["steps"]["purpose_analysis"] = purpose_result
            
            # 4. 마켓 가이드라인 적용
            if processing_options.get("apply_guidelines", True):
                print(f"[{datetime.now()}] 가이드라인 적용 시작...")
                guideline_result = await self._apply_market_guidelines(
                    product, marketplace, results
                )
                results["steps"]["guideline_application"] = guideline_result
            
            # 5. 최종 검증 및 최적화
            print(f"[{datetime.now()}] 최종 검증 시작...")
            validation_result = await self._final_validation(
                product, marketplace, results
            )
            results["steps"]["final_validation"] = validation_result
            
            # 처리 완료
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            results["processing_end"] = datetime.now().isoformat()
            results["total_processing_time_ms"] = int(processing_time)
            results["success"] = all(
                step.get("success", False) for step in results["steps"].values()
            )
            
            # 처리 이력 저장
            await self._save_processing_history(
                product, marketplace, results, processing_options
            )
            
            return results
            
        except Exception as e:
            error_result = {
                "error": str(e),
                "processing_time_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
            
            # 오류 이력 저장
            await self._save_processing_history(
                product, marketplace, error_result, processing_options, success=False
            )
            
            return error_result
    
    async def process_product_batch(
        self,
        product_ids: List[int],
        marketplace: str,
        priority: ProcessingPriority = ProcessingPriority.LOW,
        processing_options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """배치 상품가공"""
        
        start_time = datetime.now()
        
        # 배치 처리 스케줄링
        batch_requests = []
        for product_id in product_ids:
            batch_requests.append({
                "product_id": product_id,
                "marketplace": marketplace,
                "priority": priority.value,
                "processing_type": "complete_product_processing"
            })
        
        schedule_plan = self.cost_optimizer.schedule_batch_processing(batch_requests)
        
        # 실제 처리 (동시 처리 제한)
        semaphore = asyncio.Semaphore(3)  # 최대 3개 동시 처리
        
        async def process_single(product_id: int):
            async with semaphore:
                return await self.process_product_complete(
                    product_id, marketplace, priority, processing_options
                )
        
        tasks = [process_single(pid) for pid in product_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 정리
        success_count = 0
        error_count = 0
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "product_id": product_ids[i],
                    "success": False,
                    "error": str(result)
                })
                error_count += 1
            else:
                processed_results.append(result)
                if result.get("success", False):
                    success_count += 1
                else:
                    error_count += 1
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "batch_id": f"batch_{int(start_time.timestamp())}",
            "total_products": len(product_ids),
            "success_count": success_count,
            "error_count": error_count,
            "results": processed_results,
            "schedule_plan": schedule_plan,
            "total_processing_time_seconds": total_time,
            "average_time_per_product": total_time / len(product_ids) if product_ids else 0
        }
    
    async def _process_product_name(
        self, 
        product: Product, 
        marketplace: str, 
        priority: ProcessingPriority
    ) -> Dict[str, Any]:
        """상품명 가공"""
        
        try:
            # 베스트셀러 패턴 분석
            patterns = await self.name_processor.analyze_bestseller_patterns(
                marketplace, product.category_path or "기본"
            )
            
            # 최적화된 상품명 생성
            generated_names = await self.name_processor.generate_optimized_names(
                product, marketplace, target_count=5
            )
            
            # 가격비교 회피 적용
            creative_names = await self.name_processor.avoid_price_comparison(
                generated_names
            )
            
            # 마켓 가이드라인 적용
            final_names = await self.name_processor.apply_market_guidelines(
                creative_names, marketplace
            )
            
            return {
                "success": True,
                "original_name": product.name,
                "patterns_analyzed": patterns,
                "generated_names": generated_names,
                "creative_names": creative_names,
                "final_names": final_names,
                "recommended_name": final_names[0] if final_names else product.name
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "original_name": product.name
            }
    
    async def _process_product_images(
        self, 
        product: Product, 
        marketplace: str, 
        priority: ProcessingPriority
    ) -> Dict[str, Any]:
        """이미지 가공"""
        
        try:
            # 상품 이미지 전체 가공
            image_result = await self.image_processor.process_product_images(
                product, marketplace
            )
            
            if image_result.get("success"):
                # 상품 정보 업데이트 (선택사항)
                if image_result.get("main_image_url"):
                    # 실제로는 상품의 이미지 URL을 업데이트할 수 있음
                    pass
            
            return image_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_product_purpose(
        self, 
        product: Product, 
        marketplace: str, 
        priority: ProcessingPriority
    ) -> Dict[str, Any]:
        """용도 분석 및 설명 가공"""
        
        try:
            # 대체 용도 분석
            purpose_analysis = await self.purpose_analyzer.analyze_alternative_uses(product)
            
            # 가장 유망한 용도 선택
            alternative_purposes = purpose_analysis.get("alternative_purposes", [])
            if alternative_purposes:
                # 시장 점수가 가장 높은 용도 선택
                best_purpose = max(
                    alternative_purposes,
                    key=lambda x: purpose_analysis.get("market_scores", {}).get(
                        f"purpose_{alternative_purposes.index(x)}", {}
                    ).get("total_score", 0)
                )
                
                # 새로운 설명 생성
                new_description = await self.purpose_analyzer.generate_new_descriptions(
                    product, best_purpose, marketplace
                )
                
                # 경쟁력 최적화
                optimization = await self.purpose_analyzer.optimize_for_competition(
                    product, marketplace, new_description.get("seo_keywords", [])
                )
                
                return {
                    "success": True,
                    "purpose_analysis": purpose_analysis,
                    "selected_purpose": best_purpose,
                    "new_description": new_description,
                    "optimization_strategy": optimization
                }
            else:
                return {
                    "success": False,
                    "error": "대체 용도를 찾을 수 없습니다",
                    "purpose_analysis": purpose_analysis
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _apply_market_guidelines(
        self,
        product: Product,
        marketplace: str,
        processing_results: Dict
    ) -> Dict[str, Any]:
        """마켓 가이드라인 적용"""
        
        try:
            guideline_results = {}
            
            # 상품명 가이드라인 검증
            name_processing = processing_results.get("steps", {}).get("name_processing", {})
            recommended_name = name_processing.get("recommended_name", product.name)
            
            name_validation = self.guideline_manager.validate_product_name(
                recommended_name, marketplace
            )
            guideline_results["name_validation"] = name_validation
            
            # 설명 가이드라인 검증
            purpose_processing = processing_results.get("steps", {}).get("purpose_analysis", {})
            new_description = purpose_processing.get("new_description", {})
            description_text = new_description.get("detailed_description", product.description or "")
            
            description_validation = self.guideline_manager.validate_product_description(
                description_text, marketplace
            )
            guideline_results["description_validation"] = description_validation
            
            # 이미지 가이드라인 검증
            image_processing = processing_results.get("steps", {}).get("image_processing", {})
            if image_processing.get("success") and image_processing.get("processed_images"):
                main_image = image_processing["processed_images"][0]
                
                image_info = {
                    "width": 780,  # 실제로는 이미지에서 추출
                    "height": 780,
                    "file_size_mb": main_image.get("file_size", 0) / (1024 * 1024),
                    "format": "jpg"
                }
                
                image_validation = self.guideline_manager.validate_image_specs(
                    image_info, marketplace
                )
                guideline_results["image_validation"] = image_validation
            
            # 자동 수정 적용
            product_data = {
                "name": recommended_name,
                "description": description_text
            }
            
            auto_fixes = self.guideline_manager.apply_automatic_fixes(
                product_data, marketplace
            )
            guideline_results["auto_fixes"] = auto_fixes
            
            return {
                "success": True,
                "validations": guideline_results,
                "all_valid": all(
                    validation.get("valid", False) 
                    for validation in [name_validation, description_validation]
                )
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _final_validation(
        self,
        product: Product,
        marketplace: str,
        processing_results: Dict
    ) -> Dict[str, Any]:
        """최종 검증 및 품질 체크"""
        
        try:
            validation_results = {}
            
            # 각 단계별 성공 여부 확인
            steps = processing_results.get("steps", {})
            step_status = {}
            
            for step_name, step_result in steps.items():
                step_status[step_name] = step_result.get("success", False)
            
            validation_results["step_status"] = step_status
            
            # 전체 품질 점수 계산
            quality_score = self._calculate_quality_score(processing_results)
            validation_results["quality_score"] = quality_score
            
            # 경고 및 권장사항
            warnings = []
            recommendations = []
            
            # 상품명 관련
            name_processing = steps.get("name_processing", {})
            if not name_processing.get("success"):
                warnings.append("상품명 가공에 실패했습니다")
            elif not name_processing.get("final_names"):
                warnings.append("적절한 상품명을 생성하지 못했습니다")
            
            # 이미지 관련
            image_processing = steps.get("image_processing", {})
            if not image_processing.get("success"):
                warnings.append("이미지 가공에 실패했습니다")
            elif image_processing.get("quality_score", 0) < 6.0:
                recommendations.append("이미지 품질 개선이 필요합니다")
            
            # 가이드라인 관련
            guideline_application = steps.get("guideline_application", {})
            if not guideline_application.get("all_valid"):
                warnings.append("마켓 가이드라인 준수에 문제가 있습니다")
            
            validation_results["warnings"] = warnings
            validation_results["recommendations"] = recommendations
            
            # 최종 추천 액션
            if quality_score >= 8.0 and not warnings:
                validation_results["recommended_action"] = "즉시 업로드 가능"
            elif quality_score >= 6.0:
                validation_results["recommended_action"] = "검토 후 업로드"
            else:
                validation_results["recommended_action"] = "재가공 필요"
            
            return {
                "success": True,
                "validation_results": validation_results,
                "overall_success": len(warnings) == 0 and quality_score >= 6.0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_quality_score(self, processing_results: Dict) -> float:
        """품질 점수 계산 (0-10)"""
        
        scores = []
        
        steps = processing_results.get("steps", {})
        
        # 상품명 점수
        name_processing = steps.get("name_processing", {})
        if name_processing.get("success") and name_processing.get("final_names"):
            scores.append(8.0)
        else:
            scores.append(4.0)
        
        # 이미지 점수
        image_processing = steps.get("image_processing", {})
        if image_processing.get("success"):
            image_quality = image_processing.get("quality_score", 0)
            scores.append(min(image_quality, 10.0))
        else:
            scores.append(3.0)
        
        # 용도 분석 점수
        purpose_analysis = steps.get("purpose_analysis", {})
        if purpose_analysis.get("success"):
            scores.append(7.0)
        else:
            scores.append(5.0)
        
        # 가이드라인 준수 점수
        guideline_application = steps.get("guideline_application", {})
        if guideline_application.get("all_valid"):
            scores.append(9.0)
        else:
            scores.append(6.0)
        
        return round(sum(scores) / len(scores), 2) if scores else 0.0
    
    async def _save_processing_history(
        self,
        product: Product,
        marketplace: str,
        results: Dict,
        processing_options: Dict,
        success: bool = True
    ):
        """처리 이력 저장"""
        
        try:
            processing_history = ProductProcessingHistory(
                original_product_id=product.id,
                processing_type="complete_processing",
                original_data={
                    "name": product.name,
                    "description": product.description,
                    "image_urls": product.image_urls,
                    "marketplace": marketplace
                },
                processed_data=results,
                ai_model_used="mixed",  # 여러 모델 사용
                processing_cost=Decimal("0.00"),  # 실제로는 각 단계 비용 합산
                success=success,
                processing_time_ms=results.get("total_processing_time_ms", 0),
                created_at=datetime.now()
            )
            
            self.db.add(processing_history)
            self.db.commit()
            
        except Exception as e:
            print(f"처리 이력 저장 오류: {e}")
            self.db.rollback()
    
    def get_processing_history(
        self, 
        product_id: Optional[int] = None,
        marketplace: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """처리 이력 조회"""
        
        query = self.db.query(ProductProcessingHistory)
        
        if product_id:
            query = query.filter(ProductProcessingHistory.original_product_id == product_id)
        
        if marketplace:
            query = query.filter(
                ProductProcessingHistory.original_data["marketplace"].astext == marketplace
            )
        
        history_records = query.order_by(
            ProductProcessingHistory.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": record.id,
                "product_id": record.original_product_id,
                "processing_type": record.processing_type,
                "success": record.success,
                "processing_time_ms": record.processing_time_ms,
                "created_at": record.created_at.isoformat(),
                "results_summary": self._summarize_results(record.processed_data)
            }
            for record in history_records
        ]
    
    def _summarize_results(self, processed_data: Dict) -> Dict:
        """결과 요약"""
        
        steps = processed_data.get("steps", {})
        
        return {
            "total_steps": len(steps),
            "successful_steps": sum(1 for step in steps.values() if step.get("success")),
            "overall_success": processed_data.get("success", False),
            "quality_score": steps.get("final_validation", {}).get("validation_results", {}).get("quality_score", 0)
        }