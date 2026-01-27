# 更新日志 (CHANGELOG)

记录每次代码提交的主要修改点，便于 Review 和追溯。

> **文档分工**：
> - `CHANGELOG.md` - 记录每次提交的技术细节（Bug修复、代码调整等）
> - `README.md` - 只记录功能变更、架构调整、用户可见的新特性

---

## [2026-01-27] - 界面布局优化：工具栏按钮和弹窗模式

### 新增：工具栏按钮（单据设定 & 历史缓存）

**需求**：将「单据设定」和「历史缓存」按钮移到顶部流程工具栏，点击后弹出子窗口

**实现内容**：

1. `frontend/src/index.html`
   - 在 workflow-steps 中添加两个工具栏按钮：`toolbarDocTypeBtn`（单据设定）和 `toolbarHistoryBtn`（历史缓存）
   - 移除右侧的 history-panel，改为弹窗模式（history-modal）
   - 添加历史缓存弹窗的 HTML 结构
   - 更新初始化脚本，添加弹窗显示/隐藏的事件处理
   - 更新版本号：`globalFunctions.js?v=21`

2. `frontend/src/styles/steps.css`
   - 添加工具栏按钮样式（.toolbar-btn, .toolbar-btn-config, .toolbar-btn-history）
   - 添加历史缓存弹窗样式（.history-modal, .history-modal-overlay 等）
   - 添加历史记录项样式（.history-panel-item, .history-item-header 等）

3. `frontend/src/utils/globalFunctions.js`
   - 更新 `loadHistoryPanel` 函数：
     - 同时获取历史记录和单据类型配置
     - 在历史记录项中显示「单据类型」标签
     - 使用新的 HTML 结构渲染历史列表
   - 新增 `loadCachedJobAndClose` 函数：点击历史记录后先关闭弹窗再加载缓存

### 优化：上传区域仅在步骤2显示

- 上传区域（uploadSection）在进入步骤3后自动隐藏
- 从历史缓存加载时也会隐藏上传区域

---

## [2026-01-27] - 步骤5/6状态管理修复 & 历史缓存单据类型恢复

### 修复：步骤6财务确认未显示步骤5提取的数据

**问题**：步骤6界面显示"暂无检查点结果"和空的JSON数据，没有正确读取步骤5保存的数据

**根因**：
- `Step5DataExtract.js` 中部分方法使用导入的 `stateManager` 保存数据
- `Step6Confirmation.js` 使用 `window.stateManager` 读取数据
- 两者不是同一个实例，导致数据无法传递

**修复内容**：

1. `frontend/src/components/steps/Step5DataExtract.js`
   - `selectTemplate()` 方法：使用 `window.stateManager || stateManager` 保存 `selectedTemplate`
   - `startExtraction()` 方法：使用 `globalStateManager` 保存 `extractedData` 和 `selectedTemplate`
   - `saveCheckpointsToBackend()` 方法：使用 `globalStateManager` 获取 `jobId`

2. `frontend/src/components/steps/Step6Confirmation.js`
   - `saveFinalResult()` 方法：使用 `globalStateManager` 获取 `jobId`
   - `showSuccessMessage()` 中的下载函数：使用 `globalSM` 获取 `finalResult`

3. `frontend/src/index.html`
   - 更新版本号：`Step5DataExtract.js?v=21`、`Step6Confirmation.js?v=18`

---

### 修复：历史缓存加载后步骤5未自动选择正确的单据类型

**问题**：用户缓存的是"出差报告"，但加载后步骤5显示的是"发票"模板

**根因**：
- `index.js` 和 `globalFunctions.js` 中存在两个同名的 `loadCachedJob` 方法
- 调用时使用了错误的方法，导致 `selectedDocumentTypeId` 未正确恢复

**修复内容**：

1. `frontend/src/index.js`
   - 删除重复的 `loadCachedJob` 方法
   - 历史面板点击事件改为调用 `window.loadCachedJob`

2. `frontend/src/utils/globalFunctions.js`
   - 统一使用 `window.loadCachedJob` 作为唯一入口
   - 添加详细的调试日志

3. `frontend/src/index.html`
   - 更新版本号：`globalFunctions.js?v=20`、`index.js?v=32`

---

## [2026-01-27] - 步骤5自动数据提取 + Job缓存增加单据类型

### 功能：步骤5自动执行提取和检查点

**功能描述**：
用户在步骤2上传文件时选择的单据类型会保存到 Job 缓存中，步骤5进入时自动加载对应的模板和检查点，并自动执行提取和检查点验证，无需人工操作。

**后端修改**：

1. `backend/services/job_cache.py`
   - `CachedJob` dataclass 添加 `document_type_id` 字段
   - `save_job()` 方法接收 `document_type_id` 参数
   - `load_cached_result()` 返回 `document_type_id`
   - `from_dict()` 添加旧数据兼容处理

2. `backend/api/routes.py`
   - `/api/convert` 上传接口从 form data 获取 `document_type_id`
   - `/api/jobs/history` 返回 `document_type_id`
   - `/api/jobs/latest` 返回 `document_type_id`

3. `backend/services/document_processor.py`
   - `save_job()` 调用传递 `document.document_type_id`

4. `backend/models/document.py`
   - `Document` 模型添加 `document_type_id: Optional[str]` 字段

**前端修改**：

1. `frontend/src/components/steps/Step2FileUpload.js`
   - 上传时从下拉框获取选中的单据类型 ID
   - 将 `document_type_id` 添加到 FormData 发送到后端
   - 保存到 stateManager

2. `frontend/src/components/steps/Step5DataExtract.js`
   - 添加 `autoExecute()` 方法
   - `show()` 时自动执行提取和检查点验证
   - 根据步骤2选中的单据类型自动加载模板

3. `frontend/src/components/panels/HistoryPanel.js`
   - 加载历史缓存时恢复单据类型选择到下拉框

4. `frontend/src/index.html`
   - 步骤组件版本号更新到 v=16

---

## [2026-01-27] - 单据设定功能开发

### 新增：单据类型配置功能

**功能描述**：
在步骤2上传文件前，用户可以选择单据类型（发票、合同、收据、身份证、出差报告等），步骤5数据提取时会自动加载对应的关键词模板和检查点问题。

**新增文件**：
- `backend/api/document_type_routes.py` - 单据类型配置 API
  - `GET /api/document-types` - 获取所有单据类型
  - `POST /api/document-types` - 创建新单据类型
  - `PUT /api/document-types/{id}` - 更新单据类型
  - `DELETE /api/document-types/{id}` - 删除单据类型
  - `POST /api/document-types/reset` - 重置为默认配置
- `frontend/src/components/DocumentTypeConfig.js` - 单据设定弹窗组件
  - 左侧：单据类型列表（支持新增/删除）
  - 右侧：编辑关键词字段和检查点问题
  - 数据持久化到 `config/document_types.json`

**修改文件**：
- `backend/app.py` - 注册 `document_type_bp` 蓝图
- `frontend/src/index.html`
  - 上传区域添加单据类型下拉选择器
  - 添加"⚙️ 设定"按钮打开配置弹窗
  - 初始化脚本加载单据类型到下拉框
- `frontend/src/styles/components.css` - 添加单据类型选择器样式
- `frontend/src/components/steps/Step5DataExtract.js`
  - 从后端加载单据类型配置（`loadDocumentTypes()`）
  - 自动选择步骤2选中的单据类型（`autoSelectDocumentType()`）
  - 模板渲染使用后端数据而非硬编码预设
  - 选择模板时自动填充检查点问题

**默认单据类型**：
- 发票：发票号码、发票代码、开票日期、购买方名称、销售方名称、金额、税额、价税合计
- 合同：合同编号、甲方、乙方、签订日期、合同金额、有效期
- 收据：收据编号、日期、付款人、收款人、金额、事由
- 身份证：姓名、性别、民族、出生日期、住址、身份证号码
- 出差报告：报告日期、出差人、出差目的地、出差事由、出差时间、费用合计

---

## [2026-01-27] - 步骤5/6界面优化 & RAG集成修复

### 步骤5数据提取RAG集成修复

**问题**：步骤5的智能提取和检查点验证没有使用RAG检索，直接发送全文给LLM

**修复内容**：
- 智能提取：从 `/api/llm/extract` 改为 `/api/extract-info`（支持RAG检索）
- 检查点验证：从 `/api/llm/qa` 改为 `/api/document-qa`（支持RAG检索）
- 修复 `Step5DataExtract.js` 中的重复变量声明错误（`globalStateManager`）

**修改文件**：
- `frontend/src/components/steps/Step5DataExtract.js`

---

### 步骤6财务确认界面重新设计

**问题**：步骤6界面过于简单，信息展示不够清晰

**修复内容**：
- 顶部：标题栏 + 统计信息（模板、字段数、检查点数、平均置信度）
- 上半部：检查点问答结果（带置信度颜色标识）
- 下半部：关键词提取的JSON数据（支持JSON/表格视图切换）
- 新增功能：
  - `formatJsonWithHighlight()` - JSON语法高亮
  - `renderExtractedDataTable()` - 表格视图渲染
  - 视图切换按钮、复制JSON按钮
- 底部操作按钮暂时隐藏（确认提交、驳回修改、返回上一步）

**修改文件**：
- `frontend/src/components/steps/Step6Confirmation.js`

---

### 步骤6进度条状态修复

**问题**：进入步骤6时，顶部进度条的第6步按钮没有变成激活状态（蓝色）

**修复内容**：
- 添加 `updateStepStatus()` 方法
- 支持通过 `window.app.setStepStatus` 或直接操作DOM更新状态
- 步骤5标记为完成（绿色勾），步骤6标记为激活（蓝色高亮）

**修改文件**：
- `frontend/src/components/steps/Step6Confirmation.js`

---

### 步骤5界面简化

**修改内容**：
- 隐藏"识别文本预览"区域（暂时不需要显示OCR原文预览）

**修改文件**：
- `frontend/src/components/steps/Step5DataExtract.js`

---

### README.md更新

**修改内容**：
- 在"PP-ChatOCRv4 智能文档理解架构"部分添加详细的核心流程说明
- 阶段一（文档索引）：文档文本 → 分块 → 向量化 → 存入向量数据库
- 阶段二（智能问答）：用户输入 → 向量化 → 检索相关片段 → 发给LLM → 得到答案

**修改文件**：
- `README.md`

---

## [2026-01-27] - 步骤界面独立化 & 数据提取 API 修复

### 步骤界面独立显示修复

**问题**：各步骤界面之间相互干扰，切换步骤时旧界面元素仍然可见

**修复内容**：
- 步骤 4（预录入）显示左右分栏布局（左：原始文档图片，右：Block 列表）
- 切换到步骤 4 时隐藏上传区域
- 更新 CSS 布局：`.main-content`、`.image-panel`、`.editor-panel` 设置明确的 50% 宽度
- 添加 `showStep4UI()` 方法处理步骤 4 界面显示
- 更新 `loadCachedJob()` 函数正确设置布局样式

**修改文件**：
- `frontend/src/index.js`
- `frontend/src/utils/globalFunctions.js`
- `frontend/src/styles/layout.css`
- `frontend/src/components/steps/Step4PreEntry.js`

---

### 步骤 4 到步骤 5 确认按钮

**问题**：步骤 4 预录入编辑完成后，没有按钮可以进入步骤 5

**修复内容**：
- 添加 `renderStep4ConfirmButton()` 方法
- 添加全局函数：
  - `window.createStep4ConfirmButton()` - 创建绿色确认按钮
  - `window.confirmStep4AndProceed()` - 处理步骤转换
  - `window.switchToStep5UI()` - 切换到步骤 5 界面
- 按钮显示在编辑面板底部："✓ 确认并进入步骤5（数据提取）"
- 修复按钮可见性问题：
  - `.editor-panel` 从 `overflow: hidden` 改为 `overflow: visible`
  - 确认按钮添加 `position: sticky; bottom: 0; z-index: 100`
  - 添加 `flex-shrink: 0; min-height: 60px` 防止按钮被压缩

**修改文件**：
- `frontend/src/index.js`
- `frontend/src/utils/globalFunctions.js`
- `frontend/src/styles/layout.css`
- `frontend/src/styles/components.css`
- `frontend/src/index.html`

---

### 步骤 5 数据提取 API 修复

**问题**：点击"开始提取"按钮报错 `Unexpected token '<', "<!doctype "... is not valid JSON`

**根因**：
1. 前端调用 `/api/llm/extract` 但后端只有 `/api/extract-info`
2. API 返回的 `LLMResponse` 是对象，但代码用字典方法访问（`.get()`）
3. JSON 解析正则 `r'\{[^{}]*\}'` 无法匹配多字段的嵌套 JSON

**修复内容**：
- 新增三个 API 端点到 `backend/api/chatocr_routes.py`：
  - `POST /api/llm/extract` - 使用 LLM 从文本提取指定字段
  - `POST /api/llm/qa` - 使用 LLM 回答文档问题
  - `GET /api/checkpoint-config` - 获取检查点配置
- 修复 `LLMResponse` 对象访问方式：
  - `result.get('success')` → `result.success`
  - `result.get('response')` → `result.content`
  - `result.get('error')` → `result.error_message`
- 改进 JSON 解析逻辑，支持多种格式：
  1. 直接解析整个响应
  2. 提取 ```json ... ``` 代码块
  3. 找到最外层 `{...}` 对象（支持嵌套）
  4. 解析失败时返回原始响应

**修改文件**：
- `backend/api/chatocr_routes.py`

---

## [2026-01-26] - V3 前端升级完成

### 前端 V3 升级 - 测试覆盖完成

**新增测试文件**：
- `frontend/src/__tests__/EventBus.test.js` - 事件总线测试（15 用例）
  - 事件订阅/发布、多监听器、取消订阅、once 单次监听、通配符事件
- `frontend/src/__tests__/StateManager.test.js` - 状态管理测试（20 用例）
  - 状态获取/设置、嵌套路径、批量更新、状态订阅、持久化
- `frontend/src/__tests__/StepManager.test.js` - 步骤管理测试（25 用例）
  - 步骤导航、状态转换、验证逻辑、事件触发、边界条件
- `backend/tests/test_v3_api.py` - V3 API 测试（24 用例）
  - 修正记录 API、检查点 API、最终结果 API、模板管理 API、检查点配置 API
- `backend/tests/test_v3_integration.py` - V3 集成测试（13 用例）
  - 完整工作流测试、修正数据传递、驳回流程、数据持久化

**测试结果**：
- 前端测试：193 passed（含 V3 核心服务 60 用例）
- 后端测试：37 passed（含 V3 API 37 用例）
- 全部测试通过 ✅

---

### 前端 V3 升级 - 组件化重构（续）

**UI/UX 增强**：
- 步骤进度条动画：完成动画、脉冲效果、错误抖动
- 面板展开/收起动画：平滑过渡、悬停效果
- 加载状态指示器：全局加载遮罩、内联加载器、骨架屏
- Toast 通知系统：成功/错误/警告/信息四种类型
- 响应式布局：支持桌面、平板、手机、横屏手机
- 高对比度模式支持
- 减少动画模式支持（prefers-reduced-motion）

**index.js 集成**：
- 版本更新至 v9
- 集成 Step1ModelLoad、Step2FileUpload、Step3Recognition 组件
- 添加 EventBus 事件监听
- 保持向后兼容

**文档更新**：
- README.md 添加 V3 功能说明
- 创建 MDFiles/USER_GUIDE.md 用户操作指南

---

## [2026-01-26]

### 前端 V3 升级 - 组件化重构

**新增功能**：
- 6 步工作流：模型加载 → 上传文件 → 智能识别 → 预录入 → 数据提取 → 财务确认
- 步骤 4 预录入：Block 编辑、修正记录保存
- 步骤 5 数据提取：模板选择、LLM 关键词提取、检查点验证
- 步骤 6 财务确认：检查点答案展示、JSON 数据复制、确认/驳回流程

**新增文件**：
- CSS 模块化：
  - `frontend/src/styles/base.css` - CSS 变量和重置样式
  - `frontend/src/styles/layout.css` - 主布局样式
  - `frontend/src/styles/steps.css` - 工作流步骤进度条样式
  - `frontend/src/styles/panels.css` - 面板样式
  - `frontend/src/styles/components.css` - 组件样式
- 核心服务：
  - `frontend/src/services/EventBus.js` - 事件总线（发布订阅模式）
  - `frontend/src/services/StateManager.js` - 全局状态管理器
  - `frontend/src/services/StepManager.js` - 步骤管理器
- 步骤组件：
  - `frontend/src/components/steps/Step1ModelLoad.js` - 模型加载
  - `frontend/src/components/steps/Step2FileUpload.js` - 文件上传
  - `frontend/src/components/steps/Step3Recognition.js` - 智能识别
  - `frontend/src/components/steps/Step4PreEntry.js` - 预录入
  - `frontend/src/components/steps/Step5DataExtract.js` - 数据提取
  - `frontend/src/components/steps/Step6Confirmation.js` - 财务确认
- 面板组件：
  - `frontend/src/components/panels/HistoryPanel.js` - 历史缓存面板
  - `frontend/src/components/panels/TemplatePanel.js` - 关键词模板面板
  - `frontend/src/components/panels/CheckpointPanel.js` - 检查点设定面板
- 后端 API：
  - `backend/api/v3_routes.py` - V3 升级 API 路由
    - `/api/corrections/{job_id}` - 修正记录 API
    - `/api/checkpoints/{job_id}` - 检查点结果 API
    - `/api/final/{job_id}` - 最终结果 API
    - `/api/templates` - 模板管理 API
    - `/api/checkpoint-config` - 检查点配置 API

**修改文件**：
- `frontend/src/index.html` - 精简重写，引入 CSS 模块
- `frontend/src/utils/globalFunctions.js` - 抽取内联脚本
- `backend/api/__init__.py` - 注册 V3 路由

---

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
