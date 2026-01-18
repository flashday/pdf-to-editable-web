"""
Configuration settings for the application
Supports both development and production environments
"""
import os
from pathlib import Path

class Config:
    """Base configuration for PDF to Editable Web Layout System"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB file size limit
    UPLOAD_FOLDER = Path('uploads')
    TEMP_FOLDER = Path('temp')
    
    # OCR Configuration
    OCR_CONFIDENCE_THRESHOLD = 0.7
    OCR_CPU_ONLY = True
    OCR_USE_GPU = os.environ.get('OCR_USE_GPU', 'false').lower() == 'true'
    OCR_LANG = os.environ.get('OCR_LANG', 'ch')  # Default to Chinese/English
    
    # Processing Configuration
    PROCESSING_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    
    # Memory limits for OCR processing
    MEMORY_LIMIT_MB = int(os.environ.get('MEMORY_LIMIT_MB', 1024))
    
    # Status tracking configuration
    STATUS_HISTORY_LIMIT = 100
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Create necessary directories
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        Config.TEMP_FOLDER.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    UPLOAD_FOLDER = Path('test_uploads')
    TEMP_FOLDER = Path('test_temp')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Use environment variables for production paths
    UPLOAD_FOLDER = Path(os.environ.get('UPLOAD_FOLDER', 'uploads'))
    TEMP_FOLDER = Path(os.environ.get('TEMP_FOLDER', 'temp'))

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}