# React + Markdown 精准作业台 - 设计文档

## 1. 架构概述

### 1.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        精准作业台 (React App)                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │   PDF 渲染面板        │    │      Markdown 编辑面板           │ │
│  │  ┌───────────────┐  │    │  ┌───────────────────────────┐  │ │
│  │  │  PDF Canvas   │  │    │  │      Vditor Editor        │  │ │
│  │  │  (react-pdf)  │  │    │  │   (react-vditor)          │  │ │
│  │  └───────────────┘  │    │  └───────────────────────────┘  │ │
│  │  ┌───────────────┐  │    │                                 │ │
│  │  │ Overlay Layer │  │◄──►│  Block ID 锚点映射               │ │
│  │  │ (BoundingBox) │  │    │                                 │ │
│  │  └───────────────┘  │    │                                 │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      Zustand Store (状态管理)                     │
│  - activeBlockId    - scrollPosition    - editHistory           │
│  - layoutData       - markdownContent   - saveStatus            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend API                               │
│  /api/convert/{jobId}/layout-with-anchors                       │
│  /api/convert/{jobId}/markdown-with-anchors                     │
│  /api/convert/{jobId}/save-markdown                             │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈选型

| 层级 | 技术选型 | 版本 | 选型理由 |
|------|----------|------|----------|
| 框架 | React | 18.x | 生态成熟，PDF 库支持好 |
| 构建 | Vite | 5.x | 快速 HMR，与现有项目一致 |
| 状态 | Zustand | 4.x | 轻量，适合中等复杂度状态 |
| PDF | react-pdf | 7.x | 基于 PDF.js，支持 Canvas 渲染 |
| 编辑器 | Vditor | 3.x | 所见即所得，表格支持好 |
| 样式 | CSS Modules | - | 避免与现有样式冲突 |
| 路由 | React Router | 6.x | 与现有原生 JS 路由隔离 |

## 2. 目录结构设计

```
frontend/
├── src/
│   ├── index.html              # 现有入口
│   ├── index.js                # 现有原生 JS 入口
│   │
│   ├── workbench/              # 新增：React 精准作业台
│   │   ├── index.html          # React 入口 HTML
│   │   ├── main.tsx            # React 入口
│   │   ├── App.tsx             # 根组件
│   │   │
│   │   ├── components/
│   │   │   ├── PdfPanel/
│   │   │   │   ├── PdfPanel.tsx
│   │   │   │   ├── PdfPanel.module.css
│   │   │   │   ├── BoundingBoxOverlay.tsx
│   │   │   │   └── ZoomControls.tsx
│   │   │   │
│   │   │   ├── EditorPanel/
│   │   │   │   ├── EditorPanel.tsx
│   │   │   │   ├── EditorPanel.module.css
│   │   │   │   └── VditorWrapper.tsx
│   │   │   │
│   │   │   ├── Toolbar/
│   │   │   │   ├── Toolbar.tsx
│   │   │   │   └── SaveStatus.tsx
│   │   │   │
│   │   │   └── common/
│   │   │       ├── SplitPane.tsx
│   │   │       └── LoadingSpinner.tsx
│   │   │
│   │   ├── stores/
│   │   │   ├── workbenchStore.ts
│   │   │   └── types.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useBlockMapping.ts
│   │   │   ├── useSyncScroll.ts
│   │   │   └── useAutoSave.ts
│   │   │
│   │   ├── services/
│   │   │   └── api.ts
│   │   │
│   │   └── utils/
│   │       ├── coordinateUtils.ts
│   │       └── anchorParser.ts
│   │
│   └── components/             # 现有原生 JS 组件
│       └── steps/
│           └── Step4PreEntry.js  # 修改：添加模式切换按钮
```

## 3. 核心组件设计

### 3.1 Zustand Store 设计

```typescript
// stores/workbenchStore.ts
interface LayoutBlock {
  id: string;
  type: 'text' | 'table' | 'title' | 'figure';
  bbox: { x: number; y: number; width: number; height: number };
  confidence: number;
  pageNum: number;
}

interface WorkbenchState {
  // 数据
  jobId: string | null;
  layoutBlocks: LayoutBlock[];
  markdownContent: string;
  originalMarkdown: string;
  
  // UI 状态
  activeBlockId: string | null;
  hoveredBlockId: string | null;
  zoomLevel: number;
  syncScrollEnabled: boolean;
  
  // 保存状态
  isDirty: boolean;
  isSaving: boolean;
  lastSavedAt: Date | null;
  saveError: string | null;
  
  // Actions
  setJobId: (jobId: string) => void;
  setLayoutBlocks: (blocks: LayoutBlock[]) => void;
  setMarkdownContent: (content: string) => void;
  setActiveBlockId: (id: string | null) => void;
  setHoveredBlockId: (id: string | null) => void;
  setZoomLevel: (level: number) => void;
  toggleSyncScroll: () => void;
  saveContent: () => Promise<void>;
}
```

### 3.2 PDF 面板组件

```typescript
// components/PdfPanel/PdfPanel.tsx
interface PdfPanelProps {
  imageUrl: string;
  blocks: LayoutBlock[];
  activeBlockId: string | null;
  onBlockClick: (blockId: string) => void;
  onBlockHover: (blockId: string | null) => void;
  zoomLevel: number;
}

// 核心实现思路：
// 1. 使用 <img> 渲染 PDF 页面图像（已由后端转换）
// 2. 在图像上叠加绝对定位的 div 层
// 3. 根据 layoutBlocks 渲染 Bounding Box
// 4. 根据 confidence 设置边框颜色
```

### 3.3 Bounding Box 叠加层

```typescript
// components/PdfPanel/BoundingBoxOverlay.tsx
interface BoundingBoxOverlayProps {
  blocks: LayoutBlock[];
  activeBlockId: string | null;
  hoveredBlockId: string | null;
  imageWidth: number;
  imageHeight: number;
  zoomLevel: number;
  onBlockClick: (blockId: string) => void;
  onBlockHover: (blockId: string | null) => void;
}

// 置信度颜色映射
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.9) return 'rgba(40, 167, 69, 0.3)';  // 绿色
  if (confidence >= 0.8) return 'rgba(255, 193, 7, 0.3)';  // 黄色
  return 'rgba(220, 53, 69, 0.3)';  // 红色
};

// 边框样式
const getBoxStyle = (block: LayoutBlock, isActive: boolean, isHovered: boolean) => ({
  position: 'absolute',
  left: `${block.bbox.x}px`,
  top: `${block.bbox.y}px`,
  width: `${block.bbox.width}px`,
  height: `${block.bbox.height}px`,
  backgroundColor: getConfidenceColor(block.confidence),
  border: isActive ? '2px solid #007bff' : isHovered ? '2px solid #17a2b8' : '1px solid #6c757d',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
});
```

### 3.4 Vditor 编辑器封装

```typescript
// components/EditorPanel/VditorWrapper.tsx
interface VditorWrapperProps {
  content: string;
  onChange: (content: string) => void;
  onCursorChange: (blockId: string | null) => void;
}

// 核心实现思路：
// 1. 使用 Vditor 的 React 封装
// 2. 配置为所见即所得模式
// 3. 监听光标位置变化，解析当前所在的 Block ID
// 4. 支持 HTML 表格混合渲染
```

### 3.5 Block ID 锚点解析

```typescript
// utils/anchorParser.ts

// 后端注入的锚点格式：
// <div id="block_123" data-coords="100,200,500,600" style="display:none;"></div>
// # 章节标题

interface AnchorInfo {
  blockId: string;
  coords: { x: number; y: number; width: number; height: number };
  position: number;  // 在 Markdown 中的字符位置
}

export function parseAnchors(markdown: string): AnchorInfo[] {
  const anchorRegex = /<div id="block_(\w+)" data-coords="(\d+),(\d+),(\d+),(\d+)"[^>]*><\/div>/g;
  const anchors: AnchorInfo[] = [];
  let match;
  
  while ((match = anchorRegex.exec(markdown)) !== null) {
    anchors.push({
      blockId: match[1],
      coords: {
        x: parseInt(match[2]),
        y: parseInt(match[3]),
        width: parseInt(match[4]),
        height: parseInt(match[5]),
      },
      position: match.index,
    });
  }
  
  return anchors;
}

export function getBlockIdAtPosition(anchors: AnchorInfo[], position: number): string | null {
  // 找到位置之前最近的锚点
  let nearestAnchor: AnchorInfo | null = null;
  for (const anchor of anchors) {
    if (anchor.position <= position) {
      nearestAnchor = anchor;
    } else {
      break;
    }
  }
  return nearestAnchor?.blockId ?? null;
}
```

## 4. 后端 API 设计

### 4.1 获取带锚点的布局数据

```
GET /api/convert/{jobId}/layout-with-anchors

Response:
{
  "success": true,
  "data": {
    "blocks": [
      {
        "id": "block_001",
        "type": "title",
        "bbox": { "x": 100, "y": 50, "width": 400, "height": 30 },
        "confidence": 0.95,
        "pageNum": 1
      },
      {
        "id": "block_002",
        "type": "text",
        "bbox": { "x": 100, "y": 100, "width": 400, "height": 200 },
        "confidence": 0.87,
        "pageNum": 1
      }
    ],
    "imageWidth": 612,
    "imageHeight": 792
  }
}
```

### 4.2 获取带锚点的 Markdown

```
GET /api/convert/{jobId}/markdown-with-anchors

Response:
{
  "success": true,
  "data": {
    "markdown": "<div id=\"block_001\" data-coords=\"100,50,400,30\" style=\"display:none;\"></div>\n# 文档标题\n\n<div id=\"block_002\" data-coords=\"100,100,400,200\" style=\"display:none;\"></div>\n这是正文内容...",
    "anchors": [
      { "blockId": "block_001", "position": 0 },
      { "blockId": "block_002", "position": 85 }
    ]
  }
}
```

### 4.3 保存修正后的 Markdown

```
POST /api/convert/{jobId}/save-markdown

Request:
{
  "markdown": "修正后的 Markdown 内容...",
  "updateVector": true  // 是否更新向量库
}

Response:
{
  "success": true,
  "data": {
    "savedAt": "2026-01-28T10:30:00Z",
    "vectorUpdated": true
  }
}
```

## 5. 交互流程设计

### 5.1 点击定位流程（PDF -> Editor）

```
用户点击 PDF 上的 Bounding Box
    │
    ▼
BoundingBoxOverlay.onBlockClick(blockId)
    │
    ▼
workbenchStore.setActiveBlockId(blockId)
    │
    ▼
EditorPanel 监听 activeBlockId 变化
    │
    ▼
Vditor.scrollToElement(`#block_${blockId}`)
    │
    ▼
高亮对应段落 2 秒
```

### 5.2 点击定位流程（Editor -> PDF）

```
用户点击编辑器中的段落
    │
    ▼
VditorWrapper.onCursorChange(position)
    │
    ▼
getBlockIdAtPosition(anchors, position)
    │
    ▼
workbenchStore.setActiveBlockId(blockId)
    │
    ▼
PdfPanel 监听 activeBlockId 变化
    │
    ▼
滚动到对应 Bounding Box 位置
    │
    ▼
高亮对应 Box 2 秒
```

### 5.3 自动保存流程

```
用户编辑 Markdown 内容
    │
    ▼
workbenchStore.setMarkdownContent(newContent)
workbenchStore.isDirty = true
    │
    ▼
useAutoSave hook 启动 3 秒定时器
    │
    ▼
3 秒内无新编辑
    │
    ▼
workbenchStore.saveContent()
    │
    ▼
POST /api/convert/{jobId}/save-markdown
    │
    ▼
更新 lastSavedAt, isDirty = false
```

## 6. 样式设计

### 6.1 布局样式

```css
/* 主容器：左右分栏 */
.workbench-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* 左侧 PDF 面板 */
.pdf-panel {
  flex: 1;
  min-width: 300px;
  max-width: 60%;
  overflow: auto;
  background: #f5f5f5;
  position: relative;
}

/* 右侧编辑器面板 */
.editor-panel {
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #e1e4e8;
}

/* 分割条 */
.split-handle {
  width: 6px;
  background: #e1e4e8;
  cursor: col-resize;
  transition: background 0.2s;
}

.split-handle:hover {
  background: #007bff;
}
```

### 6.2 Bounding Box 样式

```css
/* 低置信度告警动画 */
@keyframes pulse-warning {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.bbox-low-confidence {
  animation: pulse-warning 1s infinite;
}

/* 选中状态 */
.bbox-active {
  border: 2px solid #007bff !important;
  box-shadow: 0 0 10px rgba(0, 123, 255, 0.5);
}

/* 悬停状态 */
.bbox-hovered {
  border: 2px solid #17a2b8 !important;
  z-index: 10;
}
```

## 7. 正确性属性（Correctness Properties）

### 7.1 Block ID 映射一致性
- **属性**：对于任意 Block ID，PDF 上的 Bounding Box 坐标与 Markdown 中的锚点坐标必须一致
- **验证方式**：属性测试 - 随机选择 Block ID，验证两侧坐标匹配

### 7.2 点击定位准确性
- **属性**：点击 PDF 上的 Block 后，编辑器必须滚动到包含对应锚点的段落
- **验证方式**：属性测试 - 随机点击 Block，验证编辑器滚动位置

### 7.3 内容保存完整性
- **属性**：保存后重新加载的 Markdown 内容必须与保存前完全一致
- **验证方式**：属性测试 - 随机编辑内容，保存后重新加载，验证内容相等

### 7.4 置信度颜色映射正确性
- **属性**：置信度 >= 0.9 显示绿色，0.8-0.9 显示黄色，< 0.8 显示红色
- **验证方式**：单元测试 - 验证 getConfidenceColor 函数

## 8. 风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 大文档性能问题 | 100+ Block 渲染卡顿 | 虚拟滚动、按需渲染 |
| 坐标缩放计算误差 | Box 位置偏移 | 使用相对坐标、统一缩放因子 |
| Vditor 与锚点冲突 | 锚点被编辑器清除 | 使用 HTML 注释格式 `<!-- block:xxx -->` |
| 自动保存冲突 | 多次保存请求堆积 | 防抖处理、取消前一次请求 |

## 9. 参考文档

- #[[file:MDFiles/implementation/基于 React 与 Markdown 的 OCR 修正与私有化 RAG 架构方案.md]]
- #[[file:MDFiles/implementation/REACT_MARKDOWN_WORKBENCH_FEASIBILITY_ANALYSIS.md]]
