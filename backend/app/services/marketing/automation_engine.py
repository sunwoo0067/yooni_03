"""
마케팅 자동화 엔진
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import json
import asyncio
from enum import Enum

from app.models.marketing import (
    AutomationWorkflow, WorkflowNode, WorkflowExecution,
    AutomationTrigger, MarketingCampaign, MarketingMessage,
    TriggerType, CampaignStatus, MessageStatus
)
from app.models.crm import Customer, CustomerBehavior, CustomerLifecycleEvent
from app.core.exceptions import BusinessException
from app.services.marketing.email_service import EmailService
from app.services.marketing.sms_service import SMSService
from app.services.ai.ai_manager import AIManager


class NodeType(Enum):
    """워크플로우 노드 타입"""
    TRIGGER = "trigger"
    ACTION = "action"
    CONDITION = "condition"
    WAIT = "wait"
    SPLIT = "split"
    MERGE = "merge"
    END = "end"


class ActionType(Enum):
    """액션 타입"""
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    ADD_TAG = "add_tag"
    UPDATE_SEGMENT = "update_segment"
    CREATE_TASK = "create_task"
    WEBHOOK = "webhook"
    AI_PERSONALIZE = "ai_personalize"


class AutomationEngine:
    """마케팅 자동화 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService(db)
        self.sms_service = SMSService(db)
        self.ai_manager = AIManager()
        self.active_executions = {}
    
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> AutomationWorkflow:
        """워크플로우 생성"""
        try:
            workflow = AutomationWorkflow(
                name=workflow_data['name'],
                description=workflow_data.get('description'),
                workflow_type=workflow_data.get('workflow_type', 'custom'),
                workflow_definition=workflow_data['workflow_definition'],
                entry_conditions=workflow_data.get('entry_conditions', {}),
                exit_conditions=workflow_data.get('exit_conditions', {}),
                max_entries_per_customer=workflow_data.get('max_entries_per_customer', 1),
                cooldown_period_days=workflow_data.get('cooldown_period_days', 0),
                is_active=workflow_data.get('is_active', True)
            )
            
            self.db.add(workflow)
            self.db.flush()
            
            # 노드 생성
            nodes_data = workflow_data.get('nodes', [])
            for node_data in nodes_data:
                node = WorkflowNode(
                    workflow_id=workflow.id,
                    node_type=node_data['node_type'],
                    node_name=node_data['node_name'],
                    position=node_data.get('position', {}),
                    config=node_data.get('config', {}),
                    conditions=node_data.get('conditions', {}),
                    next_nodes=node_data.get('next_nodes', []),
                    previous_nodes=node_data.get('previous_nodes', [])
                )
                self.db.add(node)
            
            self.db.commit()
            self.db.refresh(workflow)
            
            return workflow
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"워크플로우 생성 실패: {str(e)}")
    
    async def update_workflow(self, workflow_id: int, update_data: Dict[str, Any]) -> AutomationWorkflow:
        """워크플로우 수정"""
        try:
            workflow = self.db.query(AutomationWorkflow).filter(
                AutomationWorkflow.id == workflow_id
            ).first()
            
            if not workflow:
                raise BusinessException("워크플로우를 찾을 수 없습니다")
            
            # 활성 실행이 있는지 확인
            if workflow.active_entries > 0:
                raise BusinessException("실행 중인 인스턴스가 있어 수정할 수 없습니다")
            
            # 워크플로우 업데이트
            updateable_fields = [
                'name', 'description', 'workflow_definition',
                'entry_conditions', 'exit_conditions',
                'max_entries_per_customer', 'cooldown_period_days'
            ]
            
            for field in updateable_fields:
                if field in update_data:
                    setattr(workflow, field, update_data[field])
            
            workflow.updated_at = datetime.utcnow()
            
            # 노드 업데이트
            if 'nodes' in update_data:
                # 기존 노드 삭제
                self.db.query(WorkflowNode).filter(
                    WorkflowNode.workflow_id == workflow_id
                ).delete()
                
                # 새 노드 생성
                for node_data in update_data['nodes']:
                    node = WorkflowNode(
                        workflow_id=workflow.id,
                        node_type=node_data['node_type'],
                        node_name=node_data['node_name'],
                        position=node_data.get('position', {}),
                        config=node_data.get('config', {}),
                        conditions=node_data.get('conditions', {}),
                        next_nodes=node_data.get('next_nodes', []),
                        previous_nodes=node_data.get('previous_nodes', [])
                    )
                    self.db.add(node)
            
            self.db.commit()
            self.db.refresh(workflow)
            
            return workflow
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"워크플로우 수정 실패: {str(e)}")
    
    async def trigger_workflow(self, trigger_data: Dict[str, Any]):
        """워크플로우 트리거"""
        try:
            # 트리거 조건에 맞는 워크플로우 찾기
            triggers = self.db.query(AutomationTrigger).filter(
                AutomationTrigger.is_active == True,
                AutomationTrigger.event_name == trigger_data.get('event_name')
            ).all()
            
            for trigger in triggers:
                # 조건 확인
                if self._check_trigger_conditions(trigger, trigger_data):
                    # 지연 실행 처리
                    if trigger.delay_minutes > 0:
                        await self._schedule_delayed_trigger(trigger, trigger_data, trigger.delay_minutes)
                    else:
                        await self._execute_trigger(trigger, trigger_data)
                    
                    # 트리거 카운트 증가
                    trigger.trigger_count += 1
                    trigger.last_triggered = datetime.utcnow()
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            print(f"워크플로우 트리거 실패: {str(e)}")
    
    async def start_workflow_execution(self, workflow_id: int, customer_id: int, 
                                     context: Dict[str, Any] = None) -> WorkflowExecution:
        """워크플로우 실행 시작"""
        try:
            workflow = self.db.query(AutomationWorkflow).filter(
                AutomationWorkflow.id == workflow_id
            ).first()
            
            if not workflow or not workflow.is_active:
                raise BusinessException("활성화된 워크플로우가 아닙니다")
            
            # 고객 실행 제한 확인
            existing_executions = self.db.query(WorkflowExecution).filter(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.customer_id == customer_id
            ).count()
            
            if existing_executions >= workflow.max_entries_per_customer:
                # 쿨다운 기간 확인
                if workflow.cooldown_period_days > 0:
                    latest_execution = self.db.query(WorkflowExecution).filter(
                        WorkflowExecution.workflow_id == workflow_id,
                        WorkflowExecution.customer_id == customer_id
                    ).order_by(WorkflowExecution.completed_at.desc()).first()
                    
                    if latest_execution and latest_execution.completed_at:
                        cooldown_end = latest_execution.completed_at + timedelta(days=workflow.cooldown_period_days)
                        if datetime.utcnow() < cooldown_end:
                            raise BusinessException("쿨다운 기간 중입니다")
                else:
                    raise BusinessException("최대 실행 횟수를 초과했습니다")
            
            # 실행 생성
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                customer_id=customer_id,
                execution_id=f"{workflow_id}_{customer_id}_{datetime.utcnow().timestamp()}",
                status='active',
                execution_path=[],
                node_results={}
            )
            
            self.db.add(execution)
            self.db.flush()
            
            # 워크플로우 통계 업데이트
            workflow.total_entries += 1
            workflow.active_entries += 1
            
            self.db.commit()
            self.db.refresh(execution)
            
            # 비동기 실행 시작
            asyncio.create_task(self._run_workflow_execution(execution.id, context))
            
            return execution
            
        except Exception as e:
            self.db.rollback()
            raise BusinessException(f"워크플로우 실행 시작 실패: {str(e)}")
    
    async def _run_workflow_execution(self, execution_id: int, context: Dict[str, Any] = None):
        """워크플로우 실행"""
        try:
            execution = self.db.query(WorkflowExecution).filter(
                WorkflowExecution.id == execution_id
            ).first()
            
            if not execution:
                return
            
            workflow = execution.workflow
            
            # 시작 노드 찾기
            start_node = self.db.query(WorkflowNode).filter(
                WorkflowNode.workflow_id == workflow.id,
                WorkflowNode.node_type == NodeType.TRIGGER.value
            ).first()
            
            if not start_node:
                raise BusinessException("시작 노드를 찾을 수 없습니다")
            
            # 실행 컨텍스트 초기화
            exec_context = {
                'customer_id': execution.customer_id,
                'workflow_id': workflow.id,
                'execution_id': execution.id,
                'variables': context or {},
                'results': {}
            }
            
            # 노드 실행
            await self._execute_node(start_node, execution, exec_context)
            
            # 실행 완료
            execution.status = 'completed'
            execution.completed_at = datetime.utcnow()
            
            # 워크플로우 통계 업데이트
            workflow.active_entries -= 1
            workflow.completed_entries += 1
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            
            # 실행 실패 처리
            execution = self.db.query(WorkflowExecution).filter(
                WorkflowExecution.id == execution_id
            ).first()
            
            if execution:
                execution.status = 'failed'
                execution.error_message = str(e)
                execution.completed_at = datetime.utcnow()
                
                workflow = execution.workflow
                if workflow:
                    workflow.active_entries -= 1
                
                self.db.commit()
    
    async def _execute_node(self, node: WorkflowNode, execution: WorkflowExecution, 
                          context: Dict[str, Any]):
        """노드 실행"""
        try:
            # 실행 경로 기록
            execution_path = execution.execution_path or []
            execution_path.append(node.id)
            execution.execution_path = execution_path
            
            # 현재 노드 업데이트
            execution.current_node_id = node.id
            self.db.commit()
            
            # 노드 타입별 처리
            result = None
            if node.node_type == NodeType.ACTION.value:
                result = await self._execute_action_node(node, context)
            elif node.node_type == NodeType.CONDITION.value:
                result = await self._evaluate_condition_node(node, context)
            elif node.node_type == NodeType.WAIT.value:
                await self._execute_wait_node(node, context)
            elif node.node_type == NodeType.SPLIT.value:
                await self._execute_split_node(node, execution, context)
                return  # Split 노드는 여러 경로로 분기
            
            # 결과 저장
            node_results = execution.node_results or {}
            node_results[str(node.id)] = {
                'executed_at': datetime.utcnow().isoformat(),
                'result': result
            }
            execution.node_results = node_results
            self.db.commit()
            
            # 다음 노드로 이동
            if node.next_nodes:
                if node.node_type == NodeType.CONDITION.value:
                    # 조건 노드는 결과에 따라 분기
                    next_node_id = node.next_nodes[0] if result else node.next_nodes[1] if len(node.next_nodes) > 1 else None
                else:
                    next_node_id = node.next_nodes[0]
                
                if next_node_id:
                    next_node = self.db.query(WorkflowNode).filter(
                        WorkflowNode.id == next_node_id
                    ).first()
                    
                    if next_node:
                        await self._execute_node(next_node, execution, context)
            
        except Exception as e:
            raise BusinessException(f"노드 실행 실패: {str(e)}")
    
    async def _execute_action_node(self, node: WorkflowNode, context: Dict[str, Any]) -> Any:
        """액션 노드 실행"""
        config = node.config or {}
        action_type = config.get('action_type')
        
        if action_type == ActionType.SEND_EMAIL.value:
            return await self._send_email_action(config, context)
        elif action_type == ActionType.SEND_SMS.value:
            return await self._send_sms_action(config, context)
        elif action_type == ActionType.ADD_TAG.value:
            return await self._add_tag_action(config, context)
        elif action_type == ActionType.AI_PERSONALIZE.value:
            return await self._ai_personalize_action(config, context)
        elif action_type == ActionType.WEBHOOK.value:
            return await self._webhook_action(config, context)
        
        return None
    
    async def _evaluate_condition_node(self, node: WorkflowNode, context: Dict[str, Any]) -> bool:
        """조건 노드 평가"""
        conditions = node.conditions or {}
        condition_type = conditions.get('type', 'all')  # all, any
        rules = conditions.get('rules', [])
        
        results = []
        for rule in rules:
            field = rule.get('field')
            operator = rule.get('operator')
            value = rule.get('value')
            
            # 컨텍스트에서 값 가져오기
            field_value = self._get_field_value(field, context)
            
            # 조건 평가
            result = self._evaluate_condition(field_value, operator, value)
            results.append(result)
        
        if condition_type == 'all':
            return all(results)
        else:
            return any(results)
    
    async def _execute_wait_node(self, node: WorkflowNode, context: Dict[str, Any]):
        """대기 노드 실행"""
        config = node.config or {}
        wait_type = config.get('wait_type', 'duration')  # duration, until
        
        if wait_type == 'duration':
            duration_minutes = config.get('duration_minutes', 0)
            await asyncio.sleep(duration_minutes * 60)
        elif wait_type == 'until':
            target_time = config.get('target_time')
            # TODO: 특정 시간까지 대기 구현
            pass
    
    async def _execute_split_node(self, node: WorkflowNode, execution: WorkflowExecution, 
                                context: Dict[str, Any]):
        """분기 노드 실행"""
        config = node.config or {}
        split_type = config.get('split_type', 'percentage')  # percentage, condition
        
        if split_type == 'percentage':
            # 백분율 기반 분기
            import random
            percentages = config.get('percentages', [50, 50])
            rand = random.random() * 100
            
            cumulative = 0
            for i, percentage in enumerate(percentages):
                cumulative += percentage
                if rand <= cumulative:
                    if i < len(node.next_nodes):
                        next_node = self.db.query(WorkflowNode).filter(
                            WorkflowNode.id == node.next_nodes[i]
                        ).first()
                        if next_node:
                            await self._execute_node(next_node, execution, context)
                    break
    
    async def _send_email_action(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """이메일 발송 액션"""
        try:
            customer_id = context.get('customer_id')
            template_id = config.get('template_id')
            subject = config.get('subject')
            content = config.get('content')
            
            # 고객 정보 조회
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer or not customer.email:
                return False
            
            # 메시지 생성
            message = MarketingMessage(
                customer_id=customer_id,
                message_type='email',
                channel='email',
                personalized_subject=subject,
                personalized_content=content,
                status=MessageStatus.PENDING
            )
            
            self.db.add(message)
            self.db.commit()
            
            # 이메일 발송
            return await self.email_service.send_single_email(message.id)
            
        except Exception as e:
            print(f"이메일 발송 액션 실패: {str(e)}")
            return False
    
    async def _send_sms_action(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """SMS 발송 액션"""
        try:
            customer_id = context.get('customer_id')
            content = config.get('content')
            
            # 고객 정보 조회
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer or not customer.phone:
                return False
            
            # 메시지 생성
            message = MarketingMessage(
                customer_id=customer_id,
                message_type='sms',
                channel='sms',
                personalized_content=content,
                status=MessageStatus.PENDING
            )
            
            self.db.add(message)
            self.db.commit()
            
            # SMS 발송
            return await self.sms_service.send_single_sms(message.id)
            
        except Exception as e:
            print(f"SMS 발송 액션 실패: {str(e)}")
            return False
    
    async def _add_tag_action(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """태그 추가 액션"""
        try:
            customer_id = context.get('customer_id')
            tag = config.get('tag')
            
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if customer:
                tags = customer.tags or []
                if tag not in tags:
                    tags.append(tag)
                    customer.tags = tags
                    self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"태그 추가 액션 실패: {str(e)}")
            return False
    
    async def _ai_personalize_action(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """AI 개인화 액션"""
        try:
            customer_id = context.get('customer_id')
            prompt_template = config.get('prompt_template')
            
            # AI를 통한 개인화 콘텐츠 생성
            personalized_content = await self.ai_manager.generate_personalized_content(
                customer_id=customer_id,
                template=prompt_template,
                context=context
            )
            
            # 컨텍스트에 결과 저장
            context['variables']['ai_content'] = personalized_content
            
            return {'content': personalized_content}
            
        except Exception as e:
            print(f"AI 개인화 액션 실패: {str(e)}")
            return {}
    
    async def _webhook_action(self, config: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """웹훅 액션"""
        try:
            import httpx
            
            url = config.get('url')
            method = config.get('method', 'POST')
            headers = config.get('headers', {})
            body = config.get('body', {})
            
            # 변수 치환
            for key, value in body.items():
                if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                    var_name = value[2:-2]
                    body[key] = context.get('variables', {}).get(var_name, value)
            
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=body
                )
                
                return response.status_code < 400
                
        except Exception as e:
            print(f"웹훅 액션 실패: {str(e)}")
            return False
    
    def _check_trigger_conditions(self, trigger: AutomationTrigger, 
                                trigger_data: Dict[str, Any]) -> bool:
        """트리거 조건 확인"""
        conditions = trigger.conditions or {}
        
        # 모든 조건 확인
        for field, condition in conditions.items():
            value = trigger_data.get(field)
            
            if isinstance(condition, dict):
                operator = condition.get('operator', 'equals')
                expected = condition.get('value')
                
                if not self._evaluate_condition(value, operator, expected):
                    return False
            else:
                # 단순 동등 비교
                if value != condition:
                    return False
        
        return True
    
    def _evaluate_condition(self, value: Any, operator: str, expected: Any) -> bool:
        """조건 평가"""
        if operator == 'equals':
            return value == expected
        elif operator == 'not_equals':
            return value != expected
        elif operator == 'contains':
            return expected in str(value)
        elif operator == 'not_contains':
            return expected not in str(value)
        elif operator == 'greater_than':
            return float(value) > float(expected)
        elif operator == 'less_than':
            return float(value) < float(expected)
        elif operator == 'in':
            return value in expected
        elif operator == 'not_in':
            return value not in expected
        
        return False
    
    def _get_field_value(self, field: str, context: Dict[str, Any]) -> Any:
        """컨텍스트에서 필드 값 가져오기"""
        # 중첩된 필드 지원 (예: customer.email)
        parts = field.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    async def _schedule_delayed_trigger(self, trigger: AutomationTrigger, 
                                      trigger_data: Dict[str, Any], 
                                      delay_minutes: int):
        """지연된 트리거 스케줄링"""
        # TODO: 지연된 작업 스케줄링 구현
        # 실제 구현에서는 Celery나 다른 작업 큐를 사용
        await asyncio.sleep(delay_minutes * 60)
        await self._execute_trigger(trigger, trigger_data)
    
    async def _execute_trigger(self, trigger: AutomationTrigger, trigger_data: Dict[str, Any]):
        """트리거 실행"""
        if trigger.workflow_id:
            customer_id = trigger_data.get('customer_id')
            if customer_id:
                await self.start_workflow_execution(
                    trigger.workflow_id, 
                    customer_id, 
                    trigger_data
                )