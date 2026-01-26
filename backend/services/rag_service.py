"""
RAG Service - 检索增强生成服务
整合 Embedding、VectorStore 和 TextChunker，提供文档索引和检索功能
"""
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from backend.services.embedding_service import EmbeddingService, get_embedding_service
from backend.services.vector_store import VectorStore, get_vector_store, QueryResult
from backend.services.text_chunker import TextChunker, TextChunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    query: str
    chunks: List[Dict]
    total_found: int
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "chunks": self.chunks,
            "total_found": self.total_found,
            "processing_time": self.processing_time
        }
    
    def get_context(self, max_length: int = 4000) -> str:
        """
        获取合并后的上下文文本
        
        Args:
            max_length: 最大长度
            
        Returns:
            str: 合并的上下文
        """
        context_parts = []
        current_length = 0
        
        for chunk in self.chunks:
            text = chunk.get("document", "")
            if current_length + len(text) > max_length:
                break
            context_parts.append(text)
            current_length += len(text)
        
        return "\n\n".join(context_parts)


@dataclass
class IndexStatus:
    """索引状态"""
    job_id: str
    indexed: bool
    chunk_count: int
    index_time: Optional[float] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "indexed": self.indexed,
            "chunk_count": self.chunk_count,
            "index_time": self.index_time,
            "error": self.error
        }


class RAGService:
    """
    RAG 检索增强生成服务
    
    功能：
    - 文档索引：将 OCR 结果分块并存入向量库
    - 相似检索：根据查询检索相关文档片段
    - 上下文构建：为 LLM 构建检索增强的上下文
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        vector_store: VectorStore = None,
        chunk_size: int = None,
        chunk_overlap: int = None,
        top_k: int = None
    ):
        """
        初始化 RAG 服务
        
        Args:
            embedding_service: Embedding 服务实例
            vector_store: 向量存储实例
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            top_k: 默认检索数量
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()
        
        # 从配置加载参数
        from backend.config import ChatOCRConfig
        self.chunk_size = chunk_size or ChatOCRConfig.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or ChatOCRConfig.CHUNK_OVERLAP
        self.top_k = top_k or ChatOCRConfig.RAG_TOP_K
        
        self.chunker = TextChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        
        # 索引状态缓存
        self._index_status: Dict[str, IndexStatus] = {}
        
        logger.info("RAGService initialized")
    
    def _get_collection_name(self, job_id: str) -> str:
        """生成集合名称"""
        return f"doc_{job_id}"
    
    def index_document(
        self,
        job_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ) -> IndexStatus:
        """
        索引单个文档
        
        Args:
            job_id: 任务ID
            text: 文档文本
            metadata: 额外元数据
            
        Returns:
            IndexStatus: 索引状态
        """
        start_time = time.time()
        collection_name = self._get_collection_name(job_id)
        
        try:
            # 文本分块
            chunks = self.chunker.chunk_text(text)
            
            if not chunks:
                logger.warning(f"No chunks generated for job {job_id}")
                status = IndexStatus(
                    job_id=job_id,
                    indexed=False,
                    chunk_count=0,
                    error="No valid text chunks"
                )
                self._index_status[job_id] = status
                return status
            
            # 提取文本和元数据
            texts = self.chunker.get_chunk_texts(chunks)
            metadatas = self.chunker.get_chunk_metadatas(chunks)
            
            # 添加额外元数据
            if metadata:
                for m in metadatas:
                    m.update(metadata)
            
            # 生成向量
            embeddings = self.embedding_service.encode_documents(texts)
            
            # 生成 ID
            ids = [f"{job_id}_chunk_{i}" for i in range(len(texts))]
            
            # 存入向量库
            success = self.vector_store.add_documents(
                collection_name=collection_name,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            index_time = time.time() - start_time
            
            if success:
                status = IndexStatus(
                    job_id=job_id,
                    indexed=True,
                    chunk_count=len(chunks),
                    index_time=index_time
                )
                logger.info(f"Indexed {len(chunks)} chunks for job {job_id} in {index_time:.2f}s")
            else:
                status = IndexStatus(
                    job_id=job_id,
                    indexed=False,
                    chunk_count=0,
                    error="Failed to store vectors"
                )
            
            self._index_status[job_id] = status
            return status
            
        except Exception as e:
            logger.error(f"Failed to index document {job_id}: {e}")
            status = IndexStatus(
                job_id=job_id,
                indexed=False,
                chunk_count=0,
                error=str(e)
            )
            self._index_status[job_id] = status
            return status
    
    def index_pages(
        self,
        job_id: str,
        pages: List[Dict],
        text_key: str = "text",
        page_key: str = "page"
    ) -> IndexStatus:
        """
        索引多页文档
        
        Args:
            job_id: 任务ID
            pages: 页面列表
            text_key: 文本字段名
            page_key: 页码字段名
            
        Returns:
            IndexStatus: 索引状态
        """
        start_time = time.time()
        collection_name = self._get_collection_name(job_id)
        
        try:
            # 对所有页面进行分块
            all_chunks = self.chunker.chunk_pages(pages, text_key, page_key)
            
            if not all_chunks:
                status = IndexStatus(
                    job_id=job_id,
                    indexed=False,
                    chunk_count=0,
                    error="No valid text chunks from pages"
                )
                self._index_status[job_id] = status
                return status
            
            # 提取文本和元数据
            texts = self.chunker.get_chunk_texts(all_chunks)
            metadatas = self.chunker.get_chunk_metadatas(all_chunks)
            
            # 生成向量
            embeddings = self.embedding_service.encode_documents(texts)
            
            # 生成 ID
            ids = [f"{job_id}_chunk_{i}" for i in range(len(texts))]
            
            # 存入向量库
            success = self.vector_store.add_documents(
                collection_name=collection_name,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            index_time = time.time() - start_time
            
            if success:
                status = IndexStatus(
                    job_id=job_id,
                    indexed=True,
                    chunk_count=len(all_chunks),
                    index_time=index_time
                )
                logger.info(f"Indexed {len(all_chunks)} chunks from {len(pages)} pages for job {job_id}")
            else:
                status = IndexStatus(
                    job_id=job_id,
                    indexed=False,
                    chunk_count=0,
                    error="Failed to store vectors"
                )
            
            self._index_status[job_id] = status
            return status
            
        except Exception as e:
            logger.error(f"Failed to index pages for {job_id}: {e}")
            status = IndexStatus(
                job_id=job_id,
                indexed=False,
                chunk_count=0,
                error=str(e)
            )
            self._index_status[job_id] = status
            return status
    
    def retrieve(
        self,
        job_id: str,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict] = None
    ) -> RetrievalResult:
        """
        检索相关文档片段
        
        Args:
            job_id: 任务ID
            query: 查询文本
            top_k: 返回数量
            filter_metadata: 元数据过滤条件
            
        Returns:
            RetrievalResult: 检索结果
        """
        start_time = time.time()
        top_k = top_k or self.top_k
        collection_name = self._get_collection_name(job_id)
        
        try:
            # 检查索引是否存在
            if not self.vector_store.collection_exists(collection_name):
                logger.warning(f"Collection not found for job {job_id}")
                return RetrievalResult(
                    query=query,
                    chunks=[],
                    total_found=0,
                    processing_time=time.time() - start_time
                )
            
            # 生成查询向量
            query_embedding = self.embedding_service.encode_query(query)
            
            # 执行检索
            results = self.vector_store.query(
                collection_name=collection_name,
                query_embedding=query_embedding,
                n_results=top_k,
                where=filter_metadata
            )
            
            # 格式化结果
            chunks = results.get_formatted_results()
            
            processing_time = time.time() - start_time
            
            logger.debug(f"Retrieved {len(chunks)} chunks for query in {processing_time:.3f}s")
            
            return RetrievalResult(
                query=query,
                chunks=chunks,
                total_found=len(chunks),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Retrieval failed for job {job_id}: {e}")
            return RetrievalResult(
                query=query,
                chunks=[],
                total_found=0,
                processing_time=time.time() - start_time
            )
    
    def get_index_status(self, job_id: str) -> IndexStatus:
        """
        获取索引状态
        
        Args:
            job_id: 任务ID
            
        Returns:
            IndexStatus: 索引状态
        """
        # 先检查缓存
        if job_id in self._index_status:
            return self._index_status[job_id]
        
        # 检查向量库
        collection_name = self._get_collection_name(job_id)
        if self.vector_store.collection_exists(collection_name):
            count = self.vector_store.get_collection_count(collection_name)
            status = IndexStatus(
                job_id=job_id,
                indexed=count > 0,
                chunk_count=count
            )
        else:
            status = IndexStatus(
                job_id=job_id,
                indexed=False,
                chunk_count=0
            )
        
        self._index_status[job_id] = status
        return status
    
    def delete_index(self, job_id: str) -> bool:
        """
        删除文档索引
        
        Args:
            job_id: 任务ID
            
        Returns:
            bool: 是否成功
        """
        collection_name = self._get_collection_name(job_id)
        success = self.vector_store.delete_collection(collection_name)
        
        if success and job_id in self._index_status:
            del self._index_status[job_id]
        
        return success
    
    def build_context(
        self,
        job_id: str,
        query: str,
        max_context_length: int = 4000,
        top_k: int = None
    ) -> str:
        """
        为 LLM 构建检索增强的上下文
        
        Args:
            job_id: 任务ID
            query: 查询文本
            max_context_length: 最大上下文长度
            top_k: 检索数量
            
        Returns:
            str: 构建的上下文
        """
        results = self.retrieve(job_id, query, top_k)
        return results.get_context(max_context_length)
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "embedding_service": self.embedding_service.get_status(),
            "vector_store": self.vector_store.get_status(),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "indexed_documents": len(self._index_status)
        }


# 全局实例
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    获取 RAG 服务实例
    
    Returns:
        RAGService: 服务实例
    """
    global _rag_service
    
    if _rag_service is None:
        _rag_service = RAGService()
    
    return _rag_service


def reset_rag_service():
    """重置服务实例（用于测试）"""
    global _rag_service
    _rag_service = None
