import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from django.conf import settings
from upstash_redis import Redis
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import ConversationContext, MemorySnapshot

logger = logging.getLogger(__name__)


class UpstashMemoryStore:
    """Upstash Redis를 사용한 AI 메모리 저장소"""
    
    def __init__(self):
        self.redis = Redis(
            url=settings.UPSTASH_REDIS_REST_URL,
            token=settings.UPSTASH_REDIS_REST_TOKEN
        )
        self.prefix = "yooini:memory:"
    
    def _get_key(self, context_id: str, key_type: str = "messages") -> str:
        """Redis 키 생성"""
        return f"{self.prefix}{key_type}:{context_id}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def add_message(
        self, 
        context_id: str, 
        role: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """대화 메시지 추가"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        key = self._get_key(context_id, "messages")
        
        # Redis List에 추가
        await self.redis.rpush(key, json.dumps(message))
        
        # TTL 설정 (30일)
        await self.redis.expire(key, 86400 * 30)
        
        # DB에도 저장
        try:
            context, created = ConversationContext.objects.get_or_create(
                context_id=context_id,
                defaults={'context_type': 'system'}
            )
            
            messages = context.messages or []
            messages.append(message)
            context.messages = messages
            context.save()
            
        except Exception as e:
            logger.error(f"Failed to save to DB: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_messages(
        self, 
        context_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """대화 메시지 조회"""
        key = self._get_key(context_id, "messages")
        
        # Redis에서 조회
        messages = await self.redis.lrange(key, -limit, -1)
        
        if messages:
            return [json.loads(msg) for msg in messages]
        
        # Redis에 없으면 DB에서 조회
        try:
            context = ConversationContext.objects.get(context_id=context_id)
            messages = context.messages[-limit:] if context.messages else []
            
            # Redis에 캐시
            if messages:
                for msg in messages:
                    await self.redis.rpush(key, json.dumps(msg))
                await self.redis.expire(key, 86400 * 30)
            
            return messages
            
        except ConversationContext.DoesNotExist:
            return []
    
    async def save_summary(
        self,
        context_id: str,
        summary: str,
        key_facts: List[str],
        decisions: List[str],
        action_items: List[str]
    ) -> None:
        """대화 요약 저장"""
        try:
            context = ConversationContext.objects.get(context_id=context_id)
            
            MemorySnapshot.objects.create(
                conversation=context,
                summary=summary,
                key_facts=key_facts,
                decisions=decisions,
                action_items=action_items
            )
            
            # Redis에도 저장 (빠른 접근용)
            summary_key = self._get_key(context_id, "summary")
            summary_data = {
                "summary": summary,
                "key_facts": key_facts,
                "decisions": decisions,
                "action_items": action_items,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.redis.set(
                summary_key, 
                json.dumps(summary_data),
                ex=86400 * 30  # 30일 TTL
            )
            
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")
    
    async def get_recent_contexts(
        self,
        user_id: Optional[int] = None,
        context_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """최근 컨텍스트 조회"""
        queryset = ConversationContext.objects.filter(is_active=True)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if context_type:
            queryset = queryset.filter(context_type=context_type)
        
        contexts = queryset[:limit]
        
        result = []
        for context in contexts:
            # 최근 메시지 몇 개만 포함
            recent_messages = context.messages[-5:] if context.messages else []
            
            result.append({
                "context_id": context.context_id,
                "context_type": context.context_type,
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "recent_messages": recent_messages,
                "metadata": context.metadata
            })
        
        return result
    
    async def search_memories(
        self,
        query: str,
        context_ids: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """메모리 검색 (키워드 기반)"""
        queryset = MemorySnapshot.objects.all()
        
        if context_ids:
            queryset = queryset.filter(
                conversation__context_id__in=context_ids
            )
        
        # 간단한 텍스트 검색 (실제로는 벡터 검색 사용 권장)
        results = []
        for snapshot in queryset:
            if (query.lower() in snapshot.summary.lower() or
                any(query.lower() in fact.lower() for fact in snapshot.key_facts)):
                
                results.append({
                    "context_id": snapshot.conversation.context_id,
                    "summary": snapshot.summary,
                    "key_facts": snapshot.key_facts,
                    "decisions": snapshot.decisions,
                    "action_items": snapshot.action_items,
                    "importance_score": snapshot.importance_score,
                    "created_at": snapshot.created_at.isoformat()
                })
        
        # 중요도 순으로 정렬
        results.sort(key=lambda x: x['importance_score'], reverse=True)
        
        return results[:limit]
    
    async def cleanup_old_contexts(self, days: int = 30) -> int:
        """오래된 컨텍스트 정리"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        old_contexts = ConversationContext.objects.filter(
            updated_at__lt=cutoff_date,
            is_active=True
        )
        
        count = 0
        for context in old_contexts:
            # Redis에서 삭제
            keys_to_delete = [
                self._get_key(context.context_id, "messages"),
                self._get_key(context.context_id, "summary")
            ]
            
            for key in keys_to_delete:
                await self.redis.delete(key)
            
            # DB에서 비활성화
            context.is_active = False
            context.save()
            
            count += 1
        
        logger.info(f"Cleaned up {count} old contexts")
        return count