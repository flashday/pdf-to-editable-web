"""
Vector Store Service - 向量存储服务
使用 ChromaDB 进行向量存储和检索
"""
import logging
import os
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """查询结果"""
    documents: List[str]
    metadatas: List[Dict]
    distances: List[float]
    ids: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": self.documents,
            "metadatas": self.metadatas,
            "distances": self.distances,
            "ids": self.ids
        }
    
    def __len__(self) -> int:
        return len(self.documents)
    
    def get_formatted_results(self) -> List[Dict]:
        """获取格式化的结果列表"""
        results = []
        for i in range(len(self.documents)):
            results.append({
                "id": self.ids[i] if i < len(self.ids) else None,
                "document": self.documents[i],
                "metadata": self.metadatas[i] if i < len(self.metadatas) else {},
                "distance": self.distances[i] if i < len(self.distances) else None,
                "score": 1 - self.distances[i] if i < len(self.distances) else None
            })
        return results


class VectorStore:
    """
    向量存储服务 - 使用 ChromaDB
    
    特点：
    - 持久化存储
    - 支持元数据过滤
    - 高效的相似度检索
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, persist_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, persist_path: str = None):
        """
        初始化向量存储
        
        Args:
            persist_path: 持久化存储路径
        """
        if self._initialized:
            return
            
        if persist_path is None:
            from backend.config import ChatOCRConfig
            persist_path = ChatOCRConfig.VECTOR_DB_PATH
        
        self.persist_path = persist_path
        self._client = None
        self._init_client()
        self._initialized = True
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # 确保目录存在
            os.makedirs(self.persist_path, exist_ok=True)
            
            logger.info(f"Initializing ChromaDB at: {self.persist_path}")
            
            self._client = chromadb.PersistentClient(
                path=self.persist_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info("ChromaDB initialized successfully")
            
        except ImportError:
            logger.error("chromadb not installed. Run: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    @property
    def client(self):
        """获取 ChromaDB 客户端"""
        if self._client is None:
            self._init_client()
        return self._client
    
    def get_or_create_collection(self, name: str) -> Any:
        """
        获取或创建集合
        
        Args:
            name: 集合名称
            
        Returns:
            Collection: ChromaDB 集合对象
        """
        # ChromaDB 集合名称规则：3-63字符，字母数字和下划线
        safe_name = self._sanitize_collection_name(name)
        return self.client.get_or_create_collection(name=safe_name)
    
    def _sanitize_collection_name(self, name: str) -> str:
        """
        清理集合名称，确保符合 ChromaDB 命名规则
        
        Args:
            name: 原始名称
            
        Returns:
            str: 清理后的名称
        """
        # 替换非法字符
        safe_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        # 确保以字母开头
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'c_' + safe_name
        # 限制长度
        if len(safe_name) > 63:
            safe_name = safe_name[:63]
        if len(safe_name) < 3:
            safe_name = safe_name + '_col'
        return safe_name
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        添加文档到向量库
        
        Args:
            collection_name: 集合名称
            documents: 文档文本列表
            embeddings: 向量列表
            metadatas: 元数据列表（可选）
            ids: 文档ID列表（可选）
            
        Returns:
            bool: 是否成功
        """
        try:
            if not documents or not embeddings:
                logger.warning("Empty documents or embeddings")
                return False
            
            if len(documents) != len(embeddings):
                raise ValueError(f"Documents ({len(documents)}) and embeddings ({len(embeddings)}) count mismatch")
            
            collection = self.get_or_create_collection(collection_name)
            
            # 生成默认 ID
            if ids is None:
                ids = [f"doc_{i}" for i in range(len(documents))]
            
            # 生成默认元数据
            if metadatas is None:
                metadatas = [{"index": i} for i in range(len(documents))]
            
            # 添加文档
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False
    
    def query(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> QueryResult:
        """
        查询相似文档
        
        Args:
            collection_name: 集合名称
            query_embedding: 查询向量
            n_results: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件
            
        Returns:
            QueryResult: 查询结果
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            
            # 构建查询参数
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": n_results,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if where:
                query_params["where"] = where
            if where_document:
                query_params["where_document"] = where_document
            
            results = collection.query(**query_params)
            
            # 解析结果（ChromaDB 返回嵌套列表）
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            
            return QueryResult(
                documents=documents,
                metadatas=metadatas,
                distances=distances,
                ids=ids
            )
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return QueryResult(
                documents=[],
                metadatas=[],
                distances=[],
                ids=[]
            )
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        删除集合
        
        Args:
            collection_name: 集合名称
            
        Returns:
            bool: 是否成功
        """
        try:
            safe_name = self._sanitize_collection_name(collection_name)
            self.client.delete_collection(name=safe_name)
            logger.info(f"Deleted collection: {safe_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False
    
    def collection_exists(self, collection_name: str) -> bool:
        """
        检查集合是否存在
        
        Args:
            collection_name: 集合名称
            
        Returns:
            bool: 是否存在
        """
        try:
            safe_name = self._sanitize_collection_name(collection_name)
            collections = self.client.list_collections()
            return any(c.name == safe_name for c in collections)
        except Exception as e:
            logger.error(f"Failed to check collection: {e}")
            return False
    
    def get_collection_count(self, collection_name: str) -> int:
        """
        获取集合中的文档数量
        
        Args:
            collection_name: 集合名称
            
        Returns:
            int: 文档数量
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0
    
    def list_collections(self) -> List[str]:
        """
        列出所有集合
        
        Returns:
            List[str]: 集合名称列表
        """
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        collections = self.list_collections()
        return {
            "initialized": self._initialized,
            "persist_path": self.persist_path,
            "collections_count": len(collections),
            "collections": collections
        }


# 全局实例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    获取向量存储实例
    
    Returns:
        VectorStore: 服务实例
    """
    global _vector_store
    
    if _vector_store is None:
        _vector_store = VectorStore()
    
    return _vector_store


def reset_vector_store():
    """重置服务实例（用于测试）"""
    global _vector_store
    _vector_store = None
    VectorStore._instance = None
