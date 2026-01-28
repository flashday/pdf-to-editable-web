# 需求文档：精准作业台 V2 优化

## 简介

精准作业台 V1 已完成基础功能（Block Mapping、Overlay Layer、Sync-Scrolling、表格处理），现在需要进行 V2 优化以提升用户体验、简化代码架构和提高渲染精度。本次优化主要包含四个方面：简化预览面板、优化同步滚动算法、支持 HTML 表格直接渲染、统一锚点格式。

## 术语表

- **Workbench（精准作业台）**: 用于 OCR 结果校正的双面板编辑界面，左侧显示原始文档预览，右侧显示 Markdown 编辑器
- **Preview_Panel（预览面板）**: 显示原始文档的左侧面板，用于展示 Bounding Box 和定位
- **Bounding_Box**: 在预览面板上绘制的矩形框，标识 OCR 识别的文本区块位置
- **Block**: OCR 识别的文本区块，包含 ID、类型、坐标、置信度等信息
- **Anchor（锚点）**: 嵌入在 Markdown 中的标记，用于关联 Block ID 和坐标信息
- **Sync_Scroll（同步滚动）**: 预览面板和编辑器面板之间的滚动位置同步机制
- **Vditor**: 所见即所得的 Markdown 编辑器组件
- **OCR_Image**: OCR 处理时生成的 PNG 图像，Bounding Box 坐标基于此图像

## 需求

### 需求 1：使用 PNG 图片替代 PDF 渲染

**用户故事：** 作为开发者，我希望预览面板直接使用 OCR 处理的 PNG 图片，以便消除坐标转换逻辑并提高 Bounding Box 对齐精度。

#### 验收标准

1. WHEN Preview_Panel 加载文档 THEN THE Preview_Panel SHALL 直接加载 OCR 处理生成的 PNG 图片而非 PDF 文件
2. THE Preview_Panel SHALL 移除 react-pdf 依赖和相关的 PDF 渲染逻辑
3. THE Bounding_Box_Overlay SHALL 移除 coordScaleX 和 coordScaleY 坐标转换计算
4. WHEN Bounding_Box 渲染时 THEN THE Bounding_Box_Overlay SHALL 直接使用 OCR 坐标而无需转换
5. WHEN 用户缩放预览时 THEN THE Preview_Panel SHALL 仅应用 zoomLevel 缩放因子
6. THE Preview_Panel SHALL 保持现有的拖拽平移和滚轮缩放功能

### 需求 2：基于锚点的最近邻同步滚动

**用户故事：** 作为用户，我希望编辑器和预览面板的滚动同步更加精确，以便在编辑时能准确定位到对应的文档区域。

#### 验收标准

1. WHEN 用户在编辑器中滚动或移动光标 THEN THE Sync_Scroll SHALL 解析当前位置最近的锚点
2. WHEN 找到最近锚点 THEN THE Sync_Scroll SHALL 滚动预览面板到对应 Block 的 Bounding_Box 位置
3. WHEN 用户点击预览面板的 Bounding_Box THEN THE Sync_Scroll SHALL 滚动编辑器到对应锚点位置
4. THE Anchor_Parser SHALL 支持解析新的统一锚点格式
5. IF 当前位置没有找到锚点 THEN THE Sync_Scroll SHALL 回退到比例同步算法
6. THE Sync_Scroll SHALL 提供防抖处理以避免频繁滚动

### 需求 3：支持 HTML 表格直接渲染

**用户故事：** 作为用户，我希望复杂表格（包含 colspan/rowspan）能够正确显示，以便准确校正表格内容。

#### 验收标准

1. WHEN 后端生成 Markdown 时遇到复杂表格 THEN THE Backend SHALL 保留原始 HTML 表格格式
2. WHEN Vditor 渲染包含 HTML 表格的 Markdown THEN THE Vditor_Wrapper SHALL 正确显示 HTML 表格
3. THE Backend SHALL 检测表格是否包含 colspan 或 rowspan 属性
4. IF 表格包含 colspan 或 rowspan THEN THE Backend SHALL 输出 HTML 表格而非 Markdown 表格
5. IF 表格是简单表格（无合并单元格）THEN THE Backend SHALL 继续输出 Markdown 表格格式
6. THE Vditor_Wrapper SHALL 配置允许 HTML 表格标签通过

### 需求 4：统一锚点格式

**用户故事：** 作为开发者，我希望锚点格式统一且易于解析，以便减少解析错误和与其他注释的混淆。

#### 验收标准

1. THE Backend SHALL 使用统一的锚点格式：`<!-- @block:block_xxx x,y,width,height -->`
2. THE Anchor_Parser SHALL 仅解析以 `@block:` 开头的注释作为锚点
3. WHEN 解析锚点时 THEN THE Anchor_Parser SHALL 提取 Block ID 和坐标信息
4. THE Backend SHALL 移除旧的 div 格式锚点生成逻辑
5. THE Anchor_Parser SHALL 移除对旧格式（div 格式和无前缀注释格式）的支持
6. WHEN 保存 Markdown 时 THEN THE System SHALL 保留锚点注释不被编辑器清除

## 技术约束

- 前端使用 TypeScript + React
- 测试使用 vitest
- 保持现有 API 接口兼容（端点路径和响应格式不变）
- 所有现有测试必须通过
- 支持的浏览器：Chrome、Firefox、Edge 最新版本
