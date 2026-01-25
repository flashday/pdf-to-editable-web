# RAG 向量检索技术方案指南

> 创建日期：2026年1月25日
> 适用项目：PP-ChatOCRv4 智能文档理解集成
> 状态：技术选型完成

---

## 一、什么是向量检索（RAG）？

### 1.1 基本概念

**RAG（Retrieval-Augmented Generation）** 是一种结合检索和生成的技术架构，核心思想是：

```
传统方式：将所有文档内容发给 LLM → Token 爆炸，成本高，准确率低

RAG 方式：先检索相关内容，只将相关片段发给 LLM → 省 Token，更准确
```

### 1.2 传统搜索 vs 向量检索

| 对比项 | 传统关键词搜索 | 向量语义检索 |
|--------|--------------|-------------|
| 搜索方式 | 精确匹配关键词 | 语义相似度匹配 |
| "合同金额" | 只能找到包含这4个字的内容 | 能找到"总价款"、"交易金额"等 |
| 同义词处理 | ❌ 不支持 | ✅ 自动理解 |
| 多语言 | ❌ 需要分别处理 | ✅ 跨语言检索 |

### 1.3 为什么多页 PDF 必须用向量检索？

假设处理一个 50 页合同：

| 方案 | Token 消耗 | 成本（GPT-4o） | 准确率 |
|------|-----------|---------------|--------|
| 全文发送给 LLM | ~70,000 tokens | ~$0.35/次 | 低（上下文过长） |
| 向量检索 + LLM | ~3,000 tokens | ~$0.015/次 | 高（精准定位） |
| **节省** | **95%** | **95%** | **显著提升** |

---

## 二、向量检索工作流程

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    文档处理阶段（离线）                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  多页PDF → OCR识别 → 文本分块 → Embedding模型 → 向量数据库   │
│                         │                                   │
│                         ▼                                   │
│              "第一条：甲方支付乙方100万元"                    │
│                         │                                   │
│                         ▼                                   │
│              [0.12, -0.34, 0.56, ...] (768维向量)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    查询阶段（在线）                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  用户问题 → Embedding模型 → 查询向量 → 相似度搜索 → Top-K片段 │
│      │                                                      │
│      ▼                                                      │
│  "合同金额是多少？"                                          │
│      │                                                      │
│      ▼                                                      │
│  [0.11, -0.32, 0.58, ...] → 找到最相似的文本片段             │
│      │                                                      │
│      ▼                                                      │
│  "第一条：甲方支付乙方100万元" (相似度: 0.92)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    LLM回答阶段                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  相关片段 + 用户问题 → LLM → 生成回答                        │
│                                                             │
│  Prompt: "根据以下内容回答问题：                             │
│          内容：第一条：甲方支付乙方100万元                    │
│          问题：合同金额是多少？"                             │
│                    │                                        │
│                    ▼                                        │
│  回答："根据合同第一条，合同金额为100万元。"                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件说明

| 组件 | 作用 | 说明 |
|------|------|------|
| **Embedding 模型** | 将文本转换为向量 | 核心组件，决定检索质量 |
| **向量数据库** | 存储和检索向量 | 支持高效相似度搜索 |
| **文本分块器** | 将长文档切分为片段 | 影响检索粒度 |
| **LLM** | 理解问题并生成回答 | 最终输出 |

### 2.3 文本分块策略

```python
# 分块示例
原文档（50页合同）
    │
    ▼
按段落/章节分块
    │
    ▼
["第一条：甲方支付乙方100万元...",
 "第二条：付款期限为30天...",
 "第三条：违约责任...",
 ...]
    │
    ▼
每个片段 200-500 字符（可配置）
```

**分块参数建议**：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| chunk_size | 500 | 每个片段的最大字符数 |
| chunk_overlap | 50 | 相邻片段的重叠字符数 |
| separator | "\n\n" | 优先按段落分割 |

---

## 三、Embedding 模型选型

### 3.1 方案对比总览

| 方案 | 模型名称 | 中文支持 | 向量维度 | 模型大小 | 部署方式 | 推荐度 |
|------|---------|---------|---------|---------|---------|-------|
| **A** | Ollama nomic-embed-text | ⚠️ 一般 | 768 | ~500MB | Ollama | ⭐⭐⭐ |
| **B** | BAAI/bge-m3 | ✅ 优秀 | 1024 | ~2GB | Python | ⭐⭐⭐⭐⭐ |
| **C** | BAAI/bge-small-zh-v1.5 | ✅ 优秀 | 512 | ~100MB | Python | ⭐⭐⭐⭐ |
| **D** | shibing624/text2vec | ✅ 优秀 | 768 | ~400MB | Python | ⭐⭐⭐⭐ |

### 3.2 方案 A：Ollama Embedding

**适用场景**：快速原型验证，英文文档为主

```bash
# 安装（已有 Ollama 的情况下）
ollama pull nomic-embed-text
```

```python
import requests

def get_embedding_ollama(text: str) -> list:
    """使用 Ollama 获取文本向量"""
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": text
        }
    )
    return response.json()["embedding"]

# 使用示例
embedding = get_embedding_ollama("合同金额是多少？")
print(f"向量维度: {len(embedding)}")  # 768
```

**优点**：
- ✅ 无需额外安装，复用现有 Ollama
- ✅ 部署简单，一条命令

**缺点**：
- ❌ 中文效果一般（主要针对英文优化）
- ❌ 对于中文合同、发票等文档可能检索不准确

---

### 3.3 方案 B：BGE-M3（推荐 - 多语言场景）

**适用场景**：中英混合文档，需要高质量检索

BGE（BAAI General Embedding）是北京智源研究院开发的开源模型，在中文 Embedding 领域排名第一。

```bash
# 安装依赖
pip install sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer

# 加载模型（首次运行会下载约 2GB）
model = SentenceTransformer('BAAI/bge-m3')

def get_embedding_bge_m3(text: str) -> list:
    """使用 BGE-M3 获取文本向量"""
    # BGE 模型建议添加指令前缀以提高检索效果
    instruction = "为这个句子生成表示以用于检索相关文章："
    embedding = model.encode(instruction + text)
    return embedding.tolist()

# 使用示例
embedding = get_embedding_bge_m3("合同金额是多少？")
print(f"向量维度: {len(embedding)}")  # 1024
```

**优点**：
- ✅ 中文效果最好（MTEB 中文榜单第一）
- ✅ 多语言支持（中英日韩等 100+ 语言）
- ✅ 支持长文本（最长 8192 tokens）
- ✅ 支持稀疏检索和稠密检索混合

**缺点**：
- ❌ 模型较大（~2GB）
- ❌ 首次加载较慢（约 30 秒）
- ❌ 内存占用较高

---

### 3.4 方案 C：BGE-small-zh（推荐 - 轻量中文场景）

**适用场景**：纯中文文档，资源有限

```bash
pip install sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer

# 加载模型（首次运行会下载约 100MB）
model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

def get_embedding_bge_small(text: str) -> list:
    """使用 BGE-small-zh 获取文本向量"""
    # 查询时添加指令前缀
    instruction = "为这个句子生成表示以用于检索相关文章："
    embedding = model.encode(instruction + text)
    return embedding.tolist()

# 使用示例
embedding = get_embedding_bge_small("合同金额是多少？")
print(f"向量维度: {len(embedding)}")  # 512
```

**优点**：
- ✅ 模型小巧（~100MB）
- ✅ 中文效果优秀
- ✅ 加载快速（约 5 秒）
- ✅ 内存占用低

**缺点**：
- ❌ 仅支持中文
- ❌ 向量维度较小（512 vs 1024）
- ❌ 长文本支持有限（512 tokens）

---

### 3.5 方案 D：Text2Vec-Chinese

**适用场景**：中文文档，需要平衡效果和资源

```bash
pip install sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('shibing624/text2vec-base-chinese')

def get_embedding_text2vec(text: str) -> list:
    """使用 text2vec 获取文本向量"""
    embedding = model.encode(text)
    return embedding.tolist()
```

**优点**：
- ✅ 中文效果好
- ✅ 模型大小适中（~400MB）
- ✅ 社区活跃，文档丰富

**缺点**：
- ❌ 不如 BGE 系列效果好
- ❌ 更新频率较低

---

### 3.6 模型选择决策树

```
你的文档类型是什么？
    │
    ├─ 纯中文文档（合同、发票、报告）
    │       │
    │       ├─ 资源充足（8GB+ 内存）→ 选择 BGE-M3
    │       │
    │       └─ 资源有限（4GB 内存）→ 选择 BGE-small-zh ✅ 推荐
    │
    ├─ 中英混合文档
    │       │
    │       └─ 选择 BGE-M3
    │
    └─ 快速原型验证
            │
            └─ 选择 Ollama nomic-embed-text
```

---

## 四、向量数据库选型

### 4.1 方案对比

| 方案 | 说明 | 数据规模 | 持久化 | 安装复杂度 | 推荐度 |
|------|------|---------|--------|-----------|-------|
| **ChromaDB** | 轻量级，纯 Python | <100万 | ✅ 支持 | 简单 | ⭐⭐⭐⭐⭐ |
| **FAISS** | Facebook 开发 | 百万级 | ⚠️ 需额外处理 | 中等 | ⭐⭐⭐⭐ |
| **Milvus** | 企业级 | 亿级 | ✅ 支持 | 复杂 | ⭐⭐⭐ |
| **内存 Dict** | 最简单 | <1万 | ❌ 不支持 | 无 | ⭐⭐ |

### 4.2 推荐方案：ChromaDB

**为什么选择 ChromaDB？**
- ✅ 纯 Python，pip 一键安装
- ✅ 支持持久化存储
- ✅ 内置 Embedding 函数支持
- ✅ 适合中小规模应用
- ✅ API 简洁易用

```bash
pip install chromadb
```

```python
import chromadb
from chromadb.config import Settings

# 创建持久化客户端
client = chromadb.PersistentClient(path="./vector_db")

# 创建或获取集合
collection = client.get_or_create_collection(
    name="documents",
    metadata={"description": "文档向量存储"}
)

# 添加文档
collection.add(
    documents=[
        "第一条：甲方支付乙方100万元",
        "第二条：付款期限为30天",
        "第三条：违约金为合同金额的10%"
    ],
    metadatas=[
        {"page": 1, "type": "clause"},
        {"page": 1, "type": "clause"},
        {"page": 2, "type": "clause"}
    ],
    ids=["doc1", "doc2", "doc3"]
)

# 查询相似文档
results = collection.query(
    query_texts=["合同金额是多少？"],
    n_results=3,
    include=["documents", "metadatas", "distances"]
)

print(results)
# {
#     'ids': [['doc1', 'doc3', 'doc2']],
#     'documents': [['第一条：甲方支付乙方100万元', ...]],
#     'distances': [[0.23, 0.45, 0.67]]
# }
```

### 4.3 ChromaDB 与自定义 Embedding 集成

```python
import chromadb
from sentence_transformers import SentenceTransformer

# 加载 BGE 模型
embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')

# 自定义 Embedding 函数
class BGEEmbeddingFunction:
    def __init__(self, model):
        self.model = model
    
    def __call__(self, input: list) -> list:
        # 添加查询指令前缀
        texts = ["为这个句子生成表示以用于检索相关文章：" + t for t in input]
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

# 创建集合时指定 Embedding 函数
collection = client.get_or_create_collection(
    name="documents",
    embedding_function=BGEEmbeddingFunction(embedding_model)
)
```

---

## 五、完整实现示例

### 5.1 项目结构

```
backend/
├── services/
│   ├── embedding_service.py    # Embedding 服务
│   ├── vector_store.py         # 向量存储服务
│   └── rag_service.py          # RAG 检索服务
└── config.py                   # 配置文件
```

### 5.2 Embedding 服务实现

```python
# backend/services/embedding_service.py

from sentence_transformers import SentenceTransformer
from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    """文本向量化服务"""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5"):
        if self._model is None:
            logger.info(f"加载 Embedding 模型: {model_name}")
            self._model = SentenceTransformer(model_name)
            logger.info("Embedding 模型加载完成")
    
    def encode(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """
        将文本转换为向量
        
        Args:
            texts: 文本列表
            is_query: 是否为查询文本（查询需要添加指令前缀）
        
        Returns:
            向量列表
        """
        if is_query:
            # 查询文本添加指令前缀
            texts = ["为这个句子生成表示以用于检索相关文章：" + t for t in texts]
        
        embeddings = self._model.encode(texts)
        return embeddings.tolist()
    
    def encode_single(self, text: str, is_query: bool = False) -> List[float]:
        """编码单个文本"""
        return self.encode([text], is_query)[0]
```

### 5.3 向量存储服务实现

```python
# backend/services/vector_store.py

import chromadb
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    """向量存储服务"""
    
    def __init__(self, persist_path: str = "./vector_db"):
        self.client = chromadb.PersistentClient(path=persist_path)
        logger.info(f"向量数据库初始化完成: {persist_path}")
    
    def create_collection(self, name: str) -> chromadb.Collection:
        """创建或获取集合"""
        return self.client.get_or_create_collection(name=name)
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ):
        """添加文档到向量库"""
        collection = self.create_collection(collection_name)
        
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"添加 {len(documents)} 个文档到集合 {collection_name}")
    
    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5
    ) -> Dict:
        """查询相似文档"""
        collection = self.create_collection(collection_name)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        
        return {
            "documents": results["documents"][0],
            "metadatas": results["metadatas"][0],
            "distances": results["distances"][0]
        }
    
    def delete_collection(self, name: str):
        """删除集合"""
        self.client.delete_collection(name=name)
        logger.info(f"删除集合: {name}")
```

### 5.4 RAG 检索服务实现

```python
# backend/services/rag_service.py

from typing import List, Dict
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

class RAGService:
    """RAG 检索增强生成服务"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
    
    def index_document(
        self,
        job_id: str,
        text_chunks: List[str],
        metadatas: List[Dict] = None
    ):
        """
        索引文档
        
        Args:
            job_id: 文档任务 ID
            text_chunks: 文本片段列表
            metadatas: 元数据列表（页码、类型等）
        """
        # 生成向量
        embeddings = self.embedding_service.encode(text_chunks, is_query=False)
        
        # 存储到向量库
        self.vector_store.add_documents(
            collection_name=f"doc_{job_id}",
            documents=text_chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        logger.info(f"文档 {job_id} 索引完成，共 {len(text_chunks)} 个片段")
    
    def retrieve(
        self,
        job_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        检索相关文档片段
        
        Args:
            job_id: 文档任务 ID
            query: 查询文本
            top_k: 返回结果数量
        
        Returns:
            相关片段列表
        """
        # 生成查询向量
        query_embedding = self.embedding_service.encode_single(query, is_query=True)
        
        # 检索
        results = self.vector_store.query(
            collection_name=f"doc_{job_id}",
            query_embedding=query_embedding,
            n_results=top_k
        )
        
        # 格式化结果
        retrieved = []
        for i, doc in enumerate(results["documents"]):
            retrieved.append({
                "content": doc,
                "metadata": results["metadatas"][i] if results["metadatas"] else {},
                "score": 1 - results["distances"][i]  # 转换为相似度分数
            })
        
        return retrieved
    
    def build_context(self, retrieved_docs: List[Dict], max_length: int = 4000) -> str:
        """
        构建 LLM 上下文
        
        Args:
            retrieved_docs: 检索到的文档列表
            max_length: 最大上下文长度
        
        Returns:
            格式化的上下文字符串
        """
        context_parts = []
        current_length = 0
        
        for doc in retrieved_docs:
            content = doc["content"]
            if current_length + len(content) > max_length:
                break
            context_parts.append(content)
            current_length += len(content)
        
        return "\n\n".join(context_parts)
```

---

## 六、最终推荐配置

### 6.1 系统配置总览

```
┌─────────────────────────────────────────────────────────────┐
│                    推荐系统配置                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LLM 模型：      Ollama gpt-oss:20b（已部署）               │
│  Embedding 模型：BGE-small-zh-v1.5（推荐）                  │
│  向量数据库：    ChromaDB（推荐）                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 依赖安装

```bash
# 安装 Embedding 模型依赖
pip install sentence-transformers

# 安装向量数据库
pip install chromadb

# 可选：如果需要更好的分词
pip install jieba
```

### 6.3 配置参数

```python
# backend/config.py

class RAGConfig:
    # Embedding 模型配置
    EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIMENSION = 512
    
    # 向量数据库配置
    VECTOR_DB_PATH = "./vector_db"
    
    # 检索配置
    TOP_K_RESULTS = 5
    MAX_CONTEXT_LENGTH = 4000
    
    # 文本分块配置
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
```

### 6.4 硬件要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 内存 | 4GB | 8GB+ |
| 磁盘 | 500MB（模型） | 2GB+（含向量库） |
| CPU | 任意 x86_64 | 多核更佳 |

---

## 七、常见问题

### Q1: 首次加载模型很慢怎么办？

模型会自动从 HuggingFace 下载，首次约需 1-5 分钟。可以：
1. 使用国内镜像：`export HF_ENDPOINT=https://hf-mirror.com`
2. 手动下载后指定本地路径

### Q2: 中文检索效果不好怎么办？

1. 确保使用 BGE 系列模型（专门针对中文优化）
2. 查询时添加指令前缀
3. 调整分块大小（过大或过小都会影响效果）

### Q3: 向量库占用空间太大怎么办？

1. 使用较小维度的模型（如 BGE-small-zh，512 维）
2. 定期清理不需要的集合
3. 使用量化技术（高级）

### Q4: 如何评估检索效果？

```python
# 简单评估方法
def evaluate_retrieval(query, expected_doc, retrieved_docs):
    """检查期望文档是否在检索结果中"""
    for i, doc in enumerate(retrieved_docs):
        if expected_doc in doc["content"]:
            return {"found": True, "rank": i + 1}
    return {"found": False, "rank": -1}
```

---

## 八、参考资源

- [BGE 模型官方仓库](https://github.com/FlagOpen/FlagEmbedding)
- [ChromaDB 官方文档](https://docs.trychroma.com/)
- [Sentence-Transformers 文档](https://www.sbert.net/)
- [RAG 技术综述](https://arxiv.org/abs/2312.10997)

---

*文档最后更新：2026年1月25日*
