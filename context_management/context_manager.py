import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .memory_store import UpstashMemoryStore
from .vector_store import UpstashVectorMemory
from .models import ConversationContext, WorkflowContext

logger = logging.getLogger(__name__)


class AIContextManager:
    """통합 AI 컨텍스트 관리자"""
    
    def __init__(self):
        self.memory_store = UpstashMemoryStore()
        self.vector_store = UpstashVectorMemory()
    
    async def start_conversation(
        self,
        context_type: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """새 대화 시작"""
        import uuid
        context_id = str(uuid.uuid4())
        
        # DB에 컨텍스트 생성
        context = ConversationContext.objects.create(
            context_id=context_id,
            context_type=context_type,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        logger.info(f"Started new conversation: {context_id}")
        return context_id
    
    async def add_message(
        self,
        context_id: str,
        role: str,
        content: str,
        store_vector: bool = True
    ) -> None:
        """메시지 추가 및 선택적 벡터 저장"""
        # Redis에 메시지 저장
        await self.memory_store.add_message(
            context_id=context_id,
            role=role,
            content=content
        )
        
        # 중요한 메시지는 벡터로도 저장
        if store_vector and len(content) > 50:
            await self.vector_store.store_memory(
                context_id=context_id,
                text=f"{role}: {content}",
                metadata={
                    "type": "message",
                    "role": role
                }
            )
    
    async def get_conversation_context(
        self,
        context_id: str,
        include_similar: bool = True,
        message_limit: int = 20
    ) -> Dict[str, Any]:
        """대화 컨텍스트 조회"""
        # 최근 메시지
        messages = await self.memory_store.get_messages(
            context_id=context_id,
            limit=message_limit
        )
        
        # 관련 컨텍스트
        related_contexts = []
        if include_similar and messages:
            # 최근 메시지 기반으로 유사 컨텍스트 검색
            recent_content = " ".join([
                msg['content'] for msg in messages[-5:]
                if msg.get('content')
            ])
            
            if recent_content:
                related_contexts = await self.vector_store.find_related_contexts(
                    query=recent_content,
                    current_context_id=context_id,
                    limit=3
                )
        
        # 요약 정보
        try:
            context = ConversationContext.objects.get(context_id=context_id)
            latest_summary = context.memory_snapshots.first()
            
            summary_info = None
            if latest_summary:
                summary_info = {
                    "summary": latest_summary.summary,
                    "key_facts": latest_summary.key_facts,
                    "decisions": latest_summary.decisions,
                    "action_items": latest_summary.action_items
                }
        except ConversationContext.DoesNotExist:
            summary_info = None
        
        return {
            "context_id": context_id,
            "messages": messages,
            "summary": summary_info,
            "related_contexts": related_contexts
        }
    
    async def summarize_conversation(
        self,
        context_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """대화 요약 생성"""
        messages = await self.memory_store.get_messages(context_id)
        
        if not messages:
            return {"error": "No messages to summarize"}
        
        # 요약이 필요한지 확인
        if not force and len(messages) < 10:
            return {"info": "Not enough messages to summarize"}
        
        # AI를 사용해 요약 생성 (여기서는 간단한 예시)
        # 실제로는 OpenAI/Anthropic API 사용
        summary = f"대화 요약: {len(messages)}개의 메시지 분석"
        key_facts = [f"총 {len(messages)}개의 메시지 교환"]
        decisions = []
        action_items = []
        
        # 요약 저장
        await self.memory_store.save_summary(
            context_id=context_id,
            summary=summary,
            key_facts=key_facts,
            decisions=decisions,
            action_items=action_items
        )
        
        # 벡터로도 저장
        await self.vector_store.store_conversation_summary(
            context_id=context_id,
            summary=summary,
            key_facts=key_facts,
            decisions=decisions,
            action_items=action_items
        )
        
        return {
            "summary": summary,
            "key_facts": key_facts,
            "decisions": decisions,
            "action_items": action_items
        }
    
    async def search_knowledge(
        self,
        query: str,
        context_ids: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """지식 베이스 검색"""
        # 벡터 검색
        vector_results = await self.vector_store.search_similar_memories(
            query=query,
            k=limit * 2
        )
        
        # 컨텍스트 필터링
        if context_ids:
            vector_results = [
                r for r in vector_results
                if r['metadata'].get('context_id') in context_ids
            ]
        
        # 키워드 검색 결과도 병합
        keyword_results = await self.memory_store.search_memories(
            query=query,
            context_ids=context_ids,
            limit=limit
        )
        
        # 결과 병합 및 중복 제거
        combined_results = []
        seen_contents = set()
        
        for result in vector_results[:limit]:
            content_hash = hash(result['content'])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                combined_results.append({
                    **result,
                    "source": "vector"
                })
        
        for result in keyword_results:
            content_hash = hash(result.get('summary', ''))
            if content_hash not in seen_contents and len(combined_results) < limit:
                seen_contents.add(content_hash)
                combined_results.append({
                    **result,
                    "source": "keyword"
                })
        
        return combined_results[:limit]
    
    async def save_workflow_context(
        self,
        workflow_id: str,
        workflow_name: str,
        execution_data: Dict[str, Any],
        conversation_context_id: Optional[str] = None
    ) -> None:
        """워크플로우 실행 컨텍스트 저장"""
        # DB에 저장
        workflow_ctx = WorkflowContext.objects.create(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            input_context=execution_data.get('input', {}),
            execution_context=execution_data.get('execution', {}),
            output_context=execution_data.get('output', {}),
            performance_metrics=execution_data.get('metrics', {}),
            conversation_id=conversation_context_id
        )
        
        # 벡터로도 저장 (검색 가능하게)
        execution_summary = f"""
        Workflow: {workflow_name}
        Input: {execution_data.get('input', {})}
        Output: {execution_data.get('output', {})}
        Status: {execution_data.get('status', 'unknown')}
        """
        
        await self.vector_store.store_memory(
            context_id=workflow_id,
            text=execution_summary,
            metadata={
                "type": "workflow_execution",
                "workflow_name": workflow_name,
                "execution_status": execution_data.get('status', 'unknown')
            }
        )
    
    async def get_workflow_insights(
        self,
        workflow_name: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """워크플로우 실행 인사이트 조회"""
        # 최근 실행 조회
        recent_executions = WorkflowContext.objects.filter(
            workflow_name=workflow_name
        ).order_by('-created_at')[:limit]
        
        # 성능 분석
        success_count = 0
        total_duration = 0
        patterns = {}
        
        for execution in recent_executions:
            metrics = execution.performance_metrics
            if metrics.get('status') == 'success':
                success_count += 1
            
            duration = metrics.get('duration', 0)
            total_duration += duration
            
            # 패턴 추출
            for key, value in execution.learned_patterns.items():
                if key not in patterns:
                    patterns[key] = []
                patterns[key].append(value)
        
        # 벡터 검색으로 유사 패턴 찾기
        vector_insights = await self.vector_store.get_workflow_insights(
            workflow_name=workflow_name,
            query=f"workflow execution patterns for {workflow_name}"
        )
        
        return {
            "total_executions": len(recent_executions),
            "success_rate": success_count / len(recent_executions) if recent_executions else 0,
            "average_duration": total_duration / len(recent_executions) if recent_executions else 0,
            "common_patterns": patterns,
            "vector_insights": vector_insights
        }