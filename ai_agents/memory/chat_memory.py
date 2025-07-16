from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_community.chat_message_histories import UpstashRedisChatMessageHistory
from langchain.chat_models import ChatOpenAI

from django.conf import settings
from context_management.context_manager import AIContextManager


class AgentChatMemory:
    """AI 에이전트를 위한 대화 메모리 관리"""
    
    def __init__(self, agent_name: str, context_id: str):
        self.agent_name = agent_name
        self.context_id = context_id
        self.context_manager = AIContextManager()
        
        # Upstash Redis 메시지 히스토리
        self.message_history = UpstashRedisChatMessageHistory(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN,
            session_id=f"{agent_name}:{context_id}",
            ttl=86400 * 30  # 30일
        )
        
        # LangChain 메모리 설정
        self.buffer_memory = ConversationBufferMemory(
            chat_memory=self.message_history,
            memory_key="chat_history",
            return_messages=True
        )
        
        # 요약 메모리 (긴 대화용)
        self.summary_memory = ConversationSummaryMemory(
            llm=ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                model="gpt-3.5-turbo"
            ),
            chat_memory=self.message_history,
            memory_key="chat_summary",
            return_messages=True
        )
    
    async def add_interaction(
        self,
        human_input: str,
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """상호작용 추가"""
        # LangChain 메모리에 추가
        self.buffer_memory.chat_memory.add_user_message(human_input)
        self.buffer_memory.chat_memory.add_ai_message(ai_response)
        
        # 컨텍스트 매니저에도 추가
        await self.context_manager.add_message(
            context_id=self.context_id,
            role="human",
            content=human_input,
            store_vector=True
        )
        
        await self.context_manager.add_message(
            context_id=self.context_id,
            role="assistant",
            content=ai_response,
            store_vector=True
        )
        
        # 메타데이터 저장
        if metadata:
            await self._store_metadata(metadata)
    
    async def get_relevant_context(
        self,
        query: str,
        include_summary: bool = True,
        max_messages: int = 10
    ) -> Dict[str, Any]:
        """관련 컨텍스트 조회"""
        # 최근 메시지
        recent_messages = self.buffer_memory.chat_memory.messages[-max_messages:]
        
        # 요약 (긴 대화인 경우)
        summary = None
        if include_summary and len(self.buffer_memory.chat_memory.messages) > 20:
            summary = await self._generate_summary()
        
        # 유사한 과거 대화 검색
        similar_contexts = await self.context_manager.search_knowledge(
            query=query,
            limit=3
        )
        
        # 에이전트별 특화 메모리
        agent_specific = await self._get_agent_specific_memory(query)
        
        return {
            "recent_messages": [
                {
                    "role": "human" if isinstance(msg, HumanMessage) else "ai",
                    "content": msg.content
                }
                for msg in recent_messages
            ],
            "summary": summary,
            "similar_contexts": similar_contexts,
            "agent_specific": agent_specific
        }
    
    async def _generate_summary(self) -> str:
        """대화 요약 생성"""
        messages = self.buffer_memory.chat_memory.messages
        
        if len(messages) < 10:
            return ""
        
        # LangChain의 요약 기능 사용
        summary = await self.summary_memory.predict_new_summary(
            messages=messages[-20:],  # 최근 20개 메시지만
            existing_summary=self.summary_memory.moving_summary
        )
        
        return summary
    
    async def _store_metadata(self, metadata: Dict[str, Any]) -> None:
        """메타데이터 저장"""
        metadata_text = f"Metadata for {self.agent_name}: {metadata}"
        
        await self.context_manager.vector_store.store_memory(
            context_id=self.context_id,
            text=metadata_text,
            metadata={
                "type": "agent_metadata",
                "agent_name": self.agent_name,
                **metadata
            }
        )
    
    async def _get_agent_specific_memory(self, query: str) -> Dict[str, Any]:
        """에이전트별 특화 메모리 조회"""
        # 각 에이전트 타입에 따른 특화 메모리
        if self.agent_name == "market_manager":
            return await self._get_market_memory(query)
        elif self.agent_name == "product_processor":
            return await self._get_product_memory(query)
        elif self.agent_name == "pricing_optimizer":
            return await self._get_pricing_memory(query)
        else:
            return {}
    
    async def _get_market_memory(self, query: str) -> Dict[str, Any]:
        """마켓 관리 에이전트 전용 메모리"""
        # 마켓별 설정, 성공 패턴 등
        market_patterns = await self.context_manager.vector_store.search_similar_memories(
            query=f"market management patterns {query}",
            k=3,
            filter_metadata={"agent_name": "market_manager"}
        )
        
        return {
            "market_patterns": market_patterns,
            "recent_decisions": []  # TODO: 구현
        }
    
    async def _get_product_memory(self, query: str) -> Dict[str, Any]:
        """상품 처리 에이전트 전용 메모리"""
        # 상품 카테고리, 처리 규칙 등
        product_rules = await self.context_manager.vector_store.search_similar_memories(
            query=f"product processing rules {query}",
            k=3,
            filter_metadata={"agent_name": "product_processor"}
        )
        
        return {
            "processing_rules": product_rules,
            "category_mappings": {}  # TODO: 구현
        }
    
    async def _get_pricing_memory(self, query: str) -> Dict[str, Any]:
        """가격 최적화 에이전트 전용 메모리"""
        # 가격 전략, 성공 사례 등
        pricing_strategies = await self.context_manager.vector_store.search_similar_memories(
            query=f"pricing optimization strategies {query}",
            k=3,
            filter_metadata={"agent_name": "pricing_optimizer"}
        )
        
        return {
            "pricing_strategies": pricing_strategies,
            "market_benchmarks": {}  # TODO: 구현
        }
    
    async def clear_old_messages(self, keep_last: int = 100) -> None:
        """오래된 메시지 정리"""
        messages = self.buffer_memory.chat_memory.messages
        
        if len(messages) > keep_last:
            # 요약 생성
            summary = await self._generate_summary()
            
            # 요약 저장
            await self.context_manager.summarize_conversation(
                context_id=self.context_id,
                force=True
            )
            
            # 오래된 메시지 삭제
            messages_to_keep = messages[-keep_last:]
            self.buffer_memory.chat_memory.clear()
            
            for msg in messages_to_keep:
                if isinstance(msg, HumanMessage):
                    self.buffer_memory.chat_memory.add_user_message(msg.content)
                else:
                    self.buffer_memory.chat_memory.add_ai_message(msg.content)