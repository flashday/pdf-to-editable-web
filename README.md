# PDF to Editable Web Layout System

将扫描的 PDF 文档转换为结构化、可编辑的 Web 内容。使用 PaddleOCR PP-StructureV3 进行 OCR 处理和布局分析。

## ⚠️ 版本说明

**当前 main 分支仅支持 PaddleOCR 3.x (PP-StructureV3)**

- 基于 PaddleOCR 2.x 的旧版本已打 Tag 保存，不再维护
- main 分支不向下兼容 PaddleOCR 2.x
- 如需使用旧版本，请切换到对应 Tag

## 🆕 最新更新 (2026-01-26)

**🤖 PP-ChatOCRv4 智能文档理解集成：**
- ✅ 新增智能信息提取功能（发票、合同、身份证、简历等预设模板）
- ✅ 新增文档问答功能（基于 RAG 向量检索）
- ✅ 集成本地 Ollama LLM 服务
- ✅ 支持 BGE-small-zh-v1.5 中文向量化模型
- ✅ 使用 ChromaDB 向量数据库
- ✅ 优雅降级：LLM 不可用时不影响基础 OCR 功能

**置信度显示修复 (2026-01-25)：**
- ✅ 修复 Block 列表中置信度显示乱码问题（编码兼容性）
- ✅ 置信度现在正确显示：有值显示数值，无值显示 `-`

**Block 类型标识增强：**
- ✅ 新增 Edit Type 徽章（蓝色 TEXT / 紫色 TABLE）- 决定编辑器处理方式
- ✅ 新增 Struct Type 徽章（灰色）- 显示 PPStructureV3 原始类型（如 doc_title, figure_caption, table 等）

**后端升级 (2026-01-24)：**
- ✅ 升级到 PaddleOCR 3.3.3 + PaddlePaddle 3.2.2
- ✅ 支持 PP-OCRv5（文本识别准确率 +13%）
- ✅ 支持 PP-StructureV3（表格识别准确率 +6%）
- ✅ 新增 Markdown 输出 API
- ✅ 详细迁移指南：`MDFiles/implementation/PADDLEOCR_2X_TO_3X_MIGRATION_GUIDE.md`

## 功能特点

- 支持上传 PDF、JPG、PNG 文件（最大 10MB）
- 完整支持中文文件名和内容
- 使用 PaddleOCR PP-StructureV3 进行 OCR 和布局分析
- **流程进度条**：顶部显示 4 步处理流程（模型启动 → 上传文件 → 识别处理 → 结果显示）
- **历史缓存**：右侧面板显示历史任务，点击直接加载缓存结果
- **分屏布局**：左侧显示原始文档图像，右侧显示 Block 列表
- **双视图模式**：支持 Block 视图和 Markdown 视图切换
- **双击编辑**：双击左侧 OCR 区域或右侧 Block 进行编辑
- **表格编辑**：TABLE 类型 Block 支持直接编辑单元格
- **文本编辑**：TEXT 类型 Block 弹出文本编辑框
- **实时高亮**：选中时左右两侧同步高亮
- **类型标识**：每个 Block 显示 Edit Type 和 Struct Type 双重标识
- **下载功能**：支持 6 种格式导出
- 实时处理状态更新
- 置信度报告

### 🤖 智能文档理解功能（PP-ChatOCRv4）

- **智能信息提取**：从文档中自动提取关键信息（发票号、金额、日期等）
- **预设模板**：支持发票、合同、身份证、简历等常见文档类型
- **自定义字段**：支持用户自定义提取字段
- **文档问答**：用自然语言向文档提问，获取基于内容的回答
- **RAG 向量检索**：智能检索多页文档中的相关内容
- **引用原文**：回答中引用文档原文作为依据
- **优雅降级**：LLM 服务不可用时，基础 OCR 功能不受影响

## 界面布局

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              PDF全文结构识别还原演示                             │
├────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐  ┌──────────────────────┐ │
│  │ ① 模型启动 ─ ② 上传文件 ─ ③ 识别处理 ─ ④ 结果显示 │  │ 📂 历史缓存  🔄    │ │
│  │    (64s)       (0.5s)       (50s)       (0.1s)  │  │ 1 📄 文件1.pdf 92% │ │
│  └─────────────────────────────────────────────────┘  │ 2 📄 文件2.pdf 88% │ │
│                                                       └──────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────┤
│                         拖放或点击上传 PDF/JPG/PNG 文件                          │
├─────────────────────────────────┬──────────────────────────────────────────────┤
│                                 │  📋 识别结果  [📦Block] [📝Markdown]          │
│    📷 Original Document         │  ┌─────────────────────────────────────────┐ │
│                                 │  │ 📄原始 📊LOG 📐布局 📝OCR 🌐HTML 📝MD   │ │
│    原始文档图像                  │  └─────────────────────────────────────────┘ │
│    (OCR 区域框叠加)              │  ┌─────────────────────────────────────────┐ │
│                                 │  │ [TEXT] [doc_title]              #1      │ │
│    - 蓝色框：识别区域            │  │ 文档标题内容...                          │ │
│    - 红色框：悬停                │  │ Pos:(x,y) Size:WxH Conf:0.95            │ │
│    - 绿色框：选中                │  └─────────────────────────────────────────┘ │
│    - 单击选中高亮                │  ┌─────────────────────────────────────────┐ │
│    - 双击弹出编辑框              │  │ [TABLE] [table]                   #2    │ │
│                                 │  │ ┌───┬───┐                               │ │
│                                 │  │ │   │   │ (表格预览)                    │ │
│                                 │  │ └───┴───┘                               │ │
│                                 │  │ Pos:(x,y) Size:WxH Conf:0.92            │ │
│                                 │  └─────────────────────────────────────────┘ │
├─────────────────────────────────┴──────────────────────────────────────────────┤
│  图例：🔵 识别区域  🔴 悬停  🟢 选中                                             │
└────────────────────────────────────────────────────────────────────────────────┘
```

## Block 类型说明

每个识别出的 Block 显示两种类型标识：

| 标识 | 说明 | 示例值 |
|------|------|--------|
| **Edit Type** | 编辑器处理方式 | `TEXT`（蓝色）、`TABLE`（紫色） |
| **Struct Type** | PPStructureV3 原始类型 | `doc_title`, `text`, `table`, `figure`, `figure_caption`, `header`, `footer` 等 |

- **TEXT**：文本类型，双击弹出文本编辑框
- **TABLE**：表格类型，双击弹出表格编辑器，支持单元格编辑

## 下载按钮说明

| 按钮 | 颜色 | 说明 |
|------|------|------|
| 📄 原始文件 | 红色 | 下载原始上传的 PDF 或图片文件 |
| 📊 置信度LOG | 青色 | 置信度计算详细日志（Markdown 格式） |
| 📐 布局JSON | 绿色 | PPStructure 布局分析结果（JSON 格式） |
| 📝 OCR结果 | 蓝色 | 文本 OCR 识别原始结果（JSON 格式，含文本行+置信度） |
| 🌐 HTML | 紫色 | OCR 结果的 HTML 格式输出 |
| 📝 MD | 深紫 | OCR 结果的 Markdown 格式输出 |

## 项目结构

```
├── backend/                 # Python 后端
│   ├── api/                # REST API
│   │   ├── routes.py           # API 路由定义
│   │   └── chatocr_routes.py   # 智能文档理解 API 路由
│   ├── services/           # 业务逻辑
│   │   ├── ocr_service.py      # PaddleOCR 集成（主服务）
│   │   ├── ocr/                # OCR 模块化组件
│   │   │   ├── __init__.py         # 包初始化，导出辅助类
│   │   │   ├── image_preprocessor.py   # 图像预处理（增强、缩放）
│   │   │   ├── layout_analyzer.py      # 布局分析、区域分类
│   │   │   ├── table_processor.py      # 表格检测、结构解析
│   │   │   ├── output_generator.py     # HTML/Markdown 生成
│   │   │   ├── ppstructure_parser.py   # PPStructureV3 结果解析
│   │   │   └── confidence_logger.py    # 置信度日志生成
│   │   ├── llm_service.py          # Ollama LLM 服务封装
│   │   ├── embedding_service.py    # 文本向量化服务（BGE）
│   │   ├── vector_store.py         # 向量存储服务（ChromaDB）
│   │   ├── text_chunker.py         # 文本分块器
│   │   ├── rag_service.py          # RAG 检索增强生成服务
│   │   ├── chatocr_service.py      # ChatOCR 智能文档理解服务
│   │   ├── data_normalizer.py      # 数据转换（含类型映射）
│   │   ├── document_processor.py   # 处理流程
│   │   ├── job_cache.py            # 历史任务缓存
│   │   ├── pdf_processor.py        # PDF 转图像处理
│   │   ├── status_tracker.py       # 任务状态跟踪
│   │   ├── validation.py           # 输入验证
│   │   ├── error_handler.py        # 错误处理
│   │   ├── encoding_handler.py     # 编码处理（中文支持）
│   │   ├── confidence_monitor.py   # 置信度监控
│   │   ├── content_integrity.py    # 内容完整性检查
│   │   ├── json_validator.py       # JSON 验证
│   │   ├── schema_validator.py     # Schema 验证
│   │   ├── retry_handler.py        # 重试处理
│   │   ├── performance_monitor.py  # 性能监控
│   │   └── interfaces.py           # 接口定义
│   ├── models/             # 数据模型
│   ├── tests/              # 单元测试
│   ├── app.py              # 应用入口
│   ├── config.py           # 配置文件
│   └── requirements.txt    # Python 依赖
├── frontend/               # JavaScript 前端
│   ├── src/
│   │   ├── services/       # 前端服务
│   │   ├── components/     # React 组件
│   │   │   ├── SmartExtract.js     # 智能提取面板
│   │   │   ├── DocumentQA.js       # 文档问答面板
│   │   │   └── ChatOCRIntegration.js # ChatOCR 集成组件
│   │   ├── index.html      # 主页面（含样式）
│   │   └── index.js        # 应用入口
│   └── package.json        # Node.js 依赖
├── vector_db/              # 向量数据库存储目录
├── temp/                   # 临时文件目录（调试用）
├── uploads/                # 上传文件目录
├── logs/                   # 日志目录
├── MDFiles/                # 文档目录
│   └── implementation/     # 实现文档
├── run_dev_v3.bat          # Windows 启动脚本
├── start_backend.py        # 后端启动脚本
└── README.md
```

## 调试文件说明

每次处理 PDF 后，`temp/` 目录会保存以下调试文件（以 `{job_id}` 为前缀）：

| 文件名 | 说明 |
|--------|------|
| `{job_id}_original.pdf` | 原始上传的 PDF 文件 |
| `{job_id}_page1.png` | PyMuPDF 转换的图像（300 DPI，限制最大 2048px） |
| `{job_id}_page1_preprocessed.png` | OCR 预处理后的图像（最大 1280px，增强对比度/锐度） |
| `{job_id}_ppstructure.json` | PPStructure 识别结果（包含 bbox、类型、scale_info） |
| `{job_id}_raw_ocr.json` | OCR 原始结果（包含文本行、置信度、scale_info） |
| `{job_id}_raw_ocr.html` | HTML 格式输出（带表格结构） |
| `{job_id}_raw_ocr.md` | Markdown 格式输出 |
| `{job_id}_confidence_log.md` | 置信度计算日志（含处理时间） |

这些文件用于调试坐标对齐、OCR 准确性等问题。`scale_info` 记录了图像缩放信息，用于坐标转换。

另外，`temp/job_cache.json` 保存任务索引，用于历史缓存功能。

## 环境要求

- Python 3.10+
- Node.js 16+
- PaddleOCR 3.3.3
- PaddlePaddle 3.2.2 (⚠️ 不要使用 3.3.0，有 oneDNN 兼容性问题)
- Ollama（可选，用于智能文档理解功能）

### 智能文档理解依赖（可选）

如需使用 PP-ChatOCRv4 智能功能，还需安装：

```bash
# 向量化模型
pip install sentence-transformers

# 向量数据库
pip install chromadb

# Ollama LLM 服务（需单独安装）
# 参考: https://ollama.ai/download
```

## 技术架构

### PaddlePaddle / PaddleOCR / PPStructureV3 关系

```
┌─────────────────────────────────────────────────────────────────┐
│                      软件包依赖关系                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PaddlePaddle 3.2.2          PaddleOCR 3.3.3                   │
│  ┌─────────────────┐         ┌─────────────────────────────┐   │
│  │ 深度学习框架     │ ◄────── │ OCR 应用库                   │   │
│  │ (类似 PyTorch)  │  依赖    │                             │   │
│  │                 │         │  提供多个"管线"：            │   │
│  │ • 张量计算      │         │  ├─ PaddleOCR (纯OCR)       │   │
│  │ • 模型推理      │         │  ├─ PPStructure (2.x)       │   │
│  │ • GPU/CPU 加速  │         │  └─ PPStructureV3 (3.x) ◄── │   │
│  └─────────────────┘         └─────────────────────────────┘   │
│                                        │                        │
│                                        │ 本项目使用              │
│                                        ▼                        │
│                              ┌─────────────────────────────┐   │
│                              │ PPStructureV3               │   │
│                              │ (文档结构分析管线)           │   │
│                              │                             │   │
│                              │ 内置功能：                   │   │
│                              │ • 布局分析 (PP-DocLayout)   │   │
│                              │ • 文本检测 (PP-OCRv5_det)   │   │
│                              │ • 文本识别 (PP-OCRv5_rec)   │   │
│                              │ • 表格识别 (SLANet)         │   │
│                              │ • 公式识别 (可选)           │   │
│                              └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

| 组件 | 作用 | 类比 |
|-----|------|------|
| **PaddlePaddle** | 底层深度学习框架 | 类似 PyTorch/TensorFlow |
| **PaddleOCR** | OCR 应用库，提供多种管线 | 类似一个工具箱 |
| **PPStructureV3** | PaddleOCR 中的管线，专门做文档分析 | 工具箱里的瑞士军刀 |

### 为什么选择 PPStructureV3

- 需要**布局分析**（识别标题、段落、图片区域）
- 需要**表格识别**（提取表格结构和内容）
- 不只是简单的文字识别，而是完整的文档结构化

如果只需要纯文字识别，可以用更轻量的 `PaddleOCR` 类。

### PPStructureV3 处理流程

PPStructureV3 处理流程包含多个串行步骤：

```
PDF → 图像 → 布局分析 → 文本检测 → 文本识别 → 表格识别 → 结果整合
              ↓           ↓           ↓           ↓
           PP-DocLayout  PP-OCRv5   PP-OCRv5    SLANet
                         _det       _rec
```

每个步骤都需要独立的模型推理，这是处理时间较长的主要原因。

## 虚拟环境

| 环境 | Python | PaddleOCR | 用途 |
|------|--------|-----------|------|
| `venv_paddle3` | 3.10 | 3.3.3 | **推荐** - PP-StructureV3 |
| `venv310` | 3.10 | 2.7.0.3 | 旧版本备份（已不维护） |

## 快速开始

### 安装 PaddleOCR

```bash
# ⚠️ 重要：使用 PaddlePaddle 3.2.2，不要使用 3.3.0
pip install paddlepaddle==3.2.2
pip install paddleocr==3.3.3
```

### 启动服务

**Windows (推荐)**:
```cmd
run_dev_v3.bat
```

或手动启动：

```powershell
# 后端
.\venv_paddle3\Scripts\Activate.ps1
$env:PYTHONPATH="."
python backend/app.py

# 前端 (新终端)
cd frontend
npm install
npm run dev
```

### 访问

- 前端: http://localhost:3000
- 后端: http://localhost:5000

## 使用方法

1. 打开 http://localhost:3000
2. 拖放或点击上传 PDF/JPG/PNG 文件
3. 等待 OCR 处理完成
4. 左侧查看原始文档（带 OCR 区域框），右侧查看识别结果
5. 查看每个 Block 的 Edit Type 和 Struct Type 标识
6. 双击区域进行编辑（TEXT 弹出文本框，TABLE 弹出表格编辑器）
7. 点击下载按钮导出结果

## API 接口

### 系统接口

| 接口 | 说明 |
|------|------|
| `GET /api/health` | 健康检查，返回服务状态和 OCR 模型就绪状态 |

### 文档处理接口

| 接口 | 说明 |
|------|------|
| `POST /api/convert` | 上传文件并开始处理 |
| `GET /api/convert/{job_id}/status` | 查询处理状态（含进度百分比、预计剩余时间） |
| `GET /api/convert/{job_id}/result` | 获取 OCR 结果（Editor.js 格式） |
| `GET /api/convert/{job_id}/history` | 获取状态更新历史（用于调试） |
| `GET /api/convert/{job_id}/image` | 获取文档图像 |
| `GET /api/convert/{job_id}/original-file` | 下载原始上传文件 |
| `GET /api/convert/{job_id}/raw-output` | 获取原始 OCR 输出（JSON + HTML + PPStructure） |
| `GET /api/convert/{job_id}/markdown` | 获取 Markdown 格式输出 |
| `GET /api/convert/{job_id}/confidence-log` | 获取置信度计算日志 |

### 历史缓存接口

| 接口 | 说明 |
|------|------|
| `GET /api/jobs/history` | 获取历史任务列表（支持 limit 参数） |
| `GET /api/jobs/latest` | 获取最新任务（用于页面加载时自动恢复） |
| `GET /api/jobs/{job_id}/cached-result` | 获取缓存的识别结果（含 Markdown） |
| `DELETE /api/jobs/{job_id}` | 删除缓存任务 |

### 智能文档理解接口（PP-ChatOCRv4）

| 接口 | 说明 |
|------|------|
| `GET /api/llm/status` | 检查 LLM 服务状态 |
| `GET /api/templates` | 获取预设提取模板列表 |
| `POST /api/extract-info` | 从文档中提取关键信息 |
| `POST /api/document-qa` | 基于文档内容回答问题 |
| `GET /api/rag/status/{job_id}` | 获取文档的 RAG 索引状态 |

#### 智能提取 API 详情

**POST /api/extract-info**

请求体：
```json
{
    "job_id": "xxx",
    "fields": ["发票号", "金额", "日期"],
    "template": "invoice"
}
```

响应：
```json
{
    "success": true,
    "data": {
        "job_id": "xxx",
        "fields": {
            "发票号": "12345678",
            "金额": "1,234.56",
            "日期": "2026-01-25"
        },
        "confidence": 0.95,
        "warnings": [],
        "processing_time": 2.3
    }
}
```

**POST /api/document-qa**

请求体：
```json
{
    "job_id": "xxx",
    "question": "这份文档的总金额是多少？"
}
```

响应：
```json
{
    "success": true,
    "data": {
        "job_id": "xxx",
        "question": "这份文档的总金额是多少？",
        "answer": "根据文档内容，总金额为 1,234.56 元。",
        "references": ["金额合计：1,234.56"],
        "confidence": 0.9,
        "processing_time": 1.5
    }
}
```

#### 预设模板

| 模板 ID | 名称 | 提取字段 |
|---------|------|----------|
| `invoice` | 发票 | 发票号码、开票日期、金额合计、税额、购买方名称、销售方名称 |
| `contract` | 合同 | 甲方、乙方、合同金额、签订日期、合同期限、违约条款 |
| `id_card` | 身份证 | 姓名、性别、民族、出生日期、住址、身份证号码 |
| `resume` | 简历 | 姓名、联系电话、电子邮箱、教育背景、工作经历、技能特长 |

## 系统要求

- **操作系统**: Windows 11, macOS 13+, Linux
- **内存**: 最少 4GB RAM
- **存储**: 1GB 可用空间

## 智能文档理解配置（PP-ChatOCRv4）

### 环境变量配置

通过环境变量或 `.env` 文件配置智能功能：

```bash
# Ollama LLM 配置
OLLAMA_BASE_URL=http://localhost:11434    # Ollama 服务地址
OLLAMA_MODEL=gpt-oss:20b                  # 使用的模型名称
OLLAMA_TIMEOUT=60                         # 请求超时时间（秒）

# LLM 生成参数
LLM_MAX_TOKENS=4096                       # 最大生成 token 数
LLM_TEMPERATURE=0.1                       # 生成温度（0-1）
LLM_MAX_RETRIES=2                         # 最大重试次数

# 功能开关
ENABLE_CHATOCR=true                       # 启用智能文档理解
ENABLE_RAG=true                           # 启用 RAG 向量检索

# RAG 向量检索配置
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5    # 向量化模型
VECTOR_DB_PATH=./vector_db                # 向量数据库路径

# 文本分块配置
CHUNK_SIZE=500                            # 分块大小（字符）
CHUNK_OVERLAP=50                          # 分块重叠（字符）
RAG_TOP_K=5                               # 检索返回数量
```

### 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `OLLAMA_MODEL` | `gpt-oss:20b` | LLM 模型名称 |
| `OLLAMA_TIMEOUT` | `60` | LLM 请求超时时间（秒） |
| `ENABLE_CHATOCR` | `true` | 是否启用智能功能 |
| `ENABLE_RAG` | `true` | 是否启用 RAG 向量检索 |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 中文向量化模型 |
| `CHUNK_SIZE` | `500` | 文本分块大小 |
| `CHUNK_OVERLAP` | `50` | 分块重叠大小 |
| `RAG_TOP_K` | `5` | 检索返回的相关片段数量 |

### 降级策略

- **LLM 不可用**：智能提取和问答功能禁用，基础 OCR 功能正常
- **RAG 不可用**：回退到全文发送模式（可能影响长文档处理）
- **超时处理**：60 秒超时后返回错误，允许用户重试

## License

MIT
