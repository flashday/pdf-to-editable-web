"""
LLM Service Unit Tests - Ollama LLM 服务单元测试

测试健康检查功能、超时处理、错误降级
**Validates: Requirements 1.1, 1.2, 1.5**
"""
import pytest
import time
from unittest.mock import patch, Mock, MagicMock
from requests.exceptions import Timeout, ConnectionError, RequestException

from backend.services.llm_service import (
    OllamaLLMService,
    LLMResponse,
    LLMStatus,
    get_llm_service,
    reset_llm_service
)


class TestOllamaLLMServiceHealthCheck:
    """
    健康检查功能测试
    **Validates: Requirements 1.1, 1.2**
    """
    
    @pytest.fixture
    def llm_service(self):
        """创建 LLM 服务实例"""
        return OllamaLLMService(
            base_url="http://localhost:11434",
            model_name="gpt-oss:20b",
            timeout=60
        )
    
    def test_health_check_with_real_ollama(self, llm_service):
        """
        测试真实 Ollama 服务的健康检查
        **Validates: Requirement 1.1** - 系统启动时检测 Ollama 服务是否可用
        """
        # 强制检查，忽略缓存
        result = llm_service.check_health(force=True)
        
        # 如果 Ollama 服务运行中，应返回 True
        # 注意：此测试依赖本地 Ollama 服务
        assert isinstance(result, bool)
        
        if result:
            # 服务可用时，内部状态应正确
            assert llm_service._is_healthy is True
            assert llm_service._last_health_check is not None
    
    def test_health_check_caching(self, llm_service):
        """
        测试健康检查结果缓存（30秒内不重复检查）
        """
        # 第一次检查
        result1 = llm_service.check_health(force=True)
        first_check_time = llm_service._last_health_check
        
        # 第二次检查（应使用缓存）
        result2 = llm_service.check_health(force=False)
        second_check_time = llm_service._last_health_check
        
        # 缓存时间应相同
        assert first_check_time == second_check_time
        assert result1 == result2
    
    def test_health_check_force_refresh(self, llm_service):
        """
        测试强制刷新健康检查
        """
        # 第一次检查
        llm_service.check_health(force=True)
        first_check_time = llm_service._last_health_check
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 强制刷新
        llm_service.check_health(force=True)
        second_check_time = llm_service._last_health_check
        
        # 时间应该更新
        assert second_check_time > first_check_time
    
    @patch('backend.services.llm_service.requests.get')
    def test_health_check_connection_error(self, mock_get, llm_service):
        """
        测试连接错误时的健康检查
        **Validates: Requirement 1.2** - Ollama 服务不可用时记录警告但不影响现有功能
        """
        mock_get.side_effect = ConnectionError("Connection refused")
        
        result = llm_service.check_health(force=True)
        
        assert result is False
        assert llm_service._is_healthy is False
    
    @patch('backend.services.llm_service.requests.get')
    def test_health_check_timeout(self, mock_get, llm_service):
        """
        测试健康检查超时
        """
        mock_get.side_effect = Timeout("Request timed out")
        
        result = llm_service.check_health(force=True)
        
        assert result is False
        assert llm_service._is_healthy is False
    
    @patch('backend.services.llm_service.requests.get')
    def test_health_check_non_200_status(self, mock_get, llm_service):
        """
        测试非 200 状态码的健康检查
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = llm_service.check_health(force=True)
        
        assert result is False


class TestOllamaLLMServiceTimeout:
    """
    超时处理测试
    **Validates: Requirement 1.5**
    """
    
    @pytest.fixture
    def llm_service_short_timeout(self):
        """创建短超时的 LLM 服务实例"""
        return OllamaLLMService(
            base_url="http://localhost:11434",
            model_name="gpt-oss:20b",
            timeout=2,  # 2秒超时用于测试
            max_retries=0  # 不重试
        )
    
    @patch('backend.services.llm_service.requests.post')
    def test_chat_timeout_returns_timeout_status(self, mock_post, llm_service_short_timeout):
        """
        测试聊天请求超时返回正确状态
        **Validates: Requirement 1.5** - LLM 调用超时时返回超时错误
        """
        # 模拟健康检查通过
        with patch.object(llm_service_short_timeout, 'check_health', return_value=True):
            mock_post.side_effect = Timeout("Request timed out")
            
            response = llm_service_short_timeout.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert response.success is False
            assert response.status == LLMStatus.TIMEOUT
            assert "timed out" in response.error_message.lower()
    
    @patch('backend.services.llm_service.requests.post')
    def test_generate_timeout_returns_timeout_status(self, mock_post, llm_service_short_timeout):
        """
        测试生成请求超时返回正确状态
        """
        with patch.object(llm_service_short_timeout, 'check_health', return_value=True):
            mock_post.side_effect = Timeout("Request timed out")
            
            response = llm_service_short_timeout.generate(prompt="Hello")
            
            assert response.success is False
            assert response.status == LLMStatus.TIMEOUT
    
    def test_timeout_configuration(self):
        """
        测试超时配置正确设置
        """
        service = OllamaLLMService(timeout=60)
        assert service.timeout == 60
        
        service2 = OllamaLLMService(timeout=120)
        assert service2.timeout == 120
    
    @patch('backend.services.llm_service.requests.post')
    def test_timeout_includes_processing_time(self, mock_post, llm_service_short_timeout):
        """
        测试超时响应包含处理时间
        """
        with patch.object(llm_service_short_timeout, 'check_health', return_value=True):
            mock_post.side_effect = Timeout("Request timed out")
            
            response = llm_service_short_timeout.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert response.processing_time >= 0


class TestOllamaLLMServiceErrorDegradation:
    """
    错误降级测试
    **Validates: Requirements 1.2, 8.1, 8.2**
    """
    
    @pytest.fixture
    def llm_service(self):
        """创建 LLM 服务实例"""
        return OllamaLLMService(
            base_url="http://localhost:11434",
            model_name="gpt-oss:20b",
            timeout=60,
            max_retries=2,
            retry_delay=0.1  # 快速重试用于测试
        )
    
    def test_chat_when_service_unavailable(self, llm_service):
        """
        测试服务不可用时的聊天请求降级
        **Validates: Requirement 1.2** - 不影响现有 OCR 功能
        """
        with patch.object(llm_service, 'check_health', return_value=False):
            response = llm_service.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert response.success is False
            assert response.status == LLMStatus.UNAVAILABLE
            assert "not available" in response.error_message.lower()
    
    def test_generate_when_service_unavailable(self, llm_service):
        """
        测试服务不可用时的生成请求降级
        """
        with patch.object(llm_service, 'check_health', return_value=False):
            response = llm_service.generate(prompt="Hello")
            
            assert response.success is False
            assert response.status == LLMStatus.UNAVAILABLE
    
    @patch('backend.services.llm_service.requests.post')
    def test_retry_on_connection_error(self, mock_post, llm_service):
        """
        测试连接错误时的重试逻辑
        """
        with patch.object(llm_service, 'check_health', return_value=True):
            # 前两次失败，第三次成功
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {"content": "Hello response"}
            }
            
            mock_post.side_effect = [
                ConnectionError("Connection failed"),
                ConnectionError("Connection failed"),
                mock_response
            ]
            
            response = llm_service.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            # 应该在第三次成功
            assert response.success is True
            assert mock_post.call_count == 3
    
    @patch('backend.services.llm_service.requests.post')
    def test_all_retries_exhausted(self, mock_post, llm_service):
        """
        测试所有重试都失败的情况
        """
        with patch.object(llm_service, 'check_health', return_value=True):
            mock_post.side_effect = ConnectionError("Connection failed")
            
            response = llm_service.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert response.success is False
            assert response.status == LLMStatus.ERROR
            # 应该尝试 max_retries + 1 次
            assert mock_post.call_count == llm_service.max_retries + 1
    
    @patch('backend.services.llm_service.requests.post')
    def test_request_exception_handling(self, mock_post, llm_service):
        """
        测试通用请求异常处理
        """
        with patch.object(llm_service, 'check_health', return_value=True):
            mock_post.side_effect = RequestException("Unknown error")
            
            response = llm_service.chat(
                messages=[{"role": "user", "content": "Hello"}]
            )
            
            assert response.success is False
            assert response.error_message is not None
    
    def test_get_status_when_unavailable(self, llm_service):
        """
        测试服务不可用时获取状态
        """
        with patch.object(llm_service, 'check_health', return_value=False):
            status = llm_service.get_status()
            
            assert status['available'] is False
            assert status['model'] == llm_service.model_name
            assert status['base_url'] == llm_service.base_url


class TestLLMResponse:
    """
    LLM 响应数据类测试
    """
    
    def test_response_to_dict_success(self):
        """测试成功响应转换为字典"""
        response = LLMResponse(
            success=True,
            content="Hello, world!",
            model="gpt-oss:20b",
            status=LLMStatus.AVAILABLE,
            processing_time=1.5
        )
        
        data = response.to_dict()
        
        assert data['success'] is True
        assert data['content'] == "Hello, world!"
        assert data['model'] == "gpt-oss:20b"
        assert data['status'] == "available"
        assert data['processing_time'] == 1.5
        assert data['error_message'] is None
    
    def test_response_to_dict_error(self):
        """测试错误响应转换为字典"""
        response = LLMResponse(
            success=False,
            content="",
            model="gpt-oss:20b",
            status=LLMStatus.ERROR,
            processing_time=0.5,
            error_message="Connection failed"
        )
        
        data = response.to_dict()
        
        assert data['success'] is False
        assert data['status'] == "error"
        assert data['error_message'] == "Connection failed"


class TestGetLLMServiceSingleton:
    """
    LLM 服务单例测试
    """
    
    def teardown_method(self):
        """每个测试后重置单例"""
        reset_llm_service()
    
    def test_get_llm_service_returns_instance(self):
        """测试获取 LLM 服务实例"""
        service = get_llm_service()
        
        assert service is not None
        assert isinstance(service, OllamaLLMService)
    
    def test_get_llm_service_returns_same_instance(self):
        """测试单例模式返回相同实例"""
        service1 = get_llm_service()
        service2 = get_llm_service()
        
        assert service1 is service2
    
    def test_reset_llm_service(self):
        """测试重置 LLM 服务"""
        service1 = get_llm_service()
        reset_llm_service()
        service2 = get_llm_service()
        
        assert service1 is not service2


class TestRealOllamaIntegration:
    """
    真实 Ollama 服务集成测试
    注意：这些测试需要本地运行 Ollama 服务
    """
    
    @pytest.fixture
    def real_llm_service(self):
        """创建连接真实 Ollama 的服务实例"""
        return OllamaLLMService(
            base_url="http://localhost:11434",
            model_name="gpt-oss:20b",
            timeout=60
        )
    
    @pytest.mark.skipif(
        not OllamaLLMService().check_health(force=True),
        reason="Ollama service not available"
    )
    def test_real_health_check(self, real_llm_service):
        """
        测试真实 Ollama 服务健康检查
        **Validates: Requirement 1.1**
        """
        result = real_llm_service.check_health(force=True)
        assert result is True
    
    @pytest.mark.skipif(
        not OllamaLLMService().check_health(force=True),
        reason="Ollama service not available"
    )
    def test_real_get_available_models(self, real_llm_service):
        """
        测试获取真实可用模型列表
        **Validates: Requirement 1.3**
        """
        models = real_llm_service.get_available_models()
        
        assert isinstance(models, list)
        # 应该至少有 gpt-oss:20b 模型
        assert any('gpt-oss' in model for model in models)
    
    @pytest.mark.skipif(
        not OllamaLLMService().check_health(force=True),
        reason="Ollama service not available"
    )
    def test_real_get_status(self, real_llm_service):
        """
        测试获取真实服务状态
        """
        status = real_llm_service.get_status()
        
        assert status['available'] is True
        assert 'gpt-oss' in status['model']
        assert len(status['available_models']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
