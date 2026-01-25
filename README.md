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
- **分屏布局**：左侧显示原始文档图像，右侧显示 Block 列表
- **双击编辑**：双击左侧 OCR 区域或右侧 Block 进行编辑
- **表格编辑**：TABLE 类型 Block 支持直接编辑单元格
- **文本编辑**：TEXT 类型 Block 弹出文本编辑框
- **实时高亮**：选中时左右两侧同步高亮
- **类型标识**：每个 Block 显示 Edit Type 和 Struct Type 双重标识
- **下载功能**：支持多种格式导出
- 实时处理状态更新
- 置信度报告

## 界面布局

```
┌────────────────────────────────────────────────────────────────────┐
│                         上传区域                                    │
│              拖放或点击上传 PDF/JPG/PNG 文件                         │
├─────────────────────────────┬──────────────────────────────────────┤
│                             │  📋 识别结果                          │
│    📷 Original Document     │  ┌─────────────────────────────────┐ │
│                             │  │ [TEXT] [doc_title]        #1    │ │
│    原始文档图像              │  │ 文档标题内容...                   │ │
│    (OCR 区域框叠加)          │  │ Pos:(x,y) Size:WxH Conf:0.95    │ │
│                             │  └─────────────────────────────────┘ │
│    - 蓝色框：识别区域        │  ┌─────────────────────────────────┐ │
│    - 红色框：悬停            │  │ [TABLE] [table]           #2    │ │
│    - 绿色框：选中            │  │ ┌───┬───┐                       │ │
│    - 单击选中高亮            │  │ │   │   │ (表格预览)            │ │
│    - 双击弹出编辑框          │  │ └───┴───┘                       │ │
│                             │  │ Pos:(x,y) Size:WxH Conf:0.92    │ │
│                             │  └─────────────────────────────────┘ │
├─────────────────────────────┴──────────────────────────────────────┤
│  下载按钮：                                                         │
│  📥 布局与文本块JSON | 📥 Markdown | 📥 编辑后Block                  │
└────────────────────────────────────────────────────────────────────┘
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

| 按钮 | 说明 |
|------|------|
| 📥 布局与文本块JSON | PPStructure 布局分析和文本块识别的原始 JSON 结果 |
| 📥 Markdown | OCR 结果的 Markdown 格式输出 |
| 📥 编辑后Block | 包含用户编辑修改的 Block 数据（JSON 格式） |

## 项目结构

```
├── backend/                 # Python 后端
│   ├── api/                # REST API
│   ├── services/           # 业务逻辑
│   │   ├── ocr_service.py      # PaddleOCR 集成
│   │   ├── data_normalizer.py  # 数据转换（含类型映射）
│   │   └── document_processor.py # 处理流程
│   ├── app.py              # 应用入口
│   └── requirements.txt    # Python 依赖
├── frontend/               # JavaScript 前端
│   ├── src/
│   │   ├── services/       # 前端服务
│   │   ├── index.html      # 主页面（含样式）
│   │   └── index.js        # 应用入口
│   └── package.json        # Node.js 依赖
├── MDFiles/                # 文档目录
│   └── implementation/     # 实现文档
└── README.md
```

## 环境要求

- Python 3.10+
- Node.js 16+
- PaddleOCR 3.3.3
- PaddlePaddle 3.2.2 (⚠️ 不要使用 3.3.0，有 oneDNN 兼容性问题)

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

| 接口 | 说明 |
|------|------|
| `POST /api/convert` | 上传文件 |
| `GET /api/convert/{job_id}/status` | 查询处理状态 |
| `GET /api/convert/{job_id}/result` | 获取 OCR 结果 |
| `GET /api/convert/{job_id}/image` | 获取文档图像 |
| `GET /api/convert/{job_id}/raw-output` | 获取原始 OCR 输出 |
| `GET /api/convert/{job_id}/markdown` | 获取 Markdown 格式输出 |

## 系统要求

- **操作系统**: Windows 11, macOS 13+, Linux
- **内存**: 最少 4GB RAM
- **存储**: 1GB 可用空间

## License

MIT
