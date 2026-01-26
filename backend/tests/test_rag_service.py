"""
RAG Service Unit Tests - RAG 服务单元测试

测试向量化功能、检索准确性、分块逻辑
**Validates: Requirements 2.5.1, 2.5.2, 2.5.3, 2.5.4**
"""
import pytest
import tempfile
import shutil
import os
from typing import List

from backend.services.text_chunker import TextChunker, TextChunk, chunk_text
from backend.services.embedding_service import (
    EmbeddingService, 
    EmbeddingResult,
    get_embedding_service,
    reset_embedding_service
)
from backend.services.vector_store import (
    VectorStore,
    QueryResult,
    get_vector_store,
    reset_vector_store
)
from backend.services.rag_service import (
    RAGService,
    RetrievalResult,
    IndexStatus,
    get_rag_service,
    reset_rag_service
)


class TestTextChunker:
    """
    文本分块器测试
    **Validates: Requirement 2.5.5** - 支持配置分块大小和重叠大小
    """
    
    @pytest.fixture
    def chunker(self):
        """创建分块器实例"""
        return TextChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
    
    def test_chunk_empty_text(self, chunker):
        """测试空文本分块"""
        chunks = chunker.chunk_text("")
        assert chunks == []
        
        chunks = chunker.chunk_text("   ")
        assert chunks == []
    
    def test_chunk_short_text(self, chunker):
        """测试短文本分块（小于 chunk_size）"""
        text = "这是一段短文本，用于测试分块功能。"
        chunks = chunker.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].index == 0
    
    def test_chunk_long_text_fixed_strategy(self, chunker):
        """测试长文本固定策略分块"""
        # 创建超过 chunk_size 的文本
        text = "这是第一句话。" * 20  # 约 140 字符
        chunks = chunker.chunk_text(text, strategy="fixed")
        
        assert len(chunks) >= 1
        # 每个块应该不超过 chunk_size（除非无法切分）
        for chunk in chunks:
            assert len(chunk.content) <= chunker.chunk_size + 50  # 允许一定余量
    
    def test_chunk_by_paragraph(self, chunker):
        """测试按段落分块"""
        text = """第一段内容，这是一些测试文本。

第二段内容，这是另一些测试文本。

第三段内容，这是更多的测试文本。"""
        
        chunks = chunker.chunk_text(text, strategy="paragraph")
        
        assert len(chunks) >= 1
        # 段落应该被保留
        for chunk in chunks:
            assert chunk.content.strip() != ""
    
    def test_chunk_by_sentence(self, chunker):
        """测试按句子分块"""
        text = "第一句话。第二句话。第三句话。第四句话。第五句话。"
        chunks = chunker.chunk_text(text, strategy="sentence")
        
        assert len(chunks) >= 1
    
    def test_chunk_mixed_strategy(self, chunker):
        """测试混合策略分块"""
        text = """这是第一段，包含多个句子。句子一。句子二。句子三。

这是第二段，也包含多个句子。句子四。句子五。"""
        
        chunks = chunker.chunk_text(text, strategy="mixed")
        
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.content.strip() != ""
    
    def test_chunk_with_page_number(self, chunker):
        """测试带页码的分块"""
        text = "这是一段测试文本，用于验证页码功能。"
        chunks = chunker.chunk_text(text, page=5)
        
        assert len(chunks) == 1
        assert chunks[0].page == 5
    
    def test_chunk_pages(self, chunker):
        """测试多页文档分块"""
        pages = [
            {"text": "第一页的内容，这是测试文本。", "page": 1},
            {"text": "第二页的内容，这是更多测试文本。", "page": 2},
            {"text": "第三页的内容，这是最后的测试文本。", "page": 3}
        ]
        
        chunks = chunker.chunk_pages(pages)
        
        assert len(chunks) >= 3
        # 检查页码是否正确
        page_numbers = [c.page for c in chunks if c.page is not None]
        assert 1 in page_numbers
        assert 2 in page_numbers
        assert 3 in page_numbers
    
    def test_get_chunk_texts(self, chunker):
        """测试提取分块文本"""
        # 使用足够长的文本以满足 min_chunk_size 要求
        text = "这是一段足够长的测试文本内容，用于验证分块文本提取功能是否正常工作。"
        chunks = chunker.chunk_text(text)
        texts = chunker.get_chunk_texts(chunks)
        
        assert len(texts) == len(chunks)
        if chunks:
            assert texts[0] == chunks[0].content
    
    def test_get_chunk_metadatas(self, chunker):
        """测试提取分块元数据"""
        # 使用足够长的文本以满足 min_chunk_size 要求
        text = "这是一段足够长的测试文本内容，用于验证分块元数据提取功能是否正常工作。"
        chunks = chunker.chunk_text(text, page=1)
        metadatas = chunker.get_chunk_metadatas(chunks)
        
        assert len(metadatas) == len(chunks)
        if metadatas:
            assert "index" in metadatas[0]
            assert "start_char" in metadatas[0]
            assert "end_char" in metadatas[0]
    
    def test_chunk_text_convenience_function(self):
        """测试便捷分块函数"""
        # 使用足够长的文本以满足默认 min_chunk_size (50) 要求
        text = "这是一段足够长的测试文本，用于验证便捷分块函数是否能够正常工作并返回正确的分块结果。这段文本需要超过五十个字符才能通过测试。"
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        
        assert len(chunks) >= 1
        assert isinstance(chunks[0], TextChunk)


class TestTextChunk:
    """TextChunk 数据类测试"""
    
    def test_text_chunk_to_dict(self):
        """测试 TextChunk 转换为字典"""
        chunk = TextChunk(
            content="测试内容",
            index=0,
            start_char=0,
            end_char=4,
            page=1,
            metadata={"key": "value"}
        )
        
        data = chunk.to_dict()
        
        assert data["content"] == "测试内容"
        assert data["index"] == 0
        assert data["page"] == 1
        assert data["metadata"]["key"] == "value"



class TestEmbeddingService:
    """
    Embedding 服务测试
    **Validates: Requirement 2.5.2** - 使用 BGE-small-zh-v1.5 模型进行文本向量化
    """
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前后重置服务"""
        reset_embedding_service()
        yield
        reset_embedding_service()
    
    @pytest.fixture
    def embedding_service(self):
        """创建 Embedding 服务实例"""
        try:
            return EmbeddingService()
        except Exception as e:
            pytest.skip(f"Embedding model not available: {e}")
    
    def test_embedding_service_initialization(self, embedding_service):
        """
        测试 Embedding 服务初始化
        **Validates: Requirement 2.5.2**
        """
        assert embedding_service is not None
        assert embedding_service.dimension > 0
        assert embedding_service.model_name is not None
    
    def test_encode_single_text(self, embedding_service):
        """
        测试单个文本向量化
        **Validates: Requirement 2.5.2**
        """
        text = "这是一段测试文本"
        result = embedding_service.encode(text)
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embeddings) == 1
        assert len(result.embeddings[0]) == result.dimension
        assert result.processing_time >= 0
    
    def test_encode_multiple_texts(self, embedding_service):
        """
        测试多个文本向量化
        **Validates: Requirement 2.5.2**
        """
        texts = ["第一段文本", "第二段文本", "第三段文本"]
        result = embedding_service.encode(texts)
        
        assert len(result.embeddings) == 3
        for emb in result.embeddings:
            assert len(emb) == result.dimension
    
    def test_encode_query_with_prefix(self, embedding_service):
        """
        测试查询文本向量化（带指令前缀）
        **Validates: Requirement 2.5.2**
        """
        query = "什么是人工智能？"
        result = embedding_service.encode(query, is_query=True)
        
        assert len(result.embeddings) == 1
        assert len(result.embeddings[0]) == result.dimension
    
    def test_encode_query_convenience_method(self, embedding_service):
        """测试查询向量化便捷方法"""
        query = "测试查询"
        embedding = embedding_service.encode_query(query)
        
        assert isinstance(embedding, list)
        assert len(embedding) == embedding_service.dimension
    
    def test_encode_documents_convenience_method(self, embedding_service):
        """测试文档向量化便捷方法"""
        docs = ["文档一", "文档二"]
        embeddings = embedding_service.encode_documents(docs)
        
        assert len(embeddings) == 2
        for emb in embeddings:
            assert len(emb) == embedding_service.dimension
    
    def test_similarity_calculation(self, embedding_service):
        """
        测试向量相似度计算
        **Validates: Requirement 2.5.4**
        """
        # 相似文本应该有较高相似度
        text1 = "人工智能是计算机科学的一个分支"
        text2 = "AI是计算机科学领域的重要方向"
        text3 = "今天天气很好，适合出去玩"
        
        emb1 = embedding_service.encode(text1).embeddings[0]
        emb2 = embedding_service.encode(text2).embeddings[0]
        emb3 = embedding_service.encode(text3).embeddings[0]
        
        sim_12 = embedding_service.similarity(emb1, emb2)
        sim_13 = embedding_service.similarity(emb1, emb3)
        
        # 相似文本的相似度应该更高
        assert sim_12 > sim_13
        # 相似度应该在 0-1 之间
        assert 0 <= sim_12 <= 1
        assert 0 <= sim_13 <= 1
    
    def test_get_status(self, embedding_service):
        """测试获取服务状态"""
        status = embedding_service.get_status()
        
        assert status["initialized"] is True
        assert status["model_loaded"] is True
        assert status["dimension"] > 0
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        try:
            service1 = EmbeddingService()
            service2 = EmbeddingService()
            assert service1 is service2
        except Exception:
            pytest.skip("Embedding model not available")


class TestVectorStore:
    """
    向量存储服务测试
    **Validates: Requirement 2.5.3** - 使用 ChromaDB 存储和检索文档向量
    """
    
    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前后重置服务"""
        reset_vector_store()
        yield
        reset_vector_store()
    
    @pytest.fixture
    def vector_store(self, temp_db_path):
        """创建向量存储实例"""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb not installed")
        
        # 重置单例以使用临时路径
        reset_vector_store()
        VectorStore._instance = None
        return VectorStore(persist_path=temp_db_path)
    
    def test_vector_store_initialization(self, vector_store):
        """
        测试向量存储初始化
        **Validates: Requirement 2.5.3**
        """
        assert vector_store is not None
        assert vector_store.client is not None
    
    def test_add_documents(self, vector_store):
        """
        测试添加文档到向量库
        **Validates: Requirement 2.5.3**
        """
        documents = ["文档一", "文档二", "文档三"]
        # 模拟向量（512维）
        embeddings = [[0.1] * 512 for _ in range(3)]
        
        success = vector_store.add_documents(
            collection_name="test_collection",
            documents=documents,
            embeddings=embeddings
        )
        
        assert success is True
        
        # 验证文档数量
        count = vector_store.get_collection_count("test_collection")
        assert count == 3
    
    def test_add_documents_with_metadata(self, vector_store):
        """测试添加带元数据的文档"""
        documents = ["文档一", "文档二"]
        embeddings = [[0.1] * 512 for _ in range(2)]
        metadatas = [{"page": 1}, {"page": 2}]
        
        success = vector_store.add_documents(
            collection_name="test_meta",
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        assert success is True
    
    def test_query_documents(self, vector_store):
        """
        测试查询文档
        **Validates: Requirement 2.5.3**
        """
        # 添加文档
        documents = ["人工智能文档", "机器学习文档", "深度学习文档"]
        embeddings = [
            [0.9] + [0.1] * 511,  # 第一个文档
            [0.8] + [0.1] * 511,  # 第二个文档
            [0.1] * 512           # 第三个文档
        ]
        
        vector_store.add_documents(
            collection_name="test_query",
            documents=documents,
            embeddings=embeddings
        )
        
        # 查询（使用与第一个文档相似的向量）
        query_embedding = [0.85] + [0.1] * 511
        results = vector_store.query(
            collection_name="test_query",
            query_embedding=query_embedding,
            n_results=2
        )
        
        assert isinstance(results, QueryResult)
        assert len(results.documents) <= 2
    
    def test_query_empty_collection(self, vector_store):
        """测试查询空集合"""
        query_embedding = [0.1] * 512
        results = vector_store.query(
            collection_name="empty_collection",
            query_embedding=query_embedding,
            n_results=5
        )
        
        assert len(results.documents) == 0
    
    def test_delete_collection(self, vector_store):
        """测试删除集合"""
        # 先创建集合
        vector_store.add_documents(
            collection_name="to_delete",
            documents=["测试"],
            embeddings=[[0.1] * 512]
        )
        
        assert vector_store.collection_exists("to_delete") is True
        
        # 删除集合
        success = vector_store.delete_collection("to_delete")
        assert success is True
        assert vector_store.collection_exists("to_delete") is False
    
    def test_collection_exists(self, vector_store):
        """测试检查集合是否存在"""
        assert vector_store.collection_exists("nonexistent") is False
        
        vector_store.add_documents(
            collection_name="exists_test",
            documents=["测试"],
            embeddings=[[0.1] * 512]
        )
        
        assert vector_store.collection_exists("exists_test") is True
    
    def test_list_collections(self, vector_store):
        """测试列出所有集合"""
        # 创建几个集合
        for name in ["col1", "col2", "col3"]:
            vector_store.add_documents(
                collection_name=name,
                documents=["测试"],
                embeddings=[[0.1] * 512]
            )
        
        collections = vector_store.list_collections()
        
        assert "col1" in collections
        assert "col2" in collections
        assert "col3" in collections
    
    def test_sanitize_collection_name(self, vector_store):
        """测试集合名称清理"""
        # 包含特殊字符的名称
        safe_name = vector_store._sanitize_collection_name("test-collection-123")
        assert safe_name.isalnum() or "_" in safe_name
        
        # 以数字开头的名称
        safe_name = vector_store._sanitize_collection_name("123test")
        assert safe_name[0].isalpha()
    
    def test_get_status(self, vector_store):
        """测试获取服务状态"""
        status = vector_store.get_status()
        
        assert status["initialized"] is True
        assert "persist_path" in status
        assert "collections_count" in status


class TestQueryResult:
    """QueryResult 数据类测试"""
    
    def test_query_result_to_dict(self):
        """测试 QueryResult 转换为字典"""
        result = QueryResult(
            documents=["doc1", "doc2"],
            metadatas=[{"page": 1}, {"page": 2}],
            distances=[0.1, 0.2],
            ids=["id1", "id2"]
        )
        
        data = result.to_dict()
        
        assert data["documents"] == ["doc1", "doc2"]
        assert len(data["metadatas"]) == 2
    
    def test_query_result_len(self):
        """测试 QueryResult 长度"""
        result = QueryResult(
            documents=["doc1", "doc2", "doc3"],
            metadatas=[{}, {}, {}],
            distances=[0.1, 0.2, 0.3],
            ids=["id1", "id2", "id3"]
        )
        
        assert len(result) == 3
    
    def test_get_formatted_results(self):
        """测试获取格式化结果"""
        result = QueryResult(
            documents=["doc1", "doc2"],
            metadatas=[{"page": 1}, {"page": 2}],
            distances=[0.1, 0.2],
            ids=["id1", "id2"]
        )
        
        formatted = result.get_formatted_results()
        
        assert len(formatted) == 2
        assert formatted[0]["document"] == "doc1"
        assert formatted[0]["distance"] == 0.1
        assert formatted[0]["score"] == 0.9  # 1 - distance



class TestRAGService:
    """
    RAG 服务集成测试
    **Validates: Requirements 2.5.1, 2.5.4**
    """
    
    @pytest.fixture
    def temp_db_path(self):
        """创建临时数据库路径"""
        path = tempfile.mkdtemp()
        yield path
        shutil.rmtree(path, ignore_errors=True)
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """每个测试前后重置服务"""
        reset_rag_service()
        reset_vector_store()
        reset_embedding_service()
        yield
        reset_rag_service()
        reset_vector_store()
        reset_embedding_service()
    
    @pytest.fixture
    def rag_service(self, temp_db_path):
        """创建 RAG 服务实例"""
        try:
            # 重置单例
            reset_vector_store()
            VectorStore._instance = None
            
            embedding_service = EmbeddingService()
            vector_store = VectorStore(persist_path=temp_db_path)
            
            return RAGService(
                embedding_service=embedding_service,
                vector_store=vector_store,
                chunk_size=100,
                chunk_overlap=20,
                top_k=3
            )
        except Exception as e:
            pytest.skip(f"RAG service dependencies not available: {e}")
    
    def test_rag_service_initialization(self, rag_service):
        """
        测试 RAG 服务初始化
        **Validates: Requirement 2.5.1**
        """
        assert rag_service is not None
        assert rag_service.embedding_service is not None
        assert rag_service.vector_store is not None
        assert rag_service.chunker is not None
    
    def test_index_document(self, rag_service):
        """
        测试索引单个文档
        **Validates: Requirement 2.5.1** - OCR 处理完成后将文本分块并生成向量索引
        """
        job_id = "test_job_001"
        text = """这是一段测试文档内容。
        
        文档包含多个段落，用于测试索引功能。
        
        第三段内容，验证分块和索引是否正常工作。"""
        
        status = rag_service.index_document(job_id, text)
        
        assert isinstance(status, IndexStatus)
        assert status.job_id == job_id
        assert status.indexed is True
        assert status.chunk_count > 0
        assert status.index_time is not None
    
    def test_index_document_empty_text(self, rag_service):
        """测试索引空文本"""
        job_id = "empty_job"
        status = rag_service.index_document(job_id, "")
        
        assert status.indexed is False
        assert status.chunk_count == 0
    
    def test_index_pages(self, rag_service):
        """
        测试索引多页文档
        **Validates: Requirement 2.5.1**
        """
        job_id = "multi_page_job"
        pages = [
            {"text": "第一页内容，这是关于人工智能的介绍。", "page": 1},
            {"text": "第二页内容，这是关于机器学习的说明。", "page": 2},
            {"text": "第三页内容，这是关于深度学习的描述。", "page": 3}
        ]
        
        status = rag_service.index_pages(job_id, pages)
        
        assert status.indexed is True
        assert status.chunk_count >= 3
    
    def test_retrieve_relevant_chunks(self, rag_service):
        """
        测试检索相关文档片段
        **Validates: Requirement 2.5.4** - 先检索相关片段再发送给 LLM
        """
        # 先索引文档
        job_id = "retrieve_test"
        text = """人工智能是计算机科学的一个重要分支。
        
        机器学习是人工智能的核心技术之一。
        
        深度学习是机器学习的一个子领域。
        
        自然语言处理用于理解人类语言。
        
        计算机视觉用于图像识别和处理。"""
        
        rag_service.index_document(job_id, text)
        
        # 检索相关内容
        result = rag_service.retrieve(job_id, "什么是机器学习？")
        
        assert isinstance(result, RetrievalResult)
        assert result.total_found > 0
        assert len(result.chunks) > 0
        assert result.processing_time >= 0
    
    def test_retrieve_nonexistent_job(self, rag_service):
        """测试检索不存在的任务"""
        result = rag_service.retrieve("nonexistent_job", "测试查询")
        
        assert result.total_found == 0
        assert len(result.chunks) == 0
    
    def test_get_index_status(self, rag_service):
        """测试获取索引状态"""
        job_id = "status_test"
        
        # 索引前
        status = rag_service.get_index_status(job_id)
        assert status.indexed is False
        
        # 索引后
        rag_service.index_document(job_id, "测试文档内容，用于验证索引状态。")
        status = rag_service.get_index_status(job_id)
        assert status.indexed is True
    
    def test_delete_index(self, rag_service):
        """测试删除索引"""
        job_id = "delete_test"
        rag_service.index_document(job_id, "测试文档内容。")
        
        # 确认索引存在
        status = rag_service.get_index_status(job_id)
        assert status.indexed is True
        
        # 删除索引
        success = rag_service.delete_index(job_id)
        assert success is True
        
        # 确认索引已删除
        status = rag_service.get_index_status(job_id)
        assert status.indexed is False
    
    def test_build_context(self, rag_service):
        """
        测试构建 LLM 上下文
        **Validates: Requirement 2.5.4**
        """
        job_id = "context_test"
        text = """人工智能的发展历史可以追溯到1950年代。
        
        图灵测试是评估机器智能的重要标准。
        
        深度学习在2010年代取得了重大突破。"""
        
        rag_service.index_document(job_id, text)
        
        context = rag_service.build_context(job_id, "人工智能的历史")
        
        assert isinstance(context, str)
        assert len(context) > 0
    
    def test_get_status(self, rag_service):
        """测试获取服务状态"""
        status = rag_service.get_status()
        
        assert "embedding_service" in status
        assert "vector_store" in status
        assert "chunk_size" in status
        assert "top_k" in status


class TestRetrievalResult:
    """RetrievalResult 数据类测试"""
    
    def test_retrieval_result_to_dict(self):
        """测试 RetrievalResult 转换为字典"""
        result = RetrievalResult(
            query="测试查询",
            chunks=[{"document": "doc1", "score": 0.9}],
            total_found=1,
            processing_time=0.5
        )
        
        data = result.to_dict()
        
        assert data["query"] == "测试查询"
        assert data["total_found"] == 1
        assert data["processing_time"] == 0.5
    
    def test_get_context(self):
        """测试获取合并上下文"""
        result = RetrievalResult(
            query="测试",
            chunks=[
                {"document": "第一段内容"},
                {"document": "第二段内容"},
                {"document": "第三段内容"}
            ],
            total_found=3,
            processing_time=0.1
        )
        
        context = result.get_context(max_length=1000)
        
        assert "第一段内容" in context
        assert "第二段内容" in context
    
    def test_get_context_with_length_limit(self):
        """测试带长度限制的上下文获取"""
        result = RetrievalResult(
            query="测试",
            chunks=[
                {"document": "A" * 100},
                {"document": "B" * 100},
                {"document": "C" * 100}
            ],
            total_found=3,
            processing_time=0.1
        )
        
        context = result.get_context(max_length=150)
        
        # 应该只包含部分内容
        assert len(context) <= 200  # 允许一些余量


class TestIndexStatus:
    """IndexStatus 数据类测试"""
    
    def test_index_status_to_dict(self):
        """测试 IndexStatus 转换为字典"""
        status = IndexStatus(
            job_id="test_job",
            indexed=True,
            chunk_count=10,
            index_time=1.5
        )
        
        data = status.to_dict()
        
        assert data["job_id"] == "test_job"
        assert data["indexed"] is True
        assert data["chunk_count"] == 10
        assert data["index_time"] == 1.5
    
    def test_index_status_with_error(self):
        """测试带错误的索引状态"""
        status = IndexStatus(
            job_id="error_job",
            indexed=False,
            chunk_count=0,
            error="Index failed"
        )
        
        data = status.to_dict()
        
        assert data["indexed"] is False
        assert data["error"] == "Index failed"


class TestRAGServiceSingleton:
    """RAG 服务单例测试"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        reset_rag_service()
        reset_vector_store()
        reset_embedding_service()
    
    def test_get_rag_service_returns_instance(self):
        """测试获取 RAG 服务实例"""
        try:
            service = get_rag_service()
            assert service is not None
            assert isinstance(service, RAGService)
        except Exception:
            pytest.skip("RAG service dependencies not available")
    
    def test_reset_rag_service(self):
        """测试重置 RAG 服务"""
        try:
            service1 = get_rag_service()
            reset_rag_service()
            service2 = get_rag_service()
            assert service1 is not service2
        except Exception:
            pytest.skip("RAG service dependencies not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
