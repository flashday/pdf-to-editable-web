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
        # 先检查服务是否正在加载中（避免在加载过程中触发初始化）
        from backend.app import get_service_status
        service_status = get_service_status()
        
        # 如果 RAG 正在加载中，返回加载中状态
        if service_status['rag']['loading']:
            return _success_response({
                "available": False,
                "llm_available": service_status['llm']['loaded'],
                "rag_available": False,
                "model": ChatOCRConfig.OLLAMA_MODEL,
                "base_url": ChatOCRConfig.OLLAMA_BASE_URL,
                "chatocr_enabled": ChatOCRConfig.ENABLE_CHATOCR,
                "rag_enabled": ChatOCRConfig.ENABLE_RAG,
                "message": "RAG 服务正在加载中..."
            })
        
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


@chatocr_bp.route('/llm/extract', methods=['POST'])
def llm_extract():
    """
    POST /api/llm/extract
    使用 LLM 从文本中提取指定字段
    
    请求体:
    {
        "text": "文档全文内容...",
        "fields": ["字段1", "字段2", ...],
        "template": "发票"  // 可选，模板名称
    }
    
    响应:
    {
        "success": true,
        "data": {
            "字段1": "值1",
            "字段2": "值2",
            ...
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
        
        text = data.get('text', '')
        fields = data.get('fields', [])
        template_name = data.get('template', '自定义')
        
        if not text:
            return _error_response("text 不能为空", 400, "MISSING_TEXT")
        
        if not fields or len(fields) == 0:
            return _error_response("fields 不能为空", 400, "MISSING_FIELDS")
        
        # 构建提取 prompt
        fields_str = '\n'.join([f"- {field}" for field in fields])
        prompt = f"""你是一个专业的文档信息提取助手。请仔细阅读以下文档内容，并提取指定字段的值。

【文档内容】
{text[:8000]}

【需要提取的字段】
{fields_str}

【提取规则】
1. 仔细阅读文档，找出与每个字段相关的信息
2. 如果文档中明确包含某字段的值，请准确提取
3. 如果文档中没有某字段的信息，请将该字段的值设为 "未找到"
4. 对于金额类字段，请保留原始格式（包括货币符号和小数）
5. 对于日期类字段，请保留原始格式

【输出格式】
请严格按照以下 JSON 格式返回，不要添加任何其他内容：
{{
{', '.join([f'  "{field}": "提取的值或未找到"' for field in fields])}
}}

请直接输出 JSON，不要有任何解释或前缀。"""

        # 调用 LLM
        logger.info(f"Calling LLM for extraction with {len(fields)} fields, text length: {len(text)}")
        result = service.llm_service.generate(prompt)
        
        # LLMResponse 是对象，不是字典
        if not result or not result.success:
            logger.error(f"LLM call failed: {result.error_message if result else 'No result'}")
            return _error_response(
                result.error_message if result else 'LLM 调用失败',
                500,
                "LLM_ERROR"
            )
        
        # 解析 LLM 返回的 JSON
        response_text = result.content or '{}'
        
        # 尝试提取 JSON 部分
        import json
        import re
        
        logger.info(f"LLM response for extraction (first 1000 chars): {response_text[:1000]}")
        
        extracted_data = None
        
        # 方法1: 尝试直接解析整个响应
        try:
            extracted_data = json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # 方法2: 尝试找到 JSON 代码块 (```json ... ```)
        if extracted_data is None:
            json_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if json_block_match:
                try:
                    extracted_data = json.loads(json_block_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        # 方法3: 尝试找到最外层的 JSON 对象（支持嵌套）
        if extracted_data is None:
            # 找到第一个 { 和最后一个 }
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_str = response_text[first_brace:last_brace + 1]
                try:
                    extracted_data = json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        # 方法4: 如果所有方法都失败，返回原始响应
        if extracted_data is None:
            logger.warning(f"Failed to parse JSON from LLM response, returning raw text")
            extracted_data = {fields[0]: response_text} if fields else {"raw_response": response_text}
        
        logger.info(f"Extraction result: {extracted_data}")
        return _success_response(extracted_data)
        
    except Exception as e:
        logger.error(f"LLM extract failed: {e}")
        return _error_response(f"信息提取失败: {str(e)}", 500)


@chatocr_bp.route('/llm/qa', methods=['POST'])
def llm_qa():
    """
    POST /api/llm/qa
    使用 LLM 回答关于文档的问题
    
    请求体:
    {
        "question": "问题内容",
        "context": "文档上下文",
        "job_id": "xxx"  // 可选
    }
    
    响应:
    {
        "success": true,
        "data": {
            "answer": "回答内容",
            "confidence": 0.85
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
        
        question = data.get('question', '')
        context = data.get('context', '')
        job_id = data.get('job_id')
        
        if not question:
            return _error_response("question 不能为空", 400, "MISSING_QUESTION")
        
        # 如果有 job_id，尝试从缓存获取文档内容
        if job_id and not context:
            from backend.services.job_cache import job_cache
            job_data = job_cache.get_job(job_id)
            if job_data and job_data.get('result'):
                blocks = job_data['result'].get('blocks', [])
                context = '\n'.join([
                    block.get('data', {}).get('text', '') 
                    for block in blocks 
                    if block.get('data', {}).get('text')
                ])
        
        if not context:
            return _error_response("context 不能为空", 400, "MISSING_CONTEXT")
        
        # 构建问答 prompt
        prompt = f"""你是一个专业的文档分析助手。请根据以下文档内容回答用户的问题。

【文档内容】
{context[:8000]}

【用户问题】
{question}

【回答要求】
1. 请直接、准确地回答问题
2. 如果文档中包含相关信息，请引用具体内容
3. 如果文档中没有相关信息，请明确说明"文档中未找到相关信息"
4. 回答要简洁明了，不要添加不必要的解释

请直接回答："""

        # 调用 LLM
        result = service.llm_service.generate(prompt)
        
        # LLMResponse 是对象，不是字典
        if not result or not result.success:
            return _error_response(
                result.error_message if result else 'LLM 调用失败',
                500,
                "LLM_ERROR"
            )
        
        answer = result.content or '无法回答'
        
        # 简单的置信度估算
        confidence = 0.8
        if '未找到' in answer or '没有' in answer or '不确定' in answer:
            confidence = 0.3
        elif len(answer) > 50:
            confidence = 0.9
        
        return _success_response({
            "answer": answer,
            "confidence": confidence
        })
        
    except Exception as e:
        logger.error(f"LLM QA failed: {e}")
        return _error_response(f"问答失败: {str(e)}", 500)


@chatocr_bp.route('/checkpoint-config', methods=['GET'])
def get_checkpoint_config():
    """
    GET /api/checkpoint-config
    获取检查点配置
    
    响应:
    {
        "success": true,
        "checkpoints": [
            {"question": "文档中的主要金额是多少？"},
            {"question": "文档的日期是什么？"},
            ...
        ]
    }
    """
    try:
        # 尝试从配置文件加载
        import os
        import json
        
        # 从项目根目录查找配置文件
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, 'config', 'checkpoint_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return jsonify({
                    "success": True,
                    "checkpoints": config.get('checkpoints', [])
                })
        
        # 默认检查点
        default_checkpoints = [
            {"question": "文档中的主要金额是多少？"},
            {"question": "文档的日期是什么？"},
            {"question": "文档涉及的主要当事方有哪些？"}
        ]
        
        return jsonify({
            "success": True,
            "checkpoints": default_checkpoints
        })
        
    except Exception as e:
        logger.error(f"Failed to get checkpoint config: {e}")
        return _error_response(f"获取检查点配置失败: {str(e)}", 500)


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


@chatocr_bp.route('/llm-log/<job_id>', methods=['GET'])
def get_llm_log(job_id: str):
    """
    GET /api/llm-log/<job_id>
    获取指定 Job 的 LLM 调用日志
    
    参数:
    - summary: 是否只返回摘要（不包含完整 prompt/response），默认 false
    
    响应:
    {
        "success": true,
        "data": {
            "job_id": "xxx",
            "created_at": "2026-01-27T10:00:00",
            "total_calls": 5,
            "successful_calls": 4,
            "failed_calls": 1,
            "total_processing_time": 12.5,
            "calls": [...]
        }
    }
    """
    try:
        from backend.services.llm_logger import get_llm_logger
        
        llm_logger = get_llm_logger()
        summary_only = request.args.get('summary', 'false').lower() == 'true'
        
        if summary_only:
            log_data = llm_logger.get_log_summary(job_id)
        else:
            log_data = llm_logger.get_log(job_id)
        
        if not log_data:
            return _error_response(f"未找到 Job {job_id} 的 LLM 日志", 404, "LOG_NOT_FOUND")
        
        return _success_response(log_data)
        
    except Exception as e:
        logger.error(f"Failed to get LLM log for {job_id}: {e}")
        return _error_response(f"获取 LLM 日志失败: {str(e)}", 500)
