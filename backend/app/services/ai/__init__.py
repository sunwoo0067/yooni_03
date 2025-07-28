"""AI services package for online seller platform."""

# Core AI services that work without additional dependencies
from .ai_manager import AIManager
from .gemini_service import GeminiService
from .ollama_service import OllamaService
from .langchain_service import LangChainService

# Advanced AI services - temporarily disabled due to missing dependencies
try:
    from .recommendation_engine import RecommendationEngine
    from .price_optimizer import PriceOptimizer
    ADVANCED_AI_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Advanced AI services disabled: {e}")
    ADVANCED_AI_AVAILABLE = False
    # Dummy classes for compatibility
    class RecommendationEngine: pass
    class PriceOptimizer: pass

# AI services requiring category model - disabled until model is available
try:
    from .demand_forecasting import DemandForecasting
    DEMAND_FORECASTING_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Demand forecasting disabled (missing Category model): {e}")
    DEMAND_FORECASTING_AVAILABLE = False
    class DemandForecasting: pass

__all__ = [
    "AIManager",
    "GeminiService", 
    "OllamaService",
    "LangChainService",
    "RecommendationEngine",
    "PriceOptimizer",
    "DemandForecasting",
    "ADVANCED_AI_AVAILABLE",
    "DEMAND_FORECASTING_AVAILABLE"
]