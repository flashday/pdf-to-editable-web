"""
ChatOCR API Routes - 智能文档理解 API 接口

提供关键信息提取、文档问答、LLM 状态检查和模板管理接口
"""
import logging
from flask import Blueprint, request, jsonify

from backend.services.chatocr_service import get_chatocr_service
from backend.config import ChatOCRConfig

logger = logging.getLogger(__name__)

# 创建蓝图
chatocr_bp = Blueprint('chatocr', __name__, url_prefix='/api')


def _error_response(message: str, status_code: int = 400, error_code: str = None):
    """生成标准错误响应"""
    response = {
        "success": False,
        "error": message
    }
    if error_code:
        response["error_code"] = error_code
    return jsonify(response), status_code


def _success_response(data: dict):
    """生成标准成功响应"""
    return jsonify({
        "success": True,
        "data": data
    })


@chatocr_bp.route('/llm/status', methods=['GET'])
def get_llm_status():
    """
    GET /api/llm/status
    检查 LLM 服务状态
    
    响应:
    {
        "success": true,
        "data": {
            "available": true,
            "llm_available": true,
            "rag_available": true,
            "model": "gpt-oss:20b",
            "base_url": "http://localhost:11434",
            "chatocr_enabled": true,
            "rag_enabled": true
        }
    }
    """
    try:
        service = get_chatocr_service()
        
        if not service:
            return _success_response({
                "available": False,
                "llm_available": False,
                "rag_available": False,
                "model": ChatOCRConfig.OLLAMA_MODEL,
                "base_url": ChatOCRConfig.OLLAMA_BASE_URL,
                "chatocr_enabled": False,
                "rag_enabled": ChatOCRConfig.ENABLE_RAG,
                "message": "ChatOCR 功能未启用"
            })
        
        status = service.check_available()
        return _success_response(status)
        
    except Exception as e:
        logger.error(f"Failed to check LLM status: {e}")
        return _error_response(f"检查 LLM 状态失败: {str(e)}", 500)


@chatocr_bp.route('/templates', methods=['GET'])
def get_templates():
    """
    GET /api/templates
    获取预设提取模板列表
    
    响应:
    {
        "success": true,
        "data": {
            "templates": {
                "invoice": {"name": "发票", "name_en": "Invoice", "fields": [...]},
                "contract": {"name": "合同", "name_en": "Contract", "fields": [...]},
                ...
            }
        }
    }
    """
    try:
        service = get_chatocr_service()
        
        if not service:
            return _error_response("ChatOCR 功能未启用", 503, "SERVICE_DISABLED")
        
        templates = service.get_templates()
        return _success_response({"templates": templates})
        
    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        return _error_response(f"获取模板失败: {str(e)}", 500)


@chatocr_bp.route('/extract-info', methods=['POST'])
def extract_info():
    """
    POST /api/extract-info
    从文档中提取关键信息
    
    请求体:
    {
        "job_id": "xxx",
        "fields": ["发票号", "金额", "日期"],  // 可选，自定义字段
        "template": "invoice"  // 可选，使用预设模板
    }
    
    响应:
    {
        "success": true,
        "data": {
            "job_id": "xxx",
            "fields": {"发票号": "12345678", "金额": "1,234.56", "日期": "2026-01-25"},
            "confidence": 0.95,
            "warnings": [],
            "processing_time": 2.3
        }
    }
    """
    try:
        # 检查服务是否可用
        service = get_chatocr_service()
        if not service:
            return _error_response("ChatOCR 功能未启用", 503, "SERVICE_DISABLED")
        
        # 解析请求
        data = request.get_json()
        if not data:
            return _error_response("请求体不能为空", 400, "INVALID_REQUEST")
        
        job_id = data.get('job_id')
        if not job_id:
            return _error_response("job_id 不能为空", 400, "MISSING_JOB_ID")
        
        fields = data.get('fields')
        template = data.get('template')
        
        # 验证参数
        if not fields and not template:
            return _error_response("请指定 fields 或 template", 400, "MISSING_FIELDS")
        
        if template and template not in service.templates:
            available_templates = list(service.templates.keys())
            return _error_response(
                f"未知的模板: {template}，可用模板: {available_templates}",
                400,
                "INVALID_TEMPLATE"
            )
        
        # 执行提取
        result = service.extract_info(job_id, fields, template)
        
        if result.success:
            return _success_response(result.to_dict())
        else:
            return _error_response(
                result.error or "提取失败",
                500 if "服务" in (result.error or "") else 400,
                "EXTRACTION_FAILED"
            )
        
    except Exception as e:
        logger.error(f"Extract info failed: {e}")
        return _error_response(f"信息提取失败: {str(e)}", 500)


@chatocr_bp.route('/document-qa', methods=['POST'])
def document_qa():
    """
    POST /api/document-qa
    基于文档内容回答问题
    
    请求体:
    {
        "job_id": "xxx",
        "question": "这份文档的总金额是多少？"
    }
    
    响应:
    {
        "success": true,
        "data": {
            "job_id": "xxx",
            "question": "这份文档的总金额是多少？",
            "answer": "根据文档内容，总金额为 1,234.56 元。",
            "references": ["金额合计：1,234.56"],
            "confidence": 0.9,
            "processing_time": 1.5
        }
    }
    """
    try:
        # 检查服务是否可用
        service = get_chatocr_service()
        if not service:
            return _error_response("ChatOCR 功能未启用", 503, "SERVICE_DISABLED")
        
        # 解析请求
        data = request.get_json()
        if not data:
            return _error_response("请求体不能为空", 400, "INVALID_REQUEST")
        
        job_id = data.get('job_id')
        if not job_id:
            return _error_response("job_id 不能为空", 400, "MISSING_JOB_ID")
        
        question = data.get('question')
        if not question or not question.strip():
            return _error_response("question 不能为空", 400, "MISSING_QUESTION")
        
        # 执行问答
        result = service.document_qa(job_id, question.strip())
        
        if result.success:
            return _success_response(result.to_dict())
        else:
            return _error_response(
                result.error or "问答失败",
                500 if "服务" in (result.error or "") else 400,
                "QA_FAILED"
            )
        
    except Exception as e:
        logger.error(f"Document QA failed: {e}")
        return _error_response(f"文档问答失败: {str(e)}", 500)


@chatocr_bp.route('/rag/status/<job_id>', methods=['GET'])
def get_rag_status(job_id: str):
    """
    GET /api/rag/status/<job_id>
    获取文档的 RAG 索引状态
    
    响应:
    {
        "success": true,
        "data": {
            "indexed": true,
            "chunk_count": 15,
            "index_time": 1.2
        }
    }
    """
    try:
        service = get_chatocr_service()
        if not service:
            return _error_response("ChatOCR 功能未启用", 503, "SERVICE_DISABLED")
        
        if not service.rag_service:
            return _success_response({
                "indexed": False,
                "message": "RAG 功能未启用"
            })
        
        status = service.rag_service.get_index_status(job_id)
        return _success_response(status.to_dict())
        
    except Exception as e:
        logger.error(f"Failed to get RAG status for {job_id}: {e}")
        return _error_response(f"获取 RAG 状态失败: {str(e)}", 500)
