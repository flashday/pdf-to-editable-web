# Implementation Plan: PP-ChatOCRv4 智能文档理解集成

## Overview

本实现计划将 PP-ChatOCRv4 智能文档理解能力集成到现有系统中。采用增量开发策略，先建立 LLM 服务连接和向量检索系统，再实现核心功能，最后完成前端界面。每个阶段都确保现有 OCR 功能不受影响。

## Tasks

- [ ] 1. LLM 服务层实现
  - [ ] 1.1 创建 Ollama LLM 服务封装
    - 创建 `backend/services/llm_service.py`
    - 实现 `OllamaLLMService` 类
    - 实现健康检查方法 `check_health()`
    - 实现聊天方法 `chat()`
    - 实现模型列表获取 `get_available_models()`
    - _Requirements: 1.1, 1.3, 1.4_

  - [ ] 1.2 添加 LLM 配置管理
    - 在 `backend/config.py` 中添加 ChatOCR 配置类
    - 支持环境变量配置 Ollama 地址和模型
    - 添加功能开关配置
    - _Requirements: 1.4_

  - [ ] 1.3 实现 LLM 服务超时和错误处理
    - 实现 60 秒超时机制
    - 实现连接失败重试逻辑
    - 实现优雅降级处理
    - _Requirements: 1.5, 8.1, 8.2_

  - [ ]* 1.4 编写 LLM 服务单元测试
    - 测试健康检查功能
    - 测试超时处理
    - 测试错误降级
    - **Validates: Requirements 1.1, 1.2, 1.5**

- [ ] 2. 向量检索（RAG）系统实现
  - [ ] 2.1 创建 Embedding 服务
    - 创建 `backend/services/embedding_service.py`
    - 实现 `EmbeddingService` 单例类
    - 集成 BGE-small-zh-v1.5 模型
    - 实现文本向量化方法
    - _Requirements: 2.5.2_

  - [ ] 2.2 创建向量存储服务
    - 创建 `backend/services/vector_store.py`
    - 实现 `VectorStore` 类
    - 集成 ChromaDB
    - 实现文档添加和查询方法
    - _Requirements: 2.5.3_

  - [ ] 2.3 实现文本分块器
    - 创建 `backend/services/text_chunker.py`
    - 实现按段落/章节分块
    - 支持配置分块大小（500字符）和重叠（50字符）
    - _Requirements: 2.5.5_

  - [ ] 2.4 创建 RAG 服务
    - 创建 `backend/services/rag_service.py`
    - 实现 `RAGService` 类
    - 整合 Embedding 和 VectorStore
    - 实现文档索引和检索方法
    - _Requirements: 2.5.1, 2.5.4_

  - [ ] 2.5 集成 RAG 到 OCR 处理流程
    - 在 OCR 完成后自动构建向量索引
    - 实现索引状态管理
    - 处理索引失败的降级逻辑
    - _Requirements: 2.5.1, 2.5.6_

  - [ ]* 2.6 编写 RAG 服务单元测试
    - 测试向量化功能
    - 测试检索准确性
    - 测试分块逻辑
    - **Validates: Requirements 2.5.1, 2.5.2, 2.5.3, 2.5.4**
