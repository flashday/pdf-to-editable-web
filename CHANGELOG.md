# 更新日志 (CHANGELOG)

记录每次代码提交的主要修改点，便于 Review 和追溯。

> **文档分工**：
> - `CHANGELOG.md` - 记录每次提交的技术细节（Bug修复、代码调整等）
> - `README.md` - 只记录功能变更、架构调整、用户可见的新特性

---

## [2026-01-26]

### 3e09306 - fix: 修复智能提取和问答按钮灰色不可用问题

**问题**：智能提取和问答按钮始终显示灰色，无法点击

**原因分析**：
1. `ChatOCRIntegration.js` 中 `checkLLMStatus()` 解析 API 响应时，只检查了 `data.data.available`，但 API 实际返回的是 `data.data.llm_available`
2. 初始化时序问题：`setTimeout(600)` 可能在 `window.app` 完全初始化之前执行

**修改文件**：
- `frontend/src/components/ChatOCRIntegration.js`
  - 修复 `checkLLMStatus()`: 同时检查 `available` 和 `llm_available`
  - 在 `updateButtonStates()` 中添加调试日志
- `frontend/src/index.html`
  - 延长初始化等待时间从 600ms 到 800ms
  - 添加 `window.app` 存在性检查
  - 添加调试日志

---

### 4353b5b - fix: 修复RAG/Embedding服务加载超时问题

**问题**：后端启动时 RAG/Embedding 服务加载卡住超时

**根因**：HuggingFace 网站无法访问，`SentenceTransformer` 每次加载都尝试检查远程更新

**修改文件**：
- `backend/services/embedding_service.py`
  - 在文件开头添加离线模式环境变量：
    ```python
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_DATASETS_OFFLINE'] = '1'
    ```
- `backend/api/chatocr_routes.py`
  - 修复 `/api/llm/status` 端点：在 RAG 加载中时返回"加载中"状态，不触发重复初始化
- `backend/app.py`
  - 后端服务改为顺序加载：LLM → OCR → RAG（避免并行冲突）

**效果**：
- Embedding 模型加载从超时变为 0.08 秒
- 总启动时间：约 63 秒（LLM 0s + OCR 60s + RAG 3s）

---

## [2026-01-25]

### ec87193 - feat: 完成 PP-ChatOCRv4 智能文档理解集成

**新增功能**：
- 智能信息提取（发票、合同、身份证、简历模板）
- 文档问答（基于 RAG 向量检索）
- 服务状态栏显示
- 对话日志导出

**新增文件**：
- `backend/services/llm_service.py` - Ollama LLM 服务封装
- `backend/services/embedding_service.py` - BGE 向量化服务
- `backend/services/vector_store.py` - ChromaDB 向量存储
- `backend/services/text_chunker.py` - 文本分块器
- `backend/services/rag_service.py` - RAG 检索服务
- `backend/services/chatocr_service.py` - ChatOCR 主服务
- `backend/api/chatocr_routes.py` - 智能功能 API 路由
- `frontend/src/components/SmartExtract.js` - 智能提取面板
- `frontend/src/components/DocumentQA.js` - 文档问答面板
- `frontend/src/components/ChatOCRIntegration.js` - 集成组件

---

### 1d7e5d6 - fix: 修复OCR结果下载按钮内容为空的问题

**问题**：点击"OCR结果"下载按钮后，JSON 文件中 `ocr_result` 数组为空

**根因**：`_convert_v3_result_to_legacy` 函数期望从 PaddleOCR 3.x 结果中直接获取字段，但 PPStructure 返回的数据在 `overall_ocr_res` 字段中

**修改文件**：
- `backend/services/ocr_service.py`
  - 修改 `_convert_v3_result_to_legacy` 函数
  - 首先检查 `overall_ocr_res` 字段
  - 添加 numpy array 到列表的转换

---

## 文档更新规则

### 需要更新 CHANGELOG.md 的情况：
- Bug 修复
- 代码重构
- 性能优化
- 配置调整
- 依赖更新

### 需要同时更新 README.md 的情况：
- 新增用户可见功能
- API 接口变更
- 架构调整
- 安装/配置方式变更
- 重要的使用说明
