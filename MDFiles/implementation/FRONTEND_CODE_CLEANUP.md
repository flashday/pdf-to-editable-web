# 前端代码清理分析

## 当前问题

### 1. 双重事件绑定冲突
- `UIManager.setupEventListeners()` 绑定了上传区域事件
- `Step2FileUpload.bindEvents()` 也绑定了相同元素的事件
- 两者冲突，导致事件流程混乱

### 2. 旧代码和新代码混杂
| 文件 | 类型 | 说明 |
|------|------|------|
| `UIManager.js` | 旧代码 | 处理上传、状态显示，但调用旧的 handleFileUpload |
| `DocumentProcessor.js` | 旧代码 | 直接调用 API，不触发 EventBus 事件 |
| `Step2FileUpload.js` | V3 新代码 | 使用 EventBus 触发事件 |
| `Step3Recognition.js` | V3 新代码 | 监听 EventBus 事件 |
| `index.js` | 混合 | 同时包含旧逻辑和新逻辑 |

### 3. 事件流程问题
**旧流程（不触发步骤高亮）：**
```
UIManager.onFileSelected() 
  → window.app.handleFileUpload() 
  → DocumentProcessor.processFile() 
  → 直接调用 API（不触发 EventBus）
```

**新流程（正确触发步骤高亮）：**
```
UIManager.onFileSelected() 
  → Step2FileUpload.processFile() 
  → EventBus.emit(UPLOAD_COMPLETED) 
  → Step3Recognition 监听并激活步骤3
```

## 清理方案

### 方案1：最小改动（已实施）
修改 `UIManager.onFileSelected()` 优先调用 `Step2FileUpload.processFile()`

### 方案2：彻底重构（推荐）
1. 移除 `UIManager` 中的上传事件绑定
2. 让 `Step2FileUpload` 完全接管上传逻辑
3. 注释或删除 `index.js` 中的旧上传方法

## 需要清理的旧代码

### index.js 中的旧方法（可注释）
- `handleFileUpload()` - 旧的上传入口
- `startStatusPolling()` - 旧的轮询逻辑
- `extractOCRRegions()` - 重复定义（Step3Recognition 中也有）

### UIManager.js 中的旧逻辑
- `setupEventListeners()` 中的上传事件绑定 - 与 Step2FileUpload 冲突
