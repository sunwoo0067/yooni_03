"""
Celery tasks for AI agent processing and management.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import AIAgent
from .memory.chat_memory import ChatMemory
from .memory.semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_ai_task(self, agent_id: int, task_type: str, task_data: Dict[str, Any],
                   user_id: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Process an AI task using the specified agent.
    
    Args:
        agent_id: ID of the AI agent to use
        task_type: Type of task to process
        task_data: Data for the task
        user_id: Optional user ID for context
        session_id: Optional session ID for chat continuity
        
    Returns:
        Dictionary with task results
    """
    try:
        logger.info(f"Processing AI task: {task_type} with agent {agent_id}")
        
        # Get the AI agent (assuming we have an AIAgent model)
        try:
            agent = AIAgent.objects.get(id=agent_id)
        except:
            # If no AIAgent model exists, create a default processing flow
            agent = None
        
        # Process different types of AI tasks
        if task_type == 'chat':
            result = _process_chat_task(agent, task_data, user_id, session_id)
        elif task_type == 'product_analysis':
            result = _process_product_analysis_task(agent, task_data)
        elif task_type == 'content_generation':
            result = _process_content_generation_task(agent, task_data)
        elif task_type == 'data_enrichment':
            result = _process_data_enrichment_task(agent, task_data)
        elif task_type == 'sentiment_analysis':
            result = _process_sentiment_analysis_task(agent, task_data)
        elif task_type == 'recommendation':
            result = _process_recommendation_task(agent, task_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
        
        logger.info(f"AI task completed successfully: {task_type}")
        
        return {
            'success': True,
            'agent_id': agent_id,
            'task_type': task_type,
            'result': result,
            'processed_at': timezone.now().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error processing AI task {task_type}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


def _process_chat_task(agent: Any, task_data: Dict[str, Any], 
                      user_id: Optional[int], session_id: Optional[str]) -> Dict[str, Any]:
    """Process a chat/conversation task."""
    message = task_data.get('message', '')
    context = task_data.get('context', {})
    
    # Initialize chat memory if session_id provided
    chat_memory = None
    if session_id:
        chat_memory = ChatMemory(session_id)
        # Retrieve conversation history
        history = chat_memory.get_conversation_history(limit=10)
        context['conversation_history'] = history
    
    # Here you would integrate with your actual AI service (OpenAI, Anthropic, etc.)
    # For now, we'll simulate a response
    response = _call_ai_service('chat', {
        'message': message,
        'context': context,
        'agent_config': agent.config if agent else {}
    })
    
    # Store the conversation in memory if session provided
    if chat_memory:
        chat_memory.add_message('user', message)
        chat_memory.add_message('assistant', response.get('content', ''))
    
    return {
        'response': response.get('content', ''),
        'confidence': response.get('confidence', 0.8),
        'tokens_used': response.get('tokens_used', 0),
        'session_id': session_id
    }


def _process_product_analysis_task(agent: Any, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a product analysis task."""
    product_data = task_data.get('product_data', {})
    analysis_type = task_data.get('analysis_type', 'general')
    
    # Call AI service for product analysis
    response = _call_ai_service('product_analysis', {
        'product_data': product_data,
        'analysis_type': analysis_type,
        'agent_config': agent.config if agent else {}
    })
    
    return {
        'analysis': response.get('analysis', {}),
        'recommendations': response.get('recommendations', []),
        'confidence': response.get('confidence', 0.8),
        'tokens_used': response.get('tokens_used', 0)
    }


def _process_content_generation_task(agent: Any, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a content generation task."""
    content_type = task_data.get('content_type', 'description')
    input_data = task_data.get('input_data', {})
    parameters = task_data.get('parameters', {})
    
    # Call AI service for content generation
    response = _call_ai_service('content_generation', {
        'content_type': content_type,
        'input_data': input_data,
        'parameters': parameters,
        'agent_config': agent.config if agent else {}
    })
    
    return {
        'generated_content': response.get('content', ''),
        'metadata': response.get('metadata', {}),
        'confidence': response.get('confidence', 0.8),
        'tokens_used': response.get('tokens_used', 0)
    }


def _process_data_enrichment_task(agent: Any, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a data enrichment task."""
    data_to_enrich = task_data.get('data', {})
    enrichment_fields = task_data.get('fields', [])
    
    # Call AI service for data enrichment
    response = _call_ai_service('data_enrichment', {
        'data': data_to_enrich,
        'fields': enrichment_fields,
        'agent_config': agent.config if agent else {}
    })
    
    return {
        'enriched_data': response.get('enriched_data', {}),
        'enrichment_score': response.get('score', 0.8),
        'tokens_used': response.get('tokens_used', 0)
    }


def _process_sentiment_analysis_task(agent: Any, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a sentiment analysis task."""
    text = task_data.get('text', '')
    context = task_data.get('context', {})
    
    # Call AI service for sentiment analysis
    response = _call_ai_service('sentiment_analysis', {
        'text': text,
        'context': context,
        'agent_config': agent.config if agent else {}
    })
    
    return {
        'sentiment': response.get('sentiment', 'neutral'),
        'confidence': response.get('confidence', 0.8),
        'emotions': response.get('emotions', {}),
        'tokens_used': response.get('tokens_used', 0)
    }


def _process_recommendation_task(agent: Any, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a recommendation task."""
    user_data = task_data.get('user_data', {})
    item_data = task_data.get('item_data', {})
    recommendation_type = task_data.get('type', 'product')
    
    # Call AI service for recommendations
    response = _call_ai_service('recommendation', {
        'user_data': user_data,
        'item_data': item_data,
        'type': recommendation_type,
        'agent_config': agent.config if agent else {}
    })
    
    return {
        'recommendations': response.get('recommendations', []),
        'confidence': response.get('confidence', 0.8),
        'reasoning': response.get('reasoning', ''),
        'tokens_used': response.get('tokens_used', 0)
    }


def _call_ai_service(task_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call the appropriate AI service based on task type.
    This is a placeholder - implement with actual AI service calls.
    """
    # This would be replaced with actual AI service calls
    # For now, return a mock response
    return {
        'content': f"AI response for {task_type}",
        'confidence': 0.85,
        'tokens_used': 150,
        'analysis': {'key': 'value'},
        'recommendations': ['recommendation1', 'recommendation2'],
        'sentiment': 'positive',
        'emotions': {'positive': 0.8, 'negative': 0.1, 'neutral': 0.1}
    }


@shared_task
def batch_process_ai_tasks(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process multiple AI tasks in batch.
    
    Args:
        tasks: List of task dictionaries with agent_id, task_type, and task_data
        
    Returns:
        Dictionary with batch processing results
    """
    logger.info(f"Processing batch of {len(tasks)} AI tasks")
    
    results = []
    successful = 0
    failed = 0
    
    for i, task in enumerate(tasks):
        try:
            result = process_ai_task.delay(
                agent_id=task.get('agent_id'),
                task_type=task.get('task_type'),
                task_data=task.get('task_data', {}),
                user_id=task.get('user_id'),
                session_id=task.get('session_id')
            ).get()
            
            results.append({
                'task_index': i,
                'success': result.get('success', False),
                'result': result
            })
            
            if result.get('success', False):
                successful += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.error(f"Error processing batch task {i}: {e}")
            results.append({
                'task_index': i,
                'success': False,
                'error': str(e)
            })
            failed += 1
    
    return {
        'success': True,
        'total_tasks': len(tasks),
        'successful': successful,
        'failed': failed,
        'results': results
    }


@shared_task
def analyze_product_descriptions(product_ids: List[int]) -> Dict[str, Any]:
    """
    Analyze product descriptions using AI and suggest improvements.
    
    Args:
        product_ids: List of product IDs to analyze
        
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"Analyzing descriptions for {len(product_ids)} products")
    
    # Import here to avoid circular imports
    from suppliers.models import SupplierProduct
    
    results = []
    
    for product_id in product_ids:
        try:
            product = SupplierProduct.objects.get(id=product_id)
            
            # Analyze the product description
            task_result = process_ai_task.delay(
                agent_id=1,  # Default agent
                task_type='product_analysis',
                task_data={
                    'product_data': {
                        'name': product.supplier_name,
                        'description': product.description,
                        'category': product.category,
                        'brand': product.brand,
                        'price': float(product.cost_price) if product.cost_price else 0
                    },
                    'analysis_type': 'description'
                }
            ).get()
            
            results.append({
                'product_id': product_id,
                'product_name': product.supplier_name,
                'analysis': task_result.get('result', {}),
                'success': task_result.get('success', False)
            })
            
        except SupplierProduct.DoesNotExist:
            logger.warning(f"Product {product_id} not found")
            results.append({
                'product_id': product_id,
                'success': False,
                'error': 'Product not found'
            })
        except Exception as e:
            logger.error(f"Error analyzing product {product_id}: {e}")
            results.append({
                'product_id': product_id,
                'success': False,
                'error': str(e)
            })
    
    successful = sum(1 for r in results if r.get('success', False))
    
    return {
        'success': True,
        'total_products': len(product_ids),
        'successful_analyses': successful,
        'failed_analyses': len(product_ids) - successful,
        'results': results
    }


@shared_task
def generate_marketplace_listings(product_ids: List[int], marketplace_id: int) -> Dict[str, Any]:
    """
    Generate optimized marketplace listings using AI.
    
    Args:
        product_ids: List of product IDs to create listings for
        marketplace_id: Target marketplace ID
        
    Returns:
        Dictionary with generation results
    """
    logger.info(f"Generating marketplace listings for {len(product_ids)} products")
    
    # Import here to avoid circular imports
    from suppliers.models import SupplierProduct
    from marketplaces.models import Marketplace
    
    try:
        marketplace = Marketplace.objects.get(id=marketplace_id)
    except Marketplace.DoesNotExist:
        return {
            'success': False,
            'error': f'Marketplace {marketplace_id} not found'
        }
    
    results = []
    
    for product_id in product_ids:
        try:
            product = SupplierProduct.objects.get(id=product_id)
            
            # Generate listing content
            task_result = process_ai_task.delay(
                agent_id=1,  # Default agent
                task_type='content_generation',
                task_data={
                    'content_type': 'marketplace_listing',
                    'input_data': {
                        'product': {
                            'name': product.supplier_name,
                            'description': product.description,
                            'category': product.category,
                            'brand': product.brand,
                            'price': float(product.cost_price) if product.cost_price else 0,
                            'attributes': product.attributes
                        },
                        'marketplace': {
                            'name': marketplace.name,
                            'platform': marketplace.platform_type,
                            'requirements': marketplace.connection_settings.get('listing_requirements', {})
                        }
                    },
                    'parameters': {
                        'optimize_for_seo': True,
                        'include_features': True,
                        'target_length': 'medium'
                    }
                }
            ).get()
            
            results.append({
                'product_id': product_id,
                'product_name': product.supplier_name,
                'generated_listing': task_result.get('result', {}),
                'success': task_result.get('success', False)
            })
            
        except SupplierProduct.DoesNotExist:
            logger.warning(f"Product {product_id} not found")
            results.append({
                'product_id': product_id,
                'success': False,
                'error': 'Product not found'
            })
        except Exception as e:
            logger.error(f"Error generating listing for product {product_id}: {e}")
            results.append({
                'product_id': product_id,
                'success': False,
                'error': str(e)
            })
    
    successful = sum(1 for r in results if r.get('success', False))
    
    return {
        'success': True,
        'marketplace_id': marketplace_id,
        'marketplace_name': marketplace.name,
        'total_products': len(product_ids),
        'successful_generations': successful,
        'failed_generations': len(product_ids) - successful,
        'results': results
    }


@shared_task
def analyze_customer_feedback(feedback_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze customer feedback using AI for sentiment and insights.
    
    Args:
        feedback_data: List of feedback dictionaries
        
    Returns:
        Dictionary with analysis results
    """
    logger.info(f"Analyzing {len(feedback_data)} pieces of customer feedback")
    
    results = []
    sentiment_summary = {'positive': 0, 'negative': 0, 'neutral': 0}
    
    for i, feedback in enumerate(feedback_data):
        try:
            # Analyze sentiment
            task_result = process_ai_task.delay(
                agent_id=1,  # Default agent
                task_type='sentiment_analysis',
                task_data={
                    'text': feedback.get('text', ''),
                    'context': {
                        'product_id': feedback.get('product_id'),
                        'rating': feedback.get('rating'),
                        'source': feedback.get('source', 'unknown')
                    }
                }
            ).get()
            
            sentiment = task_result.get('result', {}).get('sentiment', 'neutral')
            sentiment_summary[sentiment] += 1
            
            results.append({
                'feedback_index': i,
                'sentiment_analysis': task_result.get('result', {}),
                'success': task_result.get('success', False)
            })
            
        except Exception as e:
            logger.error(f"Error analyzing feedback {i}: {e}")
            results.append({
                'feedback_index': i,
                'success': False,
                'error': str(e)
            })
    
    successful = sum(1 for r in results if r.get('success', False))
    
    return {
        'success': True,
        'total_feedback': len(feedback_data),
        'successful_analyses': successful,
        'failed_analyses': len(feedback_data) - successful,
        'sentiment_summary': sentiment_summary,
        'results': results
    }


@shared_task
def cleanup_ai_sessions(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up old AI chat sessions and temporary data.
    
    Args:
        days_old: Remove sessions older than this many days
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Cleaning up AI sessions older than {days_old} days")
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    # Clean up chat memory sessions
    try:
        # This would depend on your ChatMemory implementation
        # For now, we'll simulate cleanup
        cleaned_sessions = 0
        # cleaned_sessions = ChatMemory.cleanup_old_sessions(cutoff_date)
        
        logger.info(f"Cleaned up {cleaned_sessions} old AI sessions")
        
        return {
            'success': True,
            'sessions_cleaned': cleaned_sessions,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        error_msg = f"Error cleaning up AI sessions: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }


@shared_task
def update_semantic_memory(data_type: str, data_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update semantic memory with new data for AI context.
    
    Args:
        data_type: Type of data being stored
        data_items: List of data items to store
        
    Returns:
        Dictionary with update results
    """
    logger.info(f"Updating semantic memory with {len(data_items)} {data_type} items")
    
    try:
        semantic_memory = SemanticMemory()
        
        results = []
        successful = 0
        
        for item in data_items:
            try:
                # Store item in semantic memory
                result = semantic_memory.store_data(data_type, item)
                results.append({
                    'item_id': item.get('id'),
                    'success': True,
                    'vector_id': result.get('vector_id')
                })
                successful += 1
                
            except Exception as e:
                logger.error(f"Error storing item in semantic memory: {e}")
                results.append({
                    'item_id': item.get('id'),
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'data_type': data_type,
            'total_items': len(data_items),
            'successful': successful,
            'failed': len(data_items) - successful,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Error updating semantic memory: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            'success': False,
            'error': error_msg
        }