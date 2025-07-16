from typing import List, Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime, timedelta
import logging

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.chat_models import ChatOpenAI

from django.conf import settings
from .chat_memory import AgentChatMemory
from .semantic_memory import SemanticMemory
from context_management.context_manager import AIContextManager

logger = logging.getLogger(__name__)


class MemoryRetrieval:
    """통합 메모리 검색 시스템"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.context_manager = AIContextManager()
        self.semantic_memory = SemanticMemory()
        
        # LLM for retrieval compression
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0
        )
    
    async def retrieve_relevant_memories(
        self,
        query: str,
        context_id: str,
        memory_types: List[str] = None,
        time_range: Optional[timedelta] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """관련 메모리 종합 검색"""
        
        if memory_types is None:
            memory_types = ["chat", "semantic", "workflow", "market"]
        
        results = {}
        
        # 병렬로 여러 타입의 메모리 검색
        tasks = []
        
        if "chat" in memory_types:
            tasks.append(self._retrieve_chat_memories(query, context_id, limit))
        
        if "semantic" in memory_types:
            tasks.append(self._retrieve_semantic_memories(query, limit))
        
        if "workflow" in memory_types:
            tasks.append(self._retrieve_workflow_memories(query, limit))
        
        if "market" in memory_types:
            tasks.append(self._retrieve_market_memories(query, limit))
        
        # 모든 검색 실행
        memory_results = await asyncio.gather(*tasks)
        
        # 결과 정리
        for i, memory_type in enumerate(memory_types):
            if i < len(memory_results):
                results[memory_type] = memory_results[i]
        
        # 시간 필터링
        if time_range:
            results = self._filter_by_time(results, time_range)
        
        # 중요도 기반 랭킹
        ranked_results = self._rank_memories(results, query)
        
        return {
            "query": query,
            "context_id": context_id,
            "memories": ranked_results,
            "summary": await self._generate_memory_summary(ranked_results)
        }
    
    async def _retrieve_chat_memories(
        self,
        query: str,
        context_id: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """대화 메모리 검색"""
        chat_memory = AgentChatMemory(self.agent_name, context_id)
        context = await chat_memory.get_relevant_context(
            query=query,
            max_messages=limit
        )
        
        return [
            {
                "type": "chat",
                "content": msg["content"],
                "role": msg["role"],
                "relevance_score": 0.8,  # 기본 점수
                "timestamp": datetime.utcnow().isoformat()
            }
            for msg in context.get("recent_messages", [])
        ]
    
    async def _retrieve_semantic_memories(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """의미 기반 메모리 검색"""
        results = await self.semantic_memory.retrieve_product_insights(
            query=query,
            limit=limit
        )
        
        return [
            {
                "type": "semantic",
                "content": result["content"],
                "metadata": result["metadata"],
                "relevance_score": result["similarity_score"],
                "timestamp": result["metadata"].get("timestamp", datetime.utcnow().isoformat())
            }
            for result in results
        ]
    
    async def _retrieve_workflow_memories(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """워크플로우 메모리 검색"""
        # 현재 에이전트와 관련된 워크플로우 찾기
        workflow_insights = await self.context_manager.get_workflow_insights(
            workflow_name=self._get_related_workflow(),
            limit=limit
        )
        
        memories = []
        for pattern_type, patterns in workflow_insights.get("common_patterns", {}).items():
            for pattern in patterns[:limit // len(workflow_insights.get("common_patterns", {}))):
                memories.append({
                    "type": "workflow",
                    "content": f"Workflow pattern: {pattern_type} - {pattern}",
                    "metadata": {
                        "pattern_type": pattern_type,
                        "workflow": self._get_related_workflow()
                    },
                    "relevance_score": 0.7,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return memories
    
    async def _retrieve_market_memories(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """마켓 관련 메모리 검색"""
        # 쿼리에서 마켓 이름 추출 (간단한 구현)
        markets = ["smartstore", "coupang", "gmarket"]
        mentioned_market = None
        
        for market in markets:
            if market.lower() in query.lower():
                mentioned_market = market
                break
        
        if not mentioned_market:
            return []
        
        strategies = await self.semantic_memory.retrieve_market_strategies(
            market_name=mentioned_market,
            strategy_type="general"
        )
        
        return [
            {
                "type": "market",
                "content": strategy["content"],
                "metadata": strategy["metadata"],
                "relevance_score": strategy["similarity_score"],
                "timestamp": strategy["metadata"].get("timestamp", datetime.utcnow().isoformat())
            }
            for strategy in strategies[:limit]
        ]
    
    def _filter_by_time(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        time_range: timedelta
    ) -> Dict[str, List[Dict[str, Any]]]:
        """시간 기반 필터링"""
        cutoff_time = datetime.utcnow() - time_range
        
        filtered_results = {}
        for memory_type, memories in results.items():
            filtered = []
            for memory in memories:
                try:
                    timestamp = datetime.fromisoformat(
                        memory.get("timestamp", datetime.utcnow().isoformat()).replace('Z', '+00:00')
                    )
                    if timestamp > cutoff_time:
                        filtered.append(memory)
                except:
                    # 타임스탬프 파싱 실패 시 포함
                    filtered.append(memory)
            
            filtered_results[memory_type] = filtered
        
        return filtered_results
    
    def _rank_memories(
        self,
        results: Dict[str, List[Dict[str, Any]]],
        query: str
    ) -> List[Dict[str, Any]]:
        """메모리 중요도 랭킹"""
        all_memories = []
        
        # 모든 메모리를 하나의 리스트로 합침
        for memory_type, memories in results.items():
            for memory in memories:
                memory["memory_type"] = memory_type
                all_memories.append(memory)
        
        # 점수 기반 정렬
        all_memories.sort(
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )
        
        return all_memories
    
    async def _generate_memory_summary(
        self,
        memories: List[Dict[str, Any]]
    ) -> str:
        """메모리 요약 생성"""
        if not memories:
            return "No relevant memories found."
        
        # 메모리 타입별 카운트
        type_counts = {}
        for memory in memories:
            mem_type = memory.get("memory_type", "unknown")
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        summary_parts = [
            f"Found {len(memories)} relevant memories:"
        ]
        
        for mem_type, count in type_counts.items():
            summary_parts.append(f"- {count} {mem_type} memories")
        
        # 상위 3개 메모리의 핵심 내용
        summary_parts.append("\nTop relevant content:")
        for i, memory in enumerate(memories[:3]):
            content = memory.get("content", "")[:100]  # 처음 100자만
            summary_parts.append(f"{i+1}. {content}...")
        
        return "\n".join(summary_parts)
    
    def _get_related_workflow(self) -> str:
        """에이전트와 관련된 워크플로우 이름 반환"""
        agent_workflow_mapping = {
            "market_manager": "market_management",
            "product_processor": "product_sync",
            "pricing_optimizer": "pricing_optimization",
            "order_handler": "order_processing"
        }
        
        return agent_workflow_mapping.get(self.agent_name, "general")
    
    async def update_memory_importance(
        self,
        memory_id: str,
        interaction_type: str
    ) -> None:
        """메모리 중요도 업데이트"""
        # 상호작용 타입에 따른 중요도 변경
        importance_delta = {
            "viewed": 0.05,
            "used": 0.1,
            "helpful": 0.2,
            "not_helpful": -0.1
        }.get(interaction_type, 0)
        
        if importance_delta != 0:
            await self.context_manager.vector_store.update_memory_importance(
                vector_id=memory_id,
                importance_delta=importance_delta
            )