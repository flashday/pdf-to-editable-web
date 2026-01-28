# React + Markdown 精准作业台方案可行性分析报告

## 1. 方案概述

你提出的方案核心是构建一个"人机协同"的文档处理流水线：
- **左侧**：PDF 原文渲染 + OCR Bounding Box 叠加层
- **右侧**：Markdown 编辑器（Vditor）
- **核心交互**：双向同步滚动、点击定位、置信度告警

## 2. 可行性评估：✅ 方案整体可行

### 2.1 技术可行性分析

| 技术点 | 可行性 | 说明 |
|--------|--------|------|
| PDF 渲染 + Bounding Box | ✅ 成熟 | `react-pdf` + `react-pdf-highlighter` 生态成熟，支持坐标高亮 |
| Markdown 编辑器 | ✅ 成熟 | Vditor 支持 React 封装，所见即所得，表格支持好 |
| 双向同步滚动 | ⚠️ 中等难度 | 需要自研锚点映射算法，非简单百分比同步 |
| Block ID 映射 | ✅ 可行 | PaddleOCR 3.x 已输出 `layout.json` 含坐标信息 |
| 置信度告警 | ✅ 简单 | 已有 `confidence_report`，只需前端渲染 |

### 2.2 与现有系统的兼容性

**优势**：
- 后端 PaddleOCR 3.x 已经输出 `ppstructure.json`（含坐标）和 `raw_ocr.md`（Markdown）
- RAG 向量化流程已实现（`rag_service.py`, `vector_store.py`）
- LLM 服务已集成（`llm_service.py`）

**挑战**：
- 当前前端是**纯原生 JS**，引入 React 需要架构调整
- 需要建立 Markdown 段落与 JSON Block ID 的映射关系（后端需增强）

## 3. 开发代价评估

### 3.1 方案一：完整 React 重构（推荐方案）

| 阶段 | 工作内容 | 预估工期 |
|------|----------|----------|
| **阶段1：基础框架** | React 项目搭建、路由、状态管理（Zustand） | 2-3 天 |
| **阶段2：PDF 渲染** | react-pdf 集成、Canvas 叠加层、Bounding Box 渲染 | 3-4 天 |
| **阶段3：Markdown 编辑器** | Vditor 集成、Block ID 锚点注入、编辑保存 | 3-4 天 |
| **阶段4：双向同步** | 滚动同步算法、点击定位、置信度高亮 | 4-5 天 |
| **阶段5：后端增强** | Block ID 映射 API、Markdown 锚点注入 | 2-3 天 |
| **阶段6：集成测试** | 端到端测试、性能优化、边界情况处理 | 2-3 天 |
| **总计** | | **16-22 个工作日** |

### 3.2 方案二：渐进式迁移（你提出的双模式方案）✅ 推荐

保留现有模式，新增"精准编辑模式"入口，用户可选择切换。

| 阶段 | 工作内容 | 预估工期 |
|------|----------|----------|
| **阶段1：独立 React 模块** | 在 `/editor` 路由下创建独立 React 应用 | 2 天 |
| **阶段2：PDF 渲染** | react-pdf + Bounding Box 叠加层 | 3-4 天 |
| **阶段3：Markdown 编辑器** | Vditor 集成、基础编辑功能 | 2-3 天 |
| **阶段4：简化同步** | 先实现点击定位，滚动同步作为后续优化 | 2-3 天 |
| **阶段5：模式切换** | 在 Step4 添加"切换到精准编辑模式"按钮 | 1 天 |
| **阶段6：数据打通** | 与现有 API 对接、保存回写 | 2 天 |
| **总计** | | **12-15 个工作日** |

## 4. 关键技术决策建议

### 4.1 PDF 渲染方案

```
推荐：react-pdf-highlighter-extended
- 原生支持 Bounding Box 高亮
- 支持自定义 Tip 提示
- 坐标格式与 PaddleOCR 输出兼容
```

### 4.2 Markdown 编辑器方案

```
推荐：Vditor
- 所见即所得，业务人员友好
- 原生支持表格编辑
- 支持 HTML 混合渲染（复杂表格）
- 有成熟的 React 封装：react-vditor
```

### 4.3 状态管理

```
推荐：Zustand
- 比 Redux 轻量
- 适合管理：activeBlockId、scrollPosition、editHistory
```

### 4.4 双向同步算法

```javascript
// 核心思路：基于锚点的最近邻同步
// 1. 后端在 Markdown 中注入不可见锚点
//    <div id="block_123" data-coords="100,200,500,600"></div>
//    # 章节标题

// 2. PDF -> Editor 同步
function onPdfScroll(viewportCenter) {
  const nearestBlock = findNearestBlock(viewportCenter, layoutJson);
  editor.scrollToElement(`#block_${nearestBlock.id}`);
}

// 3. Editor -> PDF 同步
function onEditorScroll(cursorPosition) {
  const blockId = getBlockIdFromCursor(cursorPosition);
  const coords = layoutJson[blockId].bbox;
  pdfViewer.scrollTo(coords.y);
}
```

## 5. 风险与挑战

### 5.1 高风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 双向同步复杂度 | 图片在 PDF 中占大篇幅，Markdown 中只占一行 | 采用锚点映射而非百分比同步 |
| 大文档性能 | 100+ 页 PDF 渲染卡顿 | 虚拟滚动、按需渲染 |
| 表格编辑 | 复杂合并单元格难以用 Markdown 表示 | 保留 HTML 表格，Vditor 混合渲染 |

### 5.2 中等风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| React 与现有代码共存 | 可能有样式冲突 | 使用 CSS Modules 或 Shadow DOM |
| 用户学习成本 | 新界面需要适应 | 提供引导教程、保留旧模式 |

## 6. 实施建议

### 6.1 推荐采用方案二（渐进式迁移）

理由：
1. **风险可控**：保留现有功能，新模式作为可选项
2. **用户友好**：给用户适应时间，收集反馈后再决定是否下线旧模式
3. **开发效率**：可以先实现核心功能，复杂功能（如完美同步滚动）后续迭代

### 6.2 实施路线图

```
Week 1-2: 搭建独立 React 模块 + PDF 渲染
Week 3:   Vditor 集成 + 基础编辑
Week 4:   点击定位 + 模式切换入口
Week 5:   集成测试 + 上线 Beta
Week 6+:  收集反馈、优化同步滚动
```

### 6.3 后端需要的增强

1. **Block ID 映射 API**：返回 Markdown 段落与 JSON Block 的对应关系
2. **Markdown 锚点注入**：在生成 Markdown 时自动插入 `<div id="block_xxx">` 锚点
3. **编辑保存 API**：接收修正后的 Markdown，更新向量库

## 7. 结论

| 维度 | 评估 |
|------|------|
| **技术可行性** | ✅ 完全可行，核心库生态成熟 |
| **开发代价** | 中等，12-22 个工作日 |
| **推荐方案** | 方案二：渐进式迁移，双模式并存 |
| **核心难点** | 双向同步滚动算法、大文档性能 |
| **建议优先级** | 先实现点击定位，滚动同步作为 V2 优化 |

---

*分析日期：2026-01-28*
*分析人：Kiro AI Assistant*
