# 前端代码架构分析与重构方案

> 更新日期：2026-01-27
> 目的：提高调试效率，便于快速定位问题

---

## 一、当前代码架构概览

### 1.1 文件结构
```
frontend/src/
├── index.html          # 主 HTML（961行，含大量内联脚本 v6）
├── index.js            # App 主类（1354行，v47）
├── utils/
│   └── globalFunctions.js  # 全局函数（v26）
├── services/
│   ├── EventBus.js         # 事件总线（单例）
│   ├── StateManager.js     # 状态管理（单例）
│   ├── StepManager.js      # 步骤管理（单例）
│   ├── UIManager.js        # UI 管理（旧代码）
│   └── DocumentProcessor.js # 文档处理（旧代码）
├── components/
│   ├── steps/              # 步骤组件 Step1-6
│   └── panels/             # 面板组件
└── styles/                 # CSS 模块
```

### 1.2 核心单例实例
| 实例 | 文件 | 全局访问 | 说明 |
|------|------|----------|------|
| `eventBus` | EventBus.js | `window.eventBus` | 事件发布订阅 |
| `stateManager` | StateManager.js | `window.stateManager` | 全局状态存储 |
| `stepManager` | StepManager.js | `window.stepManager` | 步骤流程控制 |
| `app` | index.js | `window.app` | 主应用实例 |

---

## 二、核心问题分析

### 2.1 ⚠️ 代码分散问题（最严重）

**同一功能的代码分布在多处：**

| 功能 | index.js | globalFunctions.js | 内联脚本 |
|------|----------|-------------------|----------|
| 步骤状态更新 | `setStepStatus()` | `updateStepStatus()` | 直接操作 DOM |
| Block 列表渲染 | `renderBlockList()` | - | `renderBlockListInline()` |
| 历史加载 | `loadCachedJob()` | `loadCachedJob()` | - |
| 服务状态检查 | `checkLlmServiceStatus()` | `checkAllServicesStatus()` | - |

**问题影响**：
- 修改一处，其他地方不同步
- 浏览器缓存旧版本时，调用的是旧代码
- 调试时不知道哪个函数被实际执行

### 2.2 ⚠️ 浏览器缓存问题

**根因**：ES6 模块被浏览器缓存，即使版本号更新也可能不生效

**已采用的解决方案**：
- 在内联脚本中实现关键逻辑（v6）
- 版本号后缀：`index.js?v=51&t=20260127j`

**推荐的长期方案**：
- 使用 Vite 的 HMR（热模块替换）
- 或在开发时禁用缓存（DevTools → Network → Disable cache）

### 2.3 ⚠️ 状态管理混乱

**状态存储位置**：
1. `window.app` 实例属性（`ocrRegions`, `ocrData`, `currentJobId`）
2. `window.stateManager` 单例（`jobId`, `ocrRegions`, `selectedDocumentTypeId`）
3. 组件内部状态（`Step5DataExtract.extractionCompleted`）

**问题**：
- 数据不同步：`window.app.ocrRegions` vs `stateManager.get('ocrRegions')`
- 步骤间数据传递需要手动同步

### 2.4 ⚠️ 事件流复杂

**三种事件机制并存**：
1. **EventBus 事件**：`eventBus.emit(EVENTS.UPLOAD_COMPLETED)`
2. **DOM 事件**：`element.addEventListener('click', ...)`
3. **内联事件**：`onclick="window.loadCachedJob('xxx')"`

**事件流示例（上传文件）**：
```
用户选择文件
  → UIManager.onFileSelected()
  → Step2FileUpload.processFile()
  → eventBus.emit(UPLOAD_COMPLETED)
  → index.js 监听 UPLOAD_COMPLETED
  → 更新步骤状态
  → Step3Recognition 监听 RECOGNITION_STARTED
  → ...
```

---

## 三、快速调试指南

### 3.1 版本确认
```javascript
// 在浏览器控制台执行
console.log('index.js loaded:', document.querySelector('script[src*="index.js"]')?.src);
console.log('App version:', window.app ? 'loaded' : 'NOT loaded');
```

### 3.2 状态检查
```javascript
// 查看当前状态
console.log('Current jobId:', window.app?.currentJobId);
console.log('StateManager state:', window.stateManager?.getState());
console.log('OCR regions:', window.app?.ocrRegions?.length);
```

### 3.3 事件监听调试
```javascript
// 监听所有 EventBus 事件
Object.values(window.EVENTS || {}).forEach(event => {
    window.eventBus?.on(event, data => {
        console.log(`[EventBus] ${event}:`, data);
    });
});
```

### 3.4 强制刷新方法
1. **Ctrl+Shift+R**：强制刷新（清除缓存）
2. **重启前端服务**：`npm run dev`
3. **DevTools → Network → Disable cache**：开发时禁用缓存

### 3.5 常见问题定位

| 问题现象 | 可能原因 | 检查方法 |
|----------|----------|----------|
| Block 列表不显示 | 缓存旧版本 | 检查控制台 `INDEX.JS VERSION` |
| 步骤状态不更新 | 事件未触发 | 添加 EventBus 监听 |
| 数据未传递到下一步 | StateManager 未同步 | 检查 `stateManager.getState()` |
| 按钮点击无反应 | 事件绑定失败 | 检查元素是否存在 |

---

## 四、重构方案

### 4.1 短期优化（推荐立即执行）

#### A. 统一状态管理
```javascript
// 所有数据统一存储到 StateManager
// 废弃 window.app 中的重复属性
stateManager.set('jobId', jobId);
stateManager.set('ocrRegions', regions);
stateManager.set('ocrData', data);

// 读取时统一使用
const jobId = stateManager.get('jobId');
```

#### B. 统一函数入口
```javascript
// globalFunctions.js 中的函数作为唯一入口
// index.js 中的同名方法调用 globalFunctions

// index.js
setStepStatus(step, status, time) {
    window.updateStepStatus(step, status, time);  // 调用全局函数
}
```

#### C. 添加调试日志
```javascript
// 在关键函数入口添加日志
console.log(`[${new Date().toISOString()}] functionName called:`, args);
```

### 4.2 中期重构（建议下次迭代）

#### A. 移除内联脚本
将 `index.html` 中的内联脚本移到独立文件：
```
frontend/src/
├── init.js           # 初始化脚本（从内联脚本抽取）
├── inlineHelpers.js  # 内联辅助函数
```

#### B. 清理旧代码
- 移除 `UIManager.js` 中的上传事件绑定
- 移除 `DocumentProcessor.js`（已被 Step2/Step3 替代）
- 移除 `index.js` 中的废弃方法

#### C. 组件化完善
- 每个 Step 组件完全独立
- 组件间通过 EventBus 通信
- 状态统一由 StateManager 管理

### 4.3 长期目标（架构升级）

```
理想架构：
┌─────────────────────────────────────────────┐
│                  index.html                  │
│  (仅包含 HTML 结构，无内联脚本)              │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│                   App.js                     │
│  (应用入口，初始化组件和服务)                │
└─────────────────────────────────────────────┘
                      ↓
┌──────────┬──────────┬──────────┬────────────┐
│ EventBus │ State    │ Step     │ API        │
│          │ Manager  │ Manager  │ Service    │
└──────────┴──────────┴──────────┴────────────┘
                      ↓
┌──────────┬──────────┬──────────┬────────────┐
│  Step1   │  Step2   │  Step3   │  Step4-6   │
│ Component│ Component│ Component│ Components │
└──────────┴──────────┴──────────┴────────────┘
```

---

## 五、代码版本追踪

### 当前版本号
| 文件 | 版本 | 更新日期 |
|------|------|----------|
| index.js | v52 (t=20260128a) | 2026-01-28 |
| globalFunctions.js | v28 | 2026-01-28 |
| 内联脚本 | v7 (方案A) | 2026-01-28 |
| Step5DataExtract.js | v37 | 2026-01-27 |
| Step6Confirmation.js | v19 | 2026-01-28 |

### 版本号更新规则
- 修改文件后，版本号 +1
- 在 `index.html` 的 `<script>` 标签中更新
- 格式：`?v=版本号&t=日期标识`

---

## 六、附录：关键函数索引

### 步骤流程
| 函数 | 位置 | 说明 |
|------|------|------|
| `setStepStatus()` | index.js | 更新步骤状态 |
| `updateStepStatus()` | globalFunctions.js | 更新步骤状态（全局） |
| `confirmStep4AndProceed()` | globalFunctions.js | 步骤4→5 |
| `switchToStep5UI()` | globalFunctions.js | 切换到步骤5界面 |

### 数据处理
| 函数 | 位置 | 说明 |
|------|------|------|
| `handleProcessingComplete()` | index.js | OCR 完成后处理 |
| `extractOCRRegions()` | globalFunctions.js | 提取 OCR 区域（统一入口） |
| `renderBlockList()` | globalFunctions.js | 渲染 Block 列表（统一入口） |
| `drawOCRRegions()` | globalFunctions.js | 绘制 OCR 区域框（统一入口） |
| `showConfidenceReport()` | globalFunctions.js | 显示置信度报告（统一入口） |
| `showStep4UI()` | globalFunctions.js | 显示步骤4界面（统一入口） |

### 历史缓存
| 函数 | 位置 | 说明 |
|------|------|------|
| `loadCachedJob()` | globalFunctions.js | 加载历史缓存 |
| `loadHistoryPanel()` | globalFunctions.js | 加载历史面板 |
| `deleteHistoryJob()` | globalFunctions.js | 删除历史记录 |

---

## 七、已知问题与解决方案

### 问题1：Block 列表不显示
- **原因**：浏览器缓存旧版本 index.js
- **解决**：内联脚本 v6 直接实现渲染逻辑
- **状态**：✅ 已解决

### 问题2：步骤5单据类型不正确
- **原因**：`loadCachedJob` 函数重复定义
- **解决**：统一使用 `window.loadCachedJob`
- **状态**：✅ 已解决

### 问题3：LLM日志下载失败
- **原因**：TEMP_DIR 路径错误
- **解决**：修正为项目根目录的 temp
- **状态**：✅ 已解决

### 问题4：步骤4左边坐标框不显示
- **原因**：内联脚本处理 OCR 结果后没有调用绘制区域框的函数
- **解决**：按方案A重构，将 `drawOCRRegions` 移到 `globalFunctions.js` 作为统一入口
- **状态**：✅ 已解决（2026-01-28）

---

## 八、方案A重构记录（2026-01-28）

### 重构内容
按照 4.1 短期优化方案A，将以下函数从内联脚本移到 `globalFunctions.js` 作为统一入口：

| 函数 | 原位置 | 新位置 | 说明 |
|------|--------|--------|------|
| `extractOCRRegions()` | 内联脚本 | globalFunctions.js | 提取 OCR 区域信息 |
| `renderBlockList()` | 内联脚本 | globalFunctions.js | 渲染 Block 列表 |
| `drawOCRRegions()` | 内联脚本 | globalFunctions.js | 绘制 OCR 区域框 |
| `showConfidenceReport()` | 内联脚本 | globalFunctions.js | 显示置信度报告 |
| `showStep4UI()` | 内联脚本 | globalFunctions.js | 显示步骤4界面 |

### 内联脚本改动
内联脚本（v7）现在只是简单的包装函数，调用 `globalFunctions.js` 中的统一入口：

```javascript
function drawOCRRegionsInline(blocks) {
    if (window.drawOCRRegions) {
        window.drawOCRRegions(blocks);
    } else {
        console.error('drawOCRRegions not found in globalFunctions.js');
    }
}
```

### 优势
1. **统一入口**：所有数据处理函数都在 `globalFunctions.js` 中
2. **易于维护**：修改一处，全局生效
3. **调试方便**：函数位置明确，日志统一
4. **缓存友好**：`globalFunctions.js` 不是 ES6 模块，缓存问题较少
