"""
Network retry mechanism with exponential backoff and comprehensive error handling
"""
import time
import random
import logging
from typing import Callable, Any, Optional, Dict, List, Type
from functools import wraps
from dataclasses import dataclass
from enum import Enum
from backend.services.error_handler import error_handler, ErrorCategory, ErrorSeverity

# Try to import requests, but make it optional
try:
    import requests
    from requests.exceptions import (
        ConnectionError, Timeout, RequestException, 
        HTTPError, TooManyRedirects, URLRequired
    )
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    # Create dummy exceptions for type checking
    class ConnectionError(Exception): pass
    class Timeout(Exception): pass
    class RequestException(Exception): pass
    class HTTPError(Exception): pass
    class TooManyRedirects(Exception): pass
    class URLRequired(Exception): pass

class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"

class RetryableError(Exception):
    """Base exception for retryable errors"""
    pass

class NetworkRetryError(RetryableError):
    """Network-related retryable error"""
    pass

class ServiceUnavailableError(RetryableError):
    """Service unavailable retryable error"""
    pass

class RateLimitError(RetryableError):
    """Rate limit retryable error"""
    pass

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_exceptions: List[Type[Exception]] = None
    retryable_status_codes: List[int] = None

    def __post_init__(self):
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [
                ConnectionError,
                Timeout,
                NetworkRetryError,
                ServiceUnavailableError,
                RateLimitError
            ]
            
            # Add requests exceptions if available
            if REQUESTS_AVAILABLE:
                self.retryable_exceptions.extend([
                    requests.exceptions.ConnectTimeout,
                    requests.exceptions.ReadTimeout
                ])
        
        if self.retryable_status_codes is None:
            self.retryable_status_codes = [408, 429, 500, 502, 503, 504]

@dataclass
class RetryAttempt:
    """Information about a retry attempt"""
    attempt_number: int
    delay: float
    exception: Optional[Exception]
    timestamp: float
    success: bool

class RetryHandler:
    """Comprehensive retry handler with multiple strategies and monitoring"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(__name__)
        self.retry_stats = {}  # Track retry statistics
    
    def retry(self, config: Optional[RetryConfig] = None):
        """
        Decorator for adding retry functionality to functions
        
        Args:
            config: Optional retry configuration override
            
        Returns:
            Decorated function with retry capability
        """
        retry_config = config or self.config
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                return self.execute_with_retry(func, retry_config, *args, **kwargs)
            return wrapper
        return decorator
    
    def execute_with_retry(self, func: Callable, config: Optional[RetryConfig] = None, 
                          *args, **kwargs) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            config: Retry configuration
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Final exception after all retries exhausted
        """
        retry_config = config or self.config
        attempts = []
        last_exception = None
        
        func_name = getattr(func, '__name__', 'unknown_function')
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                # Log attempt
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt} for {func_name}")
                
                # Execute function
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Record successful attempt
                attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    delay=0,
                    exception=None,
                    timestamp=start_time,
                    success=True
                ))
                
                # Log success after retries
                if attempt > 0:
                    self.logger.info(f"Function {func_name} succeeded after {attempt} retries")
                
                # Update retry statistics
                self._update_retry_stats(func_name, attempts, True)
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not self._is_retryable_exception(e, retry_config):
                    self.logger.warning(f"Non-retryable exception in {func_name}: {e}")
                    self._update_retry_stats(func_name, attempts, False)
                    raise e
                
                # Check if we've exhausted retries
                if attempt >= retry_config.max_retries:
                    self.logger.error(f"All retries exhausted for {func_name}. Final exception: {e}")
                    self._update_retry_stats(func_name, attempts, False)
                    
                    # Log comprehensive retry failure
                    self._log_retry_failure(func_name, attempts, e)
                    
                    # Wrap in retry-specific exception
                    raise NetworkRetryError(f"Failed after {retry_config.max_retries} retries: {str(e)}") from e
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, retry_config)
                
                # Record failed attempt
                attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    delay=delay,
                    exception=e,
                    timestamp=time.time(),
                    success=False
                ))
                
                # Log retry with context
                self._log_retry_attempt(func_name, attempt, delay, e)
                
                # Wait before next attempt
                if delay > 0:
                    time.sleep(delay)
        
        # This should never be reached, but just in case
        raise NetworkRetryError(f"Unexpected retry loop exit for {func_name}")
    
    def _is_retryable_exception(self, exception: Exception, config: RetryConfig) -> bool:
        """
        Check if exception is retryable based on configuration
        
        Args:
            exception: Exception to check
            config: Retry configuration
            
        Returns:
            True if exception is retryable
        """
        # Check exception type
        for retryable_type in config.retryable_exceptions:
            if isinstance(exception, retryable_type):
                return True
        
        # Check HTTP status codes for requests exceptions
        if isinstance(exception, HTTPError):
            if hasattr(exception, 'response') and exception.response is not None:
                status_code = exception.response.status_code
                return status_code in config.retryable_status_codes
        
        # Check for specific error patterns in message
        error_message = str(exception).lower()
        retryable_patterns = [
            'connection', 'timeout', 'network', 'unavailable',
            'temporary', 'rate limit', 'too many requests'
        ]
        
        return any(pattern in error_message for pattern in retryable_patterns)
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """
        Calculate delay for next retry attempt
        
        Args:
            attempt: Current attempt number (0-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        if config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.backoff_factor ** attempt)
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * (attempt + 1)
        elif config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
        else:  # IMMEDIATE
            delay = 0
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter to prevent thundering herd
        if config.jitter and delay > 0:
            jitter_range = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def _log_retry_attempt(self, func_name: str, attempt: int, delay: float, exception: Exception):
        """
        Log retry attempt with context
        
        Args:
            func_name: Name of function being retried
            attempt: Attempt number
            delay: Delay before next attempt
            exception: Exception that triggered retry
        """
        context = {
            'function': func_name,
            'attempt': attempt + 1,
            'delay': delay,
            'exception_type': type(exception).__name__,
            'operation': 'network_retry'
        }
        
        # Log with appropriate severity
        if attempt == 0:
            # First failure - log as warning
            error_handler.log_error(
                exception, 
                ErrorCategory.NETWORK_ERROR,
                ErrorSeverity.MEDIUM,
                context
            )
        else:
            # Subsequent failures - log as info
            self.logger.info(f"Retry {attempt + 1} for {func_name} after {delay:.2f}s delay. Error: {exception}")
    
    def _log_retry_failure(self, func_name: str, attempts: List[RetryAttempt], final_exception: Exception):
        """
        Log comprehensive retry failure information
        
        Args:
            func_name: Name of function that failed
            attempts: List of all retry attempts
            final_exception: Final exception after all retries
        """
        context = {
            'function': func_name,
            'total_attempts': len(attempts),
            'total_delay': sum(attempt.delay for attempt in attempts),
            'attempt_details': [
                {
                    'attempt': attempt.attempt_number + 1,
                    'delay': attempt.delay,
                    'exception': str(attempt.exception) if attempt.exception else None,
                    'success': attempt.success
                }
                for attempt in attempts
            ],
            'operation': 'network_retry_failure'
        }
        
        error_handler.log_error(
            final_exception,
            ErrorCategory.NETWORK_ERROR,
            ErrorSeverity.HIGH,
            context
        )
    
    def _update_retry_stats(self, func_name: str, attempts: List[RetryAttempt], success: bool):
        """
        Update retry statistics for monitoring
        
        Args:
            func_name: Name of function
            attempts: List of retry attempts
            success: Whether operation ultimately succeeded
        """
        if func_name not in self.retry_stats:
            self.retry_stats[func_name] = {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'total_retries': 0,
                'average_retries': 0.0,
                'max_retries_used': 0
            }
        
        stats = self.retry_stats[func_name]
        stats['total_calls'] += 1
        
        if success:
            stats['successful_calls'] += 1
        else:
            stats['failed_calls'] += 1
        
        retry_count = len(attempts) - 1  # Subtract initial attempt
        stats['total_retries'] += retry_count
        stats['max_retries_used'] = max(stats['max_retries_used'], retry_count)
        stats['average_retries'] = stats['total_retries'] / stats['total_calls']
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get retry statistics for monitoring
        
        Returns:
            Dictionary containing retry statistics
        """
        return self.retry_stats.copy()
    
    def reset_retry_stats(self):
        """Reset retry statistics"""
        self.retry_stats.clear()

class NetworkClient:
    """HTTP client with built-in retry functionality"""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None, timeout: float = 30.0):
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for NetworkClient. Install it with: pip install requests")
        
        self.retry_handler = RetryHandler(retry_config)
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure session with reasonable defaults
        self.session.headers.update({
            'User-Agent': 'PDF-to-Editable-Web/1.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
    
    @property
    def retry_stats(self) -> Dict[str, Any]:
        """Get retry statistics"""
        return self.retry_handler.get_retry_stats()
    
    def get(self, url: str, **kwargs):
        """GET request with retry"""
        return self._request_with_retry('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs):
        """POST request with retry"""
        return self._request_with_retry('POST', url, **kwargs)
    
    def put(self, url: str, **kwargs):
        """PUT request with retry"""
        return self._request_with_retry('PUT', url, **kwargs)
    
    def delete(self, url: str, **kwargs):
        """DELETE request with retry"""
        return self._request_with_retry('DELETE', url, **kwargs)
    
    def _request_with_retry(self, method: str, url: str, **kwargs):
        """
        Execute HTTP request with retry logic
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Request parameters
            
        Returns:
            Response object
            
        Raises:
            NetworkRetryError: If all retries are exhausted
        """
        # Set default timeout if not provided
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        def make_request():
            try:
                response = self.session.request(method, url, **kwargs)
                
                # Check for HTTP errors
                if response.status_code in self.retry_handler.config.retryable_status_codes:
                    raise HTTPError(f"HTTP {response.status_code}: {response.reason}", response=response)
                
                # Raise for other HTTP errors (4xx, 5xx)
                response.raise_for_status()
                
                return response
                
            except Exception as e:
                # Handle requests exceptions
                if REQUESTS_AVAILABLE:
                    if isinstance(e, requests.exceptions.RequestException):
                        # Convert requests exceptions to our retryable exceptions
                        if isinstance(e, (ConnectionError, Timeout)):
                            raise NetworkRetryError(f"Network error: {str(e)}") from e
                        elif isinstance(e, HTTPError):
                            # Re-raise HTTP errors as-is for status code checking
                            raise
                        else:
                            # Other request exceptions
                            raise NetworkRetryError(f"Request error: {str(e)}") from e
                else:
                    # Generic exception handling
                    if isinstance(e, (ConnectionError, Timeout)):
                        raise NetworkRetryError(f"Network error: {str(e)}") from e
                    raise NetworkRetryError(f"Request error: {str(e)}") from e
        
        return self.retry_handler.execute_with_retry(make_request)


# Global instances for easy use
default_retry_config = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    jitter=True,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF
)

retry_handler = RetryHandler(default_retry_config)

# Only create network_client if requests is available
network_client = None
if REQUESTS_AVAILABLE:
    network_client = NetworkClient(default_retry_config)