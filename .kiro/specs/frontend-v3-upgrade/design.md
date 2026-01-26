# 前端 V3 升级设计文档

## 1. 架构概述

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         index.html (精简版)                          │
│  - 基础 HTML 结构                                                    │
│  - 引入 CSS 和 JS 模块                                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐         ┌───────────────┐
│  styles/      │         │    index.js     │         │  components/  │
│  ├─ base.css  │         │  (App 主控制器) │         │  (步骤组件)   │
│  ├─ layout.css│         │  - 工作流管理   │         │               │
│  ├─ steps.css │         │  - 步骤切换     │         │               │
│  └─ panels.css│         │  - 全局状态     │         │               │
└───────────────┘         └────────┬────────┘         └───────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐
│  StepManager.js   │    │  StateManager.js  │    │  EventBus.js      │
│  - 步骤状态管理   │    │  - 全局状态存储   │    │  - 组件间通信     │
│  - 步骤切换逻辑   │    │  - 数据传递       │    │  - 事件发布订阅   │
└───────────────────┘    └───────────────────┘    └───────────────────┘
```

### 1.2 步骤组件架构

```
components/steps/
├── Step1ModelLoad.js      # 步骤1：模型加载
├── Step2FileUpload.js     # 步骤2：文件上传
├── Step3Recognition.js    # 步骤3：智能识别
├── Step4PreEntry.js       # 步骤4：预录入（增强）
├── Step5DataExtract.js    # 步骤5：数据提取与自检
└── Step6Confirmation.js   # 步骤6：财务确认（新增）

components/panels/
├── HistoryPanel.js        # 历史缓存面板
├── TemplatePanel.js       # 关键词模板面板
└── CheckpointPanel.js     # 检查点设定面板
```

### 1.3 数据流

```
Step3 (OCR结果)
    │
    ▼ ocrResult
Step4 (预录入)
    │ 用户修正
    ▼ corrections + finalText
Step5 (数据提取)
    │ LLM提取 + 检查点验证
    ▼ extractedData + checkpointResults
Step6 (财务确认)
    │ 用户确认/驳回
    ▼ finalResult
```

---

## 2. 组件设计

### 2.1 StepManager（步骤管理器）

```javascript
// services/StepManager.js
class StepManager {
    constructor() {
        this.currentStep = 1;
        this.stepStatus = {
            1: 'pending',  // pending | in_progress | completed | error
            2: 'pending',
            3: 'pending',
            4: 'pending',
            5: 'pending',
            6: 'pending'
        };
        this.stepTimings = {};  // 每步耗时记录
    }

    // 切换到指定步骤
    goToStep(stepNumber) {}
    
    // 完成当前步骤，进入下一步
    completeCurrentStep() {}
    
    // 返回上一步（仅步骤6可返回步骤4）
    goBack() {}
    
    // 更新步骤状态
    updateStepStatus(step, status) {}
    
    // 渲染步骤进度条
    renderProgressBar() {}
}
```

### 2.2 StateManager（状态管理器）

```javascript
// services/StateManager.js
class StateManager {
    constructor() {
        this.state = {
            jobId: null,
            ocrResult: null,       // 步骤3输出
            corrections: [],       // 步骤4用户修正
            finalText: null,       // 步骤4输出（修正后文本）
            extractedData: null,   // 步骤5提取结果
            checkpointResults: [], // 步骤5检查点结果
            finalResult: null      // 步骤6最终结果
        };
    }

    // 获取状态
    get(key) {}
    
    // 设置状态
    set(key, value) {}
    
    // 重置状态（新任务时）
    reset() {}
    
    // 保存到本地存储
    persist() {}
    
    // 从本地存储恢复
    restore() {}
}
```

### 2.3 EventBus（事件总线）

```javascript
// services/EventBus.js
class EventBus {
    constructor() {
        this.listeners = {};
    }

    // 订阅事件
    on(event, callback) {}
    
    // 取消订阅
    off(event, callback) {}
    
    // 发布事件
    emit(event, data) {}
}

// 预定义事件
const EVENTS = {
    STEP_CHANGED: 'step:changed',
    OCR_COMPLETED: 'ocr:completed',
    CORRECTION_SAVED: 'correction:saved',
    EXTRACTION_COMPLETED: 'extraction:completed',
    CHECKPOINT_COMPLETED: 'checkpoint:completed',
    FINAL_CONFIRMED: 'final:confirmed',
    FINAL_REJECTED: 'final:rejected'
};
```

---

## 3. 步骤组件详细设计

### 3.1 Step4PreEntry（预录入组件）

```javascript
// components/steps/Step4PreEntry.js
class Step4PreEntry {
    constructor(container, stateManager, eventBus) {
        this.container = container;
        this.state = stateManager;
        this.events = eventBus;
        this.corrections = [];
    }

    // 渲染界面
    render() {
        // 左侧：原始图片 + OCR区域框
        // 右侧：Block列表（可编辑）
    }

    // 编辑Block
    editBlock(blockIndex) {
        // 弹出编辑框
        // 记录原始值
    }

    // 保存修正
    async saveCorrection(blockIndex, originalText, correctedText) {
        const correction = {
            blockIndex,
            originalText,
            correctedText,
            timestamp: new Date().toISOString()
        };
        this.corrections.push(correction);
        
        // 保存到后端
        await this.saveCorrectionToBackend(correction);
        
        // 发布事件
        this.events.emit(EVENTS.CORRECTION_SAVED, correction);
    }

    // 保存到后端
    async saveCorrectionToBackend(correction) {
        const jobId = this.state.get('jobId');
        await fetch(`/api/corrections/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(correction)
        });
    }

    // 确认并进入下一步
    confirmAndProceed() {
        // 合并修正后的文本
        const finalText = this.mergeCorrectedText();
        this.state.set('finalText', finalText);
        this.state.set('corrections', this.corrections);
        
        // 触发步骤完成
        this.events.emit(EVENTS.STEP_COMPLETED, { step: 4 });
    }
}
```

### 3.2 Step5DataExtract（数据提取组件）

```javascript
// components/steps/Step5DataExtract.js
class Step5DataExtract {
    constructor(container, stateManager, eventBus) {
        this.container = container;
        this.state = stateManager;
        this.events = eventBus;
    }

    // 渲染界面
    render() {
        // 模板选择区
        // 提取结果显示区
        // 检查点结果显示区
    }

    // 执行关键词提取
    async extractByTemplate(templateId) {
        const finalText = this.state.get('finalText');
        const template = await this.loadTemplate(templateId);
        
        const response = await fetch('/api/llm/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: finalText,
                fields: template.fields
            })
        });
        
        const extractedData = await response.json();
        this.state.set('extractedData', extractedData);
        this.renderExtractedData(extractedData);
        
        this.events.emit(EVENTS.EXTRACTION_COMPLETED, extractedData);
    }

    // 执行检查点验证
    async runCheckpoints() {
        const checkpoints = await this.loadCheckpoints();
        const finalText = this.state.get('finalText');
        const results = [];
        
        for (const checkpoint of checkpoints) {
            const response = await fetch('/api/llm/qa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: checkpoint.question,
                    context: finalText
                })
            });
            
            const result = await response.json();
            results.push({
                question: checkpoint.question,
                answer: result.answer,
                confidence: result.confidence
            });
        }
        
        this.state.set('checkpointResults', results);
        this.renderCheckpointResults(results);
        
        // 保存到后端
        await this.saveCheckpointsToBackend(results);
        
        this.events.emit(EVENTS.CHECKPOINT_COMPLETED, results);
    }

    // 保存检查点结果到后端
    async saveCheckpointsToBackend(results) {
        const jobId = this.state.get('jobId');
        await fetch(`/api/checkpoints/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(results)
        });
    }
}
```

### 3.3 Step6Confirmation（财务确认组件）

```javascript
// components/steps/Step6Confirmation.js
class Step6Confirmation {
    constructor(container, stateManager, eventBus) {
        this.container = container;
        this.state = stateManager;
        this.events = eventBus;
    }

    // 渲染界面
    render() {
        const checkpointResults = this.state.get('checkpointResults');
        const extractedData = this.state.get('extractedData');
        
        this.container.innerHTML = `
            <div class="confirmation-panel">
                <div class="checkpoint-section">
                    <h3>检查点验证结果</h3>
                    ${this.renderCheckpointList(checkpointResults)}
                </div>
                <div class="data-section">
                    <h3>提取数据</h3>
                    <div class="json-viewer">
                        <pre>${JSON.stringify(extractedData, null, 2)}</pre>
                    </div>
                    <button class="copy-btn">复制 JSON</button>
                </div>
                <div class="action-buttons">
                    <button class="confirm-btn">确认</button>
                    <button class="reject-btn">驳回</button>
                </div>
            </div>
        `;
        
        this.bindEvents();
    }

    // 确认
    async confirm() {
        const finalResult = {
            jobId: this.state.get('jobId'),
            extractedData: this.state.get('extractedData'),
            checkpointResults: this.state.get('checkpointResults'),
            corrections: this.state.get('corrections'),
            status: 'confirmed',
            confirmedAt: new Date().toISOString()
        };
        
        await this.saveFinalResult(finalResult);
        this.events.emit(EVENTS.FINAL_CONFIRMED, finalResult);
    }

    // 驳回（返回步骤4）
    reject() {
        this.events.emit(EVENTS.FINAL_REJECTED);
        // StepManager 监听此事件，跳转到步骤4
    }
}
```

---

## 4. 后端 API 设计

### 4.1 新增 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/corrections/{job_id}` | POST | 保存用户修正记录 |
| `/api/corrections/{job_id}` | GET | 获取修正记录 |
| `/api/checkpoints/{job_id}` | POST | 保存检查点结果 |
| `/api/checkpoints/{job_id}` | GET | 获取检查点结果 |
| `/api/final/{job_id}` | POST | 保存最终确认结果 |
| `/api/final/{job_id}` | GET | 获取最终结果 |
| `/api/templates` | GET | 获取关键词模板列表 |
| `/api/templates` | POST | 创建新模板 |
| `/api/templates/{id}` | PUT | 更新模板 |
| `/api/templates/{id}` | DELETE | 删除模板 |
| `/api/checkpoint-config` | GET | 获取检查点配置 |
| `/api/checkpoint-config` | POST | 保存检查点配置 |

### 4.2 数据存储格式

```python
# temp/{job_id}_corrections.json
{
    "job_id": "uuid",
    "corrections": [
        {
            "block_index": 0,
            "original_text": "原始文本",
            "corrected_text": "修正后文本",
            "timestamp": "2026-01-26T10:30:00Z"
        }
    ]
}

# temp/{job_id}_checkpoints.json
{
    "job_id": "uuid",
    "results": [
        {
            "question": "发票金额是多少？",
            "answer": "¥1,234.56",
            "confidence": 0.95
        }
    ],
    "executed_at": "2026-01-26T10:35:00Z"
}

# temp/{job_id}_final_result.json
{
    "job_id": "uuid",
    "extracted_data": { ... },
    "checkpoint_results": [ ... ],
    "corrections": [ ... ],
    "status": "confirmed",  // confirmed | rejected
    "confirmed_at": "2026-01-26T10:40:00Z"
}
```

---

## 5. 文件结构重构

### 5.1 目标结构

```
frontend/src/
├── index.html              # 精简版（~200行）
├── index.js                # App 入口（~150行）
├── styles/
│   ├── base.css            # 基础样式、变量
│   ├── layout.css          # 布局样式
│   ├── steps.css           # 步骤进度条样式
│   ├── panels.css          # 面板样式
│   └── components.css      # 组件样式
├── services/
│   ├── APIClient.js        # API 客户端（保留）
│   ├── StepManager.js      # 步骤管理器（新增）
│   ├── StateManager.js     # 状态管理器（新增）
│   ├── EventBus.js         # 事件总线（新增）
│   ├── DocumentProcessor.js # 文档处理（保留）
│   ├── StatusPoller.js     # 状态轮询（保留）
│   └── UIManager.js        # UI 管理（保留）
├── components/
│   ├── steps/
│   │   ├── Step1ModelLoad.js
│   │   ├── Step2FileUpload.js
│   │   ├── Step3Recognition.js
│   │   ├── Step4PreEntry.js
│   │   ├── Step5DataExtract.js
│   │   └── Step6Confirmation.js
│   ├── panels/
│   │   ├── HistoryPanel.js
│   │   ├── TemplatePanel.js
│   │   └── CheckpointPanel.js
│   ├── ChatOCRIntegration.js  # 保留
│   ├── DocumentQA.js          # 保留
│   └── SmartExtract.js        # 保留
└── __tests__/
    └── ...
```

### 5.2 CSS 抽取规划

| 原位置 | 目标文件 | 内容 |
|--------|----------|------|
| index.html `:root` | base.css | CSS 变量、重置样式 |
| index.html `.container` | layout.css | 主布局、网格 |
| index.html `.step-*` | steps.css | 步骤进度条 |
| index.html `.panel-*` | panels.css | 侧边面板 |
| index.html `.block-*` | components.css | Block 组件 |

---

## 6. 正确性属性

### 6.1 步骤流转属性

```
P1: 步骤必须按顺序完成
    ∀ step ∈ [2,6]: canEnter(step) ⟹ isCompleted(step-1)

P2: 步骤4修正必须传递到步骤5
    corrections.saved ⟹ step5.input.contains(corrections)

P3: 步骤6驳回必须返回步骤4
    step6.rejected ⟹ currentStep = 4
```

### 6.2 数据完整性属性

```
P4: 修正记录必须包含完整信息
    ∀ correction: correction.blockIndex ≠ null 
                  ∧ correction.originalText ≠ null
                  ∧ correction.correctedText ≠ null
                  ∧ correction.timestamp ≠ null

P5: 最终结果必须包含所有必要数据
    finalResult.confirmed ⟹ 
        finalResult.extractedData ≠ null
        ∧ finalResult.checkpointResults ≠ null
```

### 6.3 UI 状态属性

```
P6: 当前步骤必须高亮显示
    ∀ step: step = currentStep ⟹ step.isHighlighted

P7: 未完成步骤不可点击
    ∀ step: ¬isCompleted(step-1) ⟹ ¬step.isClickable
```

---

## 7. 测试策略

### 7.1 单元测试

| 组件 | 测试重点 |
|------|----------|
| StepManager | 步骤切换逻辑、状态更新 |
| StateManager | 状态存取、持久化 |
| EventBus | 事件发布订阅 |
| Step4PreEntry | 修正保存、文本合并 |
| Step5DataExtract | 模板提取、检查点执行 |
| Step6Confirmation | 确认/驳回逻辑 |

### 7.2 集成测试

| 场景 | 测试内容 |
|------|----------|
| 完整工作流 | 步骤1-6顺序执行 |
| 修正传递 | 步骤4修正在步骤5可见 |
| 驳回流程 | 步骤6驳回返回步骤4 |
| 数据持久化 | 刷新页面后数据恢复 |

---

## 8. 迁移策略

### 8.1 阶段一：基础重构（不影响功能）

1. 抽取 CSS 到独立文件
2. 创建 StepManager、StateManager、EventBus
3. 保持现有功能不变

### 8.2 阶段二：步骤组件化

1. 创建 Step1-3 组件（封装现有逻辑）
2. 创建 Step4 增强组件
3. 创建 Step5 增强组件
4. 创建 Step6 新组件

### 8.3 阶段三：面板组件化

1. 创建 HistoryPanel
2. 创建 TemplatePanel
3. 创建 CheckpointPanel

### 8.4 阶段四：后端 API

1. 实现修正记录 API
2. 实现检查点 API
3. 实现最终结果 API
4. 实现模板管理 API
