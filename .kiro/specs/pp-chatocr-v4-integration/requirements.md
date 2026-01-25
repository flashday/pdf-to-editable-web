# Requirements Document: PP-ChatOCRv4 智能文档理解集成

## Introduction

本功能在现有 PDF to Editable Web Layout 系统基础上，集成 PP-ChatOCRv4 智能文档理解能力。通过结合 PaddleOCR 的 OCR 能力和本地部署的 Ollama LLM，实现文档关键信息自动提取和智能问答功能。该升级作为增强功能，不影响现有 OCR 处理流程。

## Glossary

- **PP-ChatOCRv4**: PaddleOCR 3.0 推出的智能文档理解 Pipeline，结合 OCR 和 LLM 能力
- **Ollama**: 本地 LLM 运行框架，支持多种开源大语言模型
- **LLM**: Large Language Model，大语言模型
- **RAG**: Retrieval-Augmented Generation，检索增强生成，先检索相关内容再生成回答
- **Embedding**: 文本向量化，将文本转换为数值向量用于语义检索
- **Embedding Model**: 向量化模型，本项目使用 BGE-small-zh-v1.5
- **Vector Database**: 向量数据库，存储和检索文本向量，本项目使用 ChromaDB
- **Key Information Extraction**: 关键信息提取，从文档中自动提取指定字段
- **Document QA**: 文档问答，基于文档内容回答用户问题
- **Existing_OCR_System**: 现有的 PPStructureV3 OCR 处理系统
- **Text Chunking**: 文本分块，将长文档切分为适合检索的片段

## Requirements

### Requirement 1: LLM 服务连接与配置

**User Story:** 作为系统管理员，我希望系统能够连接本地 Ollama LLM 服务，以便为智能文档理解提供语言模型支持。

#### Acceptance Criteria

1. WHEN 系统启动时，THE System SHALL 检测 Ollama 服务是否可用（默认地址 http://localhost:11434）
2. WHEN Ollama 服务不可用时，THE System SHALL 记录警告日志但不影响现有 OCR 功能
3. WHEN 用户配置 LLM 模型名称时，THE System SHALL 验证该模型在 Ollama 中是否存在
4. THE System SHALL 支持通过配置文件或环境变量设置 Ollama 服务地址和模型名称
5. WHEN LLM 调用超时时，THE System SHALL 在 60 秒后返回超时错误

### Requirement 2: PP-ChatOCRv4 Pipeline 集成

**User Story:** 作为开发者，我希望系统集成 PP-ChatOCRv4 Pipeline，以便利用其智能文档理解能力。

#### Acceptance Criteria

1. WHEN 安装依赖时，THE System SHALL 安装 PaddleX 及其 OCR 组件
2. WHEN 初始化 PP-ChatOCRv4 时，THE System SHALL 配置使用 Ollama 作为 LLM 后端
3. THE System SHALL 支持配置 chat_bot_config 参数连接本地 Ollama
4. WHEN PP-ChatOCRv4 初始化失败时，THE System SHALL 回退到现有 OCR 功能并记录错误
5. THE System SHALL 复用现有 OCR 处理结果，避免重复 OCR 识别

### Requirement 2.5: 向量检索（RAG）系统

**User Story:** 作为用户，我希望系统能够智能检索多页 PDF 中的相关内容，以便在不发送全部文档内容的情况下准确回答问题。

#### Acceptance Criteria

1. WHEN 文档 OCR 处理完成后，THE System SHALL 将文本分块并生成向量索引
2. THE System SHALL 使用 BGE-small-zh-v1.5 模型进行文本向量化
3. THE System SHALL 使用 ChromaDB 存储和检索文档向量
4. WHEN 用户提问或提取信息时，THE System SHALL 先检索相关片段（Top-K），再发送给 LLM
5. THE System SHALL 支持配置分块大小（默认 500 字符）和重叠大小（默认 50 字符）
6. WHEN 向量检索服务不可用时，THE System SHALL 回退到全文发送模式并记录警告

### Requirement 3: 关键信息提取功能

**User Story:** 作为用户，我希望系统能够自动从文档中提取关键信息（如发票号、金额、日期等），以便快速获取所需数据。

#### Acceptance Criteria

1. WHEN 用户指定提取字段列表时，THE System SHALL 从文档中提取对应信息
2. WHEN 提取完成时，THE System SHALL 返回 JSON 格式的字段-值对
3. THE System SHALL 提供预设模板（发票、合同、身份证、简历等）
4. WHEN 字段未找到时，THE System SHALL 返回该字段值为 "未找到" 或 null
5. WHEN 提取结果置信度低时，THE System SHALL 在返回结果中标注警告
6. THE System SHALL 支持用户自定义提取字段

### Requirement 4: 文档问答功能

**User Story:** 作为用户，我希望能够用自然语言向系统提问关于文档内容的问题，以便快速理解文档。

#### Acceptance Criteria

1. WHEN 用户提交问题时，THE System SHALL 基于文档内容生成回答
2. WHEN 问题与文档内容无关时，THE System SHALL 返回 "无法从文档中找到相关信息"
3. THE System SHALL 在回答中引用文档中的相关原文
4. WHEN 文档内容不足以回答问题时，THE System SHALL 明确告知用户
5. THE System SHALL 支持中英文问答

### Requirement 5: API 接口设计

**User Story:** 作为前端开发者，我希望有清晰的 API 接口来调用智能文档理解功能。

#### Acceptance Criteria

1. THE System SHALL 提供 POST /api/extract-info 接口用于关键信息提取
2. THE System SHALL 提供 POST /api/document-qa 接口用于文档问答
3. THE System SHALL 提供 GET /api/llm/status 接口用于检查 LLM 服务状态
4. THE System SHALL 提供 GET /api/templates 接口用于获取预设提取模板
5. WHEN API 调用失败时，THE System SHALL 返回标准化的错误响应格式

### Requirement 6: 前端智能提取界面

**User Story:** 作为用户，我希望有直观的界面来使用智能提取和问答功能。

#### Acceptance Criteria

1. THE Web_Editor SHALL 在工具栏添加 "智能提取" 按钮
2. WHEN 用户点击智能提取时，THE System SHALL 显示模板选择和自定义字段输入界面
3. THE System SHALL 显示提取结果，支持复制和导出
4. THE Web_Editor SHALL 提供问答输入框，支持用户输入问题
5. THE System SHALL 显示问答历史记录
6. WHEN LLM 服务不可用时，THE System SHALL 禁用智能功能按钮并显示提示

### Requirement 7: 性能与资源管理

**User Story:** 作为系统管理员，我希望智能功能不会过度消耗系统资源。

#### Acceptance Criteria

1. WHEN 调用 LLM 时，THE System SHALL 限制单次请求的 token 数量（默认 4096）
2. THE System SHALL 缓存 OCR 结果，避免重复处理同一文档
3. WHEN 多个请求同时到达时，THE System SHALL 排队处理 LLM 请求
4. THE System SHALL 记录每次 LLM 调用的耗时和 token 使用量
5. WHEN 系统内存不足时，THE System SHALL 优先保证现有 OCR 功能正常运行

### Requirement 8: 错误处理与降级

**User Story:** 作为用户，我希望在智能功能出错时能够得到清晰的反馈，并且不影响基础功能使用。

#### Acceptance Criteria

1. WHEN LLM 服务不可用时，THE System SHALL 显示友好的错误提示
2. WHEN LLM 返回异常结果时，THE System SHALL 记录日志并返回错误信息
3. THE System SHALL 支持在 LLM 不可用时继续使用现有 OCR 功能
4. WHEN 提取或问答超时时，THE System SHALL 允许用户重试
5. THE System SHALL 提供 LLM 服务健康检查端点
