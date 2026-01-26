/**
 * Step5DataExtract - 步骤5：数据提取与自检组件
 * 按关键词模板提取数据，执行检查点验证
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

// 预设模板
const PRESET_TEMPLATES = [
    {
        id: 'invoice',
        name: '发票',
        fields: ['发票号码', '发票代码', '开票日期', '购买方名称', '销售方名称', '金额', '税额', '价税合计']
    },
    {
        id: 'contract',
        name: '合同',
        fields: ['合同编号', '甲方', '乙方', '签订日期', '合同金额', '有效期']
    },
    {
        id: 'id_card',
        name: '身份证',
        fields: ['姓名', '性别', '民族', '出生日期', '住址', '身份证号码']
    },
    {
        id: 'receipt',
        name: '收据',
        fields: ['收据编号', '日期', '付款人', '收款人', '金额', '事由']
    },
    {
        id: 'custom',
        name: '自定义',
        fields: []
    }
];

export class Step5DataExtract {
    constructor(container) {
        this.container = container;
        this.selectedTemplate = null;
        this.extractedData = null;
        this.checkpointResults = [];
        this.isExtracting = false;
        this.isCheckingPoints = false;
    }

    /**
     * 显示组件
     */
    show() {
        console.log('Step5DataExtract: Showing Step 5 UI');
        
        // 隐藏步骤4相关界面
        const blockList = document.getElementById('blockList');
        const confirmArea = document.getElementById('preEntryConfirmArea');
        const imagePanel = document.querySelector('.image-panel');
        const downloadButtons = document.getElementById('downloadButtons');
        const confidenceReport = document.getElementById('confidenceReport');
        const editModeToggle = document.getElementById('editModeToggle');
        const markdownView = document.getElementById('markdownView');
        
        if (blockList) blockList.style.display = 'none';
        if (confirmArea) confirmArea.style.display = 'none';
        if (imagePanel) imagePanel.style.display = 'none';
        if (downloadButtons) downloadButtons.style.display = 'none';
        if (confidenceReport) confidenceReport.style.display = 'none';
        if (editModeToggle) editModeToggle.style.display = 'none';
        if (markdownView) markdownView.style.display = 'none';
        
        // 隐藏步骤6容器（如果存在）
        const step6Container = document.getElementById('step6Container');
        if (step6Container) step6Container.style.display = 'none';
        
        this.render();
        this.bindEvents();
    }

    /**
     * 隐藏组件
     */
    hide() {
        const step5Container = document.getElementById('step5Container');
        if (step5Container) {
            step5Container.style.display = 'none';
        }
    }

    /**
     * 渲染界面
     */
    render() {
        const editorContainer = document.querySelector('.editor-container');
        if (!editorContainer) return;
        
        // 创建步骤5专用容器
        let step5Container = document.getElementById('step5Container');
        if (!step5Container) {
            step5Container = document.createElement('div');
            step5Container.id = 'step5Container';
            step5Container.style.cssText = 'display: none; padding: 15px;';
            editorContainer.appendChild(step5Container);
        }
        
        step5Container.innerHTML = `
            <div class="step5-content">
                <!-- 模板选择区 -->
                <div class="template-section" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">📋 选择提取模板</h4>
                    <div class="template-list" id="templateList" style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${PRESET_TEMPLATES.map(t => `
                            <button class="template-btn" data-template-id="${t.id}" 
                                style="padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: white; cursor: pointer; transition: all 0.2s;">
                                ${t.name}
                            </button>
                        `).join('')}
                    </div>
                </div>
                
                <!-- 自定义字段区（仅自定义模板显示） -->
                <div class="custom-fields-section" id="customFieldsSection" style="display: none; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">✏️ 自定义提取字段</h4>
                    <textarea id="customFieldsInput" placeholder="每行一个字段名，例如：&#10;发票号码&#10;金额&#10;日期"
                        style="width: 100%; height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; resize: vertical;"></textarea>
                </div>
                
                <!-- 提取按钮 -->
                <div style="margin-bottom: 20px;">
                    <button id="extractBtn" style="background: #3498db; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                        🔍 开始提取
                    </button>
                    <span id="extractStatus" style="margin-left: 10px; color: #666;"></span>
                </div>
                
                <!-- 提取结果区 -->
                <div class="extract-result-section" id="extractResultSection" style="display: none; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">📊 提取结果</h4>
                    <div id="extractedDataDisplay" style="background: #f8f9fa; border: 1px solid #ddd; border-radius: 6px; padding: 15px; max-height: 300px; overflow: auto;">
                    </div>
                </div>
                
                <!-- 检查点区 -->
                <div class="checkpoint-section" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">✅ 检查点验证</h4>
                    <div id="checkpointList" style="margin-bottom: 10px;">
                        <div style="color: #666; font-size: 14px;">请先完成数据提取</div>
                    </div>
                    <button id="runCheckpointsBtn" style="background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; display: none;">
                        ▶ 执行检查点
                    </button>
                </div>
                
                <!-- 检查点结果区 -->
                <div class="checkpoint-result-section" id="checkpointResultSection" style="display: none; margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">📝 检查点结果</h4>
                    <div id="checkpointResultsDisplay" style="background: #f0f9ff; border: 1px solid #b8daff; border-radius: 6px; padding: 15px;">
                    </div>
                </div>
                
                <!-- 确认按钮 -->
                <div style="text-align: center; padding-top: 15px; border-top: 1px solid #ddd;">
                    <button id="step5ConfirmBtn" style="background: #28a745; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; display: none;">
                        ✓ 确认并进入下一步
                    </button>
                </div>
            </div>
        `;
        
        step5Container.style.display = 'block';
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 模板选择
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const templateId = e.target.dataset.templateId;
                this.selectTemplate(templateId);
            });
        });
        
        // 提取按钮
        const extractBtn = document.getElementById('extractBtn');
        if (extractBtn) {
            extractBtn.addEventListener('click', () => this.startExtraction());
        }
        
        // 执行检查点按钮
        const runCheckpointsBtn = document.getElementById('runCheckpointsBtn');
        if (runCheckpointsBtn) {
            runCheckpointsBtn.addEventListener('click', () => this.runCheckpoints());
        }
        
        // 确认按钮
        const confirmBtn = document.getElementById('step5ConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmAndProceed());
        }
    }

    /**
     * 选择模板
     */
    selectTemplate(templateId) {
        this.selectedTemplate = PRESET_TEMPLATES.find(t => t.id === templateId);
        
        // 更新按钮状态
        document.querySelectorAll('.template-btn').forEach(btn => {
            if (btn.dataset.templateId === templateId) {
                btn.style.background = '#3498db';
                btn.style.color = 'white';
                btn.style.borderColor = '#3498db';
            } else {
                btn.style.background = 'white';
                btn.style.color = '#333';
                btn.style.borderColor = '#ddd';
            }
        });
        
        // 显示/隐藏自定义字段区
        const customSection = document.getElementById('customFieldsSection');
        if (customSection) {
            customSection.style.display = templateId === 'custom' ? 'block' : 'none';
        }
        
        stateManager.set('selectedTemplate', this.selectedTemplate);
        eventBus.emit(EVENTS.TEMPLATE_SELECTED, this.selectedTemplate);
    }

    /**
     * 开始提取
     */
    async startExtraction() {
        if (this.isExtracting) return;
        if (!this.selectedTemplate) {
            alert('请先选择提取模板');
            return;
        }
        
        this.isExtracting = true;
        const statusEl = document.getElementById('extractStatus');
        const extractBtn = document.getElementById('extractBtn');
        
        if (statusEl) statusEl.textContent = '提取中...';
        if (extractBtn) extractBtn.disabled = true;
        
        eventBus.emit(EVENTS.EXTRACTION_STARTED);
        
        try {
            const finalText = stateManager.get('finalText') || stateManager.getFinalText();
            let fields = this.selectedTemplate.fields;
            
            // 自定义模板从输入框获取字段
            if (this.selectedTemplate.id === 'custom') {
                const customInput = document.getElementById('customFieldsInput');
                if (customInput) {
                    fields = customInput.value.split('\n').map(f => f.trim()).filter(f => f);
                }
            }
            
            if (fields.length === 0) {
                throw new Error('请输入至少一个提取字段');
            }
            
            // 调用 LLM 提取
            const response = await fetch('/api/llm/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: finalText,
                    fields: fields,
                    template: this.selectedTemplate.name
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.extractedData = result.data;
                stateManager.set('extractedData', this.extractedData);
                this.renderExtractedData();
                
                if (statusEl) statusEl.textContent = '✓ 提取完成';
                
                // 显示检查点按钮
                const runCheckpointsBtn = document.getElementById('runCheckpointsBtn');
                if (runCheckpointsBtn) runCheckpointsBtn.style.display = 'inline-block';
                
                eventBus.emit(EVENTS.EXTRACTION_COMPLETED, this.extractedData);
            } else {
                throw new Error(result.error || '提取失败');
            }
        } catch (error) {
            console.error('Extraction error:', error);
            if (statusEl) statusEl.textContent = '❌ ' + error.message;
        } finally {
            this.isExtracting = false;
            if (extractBtn) extractBtn.disabled = false;
        }
    }

    /**
     * 渲染提取结果
     */
    renderExtractedData() {
        const section = document.getElementById('extractResultSection');
        const display = document.getElementById('extractedDataDisplay');
        
        if (section) section.style.display = 'block';
        
        if (display && this.extractedData) {
            let html = '<table style="width: 100%; border-collapse: collapse;">';
            html += '<tr style="background: #e9ecef;"><th style="padding: 8px; border: 1px solid #ddd; text-align: left;">字段</th><th style="padding: 8px; border: 1px solid #ddd; text-align: left;">值</th></tr>';
            
            Object.entries(this.extractedData).forEach(([key, value]) => {
                html += `<tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: 500;">${key}</td><td style="padding: 8px; border: 1px solid #ddd;">${value || '-'}</td></tr>`;
            });
            
            html += '</table>';
            display.innerHTML = html;
        }
    }

    /**
     * 执行检查点验证
     */
    async runCheckpoints() {
        if (this.isCheckingPoints) return;
        if (!this.extractedData) {
            alert('请先完成数据提取');
            return;
        }
        
        this.isCheckingPoints = true;
        const runBtn = document.getElementById('runCheckpointsBtn');
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.textContent = '执行中...';
        }
        
        eventBus.emit(EVENTS.CHECKPOINT_STARTED);
        
        try {
            // 获取检查点配置
            const checkpoints = await this.loadCheckpoints();
            const finalText = stateManager.get('finalText') || stateManager.getFinalText();
            
            this.checkpointResults = [];
            
            for (const checkpoint of checkpoints) {
                const response = await fetch('/api/llm/qa', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: checkpoint.question,
                        context: finalText,
                        job_id: stateManager.get('jobId')
                    })
                });
                
                const result = await response.json();
                
                this.checkpointResults.push({
                    question: checkpoint.question,
                    answer: result.success ? result.data.answer : '无法回答',
                    confidence: result.success ? result.data.confidence : 0
                });
            }
            
            stateManager.set('checkpointResults', this.checkpointResults);
            this.renderCheckpointResults();
            
            // 保存到后端
            await this.saveCheckpointsToBackend();
            
            // 显示确认按钮
            const confirmBtn = document.getElementById('step5ConfirmBtn');
            if (confirmBtn) confirmBtn.style.display = 'inline-block';
            
            eventBus.emit(EVENTS.CHECKPOINT_COMPLETED, this.checkpointResults);
        } catch (error) {
            console.error('Checkpoint error:', error);
            alert('检查点执行失败: ' + error.message);
        } finally {
            this.isCheckingPoints = false;
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.textContent = '▶ 执行检查点';
            }
        }
    }

    /**
     * 加载检查点配置
     */
    async loadCheckpoints() {
        try {
            const response = await fetch('/api/checkpoint-config');
            const data = await response.json();
            if (data.success && data.checkpoints) {
                return data.checkpoints;
            }
        } catch (error) {
            console.log('Using default checkpoints');
        }
        
        // 默认检查点
        return [
            { question: '文档中的主要金额是多少？' },
            { question: '文档的日期是什么？' },
            { question: '文档涉及的主要当事方有哪些？' }
        ];
    }

    /**
     * 渲染检查点结果
     */
    renderCheckpointResults() {
        const section = document.getElementById('checkpointResultSection');
        const display = document.getElementById('checkpointResultsDisplay');
        
        if (section) section.style.display = 'block';
        
        if (display && this.checkpointResults.length > 0) {
            let html = '';
            this.checkpointResults.forEach((result, idx) => {
                const confidenceColor = result.confidence >= 0.8 ? '#28a745' : result.confidence >= 0.5 ? '#ffc107' : '#dc3545';
                html += `
                    <div style="margin-bottom: 12px; padding: 10px; background: white; border-radius: 6px; border-left: 4px solid ${confidenceColor};">
                        <div style="font-weight: 600; color: #333; margin-bottom: 5px;">Q${idx + 1}: ${result.question}</div>
                        <div style="color: #666;">A: ${result.answer}</div>
                        <div style="font-size: 12px; color: ${confidenceColor}; margin-top: 5px;">置信度: ${(result.confidence * 100).toFixed(0)}%</div>
                    </div>
                `;
            });
            display.innerHTML = html;
        }
    }

    /**
     * 保存检查点结果到后端
     */
    async saveCheckpointsToBackend() {
        const jobId = stateManager.get('jobId');
        if (!jobId) return;
        
        try {
            await fetch(`/api/checkpoints/${jobId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    results: this.checkpointResults,
                    executed_at: new Date().toISOString()
                })
            });
            console.log('Checkpoints saved to backend');
        } catch (error) {
            console.error('Failed to save checkpoints:', error);
        }
    }

    /**
     * 确认并进入下一步
     */
    confirmAndProceed() {
        // 隐藏步骤5界面
        const step5Container = document.getElementById('step5Container');
        if (step5Container) step5Container.style.display = 'none';
        
        eventBus.emit(EVENTS.STEP_COMPLETED, { step: 5 });
        
        // 切换到步骤6界面
        this.switchToStep6();
    }
    
    /**
     * 切换到步骤6界面
     */
    switchToStep6() {
        // 显示步骤6界面
        if (window.step6Component) {
            window.step6Component.show();
        } else {
            // 动态加载 Step6
            import('./Step6Confirmation.js').then(module => {
                window.step6Component = new module.Step6Confirmation(document.body);
                window.step6Component.show();
            });
        }
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.Step5DataExtract = Step5DataExtract;
}
