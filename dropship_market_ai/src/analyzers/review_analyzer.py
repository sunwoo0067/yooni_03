"""NLP-based review sentiment analysis system"""
import re
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    pipeline
)
from kiwipiepy import Kiwi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import structlog

from ..database.models import Review, ReviewAnalytics, Product
from ..utils.cache import RedisCache, CacheKey

logger = structlog.get_logger()


class ReviewAnalyzer:
    """Korean review sentiment analysis and insight extraction"""
    
    def __init__(self, config: Dict[str, Any], session: AsyncSession):
        self.config = config
        self.session = session
        self.cache = RedisCache(config['redis'])
        
        # Initialize Korean NLP tools
        self.kiwi = Kiwi()
        
        # Initialize transformer models
        self.device = 0 if torch.cuda.is_available() else -1
        
        # Sentiment analysis model (Korean BERT)
        self.sentiment_model_name = "beomi/kcbert-base"
        self.sentiment_analyzer = None
        
        # Initialize models lazily
        self._models_loaded = False
    
    def _load_models(self):
        """Load NLP models"""
        if self._models_loaded:
            return
        
        logger.info("Loading NLP models...")
        
        # Load sentiment analysis pipeline
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model=self.sentiment_model_name,
            device=self.device
        )
        
        self._models_loaded = True
        logger.info("NLP models loaded successfully")
    
    async def analyze_review(
        self,
        review: Review
    ) -> Dict[str, Any]:
        """Analyze a single review"""
        
        # Check if already analyzed
        stmt = select(ReviewAnalytics).where(
            ReviewAnalytics.review_id == review.id
        )
        result = await self.session.execute(stmt)
        existing_analytics = result.scalar_one_or_none()
        
        if existing_analytics:
            return {
                'review_id': review.id,
                'sentiment_score': existing_analytics.sentiment_score,
                'sentiment_label': existing_analytics.sentiment_label,
                'key_phrases': existing_analytics.key_phrases,
                'product_aspects': existing_analytics.product_aspects
            }
        
        # Load models if needed
        if not self._models_loaded:
            self._load_models()
        
        # Combine title and content
        full_text = f"{review.title or ''} {review.content or ''}"
        
        # Perform analysis
        analysis_result = {
            'sentiment': await self._analyze_sentiment(full_text),
            'key_phrases': await self._extract_key_phrases(full_text),
            'product_aspects': await self._analyze_product_aspects(full_text),
            'mentioned_features': await self._extract_mentioned_features(full_text),
            'improvement_suggestions': await self._extract_improvements(full_text),
            'customer_type': await self._classify_customer_type(review),
            'review_category': await self._classify_review_category(full_text)
        }
        
        # Save analytics
        analytics = ReviewAnalytics(
            review_id=review.id,
            sentiment_score=analysis_result['sentiment']['score'],
            sentiment_label=analysis_result['sentiment']['label'],
            key_phrases=analysis_result['key_phrases'],
            product_aspects=analysis_result['product_aspects'],
            mentioned_features=analysis_result['mentioned_features'],
            improvement_suggestions=analysis_result['improvement_suggestions'],
            customer_type=analysis_result['customer_type'],
            review_category=analysis_result['review_category'],
            analyzed_at=datetime.utcnow()
        )
        
        self.session.add(analytics)
        await self.session.commit()
        
        return analysis_result
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of the text"""
        if not text or len(text.strip()) < 5:
            return {'score': 0.0, 'label': 'neutral'}
        
        # Use transformer model for sentiment
        try:
            # Truncate text if too long
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.sentiment_analyzer(text)[0]
            
            # Map to our sentiment scale
            label_map = {
                'POSITIVE': 'positive',
                'NEGATIVE': 'negative',
                'NEUTRAL': 'neutral'
            }
            
            sentiment_label = label_map.get(result['label'], 'neutral')
            
            # Convert score to -1 to 1 scale
            if sentiment_label == 'positive':
                sentiment_score = result['score']
            elif sentiment_label == 'negative':
                sentiment_score = -result['score']
            else:
                sentiment_score = 0.0
            
            return {
                'score': sentiment_score,
                'label': sentiment_label,
                'confidence': result['score']
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            
            # Fallback to rule-based sentiment
            return self._rule_based_sentiment(text)
    
    def _rule_based_sentiment(self, text: str) -> Dict[str, Any]:
        """Simple rule-based sentiment analysis as fallback"""
        positive_words = ['좋아요', '최고', '만족', '추천', '훌륭', '예쁘', '빠른', '친절', '편리', '저렴']
        negative_words = ['나쁨', '불만', '실망', '최악', '불편', '비싸', '느린', '불친절', '고장', '환불']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            score = min(positive_count * 0.2, 1.0)
            label = 'positive'
        elif negative_count > positive_count:
            score = max(-negative_count * 0.2, -1.0)
            label = 'negative'
        else:
            score = 0.0
            label = 'neutral'
        
        return {
            'score': score,
            'label': label,
            'confidence': 0.5
        }
    
    async def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text"""
        if not text:
            return []
        
        # Use Kiwi for Korean text processing
        try:
            tokens = self.kiwi.tokenize(text)
            
            # Extract noun phrases
            noun_phrases = []
            current_phrase = []
            
            for token in tokens:
                if token.tag.startswith('N'):  # Noun
                    current_phrase.append(token.form)
                else:
                    if current_phrase:
                        phrase = ' '.join(current_phrase)
                        if len(phrase) > 1:  # Filter out single characters
                            noun_phrases.append(phrase)
                        current_phrase = []
            
            # Add last phrase
            if current_phrase:
                phrase = ' '.join(current_phrase)
                if len(phrase) > 1:
                    noun_phrases.append(phrase)
            
            # Count frequencies
            phrase_counts = Counter(noun_phrases)
            
            # Return top phrases
            top_phrases = [phrase for phrase, count in phrase_counts.most_common(10)]
            
            return top_phrases
            
        except Exception as e:
            logger.error(f"Key phrase extraction failed: {str(e)}")
            return []
    
    async def _analyze_product_aspects(self, text: str) -> Dict[str, float]:
        """Analyze sentiment for different product aspects"""
        
        aspects = {
            'quality': ['품질', '질', '재질', '소재', '만듦새'],
            'shipping': ['배송', '배달', '도착', '포장'],
            'price': ['가격', '가성비', '비싸', '저렴', '할인'],
            'service': ['서비스', '응대', '친절', '상담', '문의'],
            'design': ['디자인', '모양', '색상', '예쁘', '이쁘'],
            'size': ['사이즈', '크기', '넓이', '길이', '핏'],
            'usability': ['사용', '편리', '편의', '쉬운', '어려운']
        }
        
        aspect_sentiments = {}
        
        for aspect, keywords in aspects.items():
            # Find sentences containing aspect keywords
            aspect_sentences = []
            sentences = text.split('.')
            
            for sentence in sentences:
                if any(keyword in sentence for keyword in keywords):
                    aspect_sentences.append(sentence)
            
            if aspect_sentences:
                # Analyze sentiment for aspect sentences
                aspect_text = ' '.join(aspect_sentences)
                sentiment = await self._analyze_sentiment(aspect_text)
                aspect_sentiments[aspect] = sentiment['score']
            else:
                aspect_sentiments[aspect] = 0.0
        
        return aspect_sentiments
    
    async def _extract_mentioned_features(self, text: str) -> List[str]:
        """Extract product features mentioned in review"""
        
        feature_patterns = [
            r'색상[은이]?\s*(\S+)',
            r'사이즈[는가]?\s*(\S+)',
            r'(\S+)\s*기능',
            r'(\S+)\s*성능',
            r'소재[는가]?\s*(\S+)'
        ]
        
        features = []
        
        for pattern in feature_patterns:
            matches = re.findall(pattern, text)
            features.extend(matches)
        
        # Also extract from key phrases
        key_phrases = await self._extract_key_phrases(text)
        
        # Filter and clean features
        cleaned_features = []
        for feature in features + key_phrases:
            if len(feature) > 1 and len(feature) < 20:
                cleaned_features.append(feature)
        
        return list(set(cleaned_features))[:10]
    
    async def _extract_improvements(self, text: str) -> List[str]:
        """Extract improvement suggestions from review"""
        
        improvement_keywords = [
            '개선', '바라', '았으면', '으면 좋', '면 좋겠',
            '아쉬', '부족', '더 ', '보완', '수정'
        ]
        
        suggestions = []
        sentences = text.split('.')
        
        for sentence in sentences:
            if any(keyword in sentence for keyword in improvement_keywords):
                # Clean and add sentence as suggestion
                suggestion = sentence.strip()
                if 10 < len(suggestion) < 200:
                    suggestions.append(suggestion)
        
        return suggestions[:5]
    
    async def _classify_customer_type(self, review: Review) -> str:
        """Classify customer type based on review patterns"""
        
        # Get customer's review history
        stmt = select(func.count(Review.id)).where(
            and_(
                Review.reviewer_name == review.reviewer_name,
                Review.marketplace == review.marketplace
            )
        )
        
        result = await self.session.execute(stmt)
        review_count = result.scalar() or 1
        
        if review_count == 1:
            return 'new'
        elif review_count < 5:
            return 'repeat'
        else:
            return 'vip'
    
    async def _classify_review_category(self, text: str) -> str:
        """Classify review into categories"""
        
        complaint_keywords = ['불만', '실망', '화나', '짜증', '최악', '환불', '교환', '반품']
        praise_keywords = ['최고', '훌륭', '만족', '좋아', '추천', '재구매']
        suggestion_keywords = ['개선', '바라', '으면 좋', '아쉬']
        
        text_lower = text.lower()
        
        complaint_count = sum(1 for keyword in complaint_keywords if keyword in text_lower)
        praise_count = sum(1 for keyword in praise_keywords if keyword in text_lower)
        suggestion_count = sum(1 for keyword in suggestion_keywords if keyword in text_lower)
        
        if complaint_count > praise_count and complaint_count > suggestion_count:
            return 'complaint'
        elif praise_count > complaint_count and praise_count > suggestion_count:
            return 'praise'
        elif suggestion_count > 0:
            return 'suggestion'
        else:
            return 'neutral'
    
    async def analyze_batch_reviews(
        self,
        product_id: int,
        marketplace: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Analyze multiple reviews for a product"""
        
        # Get unanalyzed reviews
        stmt = select(Review).outerjoin(
            ReviewAnalytics,
            Review.id == ReviewAnalytics.review_id
        ).where(
            and_(
                Review.product_id == product_id,
                ReviewAnalytics.id.is_(None)
            )
        )
        
        if marketplace:
            stmt = stmt.where(Review.marketplace == marketplace)
        
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        reviews = result.scalars().all()
        
        logger.info(f"Analyzing {len(reviews)} reviews for product {product_id}")
        
        # Analyze each review
        analysis_results = []
        for review in reviews:
            try:
                result = await self.analyze_review(review)
                analysis_results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze review {review.id}: {str(e)}")
        
        # Aggregate results
        aggregated = await self._aggregate_review_analytics(product_id, marketplace)
        
        return {
            'product_id': product_id,
            'analyzed_count': len(analysis_results),
            'aggregated_insights': aggregated
        }
    
    async def _aggregate_review_analytics(
        self,
        product_id: int,
        marketplace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Aggregate analytics across all reviews"""
        
        # Get all analytics for product
        stmt = select(ReviewAnalytics).join(
            Review,
            ReviewAnalytics.review_id == Review.id
        ).where(Review.product_id == product_id)
        
        if marketplace:
            stmt = stmt.where(Review.marketplace == marketplace)
        
        result = await self.session.execute(stmt)
        analytics = result.scalars().all()
        
        if not analytics:
            return {}
        
        # Aggregate sentiment
        sentiment_scores = [a.sentiment_score for a in analytics]
        sentiment_labels = [a.sentiment_label for a in analytics]
        
        sentiment_distribution = Counter(sentiment_labels)
        
        # Aggregate key phrases
        all_phrases = []
        for a in analytics:
            if a.key_phrases:
                all_phrases.extend(a.key_phrases)
        
        phrase_counts = Counter(all_phrases)
        
        # Aggregate product aspects
        aspect_scores = {}
        aspect_counts = {}
        
        for a in analytics:
            if a.product_aspects:
                for aspect, score in a.product_aspects.items():
                    if aspect not in aspect_scores:
                        aspect_scores[aspect] = 0
                        aspect_counts[aspect] = 0
                    
                    aspect_scores[aspect] += score
                    aspect_counts[aspect] += 1
        
        # Calculate average aspect scores
        avg_aspect_scores = {
            aspect: aspect_scores[aspect] / aspect_counts[aspect]
            for aspect in aspect_scores
        }
        
        # Aggregate improvement suggestions
        all_suggestions = []
        for a in analytics:
            if a.improvement_suggestions:
                all_suggestions.extend(a.improvement_suggestions)
        
        # Aggregate customer types
        customer_types = Counter([a.customer_type for a in analytics if a.customer_type])
        
        return {
            'total_reviews': len(analytics),
            'average_sentiment': np.mean(sentiment_scores),
            'sentiment_distribution': dict(sentiment_distribution),
            'top_phrases': phrase_counts.most_common(20),
            'aspect_sentiments': avg_aspect_scores,
            'improvement_suggestions': all_suggestions[:10],
            'customer_type_distribution': dict(customer_types),
            'insights': {
                'most_positive_aspect': max(avg_aspect_scores.items(), key=lambda x: x[1])[0] if avg_aspect_scores else None,
                'most_negative_aspect': min(avg_aspect_scores.items(), key=lambda x: x[1])[0] if avg_aspect_scores else None,
                'sentiment_trend': 'positive' if np.mean(sentiment_scores) > 0.1 else 'negative' if np.mean(sentiment_scores) < -0.1 else 'neutral'
            }
        }
    
    async def generate_review_insights(
        self,
        product_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Generate actionable insights from reviews"""
        
        # Get product
        stmt = select(Product).where(Product.id == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            return {'error': 'Product not found'}
        
        # Get aggregated analytics
        aggregated = await self._aggregate_review_analytics(product_id)
        
        if not aggregated:
            return {'error': 'No review analytics available'}
        
        # Generate insights
        insights = {
            'product_id': product_id,
            'product_name': product.name,
            'analysis_period': f'{days} days',
            'summary': {
                'total_reviews_analyzed': aggregated['total_reviews'],
                'overall_sentiment': aggregated['average_sentiment'],
                'sentiment_label': 'positive' if aggregated['average_sentiment'] > 0.1 else 'negative' if aggregated['average_sentiment'] < -0.1 else 'neutral'
            },
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'action_items': []
        }
        
        # Identify strengths (positive aspects)
        for aspect, score in aggregated['aspect_sentiments'].items():
            if score > 0.3:
                insights['strengths'].append({
                    'aspect': aspect,
                    'score': score,
                    'description': f"Customers are very satisfied with {aspect}"
                })
        
        # Identify weaknesses (negative aspects)
        for aspect, score in aggregated['aspect_sentiments'].items():
            if score < -0.2:
                insights['weaknesses'].append({
                    'aspect': aspect,
                    'score': score,
                    'description': f"Customers are dissatisfied with {aspect}"
                })
        
        # Identify opportunities from suggestions
        if aggregated['improvement_suggestions']:
            insights['opportunities'] = aggregated['improvement_suggestions'][:5]
        
        # Generate action items
        if insights['weaknesses']:
            for weakness in insights['weaknesses']:
                insights['action_items'].append({
                    'priority': 'high',
                    'action': f"Improve {weakness['aspect']}",
                    'reason': weakness['description']
                })
        
        # Add insights from top phrases
        top_negative_phrases = [
            phrase for phrase, count in aggregated['top_phrases']
            if any(neg in phrase for neg in ['불만', '나쁨', '실망', '최악'])
        ]
        
        if top_negative_phrases:
            insights['action_items'].append({
                'priority': 'medium',
                'action': 'Address recurring issues',
                'reason': f"Frequent mentions: {', '.join(top_negative_phrases[:3])}"
            })
        
        return insights