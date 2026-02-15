"""
Performance optimization utilities for FPL AI Pro API
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
import logging
from functools import wraps
from datetime import datetime, timedelta
import json
from cachetools import TTLCache, LRUCache

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and log API performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'request_count': 0,
            'total_response_time': 0,
            'slow_requests': 0,
            'error_count': 0,
            'endpoint_stats': {}
        }
        self.slow_request_threshold = 2.0  # seconds
    
    def record_request(self, endpoint: str, response_time: float, success: bool = True):
        """Record request metrics"""
        self.metrics['request_count'] += 1
        self.metrics['total_response_time'] += response_time
        
        if not success:
            self.metrics['error_count'] += 1
        
        if response_time > self.slow_request_threshold:
            self.metrics['slow_requests'] += 1
            logger.warning(f"Slow request detected: {endpoint} took {response_time:.2f}s")
        
        # Track per-endpoint stats
        if endpoint not in self.metrics['endpoint_stats']:
            self.metrics['endpoint_stats'][endpoint] = {
                'count': 0,
                'total_time': 0,
                'errors': 0,
                'slow_count': 0
            }
        
        stats = self.metrics['endpoint_stats'][endpoint]
        stats['count'] += 1
        stats['total_time'] += response_time
        if not success:
            stats['errors'] += 1
        if response_time > self.slow_request_threshold:
            stats['slow_count'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_response_time = (
            self.metrics['total_response_time'] / self.metrics['request_count']
            if self.metrics['request_count'] > 0 else 0
        )
        
        endpoint_averages = {}
        for endpoint, stats in self.metrics['endpoint_stats'].items():
            endpoint_averages[endpoint] = {
                'avg_response_time': stats['total_time'] / stats['count'] if stats['count'] > 0 else 0,
                'error_rate': stats['errors'] / stats['count'] if stats['count'] > 0 else 0,
                'slow_rate': stats['slow_count'] / stats['count'] if stats['count'] > 0 else 0,
                'request_count': stats['count']
            }
        
        return {
            'total_requests': self.metrics['request_count'],
            'avg_response_time': avg_response_time,
            'error_rate': self.metrics['error_count'] / self.metrics['request_count'] if self.metrics['request_count'] > 0 else 0,
            'slow_request_rate': self.metrics['slow_requests'] / self.metrics['request_count'] if self.metrics['request_count'] > 0 else 0,
            'endpoint_stats': endpoint_averages
        }

class AsyncCache:
    """High-performance async cache with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache = TTLCache(maxsize=max_size, ttl=default_ttl)
        self.hit_count = 0
        self.miss_count = 0
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            try:
                value = self.cache[key]
                self.hit_count += 1
                return value
            except KeyError:
                self.miss_count += 1
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            if ttl is not None:
                # For custom TTL, we need to create a new TTL cache entry
                expiry_time = time.time() + ttl
                self.cache[key] = value
            else:
                self.cache[key] = value
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        async with self._lock:
            try:
                del self.cache[key]
                return True
            except KeyError:
                return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'cache_size': len(self.cache),
            'max_size': self.cache.maxsize
        }

def performance_tracker(func):
    """Decorator to track function performance"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            end_time = time.time()
            response_time = end_time - start_time
            
            # Get endpoint name from function
            endpoint = getattr(func, '__name__', 'unknown')
            if hasattr(func, '__self__'):
                endpoint = f"{func.__self__.__class__.__name__}.{endpoint}"
            
            performance_monitor.record_request(endpoint, response_time, success)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            raise
        finally:
            end_time = time.time()
            response_time = end_time - start_time
            
            endpoint = getattr(func, '__name__', 'unknown')
            if hasattr(func, '__self__'):
                endpoint = f"{func.__self__.__class__.__name__}.{endpoint}"
            
            performance_monitor.record_request(endpoint, response_time, success)
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class BatchProcessor:
    """Process multiple requests in batches for better performance"""
    
    def __init__(self, batch_size: int = 10, max_wait_time: float = 0.1):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_requests = []
        self._processing = False
    
    async def add_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """Add a request to the batch queue"""
        future = asyncio.Future()
        request_data = {
            'func': request_func,
            'args': args,
            'kwargs': kwargs,
            'future': future
        }
        
        self.pending_requests.append(request_data)
        
        if not self._processing:
            asyncio.create_task(self._process_batch())
        
        return await future
    
    async def _process_batch(self):
        """Process pending requests in batches"""
        if self._processing:
            return
        
        self._processing = True
        
        try:
            while self.pending_requests:
                # Wait for batch to fill up or timeout
                start_time = time.time()
                
                while (len(self.pending_requests) < self.batch_size and 
                       time.time() - start_time < self.max_wait_time):
                    await asyncio.sleep(0.01)
                
                # Process current batch
                batch = self.pending_requests[:self.batch_size]
                self.pending_requests = self.pending_requests[self.batch_size:]
                
                # Execute all requests in parallel
                tasks = []
                for request in batch:
                    task = asyncio.create_task(
                        request['func'](*request['args'], **request['kwargs'])
                    )
                    tasks.append((task, request['future']))
                
                # Wait for all tasks to complete
                for task, future in tasks:
                    try:
                        result = await task
                        future.set_result(result)
                    except Exception as e:
                        future.set_exception(e)
        
        finally:
            self._processing = False

class DataOptimizer:
    """Optimize data processing and serialization"""
    
    @staticmethod
    def optimize_player_data(players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize player data for faster processing"""
        optimized = []
        
        for player in players:
            # Only include essential fields to reduce memory usage
            optimized_player = {
                'id': player.get('id'),
                'name': player.get('web_name', ''),
                'team': player.get('team'),
                'position': player.get('element_type'),
                'price': player.get('now_cost', 0) / 10,
                'total_points': player.get('total_points', 0),
                'form': float(player.get('form', 0)),
                'selected_by_percent': float(player.get('selected_by_percent', 0)),
                'minutes': player.get('minutes', 0),
                'goals': player.get('goals_scored', 0),
                'assists': player.get('assists', 0)
            }
            optimized.append(optimized_player)
        
        return optimized
    
    @staticmethod
    def compress_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress API response by removing unnecessary fields"""
        if 'predictions' in data:
            # Compress prediction data
            for pred in data['predictions']:
                # Round float values to reduce precision
                if 'predicted_points' in pred:
                    pred['predicted_points'] = round(pred['predicted_points'], 1)
                if 'confidence' in pred:
                    pred['confidence'] = round(pred['confidence'], 2)
                if 'form' in pred:
                    pred['form'] = round(pred['form'], 1)
                
                # Remove verbose reasoning for list responses
                if 'reasoning' in pred and len(str(pred['reasoning'])) > 100:
                    pred['reasoning'] = str(pred['reasoning'])[:100] + "..."
        
        return data

# Global instances
performance_monitor = PerformanceMonitor()
async_cache = AsyncCache(max_size=2000, default_ttl=300)
batch_processor = BatchProcessor(batch_size=5, max_wait_time=0.05)