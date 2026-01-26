"""
Embedding Service - 文本向量化服务
使用 BGE-small-zh-v1.5 模型进行中文文本向量化
"""
import logging
import time
from typing import List, Optional, Union
from dataclasses import dataclass
import threading

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """向量化结果"""
    embeddings: List[List[float]]
    model: str
    processing_time: float
    dimension: int


class EmbeddingService:
    """
    文本向量化服务 - 单例模式
    
    使用 BGE-small-zh-v1.5 模型，特点：
    - 专为中文优化
    - 模型小巧（~100MB）
    - 512 维向量
    - 支持查询指令前缀
    """
    
    _instance = None
    _lock = threading.Lock()
    _model = None
    _model_name: str = None
    _initialized: bool = False
    
    def __new__(cls, model_name: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, model_name: str = None):
        """
        初始化 Embedding 服务
        
        Args:
            model_name: 模型名称，默认使用配置中的模型
        """
        if self._initialized and model_name == self._model_name:
            return
            
        if model_name is None:
            from backend.config import ChatOCRConfig
            model_name = ChatOCRConfig.EMBEDDING_MODEL
        
        self._model_name = model_name
        self._load_model()
        self._initialized = True
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self._model_name}")
            start_time = time.time()
            
            self._model = SentenceTransformer(self._model_name)
            
            load_time = time.time() - start_time
            logger.info(f"Embedding model loaded in {load_time:.2f}s")
            
        except ImportError:
            logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """获取向量维度"""
        if self._model is None:
            return 512  # BGE-small-zh 默认维度
        return self._model.get_sentence_embedding_dimension()
    
    @property
    def model_name(self) -> str:
        """获取模型名称"""
        return self._model_name
    
    def encode(
        self,
        texts: Union[str, List[str]],
        is_query: bool = False,
        normalize: bool = True,
        batch_size: int = 32
    ) -> EmbeddingResult:
        """
        将文本转换为向量
        
        Args:
            texts: 单个文本或文本列表
            is_query: 是否为查询文本（查询需要添加指令前缀以提高检索效果）
            normalize: 是否归一化向量
            batch_size: 批处理大小
            
        Returns:
            EmbeddingResult: 向量化结果
        """
        if self._model is None:
            raise RuntimeError("Embedding model not loaded")
        
        start_time = time.time()
        
        # 统一转为列表
        if isinstance(texts, str):
            texts = [texts]
        
        # BGE 模型查询时需要添加指令前缀
        if is_query:
            # 中文查询指令
            texts = [f"为这个句子生成表示以用于检索相关文章：{t}" for t in texts]
        
        # 执行向量化
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=batch_size,
            show_progress_bar=False
        )
        
        # 转换为 Python 列表
        if isinstance(embeddings, np.ndarray):
            embeddings_list = embeddings.tolist()
        else:
            embeddings_list = [e.tolist() if hasattr(e, 'tolist') else list(e) for e in embeddings]
        
        processing_time = time.time() - start_time
        
        logger.debug(f"Encoded {len(texts)} texts in {processing_time:.3f}s")
        
        return EmbeddingResult(
            embeddings=embeddings_list,
            model=self._model_name,
            processing_time=processing_time,
            dimension=self.dimension
        )
    
    def encode_query(self, query: str) -> List[float]:
        """
        编码查询文本（便捷方法）
        
        Args:
            query: 查询文本
            
        Returns:
            List[float]: 查询向量
        """
        result = self.encode(query, is_query=True)
        return result.embeddings[0]
    
    def encode_documents(self, documents: List[str]) -> List[List[float]]:
        """
        编码文档文本（便捷方法）
        
        Args:
            documents: 文档文本列表
            
        Returns:
            List[List[float]]: 文档向量列表
        """
        result = self.encode(documents, is_query=False)
        return result.embeddings
    
    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # 余弦相似度
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return float(dot_product / (norm1 * norm2))
    
    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            "initialized": self._initialized,
            "model_name": self._model_name,
            "dimension": self.dimension,
            "model_loaded": self._model is not None
        }


# 全局实例获取函数
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取 Embedding 服务实例
    
    Returns:
        EmbeddingService: 服务实例
    """
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    
    return _embedding_service


def reset_embedding_service():
    """重置服务实例（用于测试）"""
    global _embedding_service
    _embedding_service = None
    EmbeddingService._instance = None
    EmbeddingService._model = None
    EmbeddingService._initialized = False
