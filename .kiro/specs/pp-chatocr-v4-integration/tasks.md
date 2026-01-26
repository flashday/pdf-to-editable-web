# Implementation Plan: PP-ChatOCRv4 智能文档理解集成

## Overview

本实现计划将 PP-ChatOCRv4 智能文档理解能力集成到现有系统中。采用增量开发策略，先建立 LLM 服务连接和向量检索系统，再实现核心功能，最后完成前端界面。每个阶段都确保现有 OCR 功能不受影响。

## Tasks

- [x] 1. LLM 服务层实现
  - [x] 1.1 创建 Ollama LLM 服务封装
    - 创建 `backend/services/llm_service.py`
    - 实现 `OllamaLLMService` 类
    - 实现健康检查方法 `check_health()`
    - 实现聊天方法 `chat()`
    - 实现模型列表获取 `get_available_models()`
    - _Requirements: 1.1, 1.3, 1.4_

  - [x] 1.2 添加 LLM 配置管理
    - 在 `backend/config.py` 中添加 ChatOCR 配置类
    - 支持环境变量配置 Ollama 地址和模型
    - 添加功能开关配置
    - _Requirements: 1.4_

  - [x] 1.3 实现 LLM 服务超时和错误处理
    - 实现 60 秒超时机制
    - 实现连接失败重试逻辑
    - 实现优雅降级处理
    - _Requirements: 1.5, 8.1, 8.2_

  - [x] 1.4 编写 LLM 服务单元测试

    - 测试健康检查功能
    - 测试超时处理
    - 测试错误降级
    - **Validates: Requirements 1.1, 1.2, 1.5**

- [x] 2. 向量检索（RAG）系统实现
  - [x] 2.1 创建 Embedding 服务
    - 创建 `backend/services/embedding_service.py`
    - 实现 `EmbeddingService` 单例类
    - 集成 BGE-small-zh-v1.5 模型
    - 实现文本向量化方法
    - _Requirements: 2.5.2_

  - [x] 2.2 创建向量存储服务
    - 创建 `backend/services/vector_store.py`
    - 实现 `VectorStore` 类
    - 集成 ChromaDB
    - 实现文档添加和查询方法
    - _Requirements: 2.5.3_

  - [x] 2.3 实现文本分块器
    - 创建 `backend/services/text_chunker.py`
    - 实现按段落/章节分块
    - 支持配置分块大小（500字符）和重叠（50字符）
    - _Requirements: 2.5.5_

  - [x] 2.4 创建 RAG 服务
    - 创建 `backend/services/rag_service.py`
    - 实现 `RAGService` 类
    - 整合 Embedding 和 VectorStore
    - 实现文档索引和检索方法
    - _Requirements: 2.5.1, 2.5.4_

  - [x] 2.5 集成 RAG 到 OCR 处理流程
    - 在 OCR 完成后自动构建向量索引
    - 实现索引状态管理
    - 处理索引失败的降级逻辑
    - _Requirements: 2.5.1, 2.5.6_

  - [x] 2.6 编写 RAG 服务单元测试

    - 测试向量化功能
    - 测试检索准确性
    - 测试分块逻辑
    - **Validates: Requirements 2.5.1, 2.5.2, 2.5.3, 2.5.4**

- [x] 3. ChatOCR 核心服务实现
  - [x] 3.1 创建 ChatOCR 服务
    - 创建 `backend/services/chatocr_service.py`
    - 实现 `ChatOCRService` 类
    - 整合 LLM 服务和 RAG 服务
    - 实现预设模板加载
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 3.2 实现关键信息提取功能
    - 实现 `extract_info()` 方法
    - 实现提取 Prompt 模板
    - 实现 JSON 结果解析
    - 处理提取失败的降级逻辑
    - _Requirements: 3.1, 3.2, 3.4, 3.5_

  - [x] 3.3 实现文档问答功能
    - 实现 `document_qa()` 方法
    - 实现问答 Prompt 模板
    - 实现引用原文提取
    - 处理无法回答的情况
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 3.4 实现预设模板管理
    - 定义发票、合同、身份证、简历模板
    - 实现 `get_templates()` 方法
    - 支持自定义字段扩展
    - _Requirements: 3.3, 3.6_

- [x] 4. API 接口实现
  - [x] 4.1 创建 ChatOCR API 路由
    - 创建 `backend/api/chatocr_routes.py`
    - 实现路由蓝图注册
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 4.2 实现信息提取 API
    - 实现 POST /api/extract-info 接口
    - 实现请求参数验证
    - 实现响应格式标准化
    - _Requirements: 5.1, 5.5_

  - [x] 4.3 实现文档问答 API
    - 实现 POST /api/document-qa 接口
    - 实现请求参数验证
    - 实现响应格式标准化
    - _Requirements: 5.2, 5.5_

  - [x] 4.4 实现 LLM 状态和模板 API
    - 实现 GET /api/llm/status 接口
    - 实现 GET /api/templates 接口
    - _Requirements: 5.3, 5.4_

  - [x] 4.5 注册 API 路由到主应用
    - 在 `backend/app.py` 中注册蓝图
    - 配置 CORS 和错误处理
    - _Requirements: 5.5_

- [x] 5. 前端界面实现
  - [x] 5.1 创建智能提取面板组件
    - 创建 `frontend/src/components/SmartExtract.js`
    - 实现模板选择 UI
    - 实现自定义字段输入
    - 实现提取结果显示
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.2 创建文档问答面板组件
    - 创建 `frontend/src/components/DocumentQA.js`
    - 实现问答输入框
    - 实现回答显示和引用高亮
    - 实现问答历史记录
    - _Requirements: 6.4, 6.5_

  - [x] 5.3 集成智能功能到主界面
    - 在工具栏添加智能提取按钮
    - 添加问答面板入口
    - 实现 LLM 状态检测和禁用逻辑
    - _Requirements: 6.1, 6.6_

  - [x] 5.4 编写前端组件测试

    - 测试组件渲染
    - 测试 API 调用
    - 测试错误处理
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [x] 6. 集成测试与文档
  - [x] 6.1 编写集成测试
    - 测试完整提取流程
    - 测试完整问答流程
    - 测试降级场景
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 6.2 更新项目文档

    - 更新 README 添加智能功能说明
    - 添加 API 文档
    - 添加配置说明
    - _Requirements: 1.4, 5.1, 5.2_
