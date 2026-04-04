"""
Performance monitoring utilities
"""
import time
import psutil
from typing import Dict, Optional
from loguru import logger
import threading


class PerformanceMonitor:
    """Monitor system performance metrics"""
    
    def __init__(self):
        self.metrics = {
            "queries": [],
            "retrieval_times": [],
            "generation_times": [],
            "total_times": []
        }
        self.start_time = time.time()
    
    def record_query(
        self,
        retrieval_time: float,
        generation_time: float,
        total_time: float
    ):
        """Record query performance metrics"""
        self.metrics["queries"].append(time.time())
        self.metrics["retrieval_times"].append(retrieval_time)
        self.metrics["generation_times"].append(generation_time)
        self.metrics["total_times"].append(total_time)
    
    def get_summary(self) -> Dict:
        """Get performance summary statistics"""
        if not self.metrics["queries"]:
            return {
                "total_queries": 0,
                "uptime_seconds": time.time() - self.start_time
            }
        
        return {
            "total_queries": len(self.metrics["queries"]),
            "avg_retrieval_time": sum(self.metrics["retrieval_times"]) / len(self.metrics["retrieval_times"]),
            "avg_generation_time": sum(self.metrics["generation_times"]) / len(self.metrics["generation_times"]),
            "avg_total_time": sum(self.metrics["total_times"]) / len(self.metrics["total_times"]),
            "uptime_seconds": time.time() - self.start_time,
            "queries_per_minute": len(self.metrics["queries"]) / ((time.time() - self.start_time) / 60)
        }
    
    def get_system_metrics(self) -> Dict:
        """Get current system resource usage"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": psutil.virtual_memory().used / (1024**3),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "disk_usage_percent": psutil.disk_usage('/').percent
        }


class Timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.elapsed: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.elapsed = time.time() - self.start_time
        logger.info(f"{self.name} took {self.elapsed:.2f}s")


def profile_memory(func):
    """Decorator to profile memory usage of a function"""
    def wrapper(*args, **kwargs):
        import tracemalloc
        
        tracemalloc.start()
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        logger.info(
            f"{func.__name__} - Current memory: {current / 1024**2:.2f} MB, "
            f"Peak memory: {peak / 1024**2:.2f} MB"
        )
        
        return result
    
    return wrapper


# Global performance monitor instance
global_monitor = PerformanceMonitor()
