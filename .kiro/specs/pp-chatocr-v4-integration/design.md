# Design Document: PP-ChatOCRv4 智能文档理解集成

## Overview

本设计文档描述如何在现有 PDF to Editable Web Layout 系统中集成 PP-ChatOCRv4 智能文档理解能力。系统将使用本地部署的 Ollama（gpt-OSS:20b 模型）作为 LLM 后端，实现关键信息提取和文档问答功能。

设计原则：
1. **增量集成**：不修改现有 OCR 流程，作为增强功能添加
2. **优雅降级**：LLM 不可用时不影响基础 OCR 功能
3. **复用优先**：复用现有 OCR 结果，避免重复处理

## Architecture

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端界面                              │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐      │
│  │ PDF预览 │  │ Block编辑│  │ 智能提取  │  │ 文档问答  │      │
│  └─────────┘  └─────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴─────────────────────────────┐
│                        后端 API                            │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────┐  │
│  │ /api/upload    │  │ /api/extract   │  │ /api/qa     │  │
│  │ /api/status    │  │ /api/templates │  │ /api/llm    │  │
│  │ (现有)         │  │ (新增)         │  │ (新增)      │  │
│  └────────────────┘  └────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────┴───────┐    ┌───────┴───────┐    ┌───────┴───────┐
│ PPStructureV3  │    │ RAG Service   │    │ Ollama LLM   │
│ (现有 OCR)     │    │ (新增)        │    │ (本地部署)    │
│               │    │ ├─Embedding   │    │ gpt-OSS:20b  │
│               │    │ └─ChromaDB    │    │              │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 数据流（含向量检索）

```
用户上传多页 PDF
      │
      ▼
┌─────────────────┐
│ 现有 OCR 处理    │ ──→ OCR 结果缓存
│ (PPStructureV3) │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ 文本分块        │ ──→ 按段落/章节切分（500字符/块）
│ Text Chunking   │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ 向量化          │ ──→ BGE-small-zh-v1.5 生成向量
│ Embedding       │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ 向量存储        │ ──→ ChromaDB 持久化存储
│ Vector Store    │
└─────────────────┘
      │
      ▼
┌─────────────────┐     ┌─────────────────┐
│ 用户查询        │     │                 │
│ ├─ 智能提取 ────┼────→│ 向量检索 Top-K  │
│ └─ 文档问答 ────┼────→│ (相关片段)      │
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │ Ollama LLM      │
                        │ (只处理相关片段) │
                        └─────────────────┘
                              │
                              ▼
                        返回结果给前端
```

## Components and Interfaces

### 1. LLM Service (新增)

负责与 Ollama 服务通信的封装层。

```python
# backend/services/llm_service.py

class OllamaLLMService:
    """Ollama LLM 服务封装"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 model_name: str = "gpt-oss:20b",
                 timeout: int = 60):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
    
    def check_health(self) -> bool:
        """检查 Ollama 服务是否可用"""
        pass
    
    def chat(self, messages: List[Dict], max_tokens: int = 4096) -> str:
        """发送聊天请求"""
        pass
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        pass
```

### 2. Embedding Service (新增)

负责文本向量化的服务。

```python
# backend/services/embedding_service.py

from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    """文本向量化服务 - 使用 BGE-small-zh-v1.5"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        if self._model is None:
            self._model = SentenceTransformer(model_name)
    
    def encode(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        将文本转换为向量
        
        Args:
            texts: 文本列表
            is_query: 是否为查询文本（查询需要添加指令前缀）
        """
        if is_query:
            texts = ["为这个句子生成表示以用于检索相关文章：" + t for t in texts]
        embeddings = self._model.encode(texts)
        return embeddings.tolist()
```

### 3. Vector Store Service (新增)

负责向量存储和检索的服务。

```python
# backend/services/vector_store.py

import chromadb
from typing import List, Dict, Optional

class VectorStore:
    """向量存储服务 - 使用 ChromaDB"""
    
    def __init__(self, persist_path: str = "./vector_db"):
        self.client = chromadb.PersistentClient(path=persist_path)
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ):
        """添加文档到向量库"""
        collection = self.client.get_or_create_collection(name=collection_name)
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids or [f"doc_{i}" for i in range(len(documents))]
        )
    
    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5
    ) -> Dict:
        """查询相似文档"""
        collection = self.client.get_or_create_collection(name=collection_name)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
```

### 4. RAG Service (新增)

整合向量检索和 LLM 的核心服务。

```python
# backend/services/rag_service.py

class RAGService:
    """RAG 检索增强生成服务"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
    
    def index_document(self, job_id: str, text_chunks: List[str], metadatas: List[Dict] = None):
        """索引文档 - OCR 完成后调用"""
        embeddings = self.embedding_service.encode(text_chunks, is_query=False)
        self.vector_store.add_documents(
            collection_name=f"doc_{job_id}",
            documents=text_chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )
    
    def retrieve(self, job_id: str, query: str, top_k: int = 5) -> List[Dict]:
        """检索相关文档片段"""
        query_embedding = self.embedding_service.encode([query], is_query=True)[0]
        results = self.vector_store.query(
            collection_name=f"doc_{job_id}",
            query_embedding=query_embedding,
            n_results=top_k
        )
        return self._format_results(results)
```

### 5. ChatOCR Service (新增)

整合 OCR 结果和 LLM 能力的核心服务。

```python
# backend/services/chatocr_service.py

class ChatOCRService:
    """PP-ChatOCRv4 智能文档理解服务"""
    
    def __init__(self, llm_service: OllamaLLMService):
        self.llm_service = llm_service
        self.templates = self._load_templates()
    
    def extract_info(self, 
                     ocr_result: Dict, 
                     fields: List[str],
                     template: Optional[str] = None) -> Dict:
        """
        从 OCR 结果中提取关键信息
        
        Args:
            ocr_result: 现有 OCR 处理结果
            fields: 要提取的字段列表
            template: 可选的预设模板名称
            
        Returns:
            {
                "fields": {"字段名": "值", ...},
                "confidence": 0.95,
                "warnings": []
            }
        """
        pass
    
    def document_qa(self, 
                    ocr_result: Dict, 
                    question: str) -> Dict:
        """
        基于文档内容回答问题
        
        Args:
            ocr_result: 现有 OCR 处理结果
            question: 用户问题
            
        Returns:
            {
                "answer": "回答内容",
                "references": ["相关原文片段"],
                "confidence": 0.9
            }
        """
        pass
    
    def get_templates(self) -> Dict[str, List[str]]:
        """获取预设提取模板"""
        pass
```

### 3. API Routes (新增)

```python
# backend/api/chatocr_routes.py

# POST /api/extract-info
# 请求体:
{
    "job_id": "xxx",           # 已处理的文档 job_id
    "fields": ["发票号", "金额", "日期"],  # 要提取的字段
    "template": "invoice"       # 可选，使用预设模板
}
# 响应:
{
    "success": true,
    "data": {
        "fields": {
            "发票号": "12345678",
            "金额": "1,234.56",
            "日期": "2026-01-25"
        },
        "confidence": 0.95,
        "processing_time": 2.3
    }
}

# POST /api/document-qa
# 请求体:
{
    "job_id": "xxx",
    "question": "这份文档的总金额是多少？"
}
# 响应:
{
    "success": true,
    "data": {
        "answer": "根据文档内容，总金额为 1,234.56 元。",
        "references": ["金额合计：1,234.56"],
        "confidence": 0.9
    }
}

# GET /api/llm/status
# 响应:
{
    "available": true,
    "model": "gpt-oss:20b",
    "base_url": "http://localhost:11434"
}

# GET /api/templates
# 响应:
{
    "templates": {
        "invoice": ["发票号码", "开票日期", "金额", "税额", "购买方"],
        "contract": ["甲方", "乙方", "合同金额", "签订日期", "有效期"],
        "id_card": ["姓名", "身份证号", "地址", "出生日期"],
        "resume": ["姓名", "电话", "邮箱", "工作经历", "教育背景"]
    }
}
```

### 4. 前端组件 (新增)

```javascript
// frontend/src/components/SmartExtract.js

class SmartExtractPanel {
    constructor(container) {
        this.container = container;
        this.templates = {};
        this.customFields = [];
    }
    
    async loadTemplates() {
        // 加载预设模板
    }
    
    async extractInfo(jobId, fields, template) {
        // 调用提取 API
    }
    
    renderResults(results) {
        // 显示提取结果
    }
}

// frontend/src/components/DocumentQA.js

class DocumentQAPanel {
    constructor(container) {
        this.container = container;
        this.history = [];
    }
    
    async askQuestion(jobId, question) {
        // 调用问答 API
    }
    
    renderAnswer(answer) {
        // 显示回答
    }
    
    renderHistory() {
        // 显示问答历史
    }
}
```

## Data Models

### 提取结果模型

```python
@dataclass
class ExtractionResult:
    job_id: str
    fields: Dict[str, Optional[str]]  # 字段名 -> 值
    confidence: float                  # 整体置信度
    warnings: List[str]               # 警告信息
    processing_time: float            # 处理耗时（秒）
    timestamp: datetime
```

### 问答结果模型

```python
@dataclass
class QAResult:
    job_id: str
    question: str
    answer: str
    references: List[str]             # 引用的原文片段
    confidence: float
    processing_time: float
    timestamp: datetime
```

### 预设模板

```python
EXTRACTION_TEMPLATES = {
    "invoice": {
        "name": "发票",
        "fields": ["发票号码", "开票日期", "金额合计", "税额", "购买方名称", "销售方名称"],
        "prompt_hint": "这是一份发票文档"
    },
    "contract": {
        "name": "合同",
        "fields": ["甲方", "乙方", "合同金额", "签订日期", "合同期限", "违约条款"],
        "prompt_hint": "这是一份合同文档"
    },
    "id_card": {
        "name": "身份证",
        "fields": ["姓名", "性别", "民族", "出生日期", "住址", "身份证号码"],
        "prompt_hint": "这是一份身份证文档"
    },
    "resume": {
        "name": "简历",
        "fields": ["姓名", "联系电话", "电子邮箱", "教育背景", "工作经历", "技能特长"],
        "prompt_hint": "这是一份个人简历"
    }
}
```

## Prompt Engineering

### 关键信息提取 Prompt

```python
EXTRACTION_PROMPT = """你是一个专业的文档信息提取助手。请从以下文档内容中提取指定的字段信息。

文档内容：
{document_content}

需要提取的字段：
{fields}

请按照以下 JSON 格式返回结果：
{{
    "字段名1": "提取的值或null",
    "字段名2": "提取的值或null",
    ...
}}

注意事项：
1. 如果某个字段在文档中找不到，返回 null
2. 保持提取值的原始格式（如日期、金额格式）
3. 只返回 JSON，不要添加其他说明文字
"""
```

### 文档问答 Prompt

```python
QA_PROMPT = """你是一个专业的文档问答助手。请基于以下文档内容回答用户的问题。

文档内容：
{document_content}

用户问题：{question}

请按照以下要求回答：
1. 只基于文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确告知
3. 在回答中引用文档原文作为依据
4. 使用简洁清晰的语言

请按照以下 JSON 格式返回：
{{
    "answer": "你的回答",
    "references": ["引用的原文片段1", "引用的原文片段2"],
    "found_in_document": true/false
}}
"""
```

## Correctness Properties

### Property 1: LLM 服务可用性检测
*For any* 系统启动或 LLM 功能调用前，系统应正确检测 Ollama 服务状态
**Validates: Requirements 1.1, 1.2**

### Property 2: LLM 服务降级
*For any* LLM 服务不可用的情况，现有 OCR 功能应继续正常工作
**Validates: Requirements 1.2, 8.3**

### Property 3: 信息提取完整性
*For any* 指定的提取字段列表，系统应返回所有字段的提取结果（值或 null）
**Validates: Requirements 3.1, 3.4**

### Property 4: 提取结果格式
*For any* 成功的提取请求，返回结果应为有效的 JSON 格式
**Validates: Requirements 3.2**

### Property 5: 问答相关性
*For any* 文档问答请求，回答应基于文档内容，不应编造信息
**Validates: Requirements 4.1, 4.2**

### Property 6: API 错误响应
*For any* API 调用失败，应返回标准化的错误响应格式
**Validates: Requirements 5.5**

### Property 7: 超时处理
*For any* LLM 调用超过 60 秒，应返回超时错误
**Validates: Requirements 1.5**

### Property 8: OCR 结果复用
*For any* 智能功能调用，应复用已有的 OCR 结果，不重复处理
**Validates: Requirements 2.5, 7.2**

## Error Handling

### 错误分类

| 错误类型 | HTTP 状态码 | 处理方式 |
|---------|------------|---------|
| LLM 服务不可用 | 503 | 返回错误提示，建议使用基础 OCR |
| LLM 调用超时 | 408 | 返回超时错误，允许重试 |
| 模型不存在 | 400 | 返回配置错误提示 |
| OCR 结果不存在 | 404 | 提示先进行 OCR 处理 |
| 提取字段为空 | 400 | 返回参数错误 |
| JSON 解析失败 | 500 | 记录日志，返回原始响应 |

### 降级策略

```python
class GracefulDegradation:
    """优雅降级处理"""
    
    @staticmethod
    def handle_llm_unavailable():
        """LLM 不可用时的处理"""
        return {
            "error": "智能功能暂时不可用",
            "fallback": "您可以继续使用基础 OCR 功能",
            "retry_after": 30  # 建议 30 秒后重试
        }
    
    @staticmethod
    def handle_extraction_failure(ocr_result):
        """提取失败时返回 OCR 原文"""
        return {
            "error": "智能提取失败",
            "fallback_content": ocr_result.get("text", ""),
            "suggestion": "请手动查找所需信息"
        }
```

## Configuration

### 配置文件结构

```python
# backend/config.py 新增配置

class ChatOCRConfig:
    # Ollama 配置
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
    
    # LLM 参数
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    
    # 功能开关
    ENABLE_CHATOCR = os.getenv("ENABLE_CHATOCR", "true").lower() == "true"
```

### 环境变量

```bash
# .env 文件示例
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_TIMEOUT=60
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.1
ENABLE_CHATOCR=true
```

## Testing Strategy

### 单元测试

1. LLM Service 连接测试
2. Prompt 模板渲染测试
3. JSON 解析测试
4. 错误处理测试

### 集成测试

1. 完整提取流程测试
2. 完整问答流程测试
3. 降级场景测试
4. 并发请求测试

### 测试数据

准备以下测试文档：
- 标准发票 PDF
- 合同文档 PDF
- 身份证图片
- 简历文档

## Implementation Notes

### 依赖安装

```bash
# 安装 PaddleX（如果需要使用官方 PP-ChatOCRv4）
pip install paddlex[ocr]

# 或者使用简化方案（直接调用 Ollama）
pip install requests  # 已有
```

### Ollama API 调用示例

```python
import requests

def call_ollama(prompt: str, model: str = "gpt-oss:20b") -> str:
    """调用 Ollama API"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 4096
            }
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["response"]
```

### 与现有系统集成点

1. **OCR 结果获取**：从 `job_cache` 获取已处理的 OCR 结果
2. **API 路由注册**：在 `backend/api/routes.py` 中注册新路由
3. **前端集成**：在 `frontend/src/index.js` 中添加智能功能入口
