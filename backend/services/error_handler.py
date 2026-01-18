"""
Comprehensive error handling system with classification and user-friendly responses
"""
import logging
import traceback
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
import hashlib
import re

class ErrorCategory(Enum):
    """Error category classification"""
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    SYSTEM_ERROR = "system_error"
    NETWORK_ERROR = "network_error"
    RESOURCE_ERROR = "resource_error"
    AUTHENTICATION_ERROR = "authentication_error"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorHandler:
    """Centralized error handling and response system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure privacy-preserving logging"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Ensure logs directory exists
        import os
        os.makedirs('logs', exist_ok=True)
        
        # Create file handler for error logs
        file_handler = logging.FileHandler('logs/error.log')
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(formatter)
        
        # Create console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def classify_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorCategory:
        """
        Classify error into appropriate category
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            ErrorCategory enum value
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Validation errors
        if any(keyword in error_type.lower() for keyword in ['validation', 'value', 'type']):
            return ErrorCategory.VALIDATION_ERROR
        
        if any(keyword in error_message for keyword in ['invalid', 'unsupported', 'format', 'size']):
            return ErrorCategory.VALIDATION_ERROR
        
        # Processing errors
        if any(keyword in error_type.lower() for keyword in ['ocr', 'pdf', 'processing']):
            return ErrorCategory.PROCESSING_ERROR
        
        if any(keyword in error_message for keyword in ['corrupt', 'extract', 'analyze', 'convert']):
            return ErrorCategory.PROCESSING_ERROR
        
        # Network errors
        if any(keyword in error_type.lower() for keyword in ['connection', 'timeout', 'network']):
            return ErrorCategory.NETWORK_ERROR
        
        if any(keyword in error_message for keyword in ['connection', 'timeout', 'network', 'unreachable']):
            return ErrorCategory.NETWORK_ERROR
        
        # Resource errors
        if any(keyword in error_type.lower() for keyword in ['memory', 'disk', 'resource']):
            return ErrorCategory.RESOURCE_ERROR
        
        if any(keyword in error_message for keyword in ['memory', 'disk', 'space', 'resource']):
            return ErrorCategory.RESOURCE_ERROR
        
        # Authentication errors
        if any(keyword in error_type.lower() for keyword in ['auth', 'permission', 'access']):
            return ErrorCategory.AUTHENTICATION_ERROR
        
        # Default to system error
        return ErrorCategory.SYSTEM_ERROR
    
    def get_error_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """
        Determine error severity based on type and category
        
        Args:
            error: The exception that occurred
            category: Error category
            
        Returns:
            ErrorSeverity enum value
        """
        error_message = str(error).lower()
        
        # Critical errors
        if category == ErrorCategory.SYSTEM_ERROR:
            if any(keyword in error_message for keyword in ['critical', 'fatal', 'crash']):
                return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.RESOURCE_ERROR, ErrorCategory.AUTHENTICATION_ERROR]:
            return ErrorSeverity.HIGH
        
        if any(keyword in error_message for keyword in ['corrupt', 'failed', 'error']):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.PROCESSING_ERROR, ErrorCategory.NETWORK_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors (validation, etc.)
        return ErrorSeverity.LOW
    
    def generate_user_friendly_message(self, error: Exception, category: ErrorCategory) -> Dict[str, str]:
        """
        Generate user-friendly error messages with specific guidance
        
        Args:
            error: The exception that occurred
            category: Error category
            
        Returns:
            Dictionary with error message and guidance
        """
        error_message = str(error).lower()
        
        if category == ErrorCategory.VALIDATION_ERROR:
            if 'file type' in error_message or 'unsupported' in error_message:
                return {
                    'message': 'The uploaded file format is not supported.',
                    'guidance': 'Please upload a PDF, JPG, or PNG file and try again.',
                    'action': 'Select a different file with a supported format.'
                }
            
            if 'size' in error_message or 'limit' in error_message:
                return {
                    'message': 'The uploaded file is too large.',
                    'guidance': 'Please upload a file smaller than 10MB.',
                    'action': 'Compress your file or select a smaller file.'
                }
            
            if 'empty' in error_message:
                return {
                    'message': 'The uploaded file appears to be empty.',
                    'guidance': 'Please check your file and upload a valid document.',
                    'action': 'Select a different file that contains content.'
                }
            
            return {
                'message': 'The uploaded file could not be validated.',
                'guidance': 'Please ensure your file is a valid PDF, JPG, or PNG document.',
                'action': 'Try uploading a different file or check the file integrity.'
            }
        
        elif category == ErrorCategory.PROCESSING_ERROR:
            if 'pdf' in error_message:
                if 'encrypted' in error_message:
                    return {
                        'message': 'The PDF file is password-protected.',
                        'guidance': 'Please remove the password protection and try again.',
                        'action': 'Upload an unencrypted version of your PDF.'
                    }
                
                if 'corrupt' in error_message:
                    return {
                        'message': 'The PDF file appears to be corrupted.',
                        'guidance': 'Please try uploading a different PDF file.',
                        'action': 'Check the file integrity or try saving the PDF again.'
                    }
            
            if 'ocr' in error_message:
                return {
                    'message': 'Text recognition processing failed.',
                    'guidance': 'This may be due to poor image quality or complex layouts.',
                    'action': 'Try uploading a higher quality scan or a simpler document layout.'
                }
            
            return {
                'message': 'Document processing encountered an error.',
                'guidance': 'This may be temporary. Please try again in a few moments.',
                'action': 'If the problem persists, try uploading a different document.'
            }
        
        elif category == ErrorCategory.NETWORK_ERROR:
            return {
                'message': 'A network connection error occurred.',
                'guidance': 'Please check your internet connection and try again.',
                'action': 'Refresh the page and retry your upload.'
            }
        
        elif category == ErrorCategory.RESOURCE_ERROR:
            return {
                'message': 'The system is currently experiencing high load.',
                'guidance': 'Please wait a few minutes and try again.',
                'action': 'Try again later when system resources are available.'
            }
        
        elif category == ErrorCategory.AUTHENTICATION_ERROR:
            return {
                'message': 'Access to this resource is not authorized.',
                'guidance': 'Please check your permissions or contact support.',
                'action': 'Verify your access rights or contact an administrator.'
            }
        
        else:  # SYSTEM_ERROR
            return {
                'message': 'An unexpected system error occurred.',
                'guidance': 'This appears to be a temporary issue with our service.',
                'action': 'Please try again later. If the problem persists, contact support.'
            }
    
    def sanitize_for_logging(self, data: Any) -> Any:
        """
        Sanitize data for privacy-preserving logging
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data safe for logging
        """
        if isinstance(data, str):
            # Remove potential PII patterns
            sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', data)
            sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', sanitized)
            sanitized = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', sanitized)
            sanitized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', sanitized)
            
            # Replace file paths with hashed versions
            sanitized = re.sub(r'/[^/\s]+/[^/\s]+', lambda m: f'/[PATH_HASH_{hashlib.md5(m.group().encode()).hexdigest()[:8]}]', sanitized)
            
            return sanitized
        
        elif isinstance(data, dict):
            return {key: self.sanitize_for_logging(value) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [self.sanitize_for_logging(item) for item in data]
        
        return data
    
    def log_error(self, error: Exception, category: ErrorCategory, severity: ErrorSeverity, 
                  context: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None):
        """
        Log error with privacy protection and sufficient debugging detail
        
        Args:
            error: The exception that occurred
            category: Error category
            severity: Error severity
            context: Additional context information
            user_id: User identifier (will be hashed for privacy)
        """
        # Create error ID for tracking
        error_id = hashlib.md5(f"{datetime.now().isoformat()}{str(error)}".encode()).hexdigest()[:12]
        
        # Sanitize context data
        safe_context = self.sanitize_for_logging(context) if context else {}
        
        # Hash user ID for privacy
        safe_user_id = hashlib.md5(user_id.encode()).hexdigest()[:8] if user_id else 'anonymous'
        
        # Create log entry
        log_data = {
            'error_id': error_id,
            'timestamp': datetime.now().isoformat(),
            'category': category.value,
            'severity': severity.value,
            'error_type': type(error).__name__,
            'error_message': self.sanitize_for_logging(str(error)),
            'user_id_hash': safe_user_id,
            'context': safe_context
        }
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"CRITICAL ERROR [{error_id}]: {log_data}")
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(f"HIGH SEVERITY ERROR [{error_id}]: {log_data}")
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"MEDIUM SEVERITY ERROR [{error_id}]: {log_data}")
        else:
            self.logger.info(f"LOW SEVERITY ERROR [{error_id}]: {log_data}")
        
        # Log stack trace for debugging (sanitized)
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            sanitized_traceback = self.sanitize_for_logging(traceback.format_exc())
            self.logger.debug(f"Stack trace for error [{error_id}]: {sanitized_traceback}")
    
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None, 
                    user_id: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """
        Complete error handling pipeline
        
        Args:
            error: The exception that occurred
            context: Additional context information
            user_id: User identifier
            
        Returns:
            Tuple of (response_data, http_status_code)
        """
        # Classify error
        category = self.classify_error(error, context)
        severity = self.get_error_severity(error, category)
        
        # Generate user-friendly message
        user_message = self.generate_user_friendly_message(error, category)
        
        # Log error with privacy protection
        self.log_error(error, category, severity, context, user_id)
        
        # Determine HTTP status code
        status_code = self._get_http_status_code(category, severity)
        
        # Create response
        response_data = {
            'error': user_message['message'],
            'category': category.value,
            'guidance': user_message['guidance'],
            'action': user_message['action'],
            'timestamp': datetime.now().isoformat()
        }
        
        return response_data, status_code
    
    def _get_http_status_code(self, category: ErrorCategory, severity: ErrorSeverity) -> int:
        """
        Determine appropriate HTTP status code based on error category and severity
        
        Args:
            category: Error category
            severity: Error severity
            
        Returns:
            HTTP status code
        """
        if category == ErrorCategory.VALIDATION_ERROR:
            return 400  # Bad Request
        elif category == ErrorCategory.AUTHENTICATION_ERROR:
            return 401  # Unauthorized
        elif category == ErrorCategory.RESOURCE_ERROR:
            return 503  # Service Unavailable
        elif category == ErrorCategory.NETWORK_ERROR:
            return 408  # Request Timeout
        elif severity == ErrorSeverity.CRITICAL:
            return 500  # Internal Server Error
        else:
            return 500  # Internal Server Error


# Global error handler instance
error_handler = ErrorHandler()