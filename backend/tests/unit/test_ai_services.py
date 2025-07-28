"""
Unit tests for AI services
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from decimal import Decimal
from datetime import datetime
import json

from tests.mocks.ai_service_mocks import (
    MockGeminiService, MockOllamaService, MockLangChainService, MockAIServiceManager
)


class TestGeminiService:
    """Test Google Gemini AI service"""
    
    @pytest.fixture
    def gemini_service(self):
        return MockGeminiService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_product_description(self, gemini_service):
        """Test product description generation"""
        prompt = "이 상품에 대한 상품 설명을 생성해주세요"
        
        result = await gemini_service.generate_content(prompt)
        
        assert "text" in result
        assert len(result["text"]) > 50  # Should be substantial description
        assert "프리미엄" in result["text"] or "품질" in result["text"]
        assert result["confidence"] > 0.8
        assert result["model_version"] == "gemini-pro-001"
        assert "tokens_used" in result
        assert "generation_time" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_keywords(self, gemini_service):
        """Test keyword generation"""
        prompt = "이 상품의 검색 키워드를 생성해주세요"
        
        result = await gemini_service.generate_content(prompt)
        
        assert "text" in result
        keywords = result["text"].split(", ")
        assert len(keywords) >= 5  # Should generate multiple keywords
        assert any("품질" in keyword or "프리미엄" in keyword for keyword in keywords)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_price_analysis(self, gemini_service):
        """Test price analysis"""
        prompt = "이 상품의 가격 분석을 해주세요"
        
        result = await gemini_service.generate_content(prompt)
        
        assert "text" in result
        assert "가격" in result["text"]
        assert "마진" in result["text"] or "경쟁" in result["text"]
        assert result["confidence"] > 0.8
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_market_data(self, gemini_service):
        """Test market data analysis"""
        product_data = {
            "category": "보석",
            "price": 125000,
            "name": "18K 골드 목걸이"
        }
        
        analysis = await gemini_service.analyze_market_data(product_data)
        
        # Check trend analysis
        assert "trend_analysis" in analysis
        trend = analysis["trend_analysis"]
        assert "trend" in trend
        assert trend["trend"] in ["상승", "안정", "하락"]
        assert "score" in trend
        assert 0 <= trend["score"] <= 100
        assert "demand_level" in trend
        assert trend["demand_level"] in ["높음", "보통", "낮음"]
        
        # Check competition analysis
        assert "competition_analysis" in analysis
        competition = analysis["competition_analysis"]
        assert "competitor_count" in competition
        assert "average_price" in competition
        assert "price_advantage" in competition
        
        # Check recommendations
        assert "recommendations" in analysis
        assert len(analysis["recommendations"]) >= 3
        
        # Check optimal price range
        assert "optimal_price_range" in analysis
        price_range = analysis["optimal_price_range"]
        assert "min" in price_range
        assert "max" in price_range
        assert "recommended" in price_range
        assert price_range["min"] < price_range["max"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_optimize_pricing(self, gemini_service):
        """Test price optimization"""
        product_data = {
            "price": 25000,
            "cost": 12500,
            "name": "테스트 상품"
        }
        market_data = {
            "competition_analysis": {
                "average_price": 27000
            }
        }
        
        optimization = await gemini_service.optimize_pricing(product_data, market_data)
        
        assert "current_price" in optimization
        assert "suggested_price" in optimization
        assert "price_change" in optimization
        assert "price_change_percent" in optimization
        assert "margin_rate" in optimization
        assert "confidence" in optimization
        assert "reasoning" in optimization
        assert "risk_assessment" in optimization
        
        # Verify data types and ranges
        assert isinstance(optimization["margin_rate"], (int, float))
        assert 0 <= optimization["confidence"] <= 1
        assert len(optimization["reasoning"]) > 0
        
        # Risk assessment should have all required fields
        risk = optimization["risk_assessment"]
        assert "price_sensitivity" in risk
        assert "margin_risk" in risk
        assert "competition_risk" in risk
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_product_tags(self, gemini_service):
        """Test product tag generation"""
        product_data = {
            "category": "주방용품",
            "name": "스테인리스 주방칼"
        }
        
        tags = await gemini_service.generate_product_tags(product_data)
        
        assert isinstance(tags, list)
        assert len(tags) <= 8  # Should not exceed 8 tags
        assert len(tags) > 0   # Should generate at least some tags
        
        # Should include relevant tags for kitchen items
        kitchen_related = any(tag in ["쿠킹", "요리", "주방", "실용적"] for tag in tags)
        assert kitchen_related


class TestOllamaService:
    """Test Ollama local LLM service"""
    
    @pytest.fixture
    def ollama_service(self):
        return MockOllamaService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_content(self, ollama_service):
        """Test content generation with Ollama"""
        prompt = "상품 설명을 생성해주세요"
        
        result = await ollama_service.generate(prompt)
        
        assert "model" in result
        assert "response" in result
        assert "done" in result
        assert result["done"] is True
        assert "total_duration" in result
        assert "eval_count" in result
        assert prompt[:100] in result["response"]  # Should include part of prompt
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, ollama_service):
        """Test generation with custom model"""
        prompt = "테스트 프롬프트"
        model = "codellama"
        
        result = await ollama_service.generate(prompt, model=model)
        
        assert result["model"] == model
        assert "response" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_models(self, ollama_service):
        """Test model listing"""
        models = await ollama_service.list_models()
        
        assert "models" in models
        assert len(models["models"]) >= 2  # Should have llama2 and codellama
        
        for model in models["models"]:
            assert "name" in model
            assert "modified_at" in model
            assert "size" in model
            assert "digest" in model
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_embeddings(self, ollama_service):
        """Test embedding generation"""
        prompt = "테스트 텍스트"
        
        result = await ollama_service.embeddings(prompt)
        
        assert "embedding" in result
        assert "model" in result
        assert "prompt" in result
        assert len(result["embedding"]) == 4096  # Standard embedding size
        assert all(isinstance(x, (int, float)) for x in result["embedding"])
        assert all(-1 <= x <= 1 for x in result["embedding"])  # Normalized embeddings


class TestLangChainService:
    """Test LangChain service"""
    
    @pytest.fixture
    def langchain_service(self):
        return MockLangChainService()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_chain(self, langchain_service):
        """Test chain creation"""
        chain_type = "product_analysis"
        config = {"model": "llama2", "temperature": 0.7}
        
        chain_id = await langchain_service.create_chain(chain_type, **config)
        
        assert chain_id.startswith("chain_product_analysis_")
        assert chain_id in langchain_service.chains
        
        chain_info = langchain_service.chains[chain_id]
        assert chain_info["type"] == chain_type
        assert chain_info["config"] == config
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_product_analysis_chain(self, langchain_service):
        """Test product analysis chain execution"""
        chain_id = await langchain_service.create_chain("product_analysis")
        input_data = {"product": "테스트 상품"}
        
        result = await langchain_service.run_chain(chain_id, input_data)
        
        assert result["chain_id"] == chain_id
        assert "result" in result
        assert "steps" in result
        assert "execution_time" in result
        assert "tokens_used" in result
        
        # Verify product analysis specific results
        analysis_result = result["result"]
        assert "analysis" in analysis_result
        assert "score" in analysis_result
        assert "recommendations" in analysis_result
        assert isinstance(analysis_result["score"], int)
        assert 0 <= analysis_result["score"] <= 100
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_market_research_chain(self, langchain_service):
        """Test market research chain execution"""
        chain_id = await langchain_service.create_chain("market_research")
        input_data = {"category": "보석"}
        
        result = await langchain_service.run_chain(chain_id, input_data)
        
        # Verify market research specific results
        research_result = result["result"]
        assert "market_size" in research_result
        assert "growth_rate" in research_result
        assert "key_trends" in research_result
        assert "opportunities" in research_result
        assert "confidence" in result
        assert "data_sources" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_chain_not_found(self, langchain_service):
        """Test running non-existing chain"""
        with pytest.raises(ValueError, match="Chain not_found not found"):
            await langchain_service.run_chain("not_found", {})
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_chain_history(self, langchain_service):
        """Test chain execution history"""
        chain_id = await langchain_service.create_chain("product_analysis")
        
        history = await langchain_service.get_chain_history(chain_id)
        
        assert isinstance(history, list)
        assert len(history) == 5  # Mock returns 5 history items
        
        for execution in history:
            assert "execution_id" in execution
            assert "timestamp" in execution
            assert "input_data" in execution
            assert "result" in execution
            assert "execution_time" in execution
            assert "status" in execution


class TestAIServiceManager:
    """Test AI service manager coordination"""
    
    @pytest.fixture
    def ai_manager(self):
        return MockAIServiceManager()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_service_valid(self, ai_manager):
        """Test switching to valid AI service"""
        result = await ai_manager.switch_service("ollama")
        
        assert result["switched_to"] == "ollama"
        assert result["status"] == "active"
        assert ai_manager.active_service == "ollama"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_switch_service_invalid(self, ai_manager):
        """Test switching to invalid AI service"""
        with pytest.raises(ValueError, match="Unknown service: invalid"):
            await ai_manager.switch_service("invalid")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_with_fallback_gemini(self, ai_manager):
        """Test generation with Gemini as primary"""
        ai_manager.active_service = "gemini"
        prompt = "상품 설명 생성"
        
        result = await ai_manager.generate_with_fallback(prompt)
        
        assert "text" in result
        assert result["service_used"] == "gemini"
        assert "confidence" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_with_fallback_ollama(self, ai_manager):
        """Test generation with Ollama as fallback"""
        ai_manager.active_service = "ollama"
        prompt = "상품 설명 생성"
        
        result = await ai_manager.generate_with_fallback(prompt)
        
        assert "response" in result or "text" in result
        assert result["service_used"] == "ollama"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('tests.mocks.ai_service_mocks.MockGeminiService.generate_content')
    @patch('tests.mocks.ai_service_mocks.MockOllamaService.generate')
    async def test_generate_with_fallback_to_default(self, mock_ollama, mock_gemini, ai_manager):
        """Test fallback to default when all services fail"""
        # Make both services fail
        mock_gemini.side_effect = Exception("Gemini failed")
        mock_ollama.side_effect = Exception("Ollama failed")
        
        prompt = "테스트 프롬프트"
        result = await ai_manager.generate_with_fallback(prompt)
        
        assert result["service_used"] == "fallback"
        assert result["confidence"] == 0.5
        assert prompt[:50] in result["text"]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_process(self, ai_manager):
        """Test batch processing of multiple prompts"""
        prompts = [
            "상품 설명 1",
            "상품 설명 2", 
            "상품 설명 3"
        ]
        
        results = await ai_manager.batch_process(prompts)
        
        assert len(results) == 3
        
        for i, result in enumerate(results):
            assert result["batch_index"] == i
            assert "service_used" in result
            assert "text" in result or "response" in result
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_service_status(self, ai_manager):
        """Test service status retrieval"""
        status = await ai_manager.get_service_status()
        
        assert "gemini" in status
        assert "ollama" in status
        assert "langchain" in status
        
        # Check Gemini status
        gemini_status = status["gemini"]
        assert gemini_status["status"] == "available"
        assert gemini_status["model"] == "gemini-pro"
        assert "requests_today" in gemini_status
        
        # Check Ollama status
        ollama_status = status["ollama"]
        assert ollama_status["status"] == "available"
        assert ollama_status["local_model"] is True
        
        # Check LangChain status
        langchain_status = status["langchain"]
        assert langchain_status["status"] == "available"
        assert "active_chains" in langchain_status


class TestAIServiceIntegration:
    """Integration tests for AI services"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_product_enhancement_workflow(self):
        """Test complete product enhancement workflow using AI"""
        manager = MockAIServiceManager()
        
        # Original product data
        product_data = {
            "name": "스테인리스 주방칼",
            "price": 35000,
            "cost": 17500,
            "category": "주방용품",
            "basic_description": "스테인리스 스틸 주방칼"
        }
        
        # Step 1: Analyze market data
        market_analysis = await manager.gemini.analyze_market_data(product_data)
        assert "trend_analysis" in market_analysis
        assert "optimal_price_range" in market_analysis
        
        # Step 2: Optimize pricing
        pricing_optimization = await manager.gemini.optimize_pricing(
            product_data, market_analysis
        )
        assert "suggested_price" in pricing_optimization
        
        # Step 3: Generate enhanced description
        description_prompt = f"다음 상품의 매력적인 설명을 생성해주세요: {product_data['name']}"
        enhanced_description = await manager.generate_with_fallback(description_prompt)
        assert len(enhanced_description["text"]) > len(product_data["basic_description"])
        
        # Step 4: Generate tags
        tags = await manager.gemini.generate_product_tags(product_data)
        assert len(tags) > 0
        
        # Step 5: Create final enhanced product
        enhanced_product = {
            **product_data,
            "enhanced_description": enhanced_description["text"],
            "optimized_price": pricing_optimization["suggested_price"],
            "margin_rate": pricing_optimization["margin_rate"],
            "tags": tags,
            "market_score": market_analysis["trend_analysis"]["score"],
            "ai_confidence": enhanced_description.get("confidence", 0.8)
        }
        
        # Verify enhancement
        assert enhanced_product["optimized_price"] != product_data["price"]
        assert len(enhanced_product["tags"]) > 0
        assert enhanced_product["market_score"] > 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ai_service_fallback_mechanism(self):
        """Test AI service fallback in real scenario"""
        manager = MockAIServiceManager()
        
        prompts = [
            "제품 설명을 생성해주세요",
            "키워드를 추천해주세요",
            "가격을 분석해주세요"
        ]
        
        # Test with different active services
        services = ["gemini", "ollama"]
        
        for service in services:
            await manager.switch_service(service)
            
            for prompt in prompts:
                result = await manager.generate_with_fallback(prompt)
                
                assert "text" in result or "response" in result
                assert "service_used" in result
                # Should use the active service or fallback
                assert result["service_used"] in [service, "fallback"]
    
    # @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_ai_service_performance(self):
        """Test AI service performance under load"""
        manager = MockAIServiceManager()
        
        # Generate multiple prompts
        prompts = [f"상품 {i}에 대한 설명을 생성해주세요" for i in range(20)]
        
        start_time = datetime.now()
        
        # Process in batch
        results = await manager.batch_process(prompts)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Verify results
        assert len(results) == 20
        assert all("service_used" in result for result in results)
        
        # Performance should be reasonable (mock operations)
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        # Check if processing was properly indexed
        for i, result in enumerate(results):
            assert result["batch_index"] == i
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_langchain_product_analysis_workflow(self):
        """Test LangChain workflow for product analysis"""
        langchain_service = MockLangChainService()
        
        # Step 1: Create analysis chain
        analysis_chain_id = await langchain_service.create_chain(
            "product_analysis", 
            model="llama2",
            temperature=0.7
        )
        
        # Step 2: Create market research chain
        research_chain_id = await langchain_service.create_chain(
            "market_research",
            model="llama2",
            temperature=0.5
        )
        
        # Step 3: Run product analysis
        product_input = {
            "product": {
                "name": "프리미엄 주방용품",
                "category": "주방용품",
                "price": 45000
            }
        }
        
        analysis_result = await langchain_service.run_chain(analysis_chain_id, product_input)
        
        # Step 4: Run market research
        market_input = {"category": "주방용품"}
        research_result = await langchain_service.run_chain(research_chain_id, market_input)
        
        # Step 5: Combine results
        combined_analysis = {
            "product_analysis": analysis_result["result"],
            "market_research": research_result["result"],
            "analysis_confidence": analysis_result.get("confidence", 0.8),
            "research_confidence": research_result.get("confidence", 0.8),
            "combined_score": (
                analysis_result["result"]["score"] + 
                research_result.get("confidence", 0.8) * 100
            ) / 2
        }
        
        # Verify combined analysis
        assert "product_analysis" in combined_analysis
        assert "market_research" in combined_analysis
        assert combined_analysis["combined_score"] > 0