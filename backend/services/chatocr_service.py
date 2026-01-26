"""
ChatOCR Service - PP-ChatOCRv4 智能文档理解服务

整合 LLM 服务和 RAG 服务，提供关键信息提取和文档问答功能
"""
import json
import logging
import time
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from backend.services.llm_service import get_llm_service, OllamaLLMService
from backend.services.rag_service import get_rag_service, RAGService
from backend.services.job_cache import get_job_cache
from backend.config import ChatOCRConfig

logger = logging.getLogger(__name__)


# ============== 预设模板定义 ==============

EXTRACTION_TEMPLATES = {
    "invoice": {
        "name": "发票",
        "name_en": "Invoice",
        "fields": ["发票号码", "发票代码", "开票日期", "金额合计", "税额", "价税合计", "购买方名称", "销售方名称"],
        "prompt_hint": "这是一份发票文档，请仔细识别发票上的各项信息"
    },
    "contract": {
        "name": "合同",
        "name_en": "Contract",
        "fields": ["甲方", "乙方", "合同金额", "签订日期", "合同期限", "合同编号", "违约条款"],
        "prompt_hint": "这是一份合同文档，请提取合同中的关键条款信息"
    },
    "id_card": {
        "name": "身份证",
        "name_en": "ID Card",
        "fields": ["姓名", "性别", "民族", "出生日期", "住址", "身份证号码"],
        "prompt_hint": "这是一份身份证文档，请提取身份证上的个人信息"
    },
    "resume": {
        "name": "简历",
        "name_en": "Resume",
        "fields": ["姓名", "联系电话", "电子邮箱", "教育背景", "工作经历", "技能特长"],
        "prompt_hint": "这是一份个人简历，请提取简历中的关键信息"
    },
    "receipt": {
        "name": "收据",
        "name_en": "Receipt",
        "fields": ["收据编号", "日期", "付款人", "收款人", "金额", "事由"],
        "prompt_hint": "这是一份收据文档，请提取收据上的交易信息"
    },
    "business_license": {
        "name": "营业执照",
        "name_en": "Business License",
        "fields": ["企业名称", "统一社会信用代码", "法定代表人", "注册资本", "成立日期", "营业期限", "经营范围"],
        "prompt_hint": "这是一份营业执照，请提取企业的注册信息"
    }
}


# ============== Prompt 模板 ==============

EXTRACTION_PROMPT = """你是一个专业的文档信息提取助手。请从以下文档内容中提取指定的字段信息。

{prompt_hint}

文档内容：
{document_content}

需要提取的字段：
{fields}

请按照以下 JSON 格式返回结果，不要添加任何其他说明文字：
{{
{field_template}
}}

注意事项：
1. 如果某个字段在文档中找不到，返回 null
2. 保持提取值的原始格式（如日期、金额格式）
3. 只返回 JSON，不要添加 markdown 代码块标记或其他说明
4. 确保 JSON 格式正确，可以被解析"""

QA_PROMPT = """你是一个专业的文档问答助手。请基于以下文档内容回答用户的问题。

文档内容：
{document_content}

用户问题：{question}

请按照以下要求回答：
1. 只基于文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确告知
3. 在回答中引用文档原文作为依据
4. 使用简洁清晰的语言

请按照以下 JSON 格式返回，不要添加任何其他说明文字：
{{
    "answer": "你的回答",
    "references": ["引用的原文片段1", "引用的原文片段2"],
    "found_in_document": true或false
}}

注意：只返回 JSON，不要添加 markdown 代码块标记或其他说明"""


# ============== 数据模型 ==============

@dataclass
class ExtractionResult:
    """提取结果"""
    job_id: str
    fields: Dict[str, Optional[str]]
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "fields": self.fields,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error": self.error
        }


@dataclass
class QAResult:
    """问答结果"""
    job_id: str
    question: str
    answer: str
    references: List[str] = field(default_factory=list)
    confidence: float = 0.0
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error: Optional[str] = None
    found_in_document: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "question": self.question,
            "answer": self.answer,
            "references": self.references,
            "confidence": self.confidence,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error": self.error,
            "found_in_document": self.found_in_document
        }


# ============== ChatOCR 服务 ==============

class ChatOCRService:
    """PP-ChatOCRv4 智能文档理解服务"""
    
    def __init__(
        self,
        llm_service: Optional[OllamaLLMService] = None,
        rag_service: Optional[RAGService] = None
    ):
        """
        初始化 ChatOCR 服务
        
        Args:
            llm_service: LLM 服务实例，如果为 None 则使用全局实例
            rag_service: RAG 服务实例，如果为 None 则使用全局实例
        """
        self._llm_service = llm_service
        self._rag_service = rag_service
        self.templates = EXTRACTION_TEMPLATES
        
        logger.info("ChatOCR service initialized")
    
    @property
    def llm_service(self) -> Optional[OllamaLLMService]:
        """获取 LLM 服务"""
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service
    
    @property
    def rag_service(self) -> Optional[RAGService]:
        """获取 RAG 服务"""
        if self._rag_service is None and ChatOCRConfig.ENABLE_RAG:
            self._rag_service = get_rag_service()
        return self._rag_service
    
    def check_available(self) -> Dict[str, Any]:
        """
        检查服务是否可用
        
        Returns:
            dict: 包含 available, llm_status, rag_status 的状态信息
        """
        llm_available = False
        rag_available = False
        
        # 检查 LLM 服务
        if self.llm_service:
            llm_available = self.llm_service.check_health()
        
        # 检查 RAG 服务
        if self.rag_service and ChatOCRConfig.ENABLE_RAG:
            rag_available = True  # RAG 服务是本地的，通常可用
        
        return {
            "available": llm_available,
            "llm_available": llm_available,
            "rag_available": rag_available,
            "model": ChatOCRConfig.OLLAMA_MODEL,
            "base_url": ChatOCRConfig.OLLAMA_BASE_URL,
            "chatocr_enabled": ChatOCRConfig.ENABLE_CHATOCR,
            "rag_enabled": ChatOCRConfig.ENABLE_RAG
        }
    
    def get_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取预设提取模板
        
        Returns:
            dict: 模板字典，key 为模板 ID，value 为模板详情
        """
        return {
            template_id: {
                "name": template["name"],
                "name_en": template["name_en"],
                "fields": template["fields"]
            }
            for template_id, template in self.templates.items()
        }
    
    def get_template_fields(self, template_id: str) -> Optional[List[str]]:
        """
        获取指定模板的字段列表
        
        Args:
            template_id: 模板 ID
            
        Returns:
            list: 字段列表，如果模板不存在返回 None
        """
        template = self.templates.get(template_id)
        return template["fields"] if template else None

    
    def _get_document_content(self, job_id: str, query: Optional[str] = None) -> Optional[str]:
        """
        获取文档内容
        
        如果启用了 RAG 且有查询，则使用向量检索获取相关片段
        否则从缓存获取完整文档内容
        
        Args:
            job_id: 文档 job_id
            query: 查询文本（用于 RAG 检索）
            
        Returns:
            str: 文档内容，如果获取失败返回 None
        """
        # 尝试使用 RAG 检索相关内容
        if query and self.rag_service and ChatOCRConfig.ENABLE_RAG:
            try:
                results = self.rag_service.retrieve(job_id, query, top_k=5)
                if results and results.documents:
                    # 合并检索到的文档片段
                    content = "\n\n".join(results.documents)
                    logger.info(f"Retrieved {len(results.documents)} chunks via RAG for job {job_id}")
                    return content
            except Exception as e:
                logger.warning(f"RAG retrieval failed, falling back to full content: {e}")
        
        # 从缓存获取完整内容
        try:
            cache = get_job_cache()
            if cache:
                job_data = cache.get_job(job_id)
                if job_data:
                    # 尝试从 raw_ocr.json 获取文本
                    import os
                    from pathlib import Path
                    temp_folder = Path(os.environ.get('TEMP_FOLDER', 'temp'))
                    
                    # 尝试读取 raw_ocr.json
                    raw_ocr_path = temp_folder / f"{job_id}_raw_ocr.json"
                    if raw_ocr_path.exists():
                        with open(raw_ocr_path, 'r', encoding='utf-8') as f:
                            ocr_data = json.load(f)
                            if isinstance(ocr_data, dict) and 'text' in ocr_data:
                                return ocr_data['text']
                            elif isinstance(ocr_data, list):
                                # 从 OCR 结果列表提取文本
                                texts = []
                                for item in ocr_data:
                                    if isinstance(item, dict) and 'text' in item:
                                        texts.append(item['text'])
                                    elif isinstance(item, str):
                                        texts.append(item)
                                return '\n'.join(texts)
                    
                    # 尝试读取 raw_ocr.html 并提取文本
                    raw_html_path = temp_folder / f"{job_id}_raw_ocr.html"
                    if raw_html_path.exists():
                        with open(raw_html_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                            return self._extract_text_from_html(html_content)
                            
        except Exception as e:
            logger.error(f"Failed to get document content for job {job_id}: {e}")
        
        return None
    
    def _extract_text_from_html(self, html: str) -> str:
        """从 HTML 中提取纯文本"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator='\n', strip=True)
        except Exception:
            # 简单的正则提取
            text = re.sub(r'<[^>]+>', ' ', html)
            return ' '.join(text.split())
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """
        解析 LLM 返回的 JSON 响应
        
        Args:
            response: LLM 响应文本
            
        Returns:
            dict: 解析后的 JSON 对象，解析失败返回 None
        """
        if not response:
            return None
        
        # 清理响应文本
        text = response.strip()
        
        # 移除可能的 markdown 代码块标记
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试找到 JSON 对象
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning(f"Failed to parse JSON response: {text[:200]}...")
        return None
    
    def extract_info(
        self,
        job_id: str,
        fields: Optional[List[str]] = None,
        template: Optional[str] = None
    ) -> ExtractionResult:
        """
        从文档中提取关键信息
        
        Args:
            job_id: 文档 job_id
            fields: 要提取的字段列表
            template: 预设模板名称
            
        Returns:
            ExtractionResult: 提取结果
        """
        start_time = time.time()
        
        # 确定要提取的字段
        if template and template in self.templates:
            template_info = self.templates[template]
            extract_fields = fields or template_info["fields"]
            prompt_hint = template_info["prompt_hint"]
        else:
            extract_fields = fields or []
            prompt_hint = "请仔细分析文档内容"
        
        if not extract_fields:
            return ExtractionResult(
                job_id=job_id,
                fields={},
                success=False,
                error="未指定提取字段",
                processing_time=time.time() - start_time
            )
        
        # 检查 LLM 服务
        if not self.llm_service or not self.llm_service.check_health():
            return ExtractionResult(
                job_id=job_id,
                fields={field: None for field in extract_fields},
                success=False,
                error="LLM 服务不可用",
                warnings=["智能提取功能暂时不可用，请稍后重试"],
                processing_time=time.time() - start_time
            )
        
        # 获取文档内容
        query_hint = "、".join(extract_fields[:3])  # 用前几个字段作为检索提示
        document_content = self._get_document_content(job_id, query_hint)
        
        if not document_content:
            return ExtractionResult(
                job_id=job_id,
                fields={field: None for field in extract_fields},
                success=False,
                error="无法获取文档内容",
                processing_time=time.time() - start_time
            )
        
        # 构建 prompt
        field_template = ",\n".join([f'    "{field}": "提取的值或null"' for field in extract_fields])
        prompt = EXTRACTION_PROMPT.format(
            prompt_hint=prompt_hint,
            document_content=document_content[:8000],  # 限制内容长度
            fields=", ".join(extract_fields),
            field_template=field_template
        )
        
        # 调用 LLM
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_service.chat(messages)
            
            # 解析响应
            result = self._parse_json_response(response)
            
            if result:
                # 确保所有字段都有值
                extracted_fields = {}
                warnings = []
                null_count = 0
                
                for field in extract_fields:
                    value = result.get(field)
                    extracted_fields[field] = value
                    if value is None:
                        null_count += 1
                
                # 计算置信度（基于成功提取的字段比例）
                confidence = (len(extract_fields) - null_count) / len(extract_fields) if extract_fields else 0
                
                if null_count > 0:
                    warnings.append(f"有 {null_count} 个字段未能从文档中找到")
                
                return ExtractionResult(
                    job_id=job_id,
                    fields=extracted_fields,
                    confidence=confidence,
                    warnings=warnings,
                    processing_time=time.time() - start_time,
                    success=True
                )
            else:
                return ExtractionResult(
                    job_id=job_id,
                    fields={field: None for field in extract_fields},
                    success=False,
                    error="无法解析 LLM 响应",
                    warnings=["LLM 返回的结果格式不正确"],
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Extraction failed for job {job_id}: {e}")
            return ExtractionResult(
                job_id=job_id,
                fields={field: None for field in extract_fields},
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )

    
    def document_qa(self, job_id: str, question: str) -> QAResult:
        """
        基于文档内容回答问题
        
        Args:
            job_id: 文档 job_id
            question: 用户问题
            
        Returns:
            QAResult: 问答结果
        """
        start_time = time.time()
        
        if not question or not question.strip():
            return QAResult(
                job_id=job_id,
                question=question,
                answer="",
                success=False,
                error="问题不能为空",
                processing_time=time.time() - start_time
            )
        
        # 检查 LLM 服务
        if not self.llm_service or not self.llm_service.check_health():
            return QAResult(
                job_id=job_id,
                question=question,
                answer="智能问答功能暂时不可用，请稍后重试。",
                success=False,
                error="LLM 服务不可用",
                processing_time=time.time() - start_time
            )
        
        # 获取文档内容（使用问题作为检索查询）
        document_content = self._get_document_content(job_id, question)
        
        if not document_content:
            return QAResult(
                job_id=job_id,
                question=question,
                answer="无法获取文档内容，请确保文档已完成 OCR 处理。",
                success=False,
                error="无法获取文档内容",
                processing_time=time.time() - start_time
            )
        
        # 构建 prompt
        prompt = QA_PROMPT.format(
            document_content=document_content[:8000],  # 限制内容长度
            question=question
        )
        
        # 调用 LLM
        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_service.chat(messages)
            
            # 解析响应
            result = self._parse_json_response(response)
            
            if result:
                answer = result.get("answer", "")
                references = result.get("references", [])
                found_in_document = result.get("found_in_document", True)
                
                # 如果没有找到相关信息
                if not found_in_document or not answer:
                    answer = answer or "无法从文档中找到与您问题相关的信息。"
                
                # 计算置信度
                confidence = 0.9 if found_in_document and references else 0.5
                
                return QAResult(
                    job_id=job_id,
                    question=question,
                    answer=answer,
                    references=references if isinstance(references, list) else [],
                    confidence=confidence,
                    found_in_document=found_in_document,
                    processing_time=time.time() - start_time,
                    success=True
                )
            else:
                # 如果无法解析 JSON，尝试直接使用响应作为答案
                return QAResult(
                    job_id=job_id,
                    question=question,
                    answer=response[:1000] if response else "无法生成回答",
                    confidence=0.3,
                    processing_time=time.time() - start_time,
                    success=True
                )
                
        except Exception as e:
            logger.error(f"Document QA failed for job {job_id}: {e}")
            return QAResult(
                job_id=job_id,
                question=question,
                answer="处理问题时发生错误，请稍后重试。",
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )


# ============== 全局实例管理 ==============

_chatocr_service: Optional[ChatOCRService] = None


def get_chatocr_service() -> Optional[ChatOCRService]:
    """获取全局 ChatOCR 服务实例"""
    global _chatocr_service
    
    if not ChatOCRConfig.ENABLE_CHATOCR:
        return None
    
    if _chatocr_service is None:
        _chatocr_service = ChatOCRService()
    
    return _chatocr_service


def init_chatocr_service(
    llm_service: Optional[OllamaLLMService] = None,
    rag_service: Optional[RAGService] = None
) -> ChatOCRService:
    """
    初始化全局 ChatOCR 服务
    
    Args:
        llm_service: LLM 服务实例
        rag_service: RAG 服务实例
        
    Returns:
        ChatOCRService: 初始化的服务实例
    """
    global _chatocr_service
    _chatocr_service = ChatOCRService(llm_service, rag_service)
    return _chatocr_service
