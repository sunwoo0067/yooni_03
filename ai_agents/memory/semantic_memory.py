from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
import logging

from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from django.conf import settings
from context_management.vector_store import UpstashVectorMemory
from source_data.models import SourceData

logger = logging.getLogger(__name__)


class SemanticMemory:
    """의미 기반 메모리 시스템"""
    
    def __init__(self):
        self.vector_memory = UpstashVectorMemory()
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def store_product_knowledge(
        self,
        product_data: Dict[str, Any],
        source_data_id: int
    ) -> List[str]:
        """상품 지식 저장"""
        # 상품 정보를 구조화된 텍스트로 변환
        product_text = self._format_product_data(product_data)
        
        # 텍스트 분할
        chunks = self.text_splitter.split_text(product_text)
        
        # 각 청크를 벡터로 저장
        vector_ids = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "type": "product_knowledge",
                "source_data_id": source_data_id,
                "product_id": product_data.get('id'),
                "product_name": product_data.get('name'),
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            
            vector_id = await self.vector_memory.store_memory(
                context_id=f"product_{source_data_id}",
                text=chunk,
                metadata=metadata
            )
            
            vector_ids.append(vector_id)
        
        logger.info(f"Stored {len(vector_ids)} chunks for product {source_data_id}")
        return vector_ids
    
    async def store_market_knowledge(
        self,
        market_name: str,
        market_data: Dict[str, Any]
    ) -> List[str]:
        """마켓 지식 저장"""
        # 마켓 정보 구조화
        market_text = f"""
        Market: {market_name}
        
        Categories: {market_data.get('categories', [])}
        
        Policies:
        - Commission: {market_data.get('commission_rate', 'N/A')}
        - Shipping: {market_data.get('shipping_policy', 'N/A')}
        - Return: {market_data.get('return_policy', 'N/A')}
        
        Best Practices:
        {market_data.get('best_practices', 'N/A')}
        
        Restrictions:
        {market_data.get('restrictions', 'N/A')}
        """
        
        # 벡터 저장
        metadata = {
            "type": "market_knowledge",
            "market_name": market_name,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        vector_id = await self.vector_memory.store_memory(
            context_id=f"market_{market_name}",
            text=market_text.strip(),
            metadata=metadata
        )
        
        return [vector_id]
    
    async def store_execution_pattern(
        self,
        workflow_name: str,
        pattern_data: Dict[str, Any]
    ) -> str:
        """실행 패턴 저장"""
        pattern_text = f"""
        Workflow: {workflow_name}
        Pattern: {pattern_data.get('pattern_name', 'Unknown')}
        
        Context:
        {pattern_data.get('context', {})}
        
        Outcome:
        - Success: {pattern_data.get('success', False)}
        - Duration: {pattern_data.get('duration', 'N/A')}
        - Error: {pattern_data.get('error', 'None')}
        
        Lessons Learned:
        {pattern_data.get('lessons', 'N/A')}
        """
        
        metadata = {
            "type": "execution_pattern",
            "workflow_name": workflow_name,
            "success": pattern_data.get('success', False),
            "pattern_type": pattern_data.get('pattern_name', 'unknown')
        }
        
        vector_id = await self.vector_memory.store_memory(
            context_id=f"workflow_{workflow_name}",
            text=pattern_text.strip(),
            metadata=metadata
        )
        
        return vector_id
    
    async def retrieve_product_insights(
        self,
        query: str,
        product_category: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """상품 인사이트 검색"""
        filter_metadata = {"type": "product_knowledge"}
        if product_category:
            filter_metadata["category"] = product_category
        
        results = await self.vector_memory.search_similar_memories(
            query=query,
            k=limit,
            filter_metadata=filter_metadata
        )
        
        # 결과 보강
        enriched_results = []
        for result in results:
            source_data_id = result['metadata'].get('source_data_id')
            if source_data_id:
                try:
                    source_data = SourceData.objects.get(id=source_data_id)
                    result['source_data'] = {
                        "id": source_data.id,
                        "source_type": source_data.source_type,
                        "created_at": source_data.created_at.isoformat()
                    }
                except SourceData.DoesNotExist:
                    pass
            
            enriched_results.append(result)
        
        return enriched_results
    
    async def retrieve_market_strategies(
        self,
        market_name: str,
        strategy_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """마켓 전략 검색"""
        query = f"{market_name} market strategies"
        if strategy_type:
            query += f" {strategy_type}"
        
        filter_metadata = {
            "type": "market_knowledge",
            "market_name": market_name
        }
        
        return await self.vector_memory.search_similar_memories(
            query=query,
            k=10,
            filter_metadata=filter_metadata
        )
    
    async def find_similar_patterns(
        self,
        current_context: Dict[str, Any],
        workflow_name: str
    ) -> List[Dict[str, Any]]:
        """유사한 실행 패턴 찾기"""
        # 현재 컨텍스트를 텍스트로 변환
        context_text = f"""
        Workflow: {workflow_name}
        Input: {current_context.get('input', {})}
        Current State: {current_context.get('state', {})}
        """
        
        filter_metadata = {
            "type": "execution_pattern",
            "workflow_name": workflow_name
        }
        
        similar_patterns = await self.vector_memory.search_similar_memories(
            query=context_text,
            k=5,
            filter_metadata=filter_metadata
        )
        
        # 성공/실패 패턴 분리
        success_patterns = [p for p in similar_patterns if p['metadata'].get('success')]
        failure_patterns = [p for p in similar_patterns if not p['metadata'].get('success')]
        
        return {
            "all_patterns": similar_patterns,
            "success_patterns": success_patterns,
            "failure_patterns": failure_patterns,
            "recommendation": self._generate_recommendation(success_patterns, failure_patterns)
        }
    
    def _format_product_data(self, product_data: Dict[str, Any]) -> str:
        """상품 데이터를 텍스트로 포맷팅"""
        return f"""
        Product Information:
        
        Name: {product_data.get('name', 'Unknown')}
        ID: {product_data.get('id', 'N/A')}
        Category: {product_data.get('category', 'N/A')}
        
        Description:
        {product_data.get('description', 'No description')}
        
        Specifications:
        {self._format_dict(product_data.get('specifications', {}))}
        
        Pricing:
        - Original Price: {product_data.get('original_price', 'N/A')}
        - Sale Price: {product_data.get('sale_price', 'N/A')}
        - Currency: {product_data.get('currency', 'KRW')}
        
        Inventory:
        - Stock: {product_data.get('stock', 'N/A')}
        - SKU: {product_data.get('sku', 'N/A')}
        
        Supplier Information:
        - Supplier: {product_data.get('supplier', 'N/A')}
        - Supplier SKU: {product_data.get('supplier_sku', 'N/A')}
        """
    
    def _format_dict(self, data: Dict[str, Any], indent: int = 0) -> str:
        """딕셔너리를 읽기 쉬운 텍스트로 변환"""
        lines = []
        indent_str = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{indent_str}- {key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{indent_str}- {key}: {', '.join(map(str, value))}")
            else:
                lines.append(f"{indent_str}- {key}: {value}")
        
        return "\n".join(lines)
    
    def _generate_recommendation(
        self,
        success_patterns: List[Dict[str, Any]],
        failure_patterns: List[Dict[str, Any]]
    ) -> str:
        """패턴 기반 추천 생성"""
        if not success_patterns and not failure_patterns:
            return "No similar patterns found. Proceed with caution."
        
        if len(success_patterns) > len(failure_patterns):
            return f"Found {len(success_patterns)} successful patterns. Recommended to proceed."
        elif failure_patterns:
            return f"Found {len(failure_patterns)} failure patterns. Review and adjust approach."
        else:
            return "Mixed results in similar patterns. Careful monitoring recommended."