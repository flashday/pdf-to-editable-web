# 更新日志 (CHANGELOG)

记录每次代码提交的主要修改点，便于 Review 和追溯。

> **文档分工**：
> - `CHANGELOG.md` - 记录每次提交的技术细节（Bug修复、代码调整等）
> - `README.md` - 只记录功能变更、架构调整、用户可见的新特性

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
