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


class ChatOCRConfig:
    """
    PP-ChatOCRv4 智能文档理解配置
    
    支持通过环境变量配置所有参数
    """
    # Ollama LLM 配置
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'gpt-oss:20b')
    OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '180'))  # 增加到180秒，复杂提取任务需要更长时间
    
    # LLM 生成参数
    LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS', '4096'))
    LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE', '0.1'))
    LLM_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', '2'))
    
    # 功能开关
    ENABLE_CHATOCR = os.environ.get('ENABLE_CHATOCR', 'true').lower() == 'true'
    ENABLE_RAG = os.environ.get('ENABLE_RAG', 'true').lower() == 'true'
    
    # RAG 向量检索配置
    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'BAAI/bge-small-zh-v1.5')
    VECTOR_DB_PATH = os.environ.get('VECTOR_DB_PATH', './vector_db')
    
    # 文本分块配置
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', '500'))
    CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', '50'))
    
    # RAG 检索配置
    # 10 页文档约 30-40 个分块，Top-30 可覆盖约 80%
    RAG_TOP_K = int(os.environ.get('RAG_TOP_K', '30'))
    
    # LLM 上下文限制（字符数）
    # 128K tokens ≈ 50-60K 中文字符，保守设置 32000
    LLM_CONTEXT_LIMIT = int(os.environ.get('LLM_CONTEXT_LIMIT', '32000'))
    
    @classmethod
    def is_enabled(cls) -> bool:
        """检查 ChatOCR 功能是否启用"""
        return cls.ENABLE_CHATOCR
    
    @classmethod
    def get_config_dict(cls) -> dict:
        """获取配置字典（用于调试）"""
        return {
            'ollama_base_url': cls.OLLAMA_BASE_URL,
            'ollama_model': cls.OLLAMA_MODEL,
            'ollama_timeout': cls.OLLAMA_TIMEOUT,
            'llm_max_tokens': cls.LLM_MAX_TOKENS,
            'llm_temperature': cls.LLM_TEMPERATURE,
            'enable_chatocr': cls.ENABLE_CHATOCR,
            'enable_rag': cls.ENABLE_RAG,
            'embedding_model': cls.EMBEDDING_MODEL,
            'vector_db_path': cls.VECTOR_DB_PATH,
            'chunk_size': cls.CHUNK_SIZE,
            'chunk_overlap': cls.CHUNK_OVERLAP,
            'rag_top_k': cls.RAG_TOP_K,
            'llm_context_limit': cls.LLM_CONTEXT_LIMIT
        }