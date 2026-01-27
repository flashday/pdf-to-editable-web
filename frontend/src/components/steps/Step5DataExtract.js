/**
 * Step5DataExtract - 步骤5：数据提取与自检组件
 * 按关键词模板提取数据，执行检查点验证
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

// 预设模板（作为后备，优先从后端加载）
const PRESET_TEMPLATES = [
    {
        id: 'invoice',
        name: '发票',
        fields: ['发票号码', '发票代码', '开票日期', '购买方名称', '销售方名称', '金额', '税额', '价税合计'],
        checkpoints: ['发票号码是多少？', '开票日期是什么？', '金额合计是多少？']
    },
    {
        id: 'contract',
        name: '合同',
        fields: ['合同编号', '甲方', '乙方', '签订日期', '合同金额', '有效期'],
        checkpoints: ['合同编号是多少？', '甲方和乙方分别是谁？', '合同金额是多少？']
    },
    {
        id: 'id_card',
        name: '身份证',
        fields: ['姓名', '性别', '民族', '出生日期', '住址', '身份证号码'],
        checkpoints: ['姓名是什么？', '身份证号码是多少？']
    },
    {
        id: 'receipt',
        name: '收据',
        fields: ['收据编号', '日期', '付款人', '收款人', '金额', '事由'],
        checkpoints: ['收据编号是多少？', '金额是多少？']
    },
    {
        id: 'custom',
        name: '自定义',
        fields: [],
        checkpoints: []
    }
];

export class Step5DataExtract {
    constructor(container) {
        this.container = container;
        this.selectedTemplate = null;
        this.documentTypes = [];  // 从后端加载的单据类型
        this.extractedData = null;
        this.checkpointResults = [];
        this.isExtracting = false;
        this.isCheckingPoints = false;
    }

    /**
     * 显示组件
     */
    async show() {
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
        
        // 加载单据类型配置
        await this.loadDocumentTypes();
        
        // 自动选择步骤2选中的单据类型
        this.autoSelectDocumentType();
        
        this.render();
        this.bindEvents();
        
        // 自动执行提取和检查点
        await this.autoExecute();
    }
    
    /**
     * 自动执行提取和检查点
     */
    async autoExecute() {
        console.log('Step5DataExtract: Auto-executing extraction and checkpoints');
        
        // 确保有选中的模板
        if (!this.selectedTemplate) {
            console.log('Step5DataExtract: No template selected, skipping auto-execute');
            return;
        }
        
        // 显示自动执行状态
        const statusEl = document.getElementById('extractStatus');
        if (statusEl) statusEl.textContent = '🤖 自动提取中...';
        
        try {
            // 1. 自动执行提取
            await this.startExtraction();
            
            // 2. 如果有检查点，自动执行检查点
            if (this.selectedTemplate.checkpoints && this.selectedTemplate.checkpoints.length > 0) {
                // 等待一小段时间让UI更新
                await new Promise(resolve => setTimeout(resolve, 500));
                await this.runCheckpoints();
            }
            
            console.log('Step5DataExtract: Auto-execution completed');
        } catch (error) {
            console.error('Step5DataExtract: Auto-execution failed:', error);
            if (statusEl) statusEl.textContent = '❌ 自动提取失败: ' + error.message;
        }
    }
    
    /**
     * 从后端加载单据类型配置
     */
    async loadDocumentTypes() {
        try {
            const response = await fetch('/api/document-types');
            const data = await response.json();
            if (data.success && data.data) {
                this.documentTypes = data.data;
                console.log('Step5: Loaded document types:', this.documentTypes.length);
            }
        } catch (error) {
            console.error('Step5: Failed to load document types:', error);
            // 使用预设模板作为后备
            this.documentTypes = PRESET_TEMPLATES;
        }
    }
    
    /**
     * 自动选择步骤2选中的单据类型
     */
    autoSelectDocumentType() {
        const globalStateManager = window.stateManager || stateManager;
        const selectedTypeId = globalStateManager.get('selectedDocumentTypeId');
        
        console.log('=== Step5: autoSelectDocumentType START ===');
        console.log('Step5: selectedDocumentTypeId from stateManager:', selectedTypeId);
        console.log('Step5: typeof selectedTypeId:', typeof selectedTypeId);
        console.log('Step5: available documentTypes count:', this.documentTypes.length);
        console.log('Step5: available documentTypes IDs:', this.documentTypes.map(t => t.id));
        console.log('Step5: full stateManager state:', JSON.stringify(globalStateManager.getState ? globalStateManager.getState() : {}, null, 2));
        
        if (selectedTypeId) {
            console.log('Step5: Looking for document type with id:', selectedTypeId);
            const docType = this.documentTypes.find(t => {
                console.log('Step5: Comparing', t.id, '===', selectedTypeId, ':', t.id === selectedTypeId);
                return t.id === selectedTypeId;
            });
            if (docType) {
                this.selectedTemplate = docType;
                console.log('Step5: ✅ Auto-selected document type:', docType.name, 'id:', docType.id);
            } else {
                console.log('Step5: ❌ Document type not found in list:', selectedTypeId);
                console.log('Step5: Available IDs:', this.documentTypes.map(t => t.id).join(', '));
            }
        } else {
            console.log('Step5: ⚠️ No selectedDocumentTypeId in stateManager');
        }
        
        // 如果没有选中，默认选第一个
        if (!this.selectedTemplate && this.documentTypes.length > 0) {
            this.selectedTemplate = this.documentTypes[0];
            console.log('Step5: ⚠️ Defaulting to first template:', this.selectedTemplate.name);
        }
        
        console.log('=== Step5: autoSelectDocumentType END, selected:', this.selectedTemplate ? this.selectedTemplate.name : 'none');
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
        
        // 获取当前文档文本用于预览
        const globalStateManager = window.stateManager || stateManager;
        let previewText = globalStateManager.get('finalText') || globalStateManager.getFinalText() || '';
        if (!previewText && window.app && window.app.ocrRegions) {
            previewText = window.app.ocrRegions.map(r => r.text || '').filter(t => t).join('\n');
        }
        const textPreview = previewText ? previewText.substring(0, 500) + (previewText.length > 500 ? '...' : '') : '(无文本内容)';
        
        // 使用从后端加载的单据类型，如果没有则使用预设模板
        const templates = this.documentTypes.length > 0 ? this.documentTypes : PRESET_TEMPLATES;
        
        step5Container.innerHTML = `
            <div class="step5-content">
                <!-- 文档内容预览区 - 暂时隐藏 -->
                <!--
                <div class="document-preview-section" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">📄 识别文本预览 <span style="font-size: 12px; color: #666; font-weight: normal;">(共 ${previewText.length} 字符)</span></h4>
                    <div id="documentTextPreview" style="background: #f8f9fa; border: 1px solid #ddd; border-radius: 6px; padding: 12px; max-height: 150px; overflow: auto; font-size: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-all;">
                        ${textPreview.replace(/</g, '&lt;').replace(/>/g, '&gt;')}
                    </div>
                </div>
                -->
                
                <!-- 模板选择区 -->
                <div class="template-section" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">📋 选择提取模板</h4>
                    <div class="template-list" id="templateList" style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${templates.map(t => `
                            <button class="template-btn" data-template-id="${t.id}" 
                                style="padding: 8px 16px; border: 1px solid #ddd; border-radius: 6px; background: ${this.selectedTemplate && this.selectedTemplate.id === t.id ? '#3498db' : 'white'}; color: ${this.selectedTemplate && this.selectedTemplate.id === t.id ? 'white' : '#333'}; cursor: pointer; transition: all 0.2s;">
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
                    <p style="color: #666; font-size: 13px; margin-bottom: 10px;">输入要验证的问题，系统将基于文档内容回答</p>
                    <textarea id="checkpointQuestionsInput" placeholder="每行一个检查点问题，例如：&#10;文档中的金额是多少？&#10;开票日期是什么？&#10;购买方名称是什么？"
                        style="width: 100%; height: 100px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; resize: vertical; margin-bottom: 10px;">${this.selectedTemplate && this.selectedTemplate.checkpoints ? this.selectedTemplate.checkpoints.join('\n') : ''}</textarea>
                    <button id="runCheckpointsBtn" style="background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">
                        ▶ 执行检查点
                    </button>
                    <span id="checkpointStatus" style="margin-left: 10px; color: #666;"></span>
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
        // 优先从后端加载的单据类型中查找，否则从预设模板中查找
        const templates = this.documentTypes.length > 0 ? this.documentTypes : PRESET_TEMPLATES;
        this.selectedTemplate = templates.find(t => t.id === templateId);
        
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
        
        // 自动填充检查点问题
        const checkpointInput = document.getElementById('checkpointQuestionsInput');
        if (checkpointInput && this.selectedTemplate && this.selectedTemplate.checkpoints) {
            checkpointInput.value = this.selectedTemplate.checkpoints.join('\n');
        }
        
        // 使用全局 stateManager 保存数据
        const globalStateManager = window.stateManager || stateManager;
        globalStateManager.set('selectedTemplate', this.selectedTemplate);
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
            let finalText = '';
            
            // 优先从 window.stateManager 获取（确保使用全局单例）
            const globalStateManager = window.stateManager || stateManager;
            
            finalText = globalStateManager.get('finalText');
            if (!finalText) {
                finalText = globalStateManager.getFinalText();
            }
            
            console.log('Step5DataExtract: finalText from stateManager, length:', finalText ? finalText.length : 0);
            
            // 如果 stateManager 中没有数据，尝试从 window.app 获取
            if (!finalText || finalText.trim() === '') {
                console.log('Step5DataExtract: trying to get data from window.app');
                if (window.app && window.app.ocrRegions && window.app.ocrRegions.length > 0) {
                    const texts = window.app.ocrRegions.map(region => region.text || '').filter(t => t);
                    finalText = texts.join('\n\n');
                    console.log('Step5DataExtract: extracted from window.app.ocrRegions, length:', finalText.length);
                }
            }
            
            // 如果还是没有，尝试从 window.app.ocrData 获取
            if (!finalText || finalText.trim() === '') {
                console.log('Step5DataExtract: trying to get data from window.app.ocrData');
                if (window.app && window.app.ocrData && window.app.ocrData.blocks) {
                    const texts = window.app.ocrData.blocks.map(block => {
                        if (block.data && block.data.text) return block.data.text;
                        if (block.data && block.data.items) return block.data.items.join(', ');
                        return '';
                    }).filter(t => t);
                    finalText = texts.join('\n\n');
                    console.log('Step5DataExtract: extracted from window.app.ocrData, length:', finalText.length);
                }
            }
            
            console.log('Step5DataExtract: finalText preview:', finalText ? finalText.substring(0, 200) : '(empty)');
            
            if (!finalText || finalText.trim() === '') {
                throw new Error('text 不能为空，请确保已完成 OCR 识别');
            }
            
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
            
            // 调用 LLM 提取 - 使用正确的 extract-info API（支持 RAG）
            console.log('Step5DataExtract: Calling /api/extract-info with text length:', finalText.length);
            console.log('Step5DataExtract: Text content (first 500 chars):', finalText.substring(0, 500));
            
            // 获取 jobId（使用已声明的 globalStateManager）
            const jobId = globalStateManager.get('jobId') || (window.app ? window.app.currentJobId : null);
            
            let response;
            if (jobId) {
                // 如果有 jobId，使用 extract-info API（支持 RAG 检索）
                console.log('Step5DataExtract: Using /api/extract-info with jobId:', jobId);
                response = await fetch('/api/extract-info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        job_id: jobId,
                        fields: fields,
                        template: this.selectedTemplate.id !== 'custom' ? this.selectedTemplate.id : null
                    })
                });
            } else {
                // 如果没有 jobId，使用简单的 llm/extract API
                console.log('Step5DataExtract: Using /api/llm/extract (no jobId)');
                response = await fetch('/api/llm/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: finalText,
                        fields: fields,
                        template: this.selectedTemplate.name
                    })
                });
            }
            
            const result = await response.json();
            console.log('Step5DataExtract: Extract result:', result);
            console.log('Step5DataExtract: Extract result.data:', result.data);
            console.log('Step5DataExtract: Extract result.success:', result.success);
            
            if (result.success) {
                // result.data 包含提取的字段数据
                // /api/extract-info 返回 { fields: {...}, confidence: 0.x, ... }
                // /api/llm/extract 返回直接的字段对象
                this.extractedData = result.data.fields || result.data;
                console.log('Step5DataExtract: Extracted data:', this.extractedData);
                // 使用全局 stateManager 保存数据，确保 Step6 能读取到
                globalStateManager.set('extractedData', this.extractedData);
                globalStateManager.set('selectedTemplate', this.selectedTemplate);
                console.log('Step5DataExtract: Saved extractedData to globalStateManager');
                this.renderExtractedData();
                
                if (statusEl) statusEl.textContent = '✓ 提取完成';
                
                // 显示检查点按钮
                const runCheckpointsBtn = document.getElementById('runCheckpointsBtn');
                if (runCheckpointsBtn) runCheckpointsBtn.style.display = 'inline-block';
                
                // 显示确认按钮
                const confirmBtn = document.getElementById('step5ConfirmBtn');
                if (confirmBtn) confirmBtn.style.display = 'inline-block';
                
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
                // 判断是否找到值
                const isEmpty = value === null || value === undefined || value === '' || value === '-' || value === '未找到' || value === 'null';
                const displayValue = isEmpty ? '<span style="color: #999; font-style: italic;">未找到</span>' : value;
                const rowStyle = isEmpty ? 'background: #fff8e1;' : '';
                
                html += `<tr style="${rowStyle}"><td style="padding: 8px; border: 1px solid #ddd; font-weight: 500;">${key}</td><td style="padding: 8px; border: 1px solid #ddd;">${displayValue}</td></tr>`;
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
        
        // 从输入框获取检查点问题
        const questionsInput = document.getElementById('checkpointQuestionsInput');
        const questionsText = questionsInput ? questionsInput.value.trim() : '';
        
        if (!questionsText) {
            alert('请输入至少一个检查点问题');
            return;
        }
        
        // 解析问题列表
        const questions = questionsText.split('\n').map(q => q.trim()).filter(q => q);
        if (questions.length === 0) {
            alert('请输入至少一个检查点问题');
            return;
        }
        
        this.isCheckingPoints = true;
        const runBtn = document.getElementById('runCheckpointsBtn');
        const statusEl = document.getElementById('checkpointStatus');
        
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.textContent = '执行中...';
        }
        if (statusEl) statusEl.textContent = '';
        
        eventBus.emit(EVENTS.CHECKPOINT_STARTED);
        
        try {
            // 获取文本内容
            const globalStateManager = window.stateManager || stateManager;
            let finalText = globalStateManager.get('finalText') || globalStateManager.getFinalText();
            
            // 如果没有，从 window.app 获取
            if (!finalText && window.app && window.app.ocrRegions) {
                finalText = window.app.ocrRegions.map(r => r.text || '').filter(t => t).join('\n\n');
            }
            
            this.checkpointResults = [];
            
            // 获取 jobId 用于 RAG 检索
            const jobId = globalStateManager.get('jobId') || (window.app ? window.app.currentJobId : null);
            
            for (let i = 0; i < questions.length; i++) {
                const question = questions[i];
                if (statusEl) statusEl.textContent = `执行中 (${i + 1}/${questions.length})...`;
                
                let response;
                if (jobId) {
                    // 如果有 jobId，使用 document-qa API（支持 RAG 检索）
                    console.log('Checkpoint: Using /api/document-qa with jobId:', jobId);
                    response = await fetch('/api/document-qa', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            job_id: jobId,
                            question: question
                        })
                    });
                } else {
                    // 如果没有 jobId，回退到简单的 llm/qa API
                    console.log('Checkpoint: Using /api/llm/qa (no jobId)');
                    response = await fetch('/api/llm/qa', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            question: question,
                            context: finalText
                        })
                    });
                }
                
                const result = await response.json();
                
                this.checkpointResults.push({
                    question: question,
                    answer: result.success ? result.data.answer : '无法回答',
                    confidence: result.success ? result.data.confidence : 0
                });
            }
            
            globalStateManager.set('checkpointResults', this.checkpointResults);
            this.renderCheckpointResults();
            
            // 保存到后端
            await this.saveCheckpointsToBackend();
            
            if (statusEl) statusEl.textContent = '✓ 检查点执行完成';
            
            // 显示确认按钮
            const confirmBtn = document.getElementById('step5ConfirmBtn');
            if (confirmBtn) confirmBtn.style.display = 'inline-block';
            
            eventBus.emit(EVENTS.CHECKPOINT_COMPLETED, this.checkpointResults);
        } catch (error) {
            console.error('Checkpoint error:', error);
            if (statusEl) statusEl.textContent = '❌ ' + error.message;
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
        const globalStateManager = window.stateManager || stateManager;
        const jobId = globalStateManager.get('jobId');
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
