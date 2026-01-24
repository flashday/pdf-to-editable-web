# PDF to Editable Web Layout System

将扫描的 PDF 文档转换为结构化、可编辑的 Web 内容。使用 PaddleOCR PP-StructureV3 进行 OCR 处理和布局分析。

## 🆕 最新更新 (2026-01-24)

- ✅ 升级到 PaddleOCR 3.3.3 + PaddlePaddle 3.2.2
- ✅ 支持 PP-OCRv5（文本识别准确率 +13%）
- ✅ 支持 PP-StructureV3（表格识别准确率 +6%）
- ✅ 新增 Markdown 输出支持
- ✅ 详细迁移指南：`MDFiles/implementation/PADDLEOCR_2X_TO_3X_MIGRATION_GUIDE.md`

## 功能特点

- 支持上传 PDF、JPG、PNG 文件（最大 10MB）
- 完整支持中文文件名和内容
- 使用 PaddleOCR PP-Structure 进行 OCR 和布局分析
- **分屏布局**：左侧显示原始文档图像，右侧显示 Block 列表
- **双击编辑**：双击左侧 OCR 区域或右侧 Block 进行编辑
- **表格编辑**：表格类型 Block 支持直接编辑单元格
- **文本编辑**：文本类型 Block 弹出文本编辑框
- **实时高亮**：选中时左右两侧同步高亮
- **下载功能**：下载文本行 JSON、布局 JSON、编辑后 Block 数据
- 实时处理状态更新
- 置信度报告

## 界面布局

```
┌────────────────────────────────────────────────────────────────────┐
│                         上传区域                                    │
├─────────────────────────────┬──────────────────────────────────────┤
│                             │                                       │
│    原始文档图像              │      Block 列表                       │
│    (OCR 区域框)             │      (识别结果)                        │
│                             │                                       │
│    - 单击选中高亮            │      - 单击选中高亮                    │
│    - 双击弹出编辑框          │      - 双击弹出编辑框                  │
│                             │                                       │
├─────────────────────────────┴──────────────────────────────────────┤
│              下载按钮：文本行JSON | 布局JSON | 编辑后Block           │
└────────────────────────────────────────────────────────────────────┘
```

## 项目结构

```
├── backend/                 # Python 后端
│   ├── api/                # REST API
│   ├── services/           # 业务逻辑
│   │   ├── ocr_service.py      # PaddleOCR 集成
│   │   ├── data_normalizer.py  # 数据转换
│   │   └── document_processor.py # 处理流程
│   ├── app.py              # 应用入口
│   └── requirements.txt    # Python 依赖
├── frontend/               # JavaScript 前端
│   ├── src/
│   │   ├── services/       # 前端服务
│   │   ├── index.html      # 主页面
│   │   └── index.js        # 应用入口
│   └── package.json        # Node.js 依赖
└── README.md
```

## 快速开始

## 环境要求

- Python 3.10+
- Node.js 16+
- PaddleOCR 3.3.3
- PaddlePaddle 3.2.2 (⚠️ 不要使用 3.3.0)

## 虚拟环境

| 环境 | Python | PaddleOCR | 用途 |
|------|--------|-----------|------|
| `venv_paddle3` | 3.10 | 3.3.3 | **推荐** - 最新版本 |
| `venv310` | 3.10 | 2.7.0.3 | 旧版本备份 |

### 安装 PaddleOCR

```bash
# ⚠️ 重要：使用 PaddlePaddle 3.2.2，不要使用 3.3.0（有 oneDNN 兼容性问题）
pip install paddlepaddle==3.2.2
pip install paddleocr==3.3.3
```

### 启动服务

**Windows (推荐 - 使用 PaddleOCR 3.x 环境)**:
```cmd
run_dev_v3.bat
```

**Windows (旧版 PaddleOCR 2.x 环境)**:
```cmd
run_dev.bat
```

或手动启动：

```cmd
# 后端 (PaddleOCR 3.x 环境)
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
4. 左侧查看原始文档，右侧查看识别结果
5. 双击区域进行编辑（文本或表格）
6. 点击下载按钮导出结果

## API 接口

- `POST /api/convert` - 上传文件
- `GET /api/convert/{job_id}/status` - 查询状态
- `GET /api/convert/{job_id}/result` - 获取结果
- `GET /api/convert/{job_id}/image` - 获取文档图像
- `GET /api/convert/{job_id}/raw-output` - 获取原始 OCR 输出

## 系统要求

- **操作系统**: Windows 11, macOS 13+, Linux
- **内存**: 最少 4GB RAM
- **存储**: 1GB 可用空间

## License

MIT
