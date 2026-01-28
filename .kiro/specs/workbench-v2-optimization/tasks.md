# 实现计划：精准作业台 V2 优化

## 概述

本实现计划将精准作业台 V2 优化分解为可执行的编码任务，按照依赖关系排序，确保增量开发和持续验证。

## 任务

- [x] 1. 统一锚点格式（后端 + 前端解析器）
  - [x] 1.1 更新后端锚点生成函数
    - 修改 `backend/api/workbench_routes.py` 中的 `_generate_markdown_with_anchors` 函数
    - 使用新格式 `<!-- @block:block_xxx x,y,width,height -->`
    - 移除旧的 div 格式锚点生成逻辑
    - _Requirements: 4.1, 4.4_
  
  - [x] 1.2 更新前端锚点解析器
    - 修改 `frontend/src/workbench/utils/anchorParser.ts`
    - 更新正则表达式匹配新格式 `<!-- @block:(\S+) (\d+),(\d+),(\d+),(\d+) -->`
    - 移除对旧格式（div 格式和无前缀注释格式）的支持
    - 更新 `generateAnchor` 和 `generateAnchorComment` 函数
    - _Requirements: 4.2, 4.3, 4.5_
  
  - [x] 1.3 编写锚点解析 round-trip 属性测试
    - **Property 3: 锚点解析 Round-Trip**
    - **Validates: Requirements 2.4, 4.2, 4.3**
  
  - [x] 1.4 编写锚点格式正确性属性测试
    - **Property 6: 锚点生成格式正确性**
    - **Validates: Requirements 4.1**
  
  - [x] 1.5 编写旧格式不被解析属性测试
    - **Property 8: 旧格式锚点不被解析**
    - **Validates: Requirements 4.5**

- [x] 2. 简化预览面板（PNG 替代 PDF）
  - [x] 2.1 重构 PdfPanel 组件
    - 修改 `frontend/src/workbench/components/PdfPanel/PdfPanel.tsx`
    - 移除 `react-pdf` 相关导入和组件（Document, Page, pdfjs）
    - 移除 `fileType` 检测逻辑，统一使用图片模式
    - 移除 `pdfUrl` 状态和 PDF 相关回调
    - 简化为纯 `<img>` 渲染
    - _Requirements: 1.1, 1.2_
  
  - [x] 2.2 简化 BoundingBoxOverlay 组件
    - 修改 `frontend/src/workbench/components/PdfPanel/BoundingBoxOverlay.tsx`
    - 移除 `ocrImageWidth`, `ocrImageHeight` props
    - 移除 `coordScaleX`, `coordScaleY` 计算逻辑
    - 直接使用 `block.bbox * scale` 计算位置
    - _Requirements: 1.3, 1.4, 1.5_
  
  - [x] 2.3 编写 Bounding Box 坐标缩放属性测试
    - **Property 1: Bounding Box 坐标直接缩放**
    - **Validates: Requirements 1.4, 1.5**
  
  - [x] 2.4 更新 workbenchStore 类型定义
    - 修改 `frontend/src/workbench/stores/types.ts`
    - 移除 `ocrImageWidth`, `ocrImageHeight` 相关类型
    - _Requirements: 1.3_

- [x] 3. Checkpoint - 确保预览面板重构测试通过
  - 运行 `npm run test` 确保所有测试通过
  - 如有问题请询问用户

- [x] 4. 基于锚点的同步滚动
  - [x] 4.1 重构 useSyncScroll Hook
    - 修改 `frontend/src/workbench/hooks/useSyncScroll.ts`
    - 添加 `anchors` 和 `layoutBlocks` 参数
    - 实现 `findNearestAnchor` 函数
    - 添加 `syncToBlock` 和 `syncToAnchor` 方法
    - 保留比例同步作为回退方案
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_
  
  - [x] 4.2 编写最近锚点查找属性测试
    - **Property 2: 最近锚点查找算法**
    - **Validates: Requirements 2.1**
  
  - [x] 4.3 集成同步滚动到 Workbench 组件
    - 更新 `frontend/src/workbench/App.tsx` 或相关容器组件
    - 传递 anchors 和 layoutBlocks 到 useSyncScroll
    - 连接编辑器光标变化事件
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 5. 支持 HTML 表格直接渲染
  - [x] 5.1 添加复杂表格检测函数
    - 修改 `backend/api/workbench_routes.py`
    - 添加 `_is_complex_table(html_content)` 函数
    - 检测 colspan > 1 或 rowspan > 1
    - _Requirements: 3.3_
  
  - [x] 5.2 更新表格内容生成逻辑
    - 修改 `_generate_block_content` 函数
    - 复杂表格输出 HTML 格式
    - 简单表格继续输出 Markdown 格式
    - _Requirements: 3.1, 3.4, 3.5_
  
  - [x] 5.3 编写复杂表格检测属性测试
    - **Property 4: 复杂表格检测与 HTML 保留**
    - **Validates: Requirements 3.1, 3.3, 3.4**
  
  - [x] 5.4 编写简单表格 Markdown 输出属性测试
    - **Property 5: 简单表格 Markdown 输出**
    - **Validates: Requirements 3.5**
  
  - [x] 5.5 配置 Vditor 允许 HTML 表格
    - 修改 `frontend/src/workbench/components/EditorPanel/VditorWrapper.tsx`
    - 配置 `preview.markdown.sanitize` 或白名单
    - 确保 HTML 表格标签不被过滤
    - _Requirements: 3.2, 3.6_

- [x] 6. Checkpoint - 确保表格处理测试通过
  - 运行 `pytest backend/tests/` 确保后端测试通过
  - 运行 `npm run test` 确保前端测试通过
  - 如有问题请询问用户

- [x] 7. 锚点保存完整性验证
  - [x] 7.1 编写锚点保存完整性属性测试
    - **Property 7: 锚点保存完整性 Round-Trip**
    - **Validates: Requirements 4.6**
  
  - [x] 7.2 更新现有测试适配新格式
    - 更新 `frontend/src/workbench/__tests__/anchorParser.test.ts`
    - 更新测试用例使用新锚点格式
    - 移除旧格式相关测试
    - _Requirements: 4.2, 4.5_

- [x] 8. 清理和优化
  - [x] 8.1 移除 react-pdf 依赖
    - 从 `package.json` 移除 `react-pdf` 依赖
    - 运行 `npm install` 更新依赖
    - _Requirements: 1.2_
  
  - [x] 8.2 清理未使用的代码
    - 移除 PdfPanel 中未使用的状态和函数
    - 移除 BoundingBoxOverlay 中的调试日志
    - 清理 anchorParser 中的旧格式相关代码
    - _Requirements: 1.2, 1.3, 4.4, 4.5_

- [x] 9. Final Checkpoint - 确保所有测试通过
  - 运行完整测试套件
  - 验证所有属性测试通过
  - 确保现有功能不受影响
  - 如有问题请询问用户

## 备注

- 所有任务均为必需，包括属性测试任务
- 每个任务引用具体的需求以确保可追溯性
- Checkpoint 任务确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
