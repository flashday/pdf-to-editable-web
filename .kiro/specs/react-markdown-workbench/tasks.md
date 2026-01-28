# React + Markdown 精准作业台 - 任务清单

## 阶段一：项目基础搭建（2-3 天）

- [x] 1. React 项目初始化
  - [x] 1.1 在 frontend/src/workbench 目录创建 React 项目结构
  - [x] 1.2 配置 Vite 多入口（原有入口 + workbench 入口）
  - [x] 1.3 安装核心依赖：react, react-dom, zustand, react-router-dom
  - [x] 1.4 配置 TypeScript（可选，推荐）
  - [x] 1.5 创建基础 App.tsx 和路由配置

- [x] 2. Zustand Store 搭建
  - [x] 2.1 创建 workbenchStore.ts 定义状态结构
  - [x] 2.2 实现基础 actions：setJobId, setLayoutBlocks, setMarkdownContent
  - [x] 2.3 实现 UI 状态 actions：setActiveBlockId, setZoomLevel
  - [x] 2.4 编写 Store 单元测试

- [x] 3. 模式切换入口
  - [x] 3.1 在 Step4PreEntry.js 添加"精准编辑模式"按钮
  - [x] 3.2 实现跳转逻辑：传递 jobId 到 /workbench?jobId=xxx
  - [x] 3.3 在 workbench 页面添加"返回传统模式"按钮
  - [x] 3.4 测试模式切换流程

## 阶段二：PDF 渲染与 Bounding Box（3-4 天）

- [x] 4. PDF 面板基础
  - [x] 4.1 创建 PdfPanel 组件框架
  - [x] 4.2 实现图像加载（使用 /api/convert/{jobId}/image）
  - [x] 4.3 实现缩放控制（50%-200%）
  - [x] 4.4 实现拖拽平移
  - [x] 4.5 添加加载状态和错误处理

- [x] 5. Bounding Box 叠加层
  - [x] 5.1 创建 BoundingBoxOverlay 组件
  - [x] 5.2 实现 Box 渲染（根据 layoutBlocks 数据）
  - [x] 5.3 实现坐标缩放计算（适配 zoomLevel）
  - [x] 5.4 实现置信度颜色映射（绿/黄/红）
  - [x] 5.5 实现低置信度闪烁动画

- [x] 6. Box 交互
  - [x] 6.1 实现鼠标悬停高亮
  - [x] 6.2 实现点击选中
  - [x] 6.3 实现 Tooltip 显示（Block 类型、置信度）
  - [x] 6.4 编写交互单元测试

## 阶段三：Markdown 编辑器（3-4 天）

- [x] 7. Vditor 集成
  - [x] 7.1 安装 vditor 依赖
  - [x] 7.2 创建 VditorWrapper 组件
  - [x] 7.3 配置所见即所得模式
  - [x] 7.4 配置工具栏（标题、表格、列表等）
  - [x] 7.5 实现内容加载和变更回调

- [x] 8. 编辑器面板
  - [x] 8.1 创建 EditorPanel 组件框架
  - [x] 8.2 实现 Markdown 内容加载（调用 API）
  - [x] 8.3 实现编辑状态追踪（isDirty）
  - [x] 8.4 实现源码/所见即所得模式切换
  - [x] 8.5 添加加载状态和错误处理

- [x] 9. 表格编辑支持
  - [x] 9.1 配置 Vditor 表格插件
  - [x] 9.2 实现 HTML 表格混合渲染
  - [x] 9.3 测试复杂表格编辑场景

## 阶段四：双向交互（3-4 天）

- [x] 10. Block ID 锚点系统
  - [x] 10.1 创建 anchorParser.ts 工具函数
  - [x] 10.2 实现 parseAnchors 函数
  - [x] 10.3 实现 getBlockIdAtPosition 函数
  - [x] 10.4 编写锚点解析单元测试

- [x] 11. 点击定位（PDF -> Editor）
  - [x] 11.1 创建 useBlockMapping hook
  - [x] 11.2 监听 activeBlockId 变化
  - [x] 11.3 实现编辑器滚动到锚点位置
  - [x] 11.4 实现段落高亮效果（2 秒）
  - [x] 11.5 测试点击定位准确性

- [x] 12. 点击定位（Editor -> PDF）
  - [x] 12.1 监听编辑器光标位置变化
  - [x] 12.2 解析当前光标所在的 Block ID
  - [x] 12.3 实现 PDF 滚动到对应 Box 位置
  - [x] 12.4 实现 Box 高亮效果（2 秒）
  - [x] 12.5 测试反向定位准确性

- [x]* 13. 同步滚动（可选，V2）
  - [x]* 13.1 创建 useSyncScroll hook
  - [x]* 13.2 实现 PDF 滚动 -> Editor 同步
  - [x]* 13.3 实现 Editor 滚动 -> PDF 同步
  - [x]* 13.4 添加同步滚动开关
  - [x]* 13.5 处理滚动循环问题

## 阶段五：后端 API 增强（2-3 天）

- [x] 14. 布局数据 API
  - [x] 14.1 创建 /api/convert/{jobId}/layout-with-anchors 端点
  - [x] 14.2 从 ppstructure.json 提取 Block 数据
  - [x] 14.3 生成唯一 Block ID
  - [x] 14.4 返回标准化的布局数据格式
  - [x] 14.5 编写 API 单元测试

- [x] 15. Markdown 锚点注入
  - [x] 15.1 创建 /api/convert/{jobId}/markdown-with-anchors 端点
  - [x] 15.2 在 Markdown 生成时注入锚点
  - [x] 15.3 锚点格式：`<div id="block_xxx" data-coords="x,y,w,h" style="display:none;"></div>`
  - [x] 15.4 返回锚点位置索引
  - [x] 15.5 编写 API 单元测试

- [x] 16. 内容保存 API
  - [x] 16.1 创建 /api/convert/{jobId}/save-markdown 端点
  - [x] 16.2 保存修正后的 Markdown 到文件
  - [x] 16.3 可选：触发向量库更新
  - [x] 16.4 返回保存状态和时间戳
  - [x] 16.5 编写 API 单元测试

## 阶段六：保存与状态管理（2 天）

- [x] 17. 手动保存
  - [x] 17.1 实现 Ctrl+S 快捷键保存
  - [x] 17.2 实现保存按钮
  - [x] 17.3 显示保存状态（保存中/已保存/保存失败）
  - [x] 17.4 保存失败时显示错误信息和重试按钮

- [x] 18. 自动保存
  - [x] 18.1 创建 useAutoSave hook
  - [x] 18.2 实现 3 秒防抖自动保存
  - [x] 18.3 显示"未保存更改"提示
  - [x] 18.4 页面关闭前提示保存
  - [x] 18.5 测试自动保存可靠性

## 阶段七：集成测试与优化（2-3 天）

- [x] 19. 端到端测试
  - [x] 19.1 测试完整工作流：加载 -> 编辑 -> 保存
  - [x] 19.2 测试模式切换流程
  - [x] 19.3 测试点击定位准确性
  - [x] 19.4 测试大文档性能（50+ Block）
  - [x] 19.5 测试浏览器兼容性（Chrome/Edge/Firefox）

- [x] 20. 性能优化
  - [x] 20.1 实现 Bounding Box 虚拟渲染（仅渲染可视区域）
  - [x] 20.2 优化图像加载（懒加载、缓存）
  - [x] 20.3 优化编辑器渲染性能
  - [x] 20.4 添加性能监控日志

- [x] 21. UI 打磨
  - [x] 21.1 添加加载骨架屏
  - [x] 21.2 优化响应式布局
  - [x] 21.3 添加键盘快捷键提示
  - [x] 21.4 添加操作引导教程（首次使用）

## 属性测试任务

- [x] PBT-1. Block ID 映射一致性测试
  - 验证 PDF Bounding Box 坐标与 Markdown 锚点坐标一致

- [x] PBT-2. 点击定位准确性测试
  - 验证点击 Block 后编辑器滚动到正确位置

- [x] PBT-3. 内容保存完整性测试
  - 验证保存后重新加载内容与保存前一致

- [x] PBT-4. 置信度颜色映射测试
  - 验证 getConfidenceColor 函数返回正确颜色

---

## 任务统计

| 阶段 | 任务数 | 预估工期 |
|------|--------|----------|
| 阶段一：项目基础搭建 | 3 | 2-3 天 |
| 阶段二：PDF 渲染与 Bounding Box | 3 | 3-4 天 |
| 阶段三：Markdown 编辑器 | 3 | 3-4 天 |
| 阶段四：双向交互 | 4 | 3-4 天 |
| 阶段五：后端 API 增强 | 3 | 2-3 天 |
| 阶段六：保存与状态管理 | 2 | 2 天 |
| 阶段七：集成测试与优化 | 3 | 2-3 天 |
| **总计** | **21** | **17-23 天** |

注：标记 `*` 的任务为可选任务，可在 V2 版本实现。
