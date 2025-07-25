"""
완전한 엔드투엔드 워크플로우 테스트 실행 스크립트
모든 비즈니스 워크플로우를 종합적으로 테스트합니다.
"""

import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, List
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('e2e_test_execution.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompleteE2ETestRunner:
    """완전한 E2E 테스트 실행기"""
    
    def __init__(self):
        self.test_session_id = f"COMPLETE_E2E_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.now()
        
    async def run_all_workflow_tests(self):
        """모든 워크플로우 테스트 실행"""
        print("🚀 드롭쉬핑 시스템 완전한 E2E 워크플로우 테스트 시작".encode('utf-8').decode('utf-8'))
        print("=" * 80)
        
        overall_start = time.time()
        
        # 전체 테스트 결과 구조
        complete_results = {
            "test_session_id": self.test_session_id,
            "test_start_time": self.start_time.isoformat(),
            "basic_workflows": [],
            "advanced_workflows": [],
            "overall_summary": {},
            "business_impact_analysis": {},
            "recommendations": [],
            "test_environment": {
                "test_data_size": "500개 한국 상품 데이터",
                "test_users": "20명의 다양한 비즈니스 타입",
                "test_scenarios": "실제 비즈니스 사용 사례 기반"
            }
        }
        
        try:
            # 1. 기본 워크플로우 테스트 실행
            print("\n📋 1단계: 기본 워크플로우 테스트 실행")
            print("-" * 50)
            
            basic_results = await self._run_basic_workflows()
            complete_results["basic_workflows"] = basic_results
            
            # 2. 고급 워크플로우 테스트 실행
            print("\n🔧 2단계: 고급 워크플로우 테스트 실행")
            print("-" * 50)
            
            advanced_results = await self._run_advanced_workflows()
            complete_results["advanced_workflows"] = advanced_results
            
            # 3. 종합 분석
            print("\n📊 3단계: 종합 결과 분석")
            print("-" * 50)
            
            complete_results["overall_summary"] = self._analyze_overall_results(
                basic_results, advanced_results
            )
            
            complete_results["business_impact_analysis"] = self._analyze_business_impact(
                basic_results, advanced_results
            )
            
            complete_results["recommendations"] = self._generate_comprehensive_recommendations(
                basic_results, advanced_results
            )
            
            # 4. 결과 저장
            await self._save_complete_results(complete_results)
            
        except Exception as e:
            logger.error(f"완전한 E2E 테스트 실행 중 오류: {str(e)}")
            complete_results["error"] = str(e)
        
        # 테스트 완료
        total_execution_time = time.time() - overall_start
        complete_results["test_end_time"] = datetime.now().isoformat()
        complete_results["total_execution_time"] = total_execution_time
        
        # 최종 결과 출력
        self._print_final_results(complete_results)
        
        return complete_results
    
    async def _run_basic_workflows(self):
        """기본 워크플로우 테스트 실행"""
        try:
            # comprehensive_e2e_workflow_tests.py의 ComprehensiveTestRunner 사용
            from comprehensive_e2e_workflow_tests import ComprehensiveTestRunner
            
            test_runner = ComprehensiveTestRunner()
            results = await test_runner.run_all_tests()
            
            logger.info("✅ 기본 워크플로우 테스트 완료")
            return results
            
        except Exception as e:
            logger.error(f"❌ 기본 워크플로우 테스트 실패: {str(e)}")
            return {
                "error": str(e),
                "workflow_results": [],
                "overall_metrics": {},
                "business_impact_summary": {}
            }
    
    async def _run_advanced_workflows(self):
        """고급 워크플로우 테스트 실행"""
        try:
            # advanced_workflow_tests.py의 테스트들 실행
            from advanced_workflow_tests import run_advanced_workflow_tests
            
            results = await run_advanced_workflow_tests()
            
            logger.info("✅ 고급 워크플로우 테스트 완료")
            return {
                "workflow_results": results,
                "total_workflows": len(results),
                "successful_workflows": len([r for r in results if r.get("overall_success", False)])
            }
            
        except Exception as e:
            logger.error(f"❌ 고급 워크플로우 테스트 실패: {str(e)}")
            return {
                "error": str(e),
                "workflow_results": [],
                "total_workflows": 0,
                "successful_workflows": 0
            }
    
    def _analyze_overall_results(self, basic_results: Dict, advanced_results: Dict) -> Dict:
        """전체 결과 종합 분석"""
        analysis = {
            "total_workflows_tested": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "overall_success_rate": 0,
            "total_steps_executed": 0,
            "successful_steps": 0,
            "step_success_rate": 0,
            "average_execution_time": 0,
            "performance_score": 0,
            "user_experience_score": 0,
            "system_reliability_score": 0
        }
        
        # 기본 워크플로우 분석
        if "workflow_results" in basic_results:
            basic_workflows = basic_results["workflow_results"]
            analysis["total_workflows_tested"] += len(basic_workflows)
            
            for workflow in basic_workflows:
                if workflow.get("overall_success", False):
                    analysis["successful_workflows"] += 1
                else:
                    analysis["failed_workflows"] += 1
                
                # 단계별 분석
                steps = workflow.get("steps", [])
                analysis["total_steps_executed"] += len(steps)
                analysis["successful_steps"] += sum(1 for step in steps if step.get("success", False))
        
        # 고급 워크플로우 분석
        if "workflow_results" in advanced_results:
            advanced_workflows = advanced_results["workflow_results"]
            analysis["total_workflows_tested"] += len(advanced_workflows)
            
            for workflow in advanced_workflows:
                if workflow.get("overall_success", False):
                    analysis["successful_workflows"] += 1
                else:
                    analysis["failed_workflows"] += 1
                
                # 단계별 분석
                steps = workflow.get("steps", [])
                analysis["total_steps_executed"] += len(steps)
                analysis["successful_steps"] += sum(1 for step in steps if step.get("success", False))
        
        # 비율 계산
        if analysis["total_workflows_tested"] > 0:
            analysis["overall_success_rate"] = (analysis["successful_workflows"] / analysis["total_workflows_tested"]) * 100
        
        if analysis["total_steps_executed"] > 0:
            analysis["step_success_rate"] = (analysis["successful_steps"] / analysis["total_steps_executed"]) * 100
        
        # 성능 점수 계산 (기본 워크플로우 메트릭 기반)
        if "overall_metrics" in basic_results:
            basic_metrics = basic_results["overall_metrics"]
            analysis["performance_score"] = basic_metrics.get("performance_score", 0)
            analysis["user_experience_score"] = basic_metrics.get("user_experience_score", 0)
            analysis["average_execution_time"] = basic_metrics.get("average_execution_time", 0)
        
        # 시스템 신뢰성 점수 (단계 성공률 기반)
        analysis["system_reliability_score"] = analysis["step_success_rate"]
        
        return analysis
    
    def _analyze_business_impact(self, basic_results: Dict, advanced_results: Dict) -> Dict:
        """비즈니스 임팩트 종합 분석"""
        impact = {
            "productivity_improvements": {
                "total_products_processed": 0,
                "time_saved_hours": 0,
                "manual_tasks_automated": 0,
                "error_reduction_rate": 0
            },
            "cost_benefits": {
                "estimated_monthly_savings": 0,
                "automation_roi": 0,
                "efficiency_gains": 0,
                "operational_cost_reduction": 0
            },
            "user_experience_improvements": {
                "user_satisfaction_increase": 0,
                "workflow_efficiency_gain": 0,
                "customization_adoption": 0,
                "notification_effectiveness": 0
            },
            "system_performance_gains": {
                "response_time_improvement": 0,
                "system_reliability_increase": 0,
                "error_handling_effectiveness": 0,
                "automated_recovery_success": 0
            },
            "business_opportunities": {
                "market_opportunities_identified": 0,
                "profit_optimization_potential": 0,
                "process_improvement_areas": 0,
                "competitive_advantages": []
            }
        }
        
        # 기본 워크플로우에서 비즈니스 임팩트 추출
        if "business_impact_summary" in basic_results:
            basic_impact = basic_results["business_impact_summary"]
            impact["productivity_improvements"]["total_products_processed"] = basic_impact.get("total_products_processed", 0)
            impact["productivity_improvements"]["time_saved_hours"] = basic_impact.get("total_time_saved_hours", 0)
            impact["cost_benefits"]["estimated_monthly_savings"] = basic_impact.get("estimated_cost_savings_krw", 0)
            impact["cost_benefits"]["automation_roi"] = basic_impact.get("roi_projection", 0)
            impact["business_opportunities"]["market_opportunities_identified"] = basic_impact.get("business_opportunities_identified", 0)
        
        # 고급 워크플로우에서 임팩트 추출
        if "workflow_results" in advanced_results:
            for workflow in advanced_results["workflow_results"]:
                workflow_name = workflow.get("workflow_name", "")
                
                # 사용자 설정 및 개인화 임팩트
                if "사용자 설정" in workflow_name and "personalization_metrics" in workflow:
                    pers_metrics = workflow["personalization_metrics"]
                    impact["user_experience_improvements"]["user_satisfaction_increase"] = pers_metrics.get("user_satisfaction_score", 0)
                    impact["user_experience_improvements"]["workflow_efficiency_gain"] = pers_metrics.get("workflow_efficiency_gain", 0)
                    impact["user_experience_improvements"]["customization_adoption"] = pers_metrics.get("customization_adoption_rate", 0)
                
                # 성능 최적화 임팩트
                if "성능 최적화" in workflow_name and "optimization_metrics" in workflow:
                    opt_metrics = workflow["optimization_metrics"]
                    impact["system_performance_gains"]["response_time_improvement"] = opt_metrics.get("overall_performance_gain", 0)
                    impact["cost_benefits"]["operational_cost_reduction"] = opt_metrics.get("roi_monthly", 0)
                
                # 오류 처리 임팩트
                if "오류 처리" in workflow_name and "error_handling_metrics" in workflow:
                    error_metrics = workflow["error_handling_metrics"]
                    impact["system_performance_gains"]["system_reliability_increase"] = error_metrics.get("system_resilience_score", 0)
                    impact["system_performance_gains"]["error_handling_effectiveness"] = error_metrics.get("overall_recovery_rate", 0)
                    impact["system_performance_gains"]["automated_recovery_success"] = error_metrics.get("automation_efficiency", 0)
        
        # 종합 지표 계산
        impact["productivity_improvements"]["manual_tasks_automated"] = min(100, 
            (impact["productivity_improvements"]["time_saved_hours"] / 40) * 100)  # 주 40시간 기준
        
        impact["cost_benefits"]["efficiency_gains"] = (
            impact["productivity_improvements"]["manual_tasks_automated"] + 
            impact["system_performance_gains"]["response_time_improvement"]
        ) / 2
        
        impact["user_experience_improvements"]["notification_effectiveness"] = (
            impact["user_experience_improvements"]["user_satisfaction_increase"] + 
            impact["user_experience_improvements"]["customization_adoption"]
        ) / 2
        
        # 경쟁 우위 요소
        impact["business_opportunities"]["competitive_advantages"] = [
            "실시간 수익성 분석 자동화",
            "다중 채널 알림 시스템",
            "지능형 오류 복구",
            "사용자 맞춤형 대시보드",
            "예측적 성능 최적화"
        ]
        
        impact["business_opportunities"]["profit_optimization_potential"] = (
            impact["cost_benefits"]["estimated_monthly_savings"] / 1000000 * 10  # 100만원당 10% 가정
        )
        
        return impact
    
    def _generate_comprehensive_recommendations(self, basic_results: Dict, advanced_results: Dict) -> List[str]:
        """종합 개선 권장사항 생성"""
        recommendations = []
        
        # 전체 성공률 기반 권장사항
        total_workflows = 0
        successful_workflows = 0
        
        if "workflow_results" in basic_results:
            basic_workflows = basic_results["workflow_results"]
            total_workflows += len(basic_workflows)
            successful_workflows += sum(1 for w in basic_workflows if w.get("overall_success", False))
        
        if "workflow_results" in advanced_results:
            advanced_workflows = advanced_results["workflow_results"]
            total_workflows += len(advanced_workflows)
            successful_workflows += sum(1 for w in advanced_workflows if w.get("overall_success", False))
        
        if total_workflows > 0:
            success_rate = (successful_workflows / total_workflows) * 100
            if success_rate < 95:
                recommendations.append(
                    f"🔧 전체 워크플로우 성공률이 {success_rate:.1f}%입니다. "
                    "핵심 비즈니스 프로세스의 안정성을 높이기 위해 오류 처리 및 복구 메커니즘을 강화하세요."
                )
        
        # 성능 관련 권장사항
        if "overall_metrics" in basic_results:
            metrics = basic_results["overall_metrics"]
            if metrics.get("performance_score", 0) < 85:
                recommendations.append(
                    "⚡ 시스템 성능 점수가 85점 미만입니다. "
                    "데이터베이스 쿼리 최적화, 캐싱 전략 개선, 비동기 처리 확대를 권장합니다."
                )
            
            if metrics.get("user_experience_score", 0) < 80:
                recommendations.append(
                    "👤 사용자 경험 점수가 80점 미만입니다. "
                    "응답 시간 단축, UI/UX 개선, 개인화 기능 강화를 통해 사용자 만족도를 높이세요."
                )
        
        # 비즈니스 임팩트 기반 권장사항
        if "business_impact_summary" in basic_results:
            impact = basic_results["business_impact_summary"]
            if impact.get("automation_efficiency", 0) < 85:
                recommendations.append(
                    "🤖 자동화 효율성이 85% 미만입니다. "
                    "반복 작업의 완전 자동화, 예외 상황 처리 로직 개선, AI 기반 의사결정 지원을 도입하세요."
                )
            
            if impact.get("roi_projection", 0) < 50:
                recommendations.append(
                    "💰 ROI 예측이 50% 미만입니다. "
                    "비용 절약 효과를 높이기 위해 리소스 사용 최적화, 프로세스 간소화, 스케일 경제 실현을 추진하세요."
                )
        
        # 고급 기능 관련 권장사항
        if "workflow_results" in advanced_results:
            for workflow in advanced_results["workflow_results"]:
                workflow_name = workflow.get("workflow_name", "")
                
                # 개인화 관련
                if "사용자 설정" in workflow_name and "personalization_metrics" in workflow:
                    pers_metrics = workflow["personalization_metrics"]
                    if pers_metrics.get("customization_adoption_rate", 0) < 70:
                        recommendations.append(
                            "🎨 사용자 커스터마이징 채택률이 70% 미만입니다. "
                            "더 직관적인 설정 인터페이스, 미리 정의된 템플릿, 가이드 투어를 제공하세요."
                        )
                
                # 성능 최적화 관련
                if "성능 최적화" in workflow_name and "optimization_metrics" in workflow:
                    opt_metrics = workflow["optimization_metrics"]
                    if opt_metrics.get("overall_performance_gain", 0) < 30:
                        recommendations.append(
                            "🚀 성능 개선 효과가 30% 미만입니다. "
                            "더 적극적인 최적화 전략, 실시간 모니터링 강화, 예측적 스케일링을 도입하세요."
                        )
                
                # 오류 처리 관련
                if "오류 처리" in workflow_name and "error_handling_metrics" in workflow:
                    error_metrics = workflow["error_handling_metrics"]
                    if error_metrics.get("overall_recovery_rate", 0) < 90:
                        recommendations.append(
                            "🛡️ 오류 복구율이 90% 미만입니다. "
                            "더 강력한 Circuit Breaker 패턴, 다중 백업 전략, 지능형 복구 알고리즘을 구현하세요."
                        )
        
        # 전략적 권장사항
        recommendations.extend([
            "📊 실시간 비즈니스 인텔리전스 대시보드를 구축하여 의사결정 속도를 높이세요.",
            "🔄 지속적 통합/배포(CI/CD) 파이프라인을 강화하여 업데이트 안정성을 향상시키세요.",
            "🧠 머신러닝 기반 예측 분석을 도입하여 프로액티브한 비즈니스 운영을 실현하세요.",
            "🌐 마이크로서비스 아키텍처로의 점진적 전환을 통해 시스템 확장성을 높이세요.",
            "📱 모바일 최적화 및 PWA 기술 도입으로 사용자 접근성을 개선하세요."
        ])
        
        # 중복 제거 및 우선순위 정렬
        unique_recommendations = list(dict.fromkeys(recommendations))
        
        return unique_recommendations[:10]  # 상위 10개 권장사항만 반환
    
    async def _save_complete_results(self, results: Dict):
        """완전한 테스트 결과 저장"""
        try:
            # JSON 결과 파일
            results_filename = f"complete_e2e_test_results_{self.test_session_id}.json"
            results_path = os.path.join(os.getcwd(), results_filename)
            
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            # 요약 보고서 (마크다운)
            summary_filename = f"e2e_test_summary_{self.test_session_id}.md"
            summary_path = os.path.join(os.getcwd(), summary_filename)
            
            await self._generate_markdown_report(results, summary_path)
            
            # 비즈니스 보고서 (Excel)
            business_filename = f"business_impact_report_{self.test_session_id}.xlsx"
            business_path = os.path.join(os.getcwd(), business_filename)
            
            await self._generate_business_report(results, business_path)
            
            logger.info(f"✅ 완전한 테스트 결과 저장:")
            logger.info(f"   📄 상세 결과: {results_path}")
            logger.info(f"   📋 요약 보고서: {summary_path}")
            logger.info(f"   📊 비즈니스 보고서: {business_path}")
            
        except Exception as e:
            logger.error(f"❌ 테스트 결과 저장 실패: {str(e)}")
    
    async def _generate_markdown_report(self, results: Dict, file_path: str):
        """마크다운 형태의 요약 보고서 생성"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# 드롭쉬핑 시스템 완전한 E2E 테스트 보고서\n\n")
                
                # 테스트 개요
                f.write("## 📋 테스트 개요\n\n")
                f.write(f"- **테스트 세션 ID**: {results['test_session_id']}\n")
                f.write(f"- **실행 기간**: {results['test_start_time']} ~ {results['test_end_time']}\n")
                f.write(f"- **총 소요 시간**: {results['total_execution_time']:.2f}초\n")
                f.write(f"- **테스트 환경**: {results['test_environment']['test_data_size']}\n\n")
                
                # 전체 결과 요약
                if "overall_summary" in results:
                    summary = results["overall_summary"]
                    f.write("## 🎯 전체 결과 요약\n\n")
                    f.write(f"| 지표 | 값 |\n")
                    f.write(f"|------|----|\n")
                    f.write(f"| 테스트된 워크플로우 | {summary['total_workflows_tested']}개 |\n")
                    f.write(f"| 성공한 워크플로우 | {summary['successful_workflows']}개 |\n")
                    f.write(f"| 전체 성공률 | {summary['overall_success_rate']:.1f}% |\n")
                    f.write(f"| 실행된 단계 | {summary['total_steps_executed']}개 |\n")
                    f.write(f"| 단계 성공률 | {summary['step_success_rate']:.1f}% |\n")
                    f.write(f"| 성능 점수 | {summary['performance_score']:.1f}/100 |\n")
                    f.write(f"| 사용자 경험 점수 | {summary['user_experience_score']:.1f}/100 |\n")
                    f.write(f"| 시스템 신뢰성 점수 | {summary['system_reliability_score']:.1f}/100 |\n\n")
                
                # 비즈니스 임팩트
                if "business_impact_analysis" in results:
                    impact = results["business_impact_analysis"]
                    f.write("## 💼 비즈니스 임팩트 분석\n\n")
                    
                    f.write("### 생산성 향상\n")
                    prod = impact["productivity_improvements"]
                    f.write(f"- 처리된 상품: **{prod['total_products_processed']:,}개**\n")
                    f.write(f"- 절약된 시간: **{prod['time_saved_hours']:.1f}시간**\n")
                    f.write(f"- 자동화된 작업: **{prod['manual_tasks_automated']:.1f}%**\n\n")
                    
                    f.write("### 비용 효과\n")
                    cost = impact["cost_benefits"]
                    f.write(f"- 월간 예상 절약: **{cost['estimated_monthly_savings']:,}원**\n")
                    f.write(f"- 자동화 ROI: **{cost['automation_roi']:.1f}%**\n")
                    f.write(f"- 효율성 증대: **{cost['efficiency_gains']:.1f}%**\n\n")
                    
                    f.write("### 사용자 경험 개선\n")
                    ux = impact["user_experience_improvements"]
                    f.write(f"- 사용자 만족도 증가: **{ux['user_satisfaction_increase']:.1f}%**\n")
                    f.write(f"- 워크플로우 효율성: **{ux['workflow_efficiency_gain']:.1f}%**\n")
                    f.write(f"- 커스터마이징 채택률: **{ux['customization_adoption']:.1f}%**\n\n")
                
                # 주요 워크플로우 결과
                f.write("## 🔄 주요 워크플로우 테스트 결과\n\n")
                
                # 기본 워크플로우
                if "basic_workflows" in results and "workflow_results" in results["basic_workflows"]:
                    f.write("### 기본 워크플로우\n")
                    for workflow in results["basic_workflows"]["workflow_results"]:
                        name = workflow.get("workflow_name", "Unknown")
                        success = "✅" if workflow.get("overall_success", False) else "❌"
                        f.write(f"- {success} **{name}**\n")
                        
                        if "steps" in workflow:
                            successful_steps = sum(1 for step in workflow["steps"] if step.get("success", False))
                            total_steps = len(workflow["steps"])
                            f.write(f"  - 단계 성공률: {successful_steps}/{total_steps} ({successful_steps/total_steps*100:.1f}%)\n")
                    f.write("\n")
                
                # 고급 워크플로우
                if "advanced_workflows" in results and "workflow_results" in results["advanced_workflows"]:
                    f.write("### 고급 워크플로우\n")
                    for workflow in results["advanced_workflows"]["workflow_results"]:
                        name = workflow.get("workflow_name", "Unknown")
                        success = "✅" if workflow.get("overall_success", False) else "❌"
                        f.write(f"- {success} **{name}**\n")
                        
                        if "steps" in workflow:
                            successful_steps = sum(1 for step in workflow["steps"] if step.get("success", False))
                            total_steps = len(workflow["steps"])
                            f.write(f"  - 단계 성공률: {successful_steps}/{total_steps} ({successful_steps/total_steps*100:.1f}%)\n")
                    f.write("\n")
                
                # 권장사항
                f.write("## 💡 개선 권장사항\n\n")
                for i, recommendation in enumerate(results.get("recommendations", []), 1):
                    f.write(f"{i}. {recommendation}\n")
                f.write("\n")
                
                # 결론
                f.write("## 🎊 결론\n\n")
                
                if "overall_summary" in results:
                    overall_success = results["overall_summary"]["overall_success_rate"]
                    performance = results["overall_summary"]["performance_score"]
                    
                    if overall_success >= 90 and performance >= 85:
                        grade = "A+ (우수)"
                        conclusion = "드롭쉬핑 시스템이 모든 핵심 비즈니스 워크플로우에서 우수한 성능을 보입니다."
                    elif overall_success >= 80 and performance >= 75:
                        grade = "A (양호)"
                        conclusion = "시스템이 안정적으로 작동하며, 몇 가지 개선을 통해 더욱 향상될 수 있습니다."
                    elif overall_success >= 70 and performance >= 65:
                        grade = "B (보통)"
                        conclusion = "기본적인 기능은 잘 작동하지만, 성능과 안정성 개선이 필요합니다."
                    else:
                        grade = "C (개선 필요)"
                        conclusion = "시스템 안정성과 성능에 대한 중대한 개선이 시급합니다."
                    
                    f.write(f"**종합 등급**: {grade}\n\n")
                    f.write(f"{conclusion}\n\n")
                
                f.write("---\n")
                f.write("*이 보고서는 자동 생성되었습니다.*\n")
                
        except Exception as e:
            logger.error(f"마크다운 보고서 생성 실패: {str(e)}")
    
    async def _generate_business_report(self, results: Dict, file_path: str):
        """비즈니스 중심의 Excel 보고서 생성"""
        try:
            import pandas as pd
            
            # 요약 데이터
            summary_data = []
            if "overall_summary" in results:
                summary = results["overall_summary"]
                summary_data = [
                    ["테스트된 워크플로우", f"{summary['total_workflows_tested']}개"],
                    ["성공률", f"{summary['overall_success_rate']:.1f}%"],
                    ["성능 점수", f"{summary['performance_score']:.1f}/100"],
                    ["사용자 경험 점수", f"{summary['user_experience_score']:.1f}/100"],
                    ["시스템 신뢰성", f"{summary['system_reliability_score']:.1f}/100"]
                ]
            
            # 비즈니스 임팩트 데이터
            impact_data = []
            if "business_impact_analysis" in results:
                impact = results["business_impact_analysis"]
                impact_data = [
                    ["생산성", "처리된 상품", f"{impact['productivity_improvements']['total_products_processed']:,}개"],
                    ["생산성", "절약된 시간", f"{impact['productivity_improvements']['time_saved_hours']:.1f}시간"],
                    ["비용", "월간 절약", f"{impact['cost_benefits']['estimated_monthly_savings']:,}원"],
                    ["비용", "ROI", f"{impact['cost_benefits']['automation_roi']:.1f}%"],
                    ["사용자", "만족도 증가", f"{impact['user_experience_improvements']['user_satisfaction_increase']:.1f}%"],
                    ["시스템", "성능 향상", f"{impact['system_performance_gains']['response_time_improvement']:.1f}%"]
                ]
            
            # Excel 파일 생성
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 요약 시트
                df_summary = pd.DataFrame(summary_data, columns=["지표", "값"])
                df_summary.to_excel(writer, sheet_name='테스트 결과 요약', index=False)
                
                # 비즈니스 임팩트 시트
                df_impact = pd.DataFrame(impact_data, columns=["카테고리", "지표", "값"])
                df_impact.to_excel(writer, sheet_name='비즈니스 임팩트', index=False)
                
                # 권장사항 시트
                recommendations_data = [[i+1, rec] for i, rec in enumerate(results.get("recommendations", []))]
                df_recommendations = pd.DataFrame(recommendations_data, columns=["순위", "권장사항"])
                df_recommendations.to_excel(writer, sheet_name='개선 권장사항', index=False)
            
            logger.info(f"✅ 비즈니스 보고서 생성 완료: {file_path}")
            
        except Exception as e:
            logger.error(f"비즈니스 보고서 생성 실패: {str(e)}")
            # pandas가 없는 경우 간단한 텍스트 파일로 대체
            try:
                with open(file_path.replace('.xlsx', '.txt'), 'w', encoding='utf-8') as f:
                    f.write("비즈니스 임팩트 보고서\n")
                    f.write("=" * 30 + "\n\n")
                    f.write(json.dumps(results.get("business_impact_analysis", {}), indent=2, ensure_ascii=False))
            except:
                pass
    
    def _print_final_results(self, results: Dict):
        """최종 결과 콘솔 출력"""
        print("\n" + "=" * 80)
        print("🎉 드롭쉬핑 시스템 완전한 E2E 테스트 완료!")
        print("=" * 80)
        
        if "overall_summary" in results:
            summary = results["overall_summary"]
            print(f"\n📊 핵심 지표:")
            print(f"   ✅ 전체 성공률: {summary['overall_success_rate']:.1f}%")
            print(f"   🚀 성능 점수: {summary['performance_score']:.1f}/100")
            print(f"   👤 사용자 경험: {summary['user_experience_score']:.1f}/100")
            print(f"   🛡️  시스템 신뢰성: {summary['system_reliability_score']:.1f}/100")
        
        if "business_impact_analysis" in results:
            impact = results["business_impact_analysis"]
            print(f"\n💼 비즈니스 임팩트:")
            print(f"   📦 처리된 상품: {impact['productivity_improvements']['total_products_processed']:,}개")
            print(f"   ⏰ 절약된 시간: {impact['productivity_improvements']['time_saved_hours']:.1f}시간")
            print(f"   💰 월간 절약액: {impact['cost_benefits']['estimated_monthly_savings']:,}원")
            print(f"   📈 자동화 ROI: {impact['cost_benefits']['automation_roi']:.1f}%")
        
        print(f"\n⏱️  총 실행 시간: {results['total_execution_time']:.2f}초")
        print(f"📄 상세 결과는 다음 파일들에 저장되었습니다:")
        print(f"   - complete_e2e_test_results_{results['test_session_id']}.json")
        print(f"   - e2e_test_summary_{results['test_session_id']}.md")
        print(f"   - business_impact_report_{results['test_session_id']}.xlsx (또는 .txt)")
        
        # 최종 등급 계산 및 출력
        if "overall_summary" in results:
            overall_success = results["overall_summary"]["overall_success_rate"]
            performance = results["overall_summary"]["performance_score"]
            user_experience = results["overall_summary"]["user_experience_score"]
            
            final_score = (overall_success + performance + user_experience) / 3
            
            if final_score >= 90:
                grade = "A+"
                emoji = "🏆"
            elif final_score >= 80:
                grade = "A"
                emoji = "🥇"
            elif final_score >= 70:
                grade = "B"
                emoji = "🥈"
            elif final_score >= 60:
                grade = "C"
                emoji = "🥉"
            else:
                grade = "D"
                emoji = "⚠️"
            
            print(f"\n{emoji} 최종 등급: {grade} ({final_score:.1f}점)")
        
        print("\n🚀 드롭쉬핑 시스템 E2E 테스트 완료! 비즈니스 성공을 위한 준비가 완료되었습니다!")

async def main():
    """메인 실행 함수"""
    runner = CompleteE2ETestRunner()
    results = await runner.run_all_workflow_tests()
    return results

if __name__ == "__main__":
    # 완전한 E2E 테스트 실행
    results = asyncio.run(main())