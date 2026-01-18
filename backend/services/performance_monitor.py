"""
Performance monitoring and resource management service
Implements processing time tracking, memory monitoring, and resource cleanup
"""
import logging
import time
import os
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import traceback

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, memory monitoring will be limited")

@dataclass
class PerformanceMetrics:
    """Performance metrics for a processing operation"""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class PerformanceMonitor:
    """
    Monitor performance metrics for processing operations
    """
    
    def __init__(self):
        """Initialize the performance monitor"""
        self.metrics_history: List[PerformanceMetrics] = []
        self.active_operations: Dict[str, PerformanceMetrics] = {}
        self.max_processing_time = 30.0  # 30 seconds max processing time
        self.memory_limit_mb = 4096  # 4GB memory limit
        self.temp_file_limit = 100  # Max 100 temp files
        self.temp_files: List[str] = []
        self.lock = threading.Lock()
        
        # Performance thresholds
        self.performance_thresholds = {
            'warning_time': 20.0,  # 20 seconds warning
            'critical_time': 25.0,  # 25 seconds critical
            'warning_memory_mb': 2048,  # 2GB warning
            'critical_memory_mb': 3072,  # 3GB critical
        }
    
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start monitoring a new operation
        
        Args:
            operation_name: Name of the operation
            metadata: Optional metadata about the operation
            
        Returns:
            Operation ID
        """
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        with self.lock:
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=time.time(),
                metadata=metadata or {}
            )
            
            # Record initial memory usage if psutil is available
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
                metrics.peak_memory_mb = metrics.memory_usage_mb
            
            self.active_operations[operation_id] = metrics
        
        logger.info(f"Started operation: {operation_name} (ID: {operation_id})")
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     error_message: Optional[str] = None) -> Optional[PerformanceMetrics]:
        """
        End monitoring for an operation
        
        Args:
            operation_id: Operation ID from start_operation
            success: Whether operation succeeded
            error_message: Error message if operation failed
            
        Returns:
            PerformanceMetrics object or None if operation not found
        """
        with self.lock:
            if operation_id not in self.active_operations:
                logger.warning(f"Operation {operation_id} not found in active operations")
                return None
            
            metrics = self.active_operations.pop(operation_id)
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            metrics.success = success
            metrics.error_message = error_message
            
            # Record final memory usage if psutil is available
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                metrics.memory_usage_mb = process.memory_info().rss / 1024 / 1024
            
            # Check performance thresholds
            self._check_performance_thresholds(metrics)
            
            # Store in history
            self.metrics_history.append(metrics)
            
            # Limit history size
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-500:]
            
            logger.info(
                f"Completed operation: {metrics.operation_name} "
                f"(ID: {operation_id}) in {metrics.duration:.2f}s"
            )
            
            return metrics
    
    def track_operation(self, operation_name: str):
        """
        Decorator for tracking function performance
        
        Args:
            operation_name: Name for the operation
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                operation_id = self.start_operation(operation_name)
                try:
                    result = func(*args, **kwargs)
                    self.end_operation(operation_id, success=True)
                    return result
                except Exception as e:
                    self.end_operation(operation_id, success=False, error_message=str(e))
                    raise
            return wrapper
        return decorator
    
    def get_operation_metrics(self, operation_id: str) -> Optional[PerformanceMetrics]:
        """
        Get metrics for a specific operation
        
        Args:
            operation_id: Operation ID
            
        Returns:
            PerformanceMetrics or None if not found
        """
        with self.lock:
            # Check active operations first
            if operation_id in self.active_operations:
                return self.active_operations[operation_id]
            
            # Check history
            for metrics in reversed(self.metrics_history):
                if f"{metrics.operation_name}_{int(metrics.start_time * 1000)}" == operation_id:
                    return metrics
            
            return None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary statistics
        
        Returns:
            Dictionary containing performance statistics
        """
        with self.lock:
            if not self.metrics_history:
                return {
                    'total_operations': 0,
                    'successful_operations': 0,
                    'failed_operations': 0,
                    'average_duration': 0.0,
                    'max_duration': 0.0,
                    'average_memory_mb': 0.0,
                    'peak_memory_mb': 0.0
                }
            
            successful_ops = [m for m in self.metrics_history if m.success]
            failed_ops = [m for m in self.metrics_history if not m.success]
            
            durations = [m.duration for m in self.metrics_history if m.duration]
            memory_usage = [m.peak_memory_mb for m in self.metrics_history if m.peak_memory_mb]
            
            return {
                'total_operations': len(self.metrics_history),
                'successful_operations': len(successful_ops),
                'failed_operations': len(failed_ops),
                'average_duration': sum(durations) / len(durations) if durations else 0.0,
                'max_duration': max(durations) if durations else 0.0,
                'average_memory_mb': sum(memory_usage) / len(memory_usage) if memory_usage else 0.0,
                'peak_memory_mb': max(memory_usage) if memory_usage else 0.0,
                'operations_by_type': self._get_operations_by_type()
            }
    
    def _get_operations_by_type(self) -> Dict[str, int]:
        """Get count of operations by type"""
        operation_counts = {}
        for metrics in self.metrics_history:
            op_type = metrics.operation_name
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1
        return operation_counts
    
    def _check_performance_thresholds(self, metrics: PerformanceMetrics):
        """
        Check if performance metrics exceed thresholds
        
        Args:
            metrics: Performance metrics to check
        """
        # Check processing time
        if metrics.duration and metrics.duration > self.performance_thresholds['critical_time']:
            logger.error(
                f"CRITICAL: Operation {metrics.operation_name} took {metrics.duration:.2f}s "
                f"(exceeds {self.performance_thresholds['critical_time']}s threshold)"
            )
        elif metrics.duration and metrics.duration > self.performance_thresholds['warning_time']:
            logger.warning(
                f"WARNING: Operation {metrics.operation_name} took {metrics.duration:.2f}s "
                f"(exceeds {self.performance_thresholds['warning_time']}s threshold)"
            )
        
        # Check memory usage
        if metrics.peak_memory_mb and metrics.peak_memory_mb > self.performance_thresholds['critical_memory_mb']:
            logger.error(
                f"CRITICAL: Operation {metrics.operation_name} used {metrics.peak_memory_mb:.2f}MB "
                f"(exceeds {self.performance_thresholds['critical_memory_mb']}MB threshold)"
            )
        elif metrics.peak_memory_mb and metrics.peak_memory_mb > self.performance_thresholds['warning_memory_mb']:
            logger.warning(
                f"WARNING: Operation {metrics.operation_name} used {metrics.peak_memory_mb:.2f}MB "
                f"(exceeds {self.performance_thresholds['warning_memory_mb']}MB threshold)"
            )
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """
        Check current memory usage
        
        Returns:
            Dictionary with memory usage information
        """
        try:
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                memory_info = process.memory_info()
                
                rss_mb = memory_info.rss / 1024 / 1024
                vms_mb = memory_info.vms / 1024 / 1024
                
                # Get system memory info
                system_memory = psutil.virtual_memory()
                
                return {
                    'process_memory_mb': rss_mb,
                    'virtual_memory_mb': vms_mb,
                    'system_memory_total_gb': system_memory.total / 1024 / 1024 / 1024,
                    'system_memory_available_gb': system_memory.available / 1024 / 1024 / 1024,
                    'system_memory_percent': system_memory.percent,
                    'within_limits': rss_mb < self.memory_limit_mb,
                    'limit_mb': self.memory_limit_mb
                }
            else:
                # Fallback when psutil is not available
                return {
                    'process_memory_mb': None,
                    'virtual_memory_mb': None,
                    'system_memory_total_gb': None,
                    'system_memory_available_gb': None,
                    'system_memory_percent': None,
                    'within_limits': True,
                    'limit_mb': self.memory_limit_mb,
                    'note': 'psutil not available, memory monitoring limited'
                }
        except Exception as e:
            logger.error(f"Failed to check memory usage: {e}")
            return {
                'error': str(e),
                'within_limits': False
            }
    
    def enforce_memory_limit(self) -> bool:
        """
        Enforce memory limit and trigger cleanup if needed
        
        Returns:
            True if within limits, False otherwise
        """
        memory_info = self.check_memory_usage()
        
        if not memory_info.get('within_limits', True):
            logger.warning(f"Memory limit exceeded: {memory_info.get('process_memory_mb', 0):.2f}MB")
            self.trigger_cleanup()
            return False
        
        return True
    
    def register_temp_file(self, file_path: str):
        """
        Register a temporary file for tracking
        
        Args:
            file_path: Path to temporary file
        """
        with self.lock:
            self.temp_files.append(file_path)
            
            # Check temp file limit
            if len(self.temp_files) > self.temp_file_limit:
                logger.warning(f"Temp file limit exceeded: {len(self.temp_files)} files")
                self.cleanup_temp_files(force=True)
    
    def cleanup_temp_files(self, force: bool = False):
        """
        Clean up temporary files
        
        Args:
            force: Force cleanup of all temp files
        """
        with self.lock:
            files_to_remove = self.temp_files.copy() if force else self.temp_files
            
            for file_path in files_to_remove:
                try:
                    path = Path(file_path)
                    if path.exists():
                        path.unlink()
                        logger.debug(f"Removed temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {file_path}: {e}")
            
            # Clear the list
            if force:
                self.temp_files.clear()
            else:
                # Keep only files that couldn't be removed
                self.temp_files = [f for f in self.temp_files if Path(f).exists()]
    
    def trigger_cleanup(self):
        """Trigger cleanup of resources"""
        logger.info("Triggering resource cleanup")
        
        # Clean up temp files
        self.cleanup_temp_files()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logger.info("Resource cleanup completed")
    
    def get_temp_file_count(self) -> int:
        """Get count of registered temporary files"""
        with self.lock:
            return len(self.temp_files)
    
    def reset_metrics(self):
        """Reset all metrics and history"""
        with self.lock:
            self.metrics_history.clear()
            self.active_operations.clear()
            logger.info("Performance metrics reset")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
