"""
Ollama LLM Service - PP-ChatOCRv4 智能文档理解
封装与 Ollama 本地 LLM 服务的通信
"""
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)


class LLMStatus(Enum):
    """LLM 服务状态"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class LLMResponse:
    """LLM 响应数据类"""
    success: bool
    content: str
    model: str
    status: LLMStatus
    processing_time: float
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "model": self.model,
            "status": self.status.value,
            "processing_time": self.processing_time,
            "error_message": self.error_message
        }


class OllamaLLMService:
    """
    Ollama LLM 服务封装
    
    提供与本地 Ollama 服务的通信能力，支持：
    - 健康检查
    - 聊天/生成
    - 模型列表获取
    - 超时和错误处理
    - 优雅降级
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "gpt-oss:20b",
        timeout: int = 60,
        max_retries: int = 2,
        retry_delay: float = 1.0
    ):
        """
        初始化 Ollama LLM 服务
        
        Args:
            base_url: Ollama 服务地址
            model_name: 默认使用的模型名称
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._last_health_check: Optional[float] = None
        self._is_healthy: bool = False
        
        logger.info(f"OllamaLLMService initialized: {self.base_url}, model={self.model_name}")
    
    def check_health(self, force: bool = False) -> bool:
        """
        检查 Ollama 服务是否可用
        
        Args:
            force: 是否强制检查（忽略缓存）
            
        Returns:
            bool: 服务是否可用
        """
        # 缓存健康检查结果 30 秒
        if not force and self._last_health_check:
            if time.time() - self._last_health_check < 30:
                return self._is_healthy
        
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            self._is_healthy = response.status_code == 200
            self._last_health_check = time.time()
            
            if self._is_healthy:
                logger.debug("Ollama service health check passed")
            else:
                logger.warning(f"Ollama service returned status {response.status_code}")
                
            return self._is_healthy
            
        except ConnectionError:
            logger.warning(f"Cannot connect to Ollama service at {self.base_url}")
            self._is_healthy = False
            self._last_health_check = time.time()
            return False
            
        except Timeout:
            logger.warning("Ollama health check timed out")
            self._is_healthy = False
            self._last_health_check = time.time()
            return False
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            self._is_healthy = False
            self._last_health_check = time.time()
            return False
    
    def get_available_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            models = [model.get("name", "") for model in data.get("models", [])]
            logger.debug(f"Available models: {models}")
            return models
            
        except Exception as e:
            logger.error(f"Failed to get model list: {e}")
            return []
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        stream: bool = False
    ) -> LLMResponse:
        """
        发送聊天请求（使用 chat API）
        
        Args:
            messages: 消息列表 [{"role": "user/assistant/system", "content": "..."}]
            model: 模型名称（可选，默认使用初始化时的模型）
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            stream: 是否流式输出
            
        Returns:
            LLMResponse: 响应对象
        """
        start_time = time.time()
        model = model or self.model_name
        
        # 先检查服务健康状态
        if not self.check_health():
            return LLMResponse(
                success=False,
                content="",
                model=model,
                status=LLMStatus.UNAVAILABLE,
                processing_time=time.time() - start_time,
                error_message="Ollama service is not available"
            )
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        return self._make_request_with_retry(
            endpoint="/api/chat",
            payload=payload,
            model=model,
            start_time=start_time
        )
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
        stream: bool = False
    ) -> LLMResponse:
        """
        发送生成请求（使用 generate API）
        
        Args:
            prompt: 提示文本
            model: 模型名称
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            stream: 是否流式输出
            
        Returns:
            LLMResponse: 响应对象
        """
        start_time = time.time()
        model = model or self.model_name
        
        if not self.check_health():
            return LLMResponse(
                success=False,
                content="",
                model=model,
                status=LLMStatus.UNAVAILABLE,
                processing_time=time.time() - start_time,
                error_message="Ollama service is not available"
            )
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        return self._make_request_with_retry(
            endpoint="/api/generate",
            payload=payload,
            model=model,
            start_time=start_time,
            response_key="response"
        )
    
    def _make_request_with_retry(
        self,
        endpoint: str,
        payload: Dict,
        model: str,
        start_time: float,
        response_key: str = "message"
    ) -> LLMResponse:
        """
        带重试的请求发送
        
        Args:
            endpoint: API 端点
            payload: 请求体
            model: 模型名称
            start_time: 开始时间
            response_key: 响应内容的键名
            
        Returns:
            LLMResponse: 响应对象
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                
                # 提取响应内容
                if response_key == "message":
                    content = data.get("message", {}).get("content", "")
                else:
                    content = data.get(response_key, "")
                
                return LLMResponse(
                    success=True,
                    content=content,
                    model=model,
                    status=LLMStatus.AVAILABLE,
                    processing_time=time.time() - start_time
                )
                
            except Timeout:
                last_error = "Request timed out"
                logger.warning(f"LLM request timed out (attempt {attempt + 1})")
                
            except ConnectionError:
                last_error = "Connection failed"
                logger.warning(f"LLM connection failed (attempt {attempt + 1})")
                # 连接错误时标记服务不健康
                self._is_healthy = False
                
            except RequestException as e:
                last_error = str(e)
                logger.error(f"LLM request failed: {e}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Unexpected error in LLM request: {e}")
        
        # 所有重试都失败
        return LLMResponse(
            success=False,
            content="",
            model=model,
            status=LLMStatus.TIMEOUT if "timed out" in (last_error or "") else LLMStatus.ERROR,
            processing_time=time.time() - start_time,
            error_message=last_error
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取服务状态信息
        
        Returns:
            Dict: 状态信息
        """
        is_healthy = self.check_health()
        models = self.get_available_models() if is_healthy else []
        
        return {
            "available": is_healthy,
            "base_url": self.base_url,
            "model": self.model_name,
            "available_models": models,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }


# 全局单例实例（延迟初始化）
_llm_service_instance: Optional[OllamaLLMService] = None


def get_llm_service() -> OllamaLLMService:
    """
    获取 LLM 服务单例实例
    
    Returns:
        OllamaLLMService: 服务实例
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        # 从配置加载参数
        from backend.config import ChatOCRConfig
        
        _llm_service_instance = OllamaLLMService(
            base_url=ChatOCRConfig.OLLAMA_BASE_URL,
            model_name=ChatOCRConfig.OLLAMA_MODEL,
            timeout=ChatOCRConfig.OLLAMA_TIMEOUT,
            max_retries=ChatOCRConfig.LLM_MAX_RETRIES
        )
    
    return _llm_service_instance


def reset_llm_service():
    """重置 LLM 服务实例（用于测试）"""
    global _llm_service_instance
    _llm_service_instance = None
