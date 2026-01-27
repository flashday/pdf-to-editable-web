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
        id: 'trip_report',
        name: '出差报告',
        fields: ['报告日期', '申请人', '出差目的地', '出差事由', '出差时间', '费用合计'],
        checkpoints: ['出差人是谁？', '出差目的地是哪里？', '费用合计是多少？']
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
        // 状态跟踪
        this.extractionCompleted = false;
        this.checkpointCompleted = false;
    }
    
    /**
     * 更新提交按钮状态
     */
    updateSubmitButtonState() {
        const submitBtn = document.getElementById('submitToStep6Btn');
        const extractStatusIcon = document.getElementById('extractStatusIcon');
        const extractStatusText = document.getElementById('extractStatusText');
        const checkpointStatusIcon = document.getElementById('checkpointStatusIcon');
        const checkpointStatusText = document.getElementById('checkpointStatusText');
        
        // 更新提取状态显示
        if (extractStatusIcon && extractStatusText) {
            if (this.extractionCompleted) {
                extractStatusIcon.textContent = '✅';
                extractStatusText.textContent = '已完成';
                extractStatusText.style.color = '#28a745';
            } else if (this.isExtracting) {
                extractStatusIcon.textContent = '⏳';
                extractStatusText.textContent = '执行中...';
                extractStatusText.style.color = '#ffc107';
            } else {
                extractStatusIcon.textContent = '⏳';
                extractStatusText.textContent = '待执行';
                extractStatusText.style.color = '#586069';
            }
        }
        
        // 更新检查点状态显示
        if (checkpointStatusIcon && checkpointStatusText) {
            if (this.checkpointCompleted) {
                checkpointStatusIcon.textContent = '✅';
                checkpointStatusText.textContent = '已完成';
                checkpointStatusText.style.color = '#28a745';
            } else if (this.isCheckingPoints) {
                checkpointStatusIcon.textContent = '⏳';
                checkpointStatusText.textContent = '执行中...';
                checkpointStatusText.style.color = '#ffc107';
            } else {
                checkpointStatusIcon.textContent = '⏳';
                checkpointStatusText.textContent = '待执行';
                checkpointStatusText.style.color = '#586069';
            }
        }
        
        // 更新提交按钮状态
        if (submitBtn) {
            const canSubmit = this.extractionCompleted && this.checkpointCompleted;
            submitBtn.disabled = !canSubmit;
            if (canSubmit) {
                submitBtn.style.background = '#28a745';
                submitBtn.style.cursor = 'pointer';
                submitBtn.style.opacity = '1';
            } else {
                submitBtn.style.background = '#6c757d';
                submitBtn.style.cursor = 'not-allowed';
                submitBtn.style.opacity = '0.6';
            }
        }
    }

    /**
     * 显示组件
     */
    async show() {
        console.log('Step5DataExtract: Showing Step 5 UI');
        
        // 隐藏步骤4相关界面
        const blockList = document.getElementById('blockList');
        const confirmArea = document.getElementById('preEntryConfirmArea');
        const step4ConfirmArea = document.getElementById('step4ConfirmArea');
        const imagePanel = document.querySelector('.image-panel');
        const downloadButtons = document.getElementById('downloadButtons');
        const confidenceReport = document.getElementById('confidenceReport');
        const editModeToggle = document.getElementById('editModeToggle');
        const markdownView = document.getElementById('markdownView');
        const confirmStep5Btn = document.getElementById('confirmStep5Btn');
        const editorPanel = document.querySelector('.editor-panel');
        
        if (blockList) blockList.style.display = 'none';
        if (confirmArea) confirmArea.style.display = 'none';
        if (step4ConfirmArea) step4ConfirmArea.style.display = 'none';
        if (imagePanel) imagePanel.style.display = 'none';
        if (downloadButtons) downloadButtons.style.display = 'none';
        if (confidenceReport) confidenceReport.style.display = 'none';
        if (editModeToggle) editModeToggle.style.display = 'none';
        if (markdownView) markdownView.style.display = 'none';
        if (confirmStep5Btn) confirmStep5Btn.style.display = 'none';
        
        // 让编辑器面板占满整个宽度（因为图像面板已隐藏）
        if (editorPanel) {
            editorPanel.style.flex = '1';
            editorPanel.style.width = '100%';
            editorPanel.style.maxWidth = '100%';
        }
        
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
            } else {
                // 没有检查点时，自动标记为完成
                console.log('Step5DataExtract: No checkpoints defined, marking as completed');
                this.checkpointCompleted = true;
                this.updateSubmitButtonState();
                
                // 更新UI显示
                const checkpointStatusIcon = document.getElementById('checkpointStatusIcon');
                const checkpointStatusText = document.getElementById('checkpointStatusText');
                if (checkpointStatusIcon) checkpointStatusIcon.textContent = '⏭️';
                if (checkpointStatusText) {
                    checkpointStatusText.textContent = '无需验证';
                    checkpointStatusText.style.color = '#17a2b8';
                }
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
        
        // 隐藏步骤4的智能按钮
        const smartButtons = document.getElementById('smartButtons');
        if (smartButtons) smartButtons.style.display = 'none';
        
        // 修改标题为"数据提取"
        const editorPanelHeader = document.querySelector('.editor-panel-header > span');
        if (editorPanelHeader) editorPanelHeader.textContent = '📊 数据提取';
        
        // 创建步骤5专用容器
        let step5Container = document.getElementById('step5Container');
        if (!step5Container) {
            step5Container = document.createElement('div');
            step5Container.id = 'step5Container';
            editorContainer.appendChild(step5Container);
        }
        // 设置容器样式 - 使用绝对定位确保占满整个编辑区域
        step5Container.style.cssText = 'display: none; position: absolute; top: 0; left: 0; right: 0; bottom: 0; padding: 15px; box-sizing: border-box; background: white; z-index: 10;';
        
        // 获取当前文档文本用于预览
        const globalStateManager = window.stateManager || stateManager;
        let previewText = globalStateManager.get('finalText') || globalStateManager.getFinalText() || '';
        if (!previewText && window.app && window.app.ocrRegions) {
            previewText = window.app.ocrRegions.map(r => r.text || '').filter(t => t).join('\n');
        }
        
        // 使用从后端加载的单据类型，如果没有则使用预设模板
        const templates = this.documentTypes.length > 0 ? this.documentTypes : PRESET_TEMPLATES;
        
        step5Container.innerHTML = `
            <!-- 顶部操作栏 -->
            <div class="step5-header" style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #e1e4e8;">
                <div id="step5StatusHint" style="flex: 1; font-size: 13px; color: #586069;">
                    <span id="extractStatusIcon">⏳</span> 数据提取: <span id="extractStatusText">待执行</span> &nbsp;|&nbsp;
                    <span id="checkpointStatusIcon">⏳</span> 检查点验证: <span id="checkpointStatusText">待执行</span>
                </div>
                <button id="submitToStep6Btn" disabled style="background: #6c757d; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: not-allowed; font-size: 14px; font-weight: 600; opacity: 0.6;">
                    ➡️ 提交到财务确认
                </button>
            </div>
            
            <div class="step5-content" style="position: absolute; top: 50px; left: 0; right: 0; bottom: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; box-sizing: border-box;">
                <!-- 左侧：提取模板与结果 -->
                <div class="step5-left-panel" style="display: flex; flex-direction: column; background: #fafbfc; border-radius: 8px; padding: 15px; border: 1px solid #e1e4e8; box-sizing: border-box; overflow: hidden;">
                    <h4 style="margin: 0 0 15px 0; color: #24292e; font-size: 15px; border-bottom: 1px solid #e1e4e8; padding-bottom: 10px; flex-shrink: 0;">📋 数据提取</h4>
                    
                    <!-- 模板选择区 -->
                    <div class="template-section" style="margin-bottom: 15px; flex-shrink: 0;">
                        <div style="font-size: 13px; color: #586069; margin-bottom: 8px;">选择提取模板：</div>
                        <div class="template-list" id="templateList" style="display: flex; flex-wrap: wrap; gap: 8px;">
                            ${templates.map(t => `
                                <button class="template-btn" data-template-id="${t.id}" 
                                    style="padding: 6px 14px; border: 1px solid ${this.selectedTemplate && this.selectedTemplate.id === t.id ? '#3498db' : '#d1d5da'}; border-radius: 6px; background: ${this.selectedTemplate && this.selectedTemplate.id === t.id ? '#3498db' : 'white'}; color: ${this.selectedTemplate && this.selectedTemplate.id === t.id ? 'white' : '#24292e'}; cursor: pointer; transition: all 0.2s; font-size: 13px;">
                                    ${t.name}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                    
                    <!-- 自定义字段区（仅自定义模板显示） -->
                    <div class="custom-fields-section" id="customFieldsSection" style="display: none; margin-bottom: 15px; flex-shrink: 0;">
                        <div style="font-size: 13px; color: #586069; margin-bottom: 8px;">自定义提取字段：</div>
                        <textarea id="customFieldsInput" placeholder="每行一个字段名"
                            style="width: 100%; height: 80px; padding: 10px; border: 1px solid #d1d5da; border-radius: 6px; resize: vertical; font-size: 13px; box-sizing: border-box;"></textarea>
                    </div>
                    
                    <!-- 提取按钮 -->
                    <div style="margin-bottom: 15px; flex-shrink: 0;">
                        <button id="extractBtn" style="background: #3498db; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 13px;">
                            🔍 开始提取
                        </button>
                        <span id="extractStatus" style="margin-left: 10px; color: #586069; font-size: 13px;"></span>
                    </div>
                    
                    <!-- 提取结果区 - 占据剩余空间 -->
                    <div class="extract-result-section" id="extractResultSection" style="flex: 1; overflow: auto; min-height: 100px; display: flex; flex-direction: column;">
                        <div style="font-size: 13px; color: #586069; margin-bottom: 8px;">提取结果：</div>
                        <div id="extractedDataDisplay" style="background: white; border: 1px solid #d1d5da; border-radius: 6px; padding: 12px; flex: 1; overflow: auto;">
                            <div style="color: #999; font-style: italic;">点击"开始提取"按钮提取数据...</div>
                        </div>
                    </div>
                    
                    <!-- 确认按钮 - 放在左侧底部 -->
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e1e4e8; flex-shrink: 0;">
                        <button id="step5ConfirmBtn" style="background: #28a745; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600; display: none; width: 100%;">
                            ✓ 确认并进入步骤6（财务确认）
                        </button>
                    </div>
                </div>
                
                <!-- 右侧：检查点验证 -->
                <div class="step5-right-panel" style="display: flex; flex-direction: column; background: #f0f9ff; border-radius: 8px; padding: 15px; border: 1px solid #b8daff; box-sizing: border-box; overflow: hidden;">
                    <h4 style="margin: 0 0 15px 0; color: #24292e; font-size: 15px; border-bottom: 1px solid #b8daff; padding-bottom: 10px; flex-shrink: 0;">✅ 检查点验证</h4>
                    
                    <!-- 检查点输入区 -->
                    <div class="checkpoint-section" style="margin-bottom: 15px; flex-shrink: 0;">
                        <div style="font-size: 13px; color: #586069; margin-bottom: 8px;">输入验证问题（每行一个）：</div>
                        <textarea id="checkpointQuestionsInput" placeholder="例如：&#10;发票号码是多少？&#10;开票日期是什么？&#10;金额合计是多少？"
                            style="width: 100%; height: 120px; padding: 10px; border: 1px solid #b8daff; border-radius: 6px; resize: vertical; font-size: 13px; background: white; box-sizing: border-box;">${this.selectedTemplate && this.selectedTemplate.checkpoints ? this.selectedTemplate.checkpoints.join('\n') : ''}</textarea>
                    </div>
                    
                    <div style="margin-bottom: 15px; flex-shrink: 0;">
                        <button id="runCheckpointsBtn" style="background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px;">
                            ▶ 执行检查点
                        </button>
                        <span id="checkpointStatus" style="margin-left: 10px; color: #586069; font-size: 13px;"></span>
                    </div>
                    
                    <!-- 检查点结果区 - 占据剩余空间 -->
                    <div class="checkpoint-result-section" id="checkpointResultSection" style="flex: 1; overflow: auto; min-height: 100px; display: flex; flex-direction: column;">
                        <div style="font-size: 13px; color: #586069; margin-bottom: 8px;">验证结果：</div>
                        <div id="checkpointResultsDisplay" style="background: white; border: 1px solid #b8daff; border-radius: 6px; padding: 12px; flex: 1; overflow: auto;">
                            <div style="color: #999; font-style: italic;">点击"执行检查点"按钮验证数据...</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 显示容器 - 保持绝对定位样式
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
        
        // 确认按钮（旧的，保留兼容）
        const confirmBtn = document.getElementById('step5ConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirmAndProceed());
        }
        
        // 提交到步骤6按钮（新的）
        const submitBtn = document.getElementById('submitToStep6Btn');
        if (submitBtn) {
            submitBtn.addEventListener('click', () => this.submitToStep6());
        }
    }
    
    /**
     * 提交到步骤6
     */
    submitToStep6() {
        if (!this.extractionCompleted || !this.checkpointCompleted) {
            alert('请先完成数据提取和检查点验证');
            return;
        }
        this.confirmAndProceed();
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
                
                // 标记提取完成
                this.extractionCompleted = true;
                this.updateSubmitButtonState();
                
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
            this.extractionCompleted = false;
            this.updateSubmitButtonState();
        } finally {
            this.isExtracting = false;
            this.updateSubmitButtonState();
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
            
            // 标记检查点完成
            this.checkpointCompleted = true;
            this.updateSubmitButtonState();
            
            // 显示确认按钮
            const confirmBtn = document.getElementById('step5ConfirmBtn');
            if (confirmBtn) confirmBtn.style.display = 'inline-block';
            
            eventBus.emit(EVENTS.CHECKPOINT_COMPLETED, this.checkpointResults);
        } catch (error) {
            console.error('Checkpoint error:', error);
            if (statusEl) statusEl.textContent = '❌ ' + error.message;
            this.checkpointCompleted = false;
            this.updateSubmitButtonState();
            alert('检查点执行失败: ' + error.message);
        } finally {
            this.isCheckingPoints = false;
            this.updateSubmitButtonState();
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
