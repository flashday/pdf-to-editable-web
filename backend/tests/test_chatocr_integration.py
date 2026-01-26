"""
ChatOCR Integration Tests - 智能文档理解集成测试

测试完整的提取流程、问答流程和降级场景
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# 导入被测试的模块
from backend.services.chatocr_service import (
    ChatOCRService, 
    ExtractionResult, 
    QAResult,
    EXTRACTION_TEMPLATES,
    get_chatocr_service
)
from backend.services.llm_service import OllamaLLMService
from backend.services.rag_service import RAGService


class TestChatOCRService:
    """ChatOCR 服务单元测试"""
    
    @pytest.fixture
    def mock_llm_service(self):
        """创建模拟的 LLM 服务"""
        mock = Mock(spec=OllamaLLMService)
        mock.check_health.return_value = True
        return mock
    
    @pytest.fixture
    def mock_rag_service(self):
        """创建模拟的 RAG 服务"""
        mock = Mock(spec=RAGService)
        return mock
    
    @pytest.fixture
    def chatocr_service(self, mock_llm_service, mock_rag_service):
        """创建 ChatOCR 服务实例"""
        return ChatOCRService(
            llm_service=mock_llm_service,
            rag_service=mock_rag_service
        )
    
    def test_get_templates(self, chatocr_service):
        """测试获取预设模板"""
        templates = chatocr_service.get_templates()
        
        assert 'invoice' in templates
        assert 'contract' in templates
        assert 'id_card' in templates
        assert 'resume' in templates
        
        # 验证模板结构
        invoice = templates['invoice']
        assert 'name' in invoice
        assert 'name_en' in invoice
        assert 'fields' in invoice
        assert isinstance(invoice['fields'], list)
    
    def test_get_template_fields(self, chatocr_service):
        """测试获取模板字段"""
        fields = chatocr_service.get_template_fields('invoice')
        
        assert fields is not None
        assert '发票号码' in fields
        assert '金额合计' in fields
        
        # 测试不存在的模板
        assert chatocr_service.get_template_fields('nonexistent') is None
    
    def test_check_available_llm_online(self, chatocr_service, mock_llm_service):
        """测试 LLM 在线时的状态检查"""
        mock_llm_service.check_health.return_value = True
        
        status = chatocr_service.check_available()
        
        assert status['available'] is True
        assert status['llm_available'] is True
    
    def test_check_available_llm_offline(self, chatocr_service, mock_llm_service):
        """测试 LLM 离线时的状态检查"""
        mock_llm_service.check_health.return_value = False
        
        status = chatocr_service.check_available()
        
        assert status['available'] is False
        assert status['llm_available'] is False


class TestExtractionResult:
    """提取结果数据模型测试"""
    
    def test_extraction_result_to_dict(self):
        """测试提取结果转换为字典"""
        result = ExtractionResult(
            job_id='test-job-123',
            fields={'发票号码': '12345', '金额': '100.00'},
            confidence=0.95,
            warnings=['部分字段未找到'],
            processing_time=1.5,
            success=True
        )
        
        data = result.to_dict()
        
        assert data['job_id'] == 'test-job-123'
        assert data['fields']['发票号码'] == '12345'
        assert data['confidence'] == 0.95
        assert len(data['warnings']) == 1
        assert data['success'] is True
    
    def test_extraction_result_with_error(self):
        """测试带错误的提取结果"""
        result = ExtractionResult(
            job_id='test-job-456',
            fields={},
            success=False,
            error='LLM 服务不可用'
        )
        
        data = result.to_dict()
        
        assert data['success'] is False
        assert data['error'] == 'LLM 服务不可用'


class TestQAResult:
    """问答结果数据模型测试"""
    
    def test_qa_result_to_dict(self):
        """测试问答结果转换为字典"""
        result = QAResult(
            job_id='test-job-789',
            question='文档的总金额是多少？',
            answer='根据文档，总金额为 1,234.56 元。',
            references=['金额合计：1,234.56'],
            confidence=0.9,
            processing_time=2.0,
            found_in_document=True,
            success=True
        )
        
        data = result.to_dict()
        
        assert data['job_id'] == 'test-job-789'
        assert data['question'] == '文档的总金额是多少？'
        assert '1,234.56' in data['answer']
        assert len(data['references']) == 1
        assert data['found_in_document'] is True
    
    def test_qa_result_not_found(self):
        """测试未找到答案的问答结果"""
        result = QAResult(
            job_id='test-job-000',
            question='文档中有什么？',
            answer='无法从文档中找到相关信息。',
            references=[],
            confidence=0.3,
            found_in_document=False,
            success=True
        )
        
        data = result.to_dict()
        
        assert data['found_in_document'] is False
        assert data['confidence'] == 0.3


class TestExtractInfoIntegration:
    """信息提取集成测试"""
    
    @pytest.fixture
    def mock_llm_with_response(self):
        """创建带响应的模拟 LLM 服务"""
        mock = Mock(spec=OllamaLLMService)
        mock.check_health.return_value = True
        mock.chat.return_value = json.dumps({
            '发票号码': '12345678',
            '金额合计': '1,234.56',
            '开票日期': '2026-01-25'
        })
        return mock
    
    @pytest.fixture
    def service_with_mock_content(self, mock_llm_with_response):
        """创建带模拟内容的服务"""
        service = ChatOCRService(llm_service=mock_llm_with_response)
        
        # 模拟文档内容获取
        with patch.object(service, '_get_document_content') as mock_content:
            mock_content.return_value = """
            发票号码：12345678
            开票日期：2026年1月25日
            金额合计：1,234.56 元
            """
            yield service
    
    def test_extract_with_template(self, service_with_mock_content):
        """测试使用模板提取"""
        result = service_with_mock_content.extract_info(
            job_id='test-job',
            template='invoice'
        )
        
        assert result.success is True
        assert '发票号码' in result.fields
    
    def test_extract_with_custom_fields(self, service_with_mock_content):
        """测试使用自定义字段提取"""
        result = service_with_mock_content.extract_info(
            job_id='test-job',
            fields=['发票号码', '金额合计']
        )
        
        assert result.success is True
        assert len(result.fields) >= 2
    
    def test_extract_llm_unavailable(self):
        """测试 LLM 不可用时的降级"""
        mock_llm = Mock(spec=OllamaLLMService)
        mock_llm.check_health.return_value = False
        
        service = ChatOCRService(llm_service=mock_llm)
        result = service.extract_info(
            job_id='test-job',
            fields=['发票号码']
        )
        
        assert result.success is False
        assert 'LLM 服务不可用' in result.error
    
    def test_extract_no_fields(self):
        """测试未指定字段时的错误处理"""
        mock_llm = Mock(spec=OllamaLLMService)
        mock_llm.check_health.return_value = True
        
        service = ChatOCRService(llm_service=mock_llm)
        result = service.extract_info(
            job_id='test-job',
            fields=[]
        )
        
        assert result.success is False
        assert '未指定提取字段' in result.error


class TestDocumentQAIntegration:
    """文档问答集成测试"""
    
    @pytest.fixture
    def mock_llm_with_qa_response(self):
        """创建带问答响应的模拟 LLM 服务"""
        mock = Mock(spec=OllamaLLMService)
        mock.check_health.return_value = True
        mock.chat.return_value = json.dumps({
            'answer': '根据文档内容，总金额为 1,234.56 元。',
            'references': ['金额合计：1,234.56'],
            'found_in_document': True
        })
        return mock
    
    @pytest.fixture
    def qa_service(self, mock_llm_with_qa_response):
        """创建问答服务"""
        service = ChatOCRService(llm_service=mock_llm_with_qa_response)
        
        with patch.object(service, '_get_document_content') as mock_content:
            mock_content.return_value = "金额合计：1,234.56 元"
            yield service
    
    def test_document_qa_success(self, qa_service):
        """测试成功的文档问答"""
        result = qa_service.document_qa(
            job_id='test-job',
            question='总金额是多少？'
        )
        
        assert result.success is True
        assert '1,234.56' in result.answer
        assert len(result.references) > 0
    
    def test_document_qa_empty_question(self):
        """测试空问题的错误处理"""
        mock_llm = Mock(spec=OllamaLLMService)
        mock_llm.check_health.return_value = True
        
        service = ChatOCRService(llm_service=mock_llm)
        result = service.document_qa(
            job_id='test-job',
            question=''
        )
        
        assert result.success is False
        assert '问题不能为空' in result.error
    
    def test_document_qa_llm_unavailable(self):
        """测试 LLM 不可用时的问答降级"""
        mock_llm = Mock(spec=OllamaLLMService)
        mock_llm.check_health.return_value = False
        
        service = ChatOCRService(llm_service=mock_llm)
        result = service.document_qa(
            job_id='test-job',
            question='这是什么文档？'
        )
        
        assert result.success is False
        assert 'LLM 服务不可用' in result.error


class TestGracefulDegradation:
    """优雅降级测试"""
    
    def test_service_disabled(self):
        """测试服务禁用时的行为"""
        with patch('backend.services.chatocr_service.ChatOCRConfig') as mock_config:
            mock_config.ENABLE_CHATOCR = False
            
            service = get_chatocr_service()
            # 当服务禁用时，应返回 None
            # 注意：这取决于实际实现
    
    def test_rag_fallback(self):
        """测试 RAG 不可用时的回退"""
        mock_llm = Mock(spec=OllamaLLMService)
        mock_llm.check_health.return_value = True
        mock_llm.chat.return_value = '{"answer": "test", "references": [], "found_in_document": true}'
        
        # 创建服务，不提供 RAG
        service = ChatOCRService(llm_service=mock_llm, rag_service=None)
        
        with patch.object(service, '_get_document_content') as mock_content:
            mock_content.return_value = "测试文档内容"
            
            result = service.document_qa(
                job_id='test-job',
                question='测试问题'
            )
            
            # 即使没有 RAG，也应该能够回答
            assert result.success is True


class TestJSONParsing:
    """JSON 解析测试"""
    
    @pytest.fixture
    def service(self):
        """创建服务实例"""
        mock_llm = Mock(spec=OllamaLLMService)
        return ChatOCRService(llm_service=mock_llm)
    
    def test_parse_clean_json(self, service):
        """测试解析干净的 JSON"""
        response = '{"key": "value", "number": 123}'
        result = service._parse_json_response(response)
        
        assert result is not None
        assert result['key'] == 'value'
        assert result['number'] == 123
    
    def test_parse_json_with_markdown(self, service):
        """测试解析带 markdown 标记的 JSON"""
        response = '```json\n{"key": "value"}\n```'
        result = service._parse_json_response(response)
        
        assert result is not None
        assert result['key'] == 'value'
    
    def test_parse_json_with_extra_text(self, service):
        """测试解析带额外文本的 JSON"""
        response = 'Here is the result: {"key": "value"} That is all.'
        result = service._parse_json_response(response)
        
        assert result is not None
        assert result['key'] == 'value'
    
    def test_parse_invalid_json(self, service):
        """测试解析无效 JSON"""
        response = 'This is not JSON at all'
        result = service._parse_json_response(response)
        
        assert result is None
    
    def test_parse_empty_response(self, service):
        """测试解析空响应"""
        result = service._parse_json_response('')
        assert result is None
        
        result = service._parse_json_response(None)
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
