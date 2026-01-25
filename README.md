# PDF to Editable Web Layout System

将扫描的 PDF 文档转换为结构化、可编辑的 Web 内容。使用 PaddleOCR PP-StructureV3 进行 OCR 处理和布局分析。

## ⚠️ 版本说明

**当前 main 分支仅支持 PaddleOCR 3.x (PP-StructureV3)**

- 基于 PaddleOCR 2.x 的旧版本已打 Tag 保存，不再维护
- main 分支不向下兼容 PaddleOCR 2.x
- 如需使用旧版本，请切换到对应 Tag

## 🆕 最新更新 (2026-01-25)

**置信度显示修复：**
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
│   │   ├── data_normalizer.py  # 数据转换（含类型映射）
│   │   ├── document_processor.py # 处理流程
│   │   └── job_cache.py        # 历史任务缓存
│   ├── models/             # 数据模型
│   ├── tests/              # 单元测试
│   ├── app.py              # 应用入口
│   └── requirements.txt    # Python 依赖
├── frontend/               # JavaScript 前端
│   ├── src/
│   │   ├── services/       # 前端服务
│   │   ├── index.html      # 主页面（含样式）
│   │   └── index.js        # 应用入口
│   └── package.json        # Node.js 依赖
├── temp/                   # 临时文件目录（调试用）
├── MDFiles/                # 文档目录
│   └── implementation/     # 实现文档
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

## 系统要求

- **操作系统**: Windows 11, macOS 13+, Linux
- **内存**: 最少 4GB RAM
- **存储**: 1GB 可用空间

## License

MIT
