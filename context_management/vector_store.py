import json
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from django.conf import settings
from upstash_vector import Index
from langchain.embeddings import OpenAIEmbeddings
from langchain_upstash import UpstashVectorStore
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import MemorySnapshot, ConversationContext

logger = logging.getLogger(__name__)


class UpstashVectorMemory:
    """Upstash Vector를 사용한 의미 기반 메모리 저장소"""
    
    def __init__(self):
        # Upstash Vector Index
        self.index = Index(
            url=settings.UPSTASH_VECTOR_REST_URL,
            token=settings.UPSTASH_VECTOR_REST_TOKEN
        )
        
        # OpenAI Embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # LangChain Vector Store
        self.vector_store = UpstashVectorStore(
            index=self.index,
            embeddings=self.embeddings,
            namespace="yooini_memory"
        )
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def store_memory(
        self,
        context_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> str:
        """메모리를 벡터로 저장"""
        try:
            # 메타데이터 준비
            meta = {
                "context_id": context_id,
                "timestamp": datetime.utcnow().isoformat(),
                **metadata
            }
            
            # 벡터 저장
            doc_id = await self.vector_store.aadd_texts(
                texts=[text],
                metadatas=[meta]
            )
            
            logger.info(f"Stored memory vector: {doc_id}")
            return doc_id[0]
            
        except Exception as e:
            logger.error(f"Failed to store memory vector: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search_similar_memories(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """유사한 메모리 검색"""
        try:
            # 벡터 검색
            results = await self.vector_store.asimilarity_search_with_score(
                query,
                k=k,
                filter=filter_metadata
            )
            
            memories = []
            for doc, score in results:
                memories.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": float(score)
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def store_conversation_summary(
        self,
        context_id: str,
        summary: str,
        key_facts: List[str],
        decisions: List[str],
        action_items: List[str]
    ) -> Optional[str]:
        """대화 요약을 벡터로 저장"""
        try:
            # 전체 내용을 하나의 텍스트로 결합
            full_text = f"""
            Summary: {summary}
            
            Key Facts:
            {' '.join(f'- {fact}' for fact in key_facts)}
            
            Decisions:
            {' '.join(f'- {decision}' for decision in decisions)}
            
            Action Items:
            {' '.join(f'- {item}' for item in action_items)}
            """
            
            # 메타데이터
            metadata = {
                "type": "conversation_summary",
                "key_facts_count": len(key_facts),
                "decisions_count": len(decisions),
                "action_items_count": len(action_items)
            }
            
            # 벡터 저장
            vector_id = await self.store_memory(
                context_id=context_id,
                text=full_text.strip(),
                metadata=metadata
            )
            
            # DB 업데이트
            try:
                context = ConversationContext.objects.get(context_id=context_id)
                latest_snapshot = context.memory_snapshots.first()
                if latest_snapshot:
                    latest_snapshot.embedding_id = vector_id
                    latest_snapshot.save()
            except Exception as e:
                logger.error(f"Failed to update DB with vector ID: {e}")
            
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to store conversation summary: {e}")
            return None
    
    async def find_related_contexts(
        self,
        query: str,
        current_context_id: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """관련된 이전 컨텍스트 찾기"""
        # 현재 컨텍스트 제외하고 검색
        filter_metadata = {
            "context_id": {"$ne": current_context_id}
        }
        
        similar_memories = await self.search_similar_memories(
            query=query,
            k=limit * 2,  # 더 많이 검색해서 필터링
            filter_metadata=filter_metadata
        )
        
        # 컨텍스트별로 그룹화
        context_scores = {}
        for memory in similar_memories:
            ctx_id = memory['metadata'].get('context_id')
            if ctx_id:
                if ctx_id not in context_scores:
                    context_scores[ctx_id] = []
                context_scores[ctx_id].append(memory['similarity_score'])
        
        # 평균 점수로 정렬
        sorted_contexts = sorted(
            context_scores.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True
        )[:limit]
        
        # 컨텍스트 정보 조회
        results = []
        for ctx_id, scores in sorted_contexts:
            try:
                context = ConversationContext.objects.get(context_id=ctx_id)
                results.append({
                    "context_id": ctx_id,
                    "context_type": context.context_type,
                    "average_similarity": sum(scores) / len(scores),
                    "created_at": context.created_at.isoformat(),
                    "metadata": context.metadata
                })
            except ConversationContext.DoesNotExist:
                continue
        
        return results
    
    async def get_workflow_insights(
        self,
        workflow_name: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """특정 워크플로우에 대한 인사이트 검색"""
        filter_metadata = {
            "type": "workflow_execution",
            "workflow_name": workflow_name
        }
        
        insights = await self.search_similar_memories(
            query=query,
            k=10,
            filter_metadata=filter_metadata
        )
        
        # 패턴 분석
        patterns = {}
        for insight in insights:
            metadata = insight['metadata']
            
            # 성공/실패 패턴
            status = metadata.get('execution_status', 'unknown')
            if status not in patterns:
                patterns[status] = []
            patterns[status].append(insight)
        
        return {
            "insights": insights,
            "patterns": patterns,
            "success_rate": len(patterns.get('success', [])) / len(insights) if insights else 0
        }
    
    async def update_memory_importance(
        self,
        vector_id: str,
        importance_delta: float
    ) -> None:
        """메모리 중요도 업데이트"""
        try:
            # 벡터 메타데이터 업데이트
            vector = await self.index.fetch(vector_id)
            if vector:
                current_importance = vector.metadata.get('importance', 0.5)
                new_importance = max(0, min(1, current_importance + importance_delta))
                
                vector.metadata['importance'] = new_importance
                vector.metadata['last_accessed'] = datetime.utcnow().isoformat()
                
                await self.index.update(
                    id=vector_id,
                    metadata=vector.metadata
                )
                
        except Exception as e:
            logger.error(f"Failed to update memory importance: {e}")