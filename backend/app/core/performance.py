"""
Performance decorators module
Provides caching and batch processing decorators for performance optimization
"""
import asyncio
import functools
import hashlib
import time
from typing import Any, Callable, Dict, List, Optional, Union
import redis
import orjson
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Redis client for caching (should be initialized from config)
_redis_client = None

def init_redis_client(redis_url: str):
    """Initialize Redis client for caching"""
    global _redis_client
    import redis
    _redis_client = redis.from_url(redis_url, decode_responses=True)

def get_redis_client():
    """Get Redis client instance"""
    global _redis_client
    if not _redis_client:
        # Fallback to localhost if not initialized
        import redis
        _redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    return _redis_client


def redis_cache(expiration: int = 300, key_prefix: str = ""):
    """
    Redis cache decorator for method results
    
    Args:
        expiration: Cache expiration time in seconds (default: 300 = 5 minutes)
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, key_prefix, *args, **kwargs)
            
            try:
                redis_client = get_redis_client()
                
                # Try to get from cache
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return orjson.loads(cached_value)
                
                # Execute function
                logger.debug(f"Cache miss for {func.__name__}")
                result = await func(*args, **kwargs)
                
                # Cache result
                redis_client.setex(
                    cache_key, 
                    expiration, 
                    orjson.dumps(result, default=str)
                )
                
                return result
                
            except Exception as e:
                logger.warning(f"Redis cache error for {func.__name__}: {e}")
                # Fallback to direct execution
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, key_prefix, *args, **kwargs)
            
            try:
                redis_client = get_redis_client()
                
                # Try to get from cache
                cached_value = redis_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return orjson.loads(cached_value)
                
                # Execute function
                logger.debug(f"Cache miss for {func.__name__}")
                result = func(*args, **kwargs)
                
                # Cache result
                redis_client.setex(
                    cache_key, 
                    expiration, 
                    orjson.dumps(result, default=str)
                )
                
                return result
                
            except Exception as e:
                logger.warning(f"Redis cache error for {func.__name__}: {e}")
                # Fallback to direct execution
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def memory_cache(max_size: int = 50, expiration: int = 600):
    """
    In-memory cache decorator with LRU eviction
    
    Args:
        max_size: Maximum number of cached items
        expiration: Cache expiration time in seconds (default: 600 = 10 minutes)
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        access_times = {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, "", *args, **kwargs)
            current_time = time.time()
            
            # Check if cached and not expired
            if cache_key in cache:
                cached_time, cached_value = cache[cache_key]
                if current_time - cached_time < expiration:
                    access_times[cache_key] = current_time
                    logger.debug(f"Memory cache hit for {func.__name__}")
                    return cached_value
                else:
                    # Remove expired entry
                    del cache[cache_key]
                    if cache_key in access_times:
                        del access_times[cache_key]
            
            # Execute function
            logger.debug(f"Memory cache miss for {func.__name__}")
            result = await func(*args, **kwargs)
            
            # Add to cache
            cache[cache_key] = (current_time, result)
            access_times[cache_key] = current_time
            
            # Evict oldest entries if cache is full
            if len(cache) > max_size:
                oldest_key = min(access_times.keys(), key=lambda k: access_times[k])
                del cache[oldest_key]
                del access_times[oldest_key]
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, "", *args, **kwargs)
            current_time = time.time()
            
            # Check if cached and not expired
            if cache_key in cache:
                cached_time, cached_value = cache[cache_key]
                if current_time - cached_time < expiration:
                    access_times[cache_key] = current_time
                    logger.debug(f"Memory cache hit for {func.__name__}")
                    return cached_value
                else:
                    # Remove expired entry
                    del cache[cache_key]
                    if cache_key in access_times:
                        del access_times[cache_key]
            
            # Execute function
            logger.debug(f"Memory cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Add to cache
            cache[cache_key] = (current_time, result)
            access_times[cache_key] = current_time
            
            # Evict oldest entries if cache is full
            if len(cache) > max_size:
                oldest_key = min(access_times.keys(), key=lambda k: access_times[k])
                del cache[oldest_key]
                del access_times[oldest_key]
            
            return result
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def batch_process(batch_size: int = 100, max_concurrency: int = 10):
    """
    Batch processing decorator for bulk operations
    
    Args:
        batch_size: Number of items to process in each batch
        max_concurrency: Maximum number of concurrent batch operations
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(items: List[Any], *args, **kwargs):
            if not items:
                return []
            
            # Create batches
            batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
            semaphore = asyncio.Semaphore(max_concurrency)
            
            async def process_batch(batch):
                async with semaphore:
                    return await func(batch, *args, **kwargs)
            
            # Process batches concurrently
            logger.info(f"Processing {len(items)} items in {len(batches)} batches")
            start_time = time.time()
            
            tasks = [process_batch(batch) for batch in batches]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Flatten results
            results = []
            for batch_result in batch_results:
                if isinstance(batch_result, Exception):
                    logger.error(f"Batch processing error: {batch_result}")
                    continue
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
            
            elapsed_time = time.time() - start_time
            logger.info(f"Batch processing completed in {elapsed_time:.2f}s")
            
            return results
        
        @functools.wraps(func)
        def sync_wrapper(items: List[Any], *args, **kwargs):
            if not items:
                return []
            
            # Create batches
            batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
            
            logger.info(f"Processing {len(items)} items in {len(batches)} batches")
            start_time = time.time()
            
            results = []
            for batch in batches:
                try:
                    batch_result = func(batch, *args, **kwargs)
                    if isinstance(batch_result, list):
                        results.extend(batch_result)
                    else:
                        results.append(batch_result)
                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    continue
            
            elapsed_time = time.time() - start_time
            logger.info(f"Batch processing completed in {elapsed_time:.2f}s")
            
            return results
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def optimize_memory_usage(func: Callable) -> Callable:
    """
    Memory optimization decorator for large data operations
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        import gc
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = await func(*args, **kwargs)
            
            # Force garbage collection
            gc.collect()
            
            # Log memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = final_memory - initial_memory
            
            if memory_diff > 100:  # Log if memory increased by more than 100MB
                logger.warning(f"{func.__name__} memory usage: {memory_diff:.1f}MB increase")
            else:
                logger.debug(f"{func.__name__} memory usage: {memory_diff:.1f}MB change")
            
            return result
            
        except Exception as e:
            # Force cleanup on error
            gc.collect()
            raise e
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        import gc
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = func(*args, **kwargs)
            
            # Force garbage collection
            gc.collect()
            
            # Log memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = final_memory - initial_memory
            
            if memory_diff > 100:  # Log if memory increased by more than 100MB
                logger.warning(f"{func.__name__} memory usage: {memory_diff:.1f}MB increase")
            else:
                logger.debug(f"{func.__name__} memory usage: {memory_diff:.1f}MB change")
            
            return result
            
        except Exception as e:
            # Force cleanup on error
            gc.collect()
            raise e
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def _generate_cache_key(func: Callable, prefix: str, *args, **kwargs) -> str:
    """Generate a cache key for function arguments"""
    # Create a string representation of arguments
    arg_strings = []
    
    # Add positional arguments (skip 'self' if it's a method)
    for i, arg in enumerate(args):
        if i == 0 and hasattr(arg, '__dict__'):  # Skip self parameter
            continue
        arg_strings.append(str(arg))
    
    # Add keyword arguments
    for key, value in sorted(kwargs.items()):
        arg_strings.append(f"{key}:{value}")
    
    # Create hash of arguments
    arg_hash = hashlib.md5("|".join(arg_strings).encode()).hexdigest()[:8]
    
    # Create cache key
    cache_key = f"{prefix}:{func.__module__}.{func.__name__}:{arg_hash}"
    
    return cache_key


def performance_monitor(func: Callable) -> Callable:
    """
    Performance monitoring decorator that logs execution time and memory usage
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 5.0:  # Log slow operations (>5 seconds)
                logger.warning(f"Slow operation: {func.__name__} took {execution_time:.2f}s")
            else:
                logger.debug(f"{func.__name__} executed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 5.0:  # Log slow operations (>5 seconds)
                logger.warning(f"Slow operation: {func.__name__} took {execution_time:.2f}s")
            else:
                logger.debug(f"{func.__name__} executed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    
    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper