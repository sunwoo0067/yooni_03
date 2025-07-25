"""
파이프라인 통합 시스템 유닛 테스트
- 워크플로우 실행 테스트
- 상태 관리 테스트
- 에러 복구 테스트
- 진행상황 추적 테스트
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import asyncio
import json
from typing import List, Dict, Any
from enum import Enum

from app.services.pipeline.workflow_orchestrator import WorkflowOrchestrator
from app.services.pipeline.state_manager import StateManager
from app.services.pipeline.progress_tracker import ProgressTracker
from app.models.pipeline import PipelineStatus, PipelineStep


class TestWorkflowOrchestrator:
    """워크플로우 오케스트레이터 테스트"""
    
    @pytest.fixture
    def orchestrator(self):
        return WorkflowOrchestrator()
    
    def test_create_workflow(self, orchestrator):
        """워크플로우 생성 테스트"""
        workflow_config = {
            "name": "상품 등록 워크플로우",
            "steps": [
                {"name": "collect", "type": "collection", "config": {}},
                {"name": "process", "type": "processing", "config": {}},
                {"name": "register", "type": "registration", "config": {}}
            ],
            "triggers": {
                "schedule": "0 9 * * *",  # 매일 오전 9시
                "manual": True
            }
        }
        
        workflow = orchestrator.create_workflow(workflow_config)
        
        assert workflow["id"] is not None
        assert workflow["name"] == "상품 등록 워크플로우"
        assert len(workflow["steps"]) == 3
        assert workflow["status"] == "created"
    
    @pytest.mark.asyncio
    async def test_execute_workflow(self, orchestrator):
        """워크플로우 실행 테스트"""
        workflow_id = "WF123"
        
        # Mock step executors
        mock_steps = {
            "collect": Mock(return_value={"products": 10}),
            "process": Mock(return_value={"processed": 10}),
            "register": Mock(return_value={"registered": 10})
        }
        
        with patch.object(orchestrator, '_execute_step') as mock_execute:
            mock_execute.side_effect = [
                {"status": "success", "output": {"products": 10}},
                {"status": "success", "output": {"processed": 10}},
                {"status": "success", "output": {"registered": 10}}
            ]
            
            result = await orchestrator.execute_workflow(workflow_id)
        
        assert result["status"] == "completed"
        assert result["total_steps"] == 3
        assert result["completed_steps"] == 3
        assert mock_execute.call_count == 3
    
    def test_workflow_validation(self, orchestrator):
        """워크플로우 유효성 검사 테스트"""
        # 유효한 워크플로우
        valid_workflow = {
            "steps": [
                {"name": "step1", "type": "collection"},
                {"name": "step2", "type": "processing", "depends_on": ["step1"]}
            ]
        }
        
        is_valid, errors = orchestrator.validate_workflow(valid_workflow)
        assert is_valid == True
        assert len(errors) == 0
        
        # 순환 의존성이 있는 워크플로우
        circular_workflow = {
            "steps": [
                {"name": "step1", "depends_on": ["step2"]},
                {"name": "step2", "depends_on": ["step1"]}
            ]
        }
        
        is_valid, errors = orchestrator.validate_workflow(circular_workflow)
        assert is_valid == False
        assert "순환 의존성" in str(errors)
    
    @pytest.mark.asyncio
    async def test_parallel_step_execution(self, orchestrator):
        """병렬 스텝 실행 테스트"""
        workflow = {
            "steps": [
                {"name": "collect_zentrade", "type": "collection", "parallel": True},
                {"name": "collect_ownerclan", "type": "collection", "parallel": True},
                {"name": "collect_domeggook", "type": "collection", "parallel": True},
                {"name": "merge", "type": "merge", "depends_on": ["collect_zentrade", "collect_ownerclan", "collect_domeggook"]}
            ]
        }
        
        start_time = datetime.now()
        
        with patch.object(orchestrator, '_execute_step') as mock_execute:
            # 각 스텝이 1초씩 걸린다고 가정
            async def delayed_response(step):
                await asyncio.sleep(0.1)
                return {"status": "success", "output": {}}
            
            mock_execute.side_effect = lambda s: delayed_response(s)
            
            result = await orchestrator.execute_workflow_steps(workflow["steps"])
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # 병렬 실행이므로 1초 정도만 걸려야 함 (순차적이면 3초)
        assert execution_time < 0.5
        assert mock_execute.call_count == 4
    
    def test_workflow_retry_logic(self, orchestrator):
        """워크플로우 재시도 로직 테스트"""
        workflow_step = {
            "name": "flaky_step",
            "type": "processing",
            "retry": {
                "max_attempts": 3,
                "backoff": "exponential",
                "initial_delay": 1
            }
        }
        
        with patch.object(orchestrator, '_execute_step_logic') as mock_logic:
            mock_logic.side_effect = [
                Exception("일시적 오류"),
                Exception("또 실패"),
                {"status": "success"}  # 세 번째 시도에서 성공
            ]
            
            result = orchestrator.execute_with_retry(workflow_step)
        
        assert result["status"] == "success"
        assert mock_logic.call_count == 3


class TestStateManager:
    """상태 관리자 테스트"""
    
    @pytest.fixture
    def state_manager(self):
        return StateManager()
    
    def test_save_and_load_state(self, state_manager):
        """상태 저장 및 로드 테스트"""
        pipeline_id = "PL123"
        state = {
            "current_step": "processing",
            "processed_items": 50,
            "total_items": 100,
            "metadata": {
                "start_time": datetime.now().isoformat(),
                "errors": []
            }
        }
        
        # 상태 저장
        state_manager.save_state(pipeline_id, state)
        
        # 상태 로드
        loaded_state = state_manager.load_state(pipeline_id)
        
        assert loaded_state["current_step"] == "processing"
        assert loaded_state["processed_items"] == 50
        assert loaded_state["metadata"]["errors"] == []
    
    def test_state_transitions(self, state_manager):
        """상태 전이 테스트"""
        pipeline_id = "PL456"
        
        # 초기 상태
        state_manager.initialize_state(pipeline_id)
        state = state_manager.get_state(pipeline_id)
        assert state["status"] == PipelineStatus.PENDING
        
        # 시작
        state_manager.transition_to(pipeline_id, PipelineStatus.RUNNING)
        state = state_manager.get_state(pipeline_id)
        assert state["status"] == PipelineStatus.RUNNING
        
        # 완료
        state_manager.transition_to(pipeline_id, PipelineStatus.COMPLETED)
        state = state_manager.get_state(pipeline_id)
        assert state["status"] == PipelineStatus.COMPLETED
    
    def test_checkpoint_management(self, state_manager):
        """체크포인트 관리 테스트"""
        pipeline_id = "PL789"
        
        # 체크포인트 생성
        checkpoint1 = state_manager.create_checkpoint(pipeline_id, {
            "step": "collection",
            "progress": 30
        })
        
        checkpoint2 = state_manager.create_checkpoint(pipeline_id, {
            "step": "processing",
            "progress": 60
        })
        
        # 체크포인트 목록 조회
        checkpoints = state_manager.list_checkpoints(pipeline_id)
        assert len(checkpoints) == 2
        
        # 특정 체크포인트로 복원
        state_manager.restore_from_checkpoint(pipeline_id, checkpoint1["id"])
        state = state_manager.get_state(pipeline_id)
        assert state["step"] == "collection"
        assert state["progress"] == 30
    
    def test_distributed_locking(self, state_manager):
        """분산 락 테스트"""
        resource_id = "product_123"
        
        # 락 획득
        lock1 = state_manager.acquire_lock(resource_id, timeout=5)
        assert lock1 is not None
        
        # 동시에 같은 리소스 락 시도 (실패해야 함)
        lock2 = state_manager.acquire_lock(resource_id, timeout=0.1)
        assert lock2 is None
        
        # 락 해제
        state_manager.release_lock(resource_id, lock1)
        
        # 이제 락 획득 가능
        lock3 = state_manager.acquire_lock(resource_id, timeout=1)
        assert lock3 is not None
    
    def test_state_expiration(self, state_manager):
        """상태 만료 테스트"""
        pipeline_id = "PL_EXPIRE"
        
        # TTL이 있는 상태 저장
        state_manager.save_state(pipeline_id, {
            "data": "temporary"
        }, ttl=1)  # 1초 후 만료
        
        # 즉시 조회 (존재해야 함)
        state = state_manager.load_state(pipeline_id)
        assert state is not None
        
        # 2초 후 조회 (만료되어야 함)
        import time
        time.sleep(2)
        state = state_manager.load_state(pipeline_id)
        assert state is None


class TestProgressTracker:
    """진행상황 추적기 테스트"""
    
    @pytest.fixture
    def progress_tracker(self):
        return ProgressTracker()
    
    def test_track_progress(self, progress_tracker):
        """진행상황 추적 테스트"""
        task_id = "TASK123"
        
        # 작업 시작
        progress_tracker.start_task(task_id, total_items=100)
        
        # 진행상황 업데이트
        for i in range(5):
            progress_tracker.update_progress(task_id, processed=20)
        
        # 현재 진행상황 확인
        progress = progress_tracker.get_progress(task_id)
        
        assert progress["total_items"] == 100
        assert progress["processed_items"] == 100
        assert progress["percentage"] == 100.0
        assert progress["status"] == "completed"
    
    def test_estimated_time_remaining(self, progress_tracker):
        """남은 시간 예측 테스트"""
        task_id = "TASK456"
        
        progress_tracker.start_task(task_id, total_items=1000)
        
        # 시뮬레이션: 초당 10개 처리
        import time
        for i in range(3):
            progress_tracker.update_progress(task_id, processed=100)
            time.sleep(0.1)
        
        eta = progress_tracker.estimate_completion_time(task_id)
        
        assert eta is not None
        assert eta > datetime.now()
        # 대략 7초 후 완료 예상 (700개 남음 / 초당 100개)
    
    def test_progress_with_errors(self, progress_tracker):
        """에러가 있는 진행상황 추적 테스트"""
        task_id = "TASK789"
        
        progress_tracker.start_task(task_id, total_items=50)
        
        # 일부 성공, 일부 실패
        progress_tracker.update_progress(task_id, processed=10, success=8, failed=2)
        progress_tracker.update_progress(task_id, processed=10, success=9, failed=1)
        
        progress = progress_tracker.get_progress(task_id)
        
        assert progress["processed_items"] == 20
        assert progress["success_count"] == 17
        assert progress["error_count"] == 3
        assert progress["success_rate"] == 0.85
    
    def test_multi_stage_progress(self, progress_tracker):
        """다단계 진행상황 추적 테스트"""
        pipeline_id = "PIPELINE123"
        
        stages = [
            {"name": "collection", "weight": 0.3},
            {"name": "processing", "weight": 0.5},
            {"name": "registration", "weight": 0.2}
        ]
        
        progress_tracker.init_multi_stage(pipeline_id, stages)
        
        # 각 단계별 진행
        progress_tracker.update_stage_progress(pipeline_id, "collection", 100)
        progress_tracker.update_stage_progress(pipeline_id, "processing", 50)
        progress_tracker.update_stage_progress(pipeline_id, "registration", 0)
        
        overall = progress_tracker.get_overall_progress(pipeline_id)
        
        # 전체 진행률 = 0.3 * 100 + 0.5 * 50 + 0.2 * 0 = 55%
        assert overall["percentage"] == 55.0
        assert overall["current_stage"] == "processing"
    
    def test_progress_history(self, progress_tracker):
        """진행상황 이력 추적 테스트"""
        task_id = "TASK_HISTORY"
        
        progress_tracker.start_task(task_id, total_items=100)
        
        # 여러 번 업데이트
        updates = [10, 20, 30, 20, 20]
        for update in updates:
            progress_tracker.update_progress(task_id, processed=update)
            import time
            time.sleep(0.1)
        
        history = progress_tracker.get_progress_history(task_id)
        
        assert len(history) == 5
        assert history[-1]["total_processed"] == 100
        
        # 처리 속도 계산
        speed = progress_tracker.calculate_processing_speed(task_id)
        assert speed > 0  # items per second


class TestErrorRecovery:
    """에러 복구 시스템 테스트"""
    
    @pytest.fixture
    def error_recovery(self):
        from app.services.pipeline.error_recovery import ErrorRecoveryManager
        return ErrorRecoveryManager()
    
    def test_error_detection_and_recovery(self, error_recovery):
        """에러 감지 및 복구 테스트"""
        pipeline_id = "PL_ERROR"
        
        error = {
            "type": "APIError",
            "message": "Rate limit exceeded",
            "step": "collection",
            "timestamp": datetime.now()
        }
        
        # 에러 등록
        recovery_strategy = error_recovery.handle_error(pipeline_id, error)
        
        assert recovery_strategy["action"] == "retry"
        assert recovery_strategy["delay"] > 0
        assert recovery_strategy["max_attempts"] == 3
    
    def test_circuit_breaker(self, error_recovery):
        """서킷 브레이커 테스트"""
        service_name = "zentrade_api"
        
        # 연속된 실패 시뮬레이션
        for i in range(5):
            error_recovery.record_failure(service_name)
        
        # 서킷 오픈 확인
        is_open = error_recovery.is_circuit_open(service_name)
        assert is_open == True
        
        # 서킷이 열려있을 때 요청 차단
        can_proceed = error_recovery.check_circuit(service_name)
        assert can_proceed == False
        
        # 일정 시간 후 half-open 상태로 전환
        import time
        time.sleep(error_recovery.circuit_reset_timeout)
        
        can_proceed = error_recovery.check_circuit(service_name)
        assert can_proceed == True  # 한 번 시도 허용
    
    def test_dead_letter_queue(self, error_recovery):
        """데드레터 큐 테스트"""
        failed_item = {
            "id": "ITEM123",
            "type": "product",
            "error_count": 3,
            "last_error": "Processing failed"
        }
        
        # DLQ에 추가
        error_recovery.send_to_dlq(failed_item)
        
        # DLQ 항목 조회
        dlq_items = error_recovery.get_dlq_items()
        assert len(dlq_items) == 1
        assert dlq_items[0]["id"] == "ITEM123"
        
        # DLQ 항목 재처리
        reprocessed = error_recovery.reprocess_dlq_item("ITEM123")
        assert reprocessed["status"] in ["success", "failed"]


class TestPipelineIntegration:
    """파이프라인 통합 테스트"""
    
    def test_complete_pipeline_flow(self):
        """완전한 파이프라인 플로우 테스트"""
        # 1. 워크플로우 생성
        orchestrator = WorkflowOrchestrator()
        workflow = orchestrator.create_workflow({
            "name": "통합 테스트 파이프라인",
            "steps": [
                {"name": "collect", "type": "collection"},
                {"name": "process", "type": "processing"},
                {"name": "register", "type": "registration"}
            ]
        })
        
        # 2. 상태 관리 초기화
        state_manager = StateManager()
        state_manager.initialize_state(workflow["id"])
        
        # 3. 진행상황 추적 시작
        progress_tracker = ProgressTracker()
        progress_tracker.start_task(workflow["id"], total_items=100)
        
        # 4. 워크플로우 실행 시뮬레이션
        for step in workflow["steps"]:
            # 상태 업데이트
            state_manager.update_state(workflow["id"], {
                "current_step": step["name"],
                "status": "running"
            })
            
            # 진행상황 업데이트
            progress_tracker.update_progress(
                workflow["id"], 
                processed=33
            )
            
            # 스텝 완료
            state_manager.update_state(workflow["id"], {
                "current_step": step["name"],
                "status": "completed"
            })
        
        # 최종 검증
        final_state = state_manager.get_state(workflow["id"])
        final_progress = progress_tracker.get_progress(workflow["id"])
        
        assert final_state["status"] == "completed"
        assert final_progress["percentage"] >= 99.0
        assert final_progress["processed_items"] >= 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])