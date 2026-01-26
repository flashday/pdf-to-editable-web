/**
 * ChatOCRIntegration.js - 智能文档理解功能集成模块
 * 
 * 将智能提取和文档问答功能集成到主界面
 */

class ChatOCRIntegration {
    constructor(options = {}) {
        this.options = {
            apiBaseUrl: options.apiBaseUrl || '',
            ...options
        };
        
        this.currentJobId = null;
        this.llmAvailable = false;
        this.smartExtractPanel = null;
        this.documentQAPanel = null;
        this.activePanel = null;
        
        this.init();
    }
    
    async init() {
        await this.checkLLMStatus();
        this.createToolbarButtons();
        this.createPanelContainers();
        this.bindEvents();
    }
    
    async checkLLMStatus() {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/llm/status`);
            const data = await response.json();
            
            console.log('LLM status response:', data);
            
            if (data.success && data.data) {
                // API 返回 data.data.available 或 data.data.llm_available
                this.llmAvailable = data.data.available || data.data.llm_available || false;
                console.log('LLM available:', this.llmAvailable);
                this.updateButtonStates();
                
                if (!this.llmAvailable) {
                    console.log('LLM service not available, smart features disabled');
                }
            } else {
                console.log('LLM status check failed:', data);
                this.llmAvailable = false;
                this.updateButtonStates();
            }
        } catch (error) {
            console.error('Failed to check LLM status:', error);
            this.llmAvailable = false;
            this.updateButtonStates();
        }
    }
    
    createToolbarButtons() {
        // 查找工具栏位置
        const editorHeader = document.querySelector('.editor-panel-header');
        if (!editorHeader) {
            console.warn('Editor panel header not found, will retry later');
            setTimeout(() => this.createToolbarButtons(), 1000);
            return;
        }
        
        // 检查是否已存在
        if (document.getElementById('smartFeaturesToolbar')) return;
        
        // 创建智能功能工具栏
        const toolbar = document.createElement('div');
        toolbar.id = 'smartFeaturesToolbar';
        toolbar.className = 'smart-features-toolbar';
        toolbar.innerHTML = `
            <button id="smartExtractBtn" class="smart-btn" title="智能信息提取" disabled>
                🔍 智能提取
            </button>
            <button id="documentQABtn" class="smart-btn" title="文档问答" disabled>
                💬 问答
            </button>
            <span id="llmStatusIndicator" class="llm-status-indicator" title="LLM 服务状态">
                <span class="status-dot offline"></span>
            </span>
        `;
        
        // 插入到下载按钮之前
        const downloadButtons = editorHeader.querySelector('.download-buttons');
        if (downloadButtons) {
            editorHeader.insertBefore(toolbar, downloadButtons);
        } else {
            editorHeader.appendChild(toolbar);
        }
        
        this.addToolbarStyles();
        this.updateButtonStates();
    }
    
    addToolbarStyles() {
        if (document.getElementById('chatocr-integration-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'chatocr-integration-styles';
        style.textContent = `
            .smart-features-toolbar {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-right: 10px;
            }
            
            .smart-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 4px 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 500;
                transition: all 0.2s;
                white-space: nowrap;
            }
            
            .smart-btn:hover:not(:disabled) {
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
            }
            
            .smart-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            .smart-btn.active {
                background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
                box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
            }
            
            .llm-status-indicator {
                display: flex;
                align-items: center;
                padding: 0 4px;
            }
            
            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                transition: background 0.3s;
            }
            
            .status-dot.online {
                background: #2ecc71;
                box-shadow: 0 0 6px rgba(46, 204, 113, 0.6);
            }
            
            .status-dot.offline {
                background: #95a5a6;
            }
            
            .status-dot.checking {
                background: #f39c12;
                animation: pulse 1s infinite;
            }
            
            /* 面板容器 */
            .smart-panel-container {
                position: fixed;
                top: 100px;
                right: 20px;
                z-index: 1000;
                display: none;
            }
            
            .smart-panel-container.visible {
                display: block;
            }
            
            /* 面板遮罩 */
            .smart-panel-overlay {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.3);
                z-index: 999;
                display: none;
            }
            
            .smart-panel-overlay.visible {
                display: block;
            }
        `;
        document.head.appendChild(style);
    }
    
    createPanelContainers() {
        // 创建遮罩
        if (!document.getElementById('smartPanelOverlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'smartPanelOverlay';
            overlay.className = 'smart-panel-overlay';
            document.body.appendChild(overlay);
        }
        
        // 创建智能提取面板容器
        if (!document.getElementById('smartExtractContainer')) {
            const extractContainer = document.createElement('div');
            extractContainer.id = 'smartExtractContainer';
            extractContainer.className = 'smart-panel-container';
            document.body.appendChild(extractContainer);
        }
        
        // 创建问答面板容器
        if (!document.getElementById('documentQAContainer')) {
            const qaContainer = document.createElement('div');
            qaContainer.id = 'documentQAContainer';
            qaContainer.className = 'smart-panel-container';
            document.body.appendChild(qaContainer);
        }
    }
    
    bindEvents() {
        // 智能提取按钮
        document.addEventListener('click', (e) => {
            if (e.target.id === 'smartExtractBtn' || e.target.closest('#smartExtractBtn')) {
                this.toggleSmartExtract();
            }
            if (e.target.id === 'documentQABtn' || e.target.closest('#documentQABtn')) {
                this.toggleDocumentQA();
            }
        });
        
        // 遮罩点击关闭
        const overlay = document.getElementById('smartPanelOverlay');
        if (overlay) {
            overlay.addEventListener('click', () => this.closeAllPanels());
        }
        
        // ESC 键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activePanel) {
                this.closeAllPanels();
            }
        });
    }
    
    updateButtonStates() {
        const extractBtn = document.getElementById('smartExtractBtn');
        const qaBtn = document.getElementById('documentQABtn');
        const statusDot = document.querySelector('.status-dot');
        
        const canUse = this.llmAvailable && this.currentJobId;
        
        console.log('updateButtonStates: llmAvailable=', this.llmAvailable, 'currentJobId=', this.currentJobId, 'canUse=', canUse);
        
        if (extractBtn) {
            extractBtn.disabled = !canUse;
            extractBtn.title = canUse ? '智能信息提取' : 
                              (!this.llmAvailable ? 'LLM 服务不可用' : '请先上传文档');
            console.log('extractBtn.disabled =', extractBtn.disabled);
        }
        
        if (qaBtn) {
            qaBtn.disabled = !canUse;
            qaBtn.title = canUse ? '文档问答' : 
                         (!this.llmAvailable ? 'LLM 服务不可用' : '请先上传文档');
            console.log('qaBtn.disabled =', qaBtn.disabled);
        }
        
        if (statusDot) {
            statusDot.className = 'status-dot ' + (this.llmAvailable ? 'online' : 'offline');
            statusDot.parentElement.title = this.llmAvailable ? 'LLM 服务在线' : 'LLM 服务离线';
        }
    }
    
    setJobId(jobId) {
        this.currentJobId = jobId;
        this.updateButtonStates();
        
        // 更新面板的 jobId
        if (this.smartExtractPanel) {
            this.smartExtractPanel.setJobId(jobId);
        }
        if (this.documentQAPanel) {
            this.documentQAPanel.setJobId(jobId);
        }
    }
    
    toggleSmartExtract() {
        if (this.activePanel === 'extract') {
            this.closeAllPanels();
        } else {
            this.openSmartExtract();
        }
    }
    
    toggleDocumentQA() {
        if (this.activePanel === 'qa') {
            this.closeAllPanels();
        } else {
            this.openDocumentQA();
        }
    }
    
    openSmartExtract() {
        this.closeAllPanels();
        
        const container = document.getElementById('smartExtractContainer');
        const overlay = document.getElementById('smartPanelOverlay');
        
        if (!this.smartExtractPanel) {
            // 动态加载组件
            this.smartExtractPanel = new SmartExtractPanel(container, {
                apiBaseUrl: this.options.apiBaseUrl,
                onClose: () => this.closeAllPanels(),
                onExtract: (result) => {
                    console.log('Extraction result:', result);
                }
            });
            this.smartExtractPanel.setJobId(this.currentJobId);
        }
        
        container.classList.add('visible');
        overlay.classList.add('visible');
        this.activePanel = 'extract';
        
        // 更新按钮状态
        document.getElementById('smartExtractBtn')?.classList.add('active');
    }
    
    openDocumentQA() {
        this.closeAllPanels();
        
        const container = document.getElementById('documentQAContainer');
        const overlay = document.getElementById('smartPanelOverlay');
        
        if (!this.documentQAPanel) {
            // 动态加载组件
            this.documentQAPanel = new DocumentQAPanel(container, {
                apiBaseUrl: this.options.apiBaseUrl,
                onClose: () => this.closeAllPanels(),
                onAnswer: (result) => {
                    console.log('QA result:', result);
                }
            });
            this.documentQAPanel.setJobId(this.currentJobId);
        }
        
        container.classList.add('visible');
        overlay.classList.add('visible');
        this.activePanel = 'qa';
        
        // 更新按钮状态
        document.getElementById('documentQABtn')?.classList.add('active');
    }
    
    closeAllPanels() {
        const extractContainer = document.getElementById('smartExtractContainer');
        const qaContainer = document.getElementById('documentQAContainer');
        const overlay = document.getElementById('smartPanelOverlay');
        
        extractContainer?.classList.remove('visible');
        qaContainer?.classList.remove('visible');
        overlay?.classList.remove('visible');
        
        document.getElementById('smartExtractBtn')?.classList.remove('active');
        document.getElementById('documentQABtn')?.classList.remove('active');
        
        this.activePanel = null;
    }
    
    // 刷新 LLM 状态
    async refreshStatus() {
        await this.checkLLMStatus();
    }
}

// 全局实例
let chatOCRIntegration = null;

// 初始化函数
function initChatOCRIntegration(options = {}) {
    if (!chatOCRIntegration) {
        chatOCRIntegration = new ChatOCRIntegration(options);
    }
    return chatOCRIntegration;
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChatOCRIntegration, initChatOCRIntegration };
}
