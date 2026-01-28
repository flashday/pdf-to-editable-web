# 设计文档：精准作业台 V2 优化

## 概述

本设计文档描述精准作业台 V2 的四项核心优化：简化预览面板（PNG 替代 PDF）、基于锚点的同步滚动、HTML 表格支持、统一锚点格式。这些优化将减少约 100 行代码、消除坐标转换复杂性、提高渲染精度和用户体验。

### 设计目标

1. **简化架构**：移除 react-pdf 依赖，消除 PNG→PDF 坐标转换
2. **提高精度**：Bounding Box 直接使用 OCR 坐标，无转换误差
3. **增强同步**：基于锚点的精确定位替代简单比例同步
4. **保持兼容**：API 接口保持不变，现有测试继续通过

## 架构

### 当前架构问题

```
┌─────────────────────────────────────────────────────────────────┐
│                     当前架构（V1）                                │
├─────────────────────────────────────────────────────────────────┤
│  Preview Panel                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  react-pdf (PDF.js)                                         ││
│  │  ┌─────────────────┐    ┌─────────────────────────────────┐ ││
│  │  │ PDF 渲染        │    │ 坐标转换层                       │ ││
│  │  │ (加载 worker)   │    │ coordScaleX = pdfW / ocrW       │ ││
│  │  │                 │    │ coordScaleY = pdfH / ocrH       │ ││
│  │  └─────────────────┘    └─────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│  问题：                                                          │
│  - PDF.js worker 加载慢                                          │
│  - 坐标转换引入误差                                               │
│  - 代码复杂度高                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 优化后架构（V2）

```
┌─────────────────────────────────────────────────────────────────┐
│                     优化架构（V2）                                │
├─────────────────────────────────────────────────────────────────┤
│  Preview Panel                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  <img> 直接渲染 OCR PNG                                      ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │ Bounding Box Overlay                                    │││
│  │  │ - 直接使用 OCR 坐标                                      │││
│  │  │ - 仅应用 zoomLevel 缩放                                  │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│  优势：                                                          │
│  - 加载速度快（无 worker）                                        │
│  - 坐标精确（无转换）                                             │
│  - 代码简洁                                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 同步滚动架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   基于锚点的同步滚动                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Editor Panel                    Preview Panel                   │
│  ┌─────────────────┐            ┌─────────────────┐             │
│  │ Markdown 内容    │            │ PNG 图像        │             │
│  │                 │            │                 │             │
│  │ <!-- @block:001 │ ──────────►│ ┌─────────────┐ │             │
│  │ 100,50,400,30   │            │ │ Block 001   │ │             │
│  │ -->             │            │ └─────────────┘ │             │
│  │ # 标题          │            │                 │             │
│  │                 │            │ ┌─────────────┐ │             │
│  │ <!-- @block:002 │ ──────────►│ │ Block 002   │ │             │
│  │ 100,100,400,200 │            │ └─────────────┘ │             │
│  │ -->             │            │                 │             │
│  │ 正文内容...      │            │                 │             │
│  └─────────────────┘            └─────────────────┘             │
│                                                                  │
│  同步流程：                                                       │
│  1. 编辑器光标移动 → 解析最近锚点 → 滚动预览到对应 Block           │
│  2. 点击预览 Block → 查找对应锚点 → 滚动编辑器到锚点位置           │
└─────────────────────────────────────────────────────────────────┘
```

## 组件与接口

### 1. PdfPanel 组件重构

**文件**: `frontend/src/workbench/components/PdfPanel/PdfPanel.tsx`

**变更**:
- 移除 `react-pdf` 的 `Document` 和 `Page` 组件
- 移除 `pdfjs` worker 配置
- 移除 `fileType` 检测逻辑（统一使用图片模式）
- 简化为纯图片渲染

```typescript
// 移除的导入
// import { Document, Page, pdfjs } from 'react-pdf';

// 简化后的组件
interface PdfPanelProps {
  // 保持不变
}

const PdfPanel: React.FC = () => {
  // 移除: pdfUrl, fileType 状态
  // 移除: onDocumentLoadSuccess, onDocumentLoadError 回调
  // 保留: imageUrl, zoomLevel, 拖拽/缩放逻辑
  
  const imageUrl = `/api/convert/${jobId}/image?t=${Date.now()}`;
  
  return (
    <div className={styles.container}>
      <img src={imageUrl} ... />
      <BoundingBoxOverlay 
        // 移除: ocrImageWidth, ocrImageHeight props
        imageWidth={imageDimensions.width}
        imageHeight={imageDimensions.height}
        ...
      />
    </div>
  );
};
```

### 2. BoundingBoxOverlay 组件简化

**文件**: `frontend/src/workbench/components/PdfPanel/BoundingBoxOverlay.tsx`

**变更**:
- 移除 `ocrImageWidth`, `ocrImageHeight` props
- 移除 `coordScaleX`, `coordScaleY` 计算
- 直接使用 block.bbox 坐标

```typescript
interface BoundingBoxOverlayProps {
  blocks: LayoutBlock[];
  activeBlockId: string | null;
  hoveredBlockId: string | null;
  imageWidth: number;      // 现在等于 OCR 图像宽度
  imageHeight: number;     // 现在等于 OCR 图像高度
  zoomLevel: number;
  onBlockClick: (blockId: string) => void;
  onBlockHover: (blockId: string | null) => void;
  scrollTop?: number;
  scrollLeft?: number;
  containerWidth?: number;
  containerHeight?: number;
  // 移除: ocrImageWidth, ocrImageHeight
}

// 简化后的坐标计算
const renderBlock = (block: LayoutBlock) => {
  const scale = zoomLevel / 100;
  return {
    left: block.bbox.x * scale,
    top: block.bbox.y * scale,
    width: block.bbox.width * scale,
    height: block.bbox.height * scale,
  };
};
```

### 3. useSyncScroll Hook 重构

**文件**: `frontend/src/workbench/hooks/useSyncScroll.ts`

**新增功能**:
- 基于锚点的最近邻同步
- 编辑器光标位置追踪
- 双向同步支持

```typescript
interface UseSyncScrollOptions {
  pdfContainerRef: React.RefObject<HTMLElement>;
  editorContainerRef: React.RefObject<HTMLElement>;
  anchors: AnchorInfo[];           // 新增：锚点列表
  layoutBlocks: LayoutBlock[];     // 新增：Block 列表
  debounceDelay?: number;
  enabled?: boolean;
}

interface UseSyncScrollReturn {
  isSyncing: boolean;
  syncEnabled: boolean;
  toggleSync: () => void;
  syncToBlock: (blockId: string) => void;      // 新增
  syncToAnchor: (anchorId: string) => void;    // 新增
  getCurrentBlockId: () => string | null;       // 新增
}

// 核心算法：找到最近的锚点
function findNearestAnchor(
  anchors: AnchorInfo[], 
  cursorPosition: number
): AnchorInfo | null {
  let nearest: AnchorInfo | null = null;
  for (const anchor of anchors) {
    if (anchor.position <= cursorPosition) {
      nearest = anchor;
    } else {
      break;
    }
  }
  return nearest;
}
```

### 4. anchorParser 工具更新

**文件**: `frontend/src/workbench/utils/anchorParser.ts`

**变更**:
- 更新正则表达式匹配新格式
- 移除旧格式支持

```typescript
// 新的统一锚点格式
// <!-- @block:block_xxx x,y,width,height -->
const ANCHOR_REGEX = /<!--\s*@block:(\S+)\s+(\d+),(\d+),(\d+),(\d+)\s*-->/g;

// 移除旧格式
// const ANCHOR_REGEX = /<div\s+id="block_([^"]+)"...
// const COMMENT_ANCHOR_REGEX = /<!--\s*block:([^\s]+)...

export function parseAnchors(markdown: string): AnchorInfo[] {
  const anchors: AnchorInfo[] = [];
  let match;
  
  while ((match = ANCHOR_REGEX.exec(markdown)) !== null) {
    anchors.push({
      blockId: match[1],
      coords: {
        x: parseInt(match[2], 10),
        y: parseInt(match[3], 10),
        width: parseInt(match[4], 10),
        height: parseInt(match[5], 10)
      },
      position: match.index
    });
  }
  
  return anchors.sort((a, b) => a.position - b.position);
}

export function generateAnchor(
  blockId: string,
  coords: { x: number; y: number; width: number; height: number }
): string {
  return `<!-- @block:${blockId} ${coords.x},${coords.y},${coords.width},${coords.height} -->`;
}
```

### 5. VditorWrapper 配置更新

**文件**: `frontend/src/workbench/components/EditorPanel/VditorWrapper.tsx`

**变更**:
- 配置允许 HTML 表格标签
- 添加光标位置变化回调

```typescript
// Vditor 配置更新
const vditorConfig = {
  // ... 现有配置
  
  // 允许 HTML 表格标签
  preview: {
    markdown: {
      // 允许的 HTML 标签
      sanitize: false,  // 或配置白名单
    }
  },
  
  // 或使用 options.customRenders 处理 HTML 表格
};
```

### 6. 后端 API 更新

**文件**: `backend/api/workbench_routes.py`

**变更**:
- `_generate_markdown_with_anchors`: 使用新锚点格式
- `_generate_block_content`: 复杂表格输出 HTML
- `_html_table_to_markdown`: 添加复杂表格检测

```python
def _generate_anchor(block_id: str, bbox: dict) -> str:
    """生成统一格式的锚点"""
    return f"<!-- @block:{block_id} {bbox['x']},{bbox['y']},{bbox['width']},{bbox['height']} -->"

def _is_complex_table(html_content: str) -> bool:
    """检测表格是否包含 colspan 或 rowspan"""
    soup = BeautifulSoup(html_content, 'html.parser')
    cells = soup.find_all(['td', 'th'])
    for cell in cells:
        if cell.get('colspan') or cell.get('rowspan'):
            colspan = int(cell.get('colspan', 1))
            rowspan = int(cell.get('rowspan', 1))
            if colspan > 1 or rowspan > 1:
                return True
    return False

def _generate_block_content(item_type: str, res) -> str:
    """根据 Block 类型生成内容"""
    if item_type == 'table':
        if isinstance(res, dict) and 'html' in res:
            html_content = res['html']
            if _is_complex_table(html_content):
                # 复杂表格：保留 HTML 格式
                return f"\n{html_content}\n"
            else:
                # 简单表格：转换为 Markdown
                return f"\n{_html_table_to_markdown(html_content)}\n"
    # ... 其他类型处理
```

## 数据模型

### AnchorInfo（更新）

```typescript
interface AnchorInfo {
  blockId: string;           // Block ID，如 "block_001"
  coords: {
    x: number;               // 左上角 X 坐标（OCR 图像坐标系）
    y: number;               // 左上角 Y 坐标
    width: number;           // 宽度
    height: number;          // 高度
  };
  position: number;          // 在 Markdown 文本中的字符位置
}
```

### LayoutBlock（保持不变）

```typescript
interface LayoutBlock {
  id: string;                // Block ID
  type: 'text' | 'table' | 'title' | 'figure' | 'list' | 'reference';
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  confidence: number;        // 0-1 置信度
  pageNum: number;           // 页码
  text?: string;             // 文本内容预览
}
```

### 锚点格式规范

```
旧格式（移除）:
  <div id="block_xxx" data-coords="x,y,w,h" style="display:none;"></div>
  <!-- block:xxx coords:x,y,w,h -->

新格式（统一）:
  <!-- @block:block_001 100,50,400,30 -->
  
格式说明:
  - 以 "<!-- @block:" 开头，便于区分普通注释
  - Block ID 紧跟冒号，无空格
  - 坐标以逗号分隔：x,y,width,height
  - 以 " -->" 结尾
```



## 正确性属性

*正确性属性是系统在所有有效执行中应该保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### Property 1: Bounding Box 坐标直接缩放

*对于任意* LayoutBlock 和任意 zoomLevel（10-500），渲染后的 Bounding Box 位置应该等于 `block.bbox * (zoomLevel / 100)`，无需任何额外的坐标转换因子。

**Validates: Requirements 1.4, 1.5**

### Property 2: 最近锚点查找算法

*对于任意* 已排序的锚点列表和任意光标位置，`findNearestAnchor` 函数应该返回位置小于等于光标位置的最后一个锚点；如果光标位置在所有锚点之前，应该返回 null。

**Validates: Requirements 2.1**

### Property 3: 锚点解析 Round-Trip

*对于任意* 有效的 Block ID 和坐标，使用 `generateAnchor` 生成锚点字符串后，再使用 `parseAnchors` 解析，应该得到相同的 Block ID 和坐标值。

**Validates: Requirements 2.4, 4.2, 4.3**

### Property 4: 复杂表格检测与 HTML 保留

*对于任意* 包含 colspan > 1 或 rowspan > 1 的 HTML 表格，`_is_complex_table` 应该返回 True，且 `_generate_block_content` 应该输出原始 HTML 格式而非 Markdown 表格。

**Validates: Requirements 3.1, 3.3, 3.4**

### Property 5: 简单表格 Markdown 输出

*对于任意* 不包含 colspan 或 rowspan（或值均为 1）的 HTML 表格，`_is_complex_table` 应该返回 False，且 `_generate_block_content` 应该输出 Markdown 表格格式。

**Validates: Requirements 3.5**

### Property 6: 锚点生成格式正确性

*对于任意* Block ID（非空字符串）和坐标（非负整数），`generateAnchor` 生成的字符串应该匹配正则表达式 `/^<!-- @block:\S+ \d+,\d+,\d+,\d+ -->$/`。

**Validates: Requirements 4.1**

### Property 7: 锚点保存完整性 Round-Trip

*对于任意* 包含锚点的 Markdown 内容，保存到后端再重新加载后，所有锚点应该保持不变（数量相同、内容相同）。

**Validates: Requirements 4.6**

### Property 8: 旧格式锚点不被解析

*对于任意* 使用旧格式（div 格式或无 @block: 前缀的注释格式）的锚点字符串，`parseAnchors` 应该返回空数组。

**Validates: Requirements 4.5**

## 错误处理

### 预览面板错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| PNG 图片加载失败 | 显示错误提示，提供重试按钮 |
| 图片尺寸获取失败 | 使用默认尺寸，记录警告日志 |
| Block 数据为空 | 正常显示图片，不渲染 Bounding Box |

### 同步滚动错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 锚点解析失败 | 回退到比例同步算法 |
| 目标元素不存在 | 忽略滚动请求，记录警告 |
| 滚动容器未挂载 | 跳过同步操作 |

### 表格处理错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| HTML 解析失败 | 输出原始 HTML，记录错误 |
| 表格结构异常 | 输出 "[表格解析失败]" 占位符 |
| 空表格 | 输出 "[空表格]" 占位符 |

## 测试策略

### 测试框架

- **前端单元测试**: Vitest
- **前端属性测试**: fast-check
- **后端单元测试**: pytest
- **后端属性测试**: hypothesis

### 属性测试配置

```typescript
// 前端属性测试配置
import fc from 'fast-check';

// 每个属性测试至少运行 100 次迭代
const propertyTestConfig = {
  numRuns: 100,
  verbose: true,
};
```

```python
# 后端属性测试配置
from hypothesis import settings

@settings(max_examples=100)
def test_property():
    pass
```

### 测试覆盖要求

1. **属性测试**：覆盖所有 8 个正确性属性
2. **单元测试**：覆盖边界情况和错误处理
3. **集成测试**：覆盖端到端工作流

### 测试文件结构

```
frontend/src/workbench/__tests__/
├── pbt/                              # 属性测试
│   ├── boundingBoxCoords.property.test.ts    # Property 1
│   ├── nearestAnchor.property.test.ts        # Property 2
│   ├── anchorRoundTrip.property.test.ts      # Property 3, 6, 8
│   └── anchorSaveIntegrity.property.test.ts  # Property 7
├── anchorParser.test.ts              # 单元测试
├── useSyncScroll.test.ts             # 单元测试
└── BoundingBoxOverlay.test.ts        # 单元测试

backend/tests/
├── test_workbench_api.py             # 现有测试
├── test_table_detection.py           # Property 4, 5 属性测试
└── test_anchor_generation.py         # 锚点生成测试
```

### 测试标签格式

每个属性测试必须包含注释标签：

```typescript
// Feature: workbench-v2-optimization, Property 1: Bounding Box 坐标直接缩放
test.prop('bbox coordinates scale directly with zoomLevel', ...);
```

```python
# Feature: workbench-v2-optimization, Property 4: 复杂表格检测与 HTML 保留
@given(...)
def test_complex_table_detection(...):
    pass
```
