/**
 * UIManager - UI 辅助管理器 (V3 重构版)
 * 
 * 职责：
 * - 模型状态检查和显示
 * - 进度条显示
 * - 状态消息显示
 * - 编辑器显示/隐藏
 * 
 * 注意：上传事件处理已移至 Step2FileUpload 组件
 */

import { eventBus, EVENTS } from './EventBus.js';

export class UIManager {
    constructor() {
        this.uploadArea = null;
        this.fileInput = null;
        this.statusDiv = null;
        this.editorSection = null;
        this.progressContainer = null;
        this.progressBar = null;
        this.progressText = null;
        this.modelsReady = false;
        this.modelCheckInterval = null;
    }

    /**
     * Initialize UI components
     * 注意：不再绑定上传事件，由 Step2FileUpload 处理
     */
    initialize() {
        // Get DOM elements after DOM is ready
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.statusDiv = document.getElementById('status');
        this.editorSection = document.querySelector('.editor-section');
        
        console.log('UIManager initialize (V3 - no upload events):', {
            uploadArea: !!this.uploadArea,
            fileInput: !!this.fileInput,
            statusDiv: !!this.statusDiv
        });
        
        // 只创建进度指示器，不绑定上传事件
        this.createProgressIndicator();
        
        // 检查模型加载状态
        this.checkModelsStatus();
    }

    /**
     * Check if OCR models are loaded
     */
    async checkModelsStatus() {
        this.disableUpload('正在加载 OCR 模型，请稍候...');
        
        const checkStatus = async () => {
            try {
                const response = await fetch('http://localhost:5000/api/models/status');
                const data = await response.json();
                
                if (data.ready) {
                    this.enableUpload();
                    if (this.modelCheckInterval) {
                        clearInterval(this.modelCheckInterval);
                        this.modelCheckInterval = null;
                    }
                    this.showStatus('OCR 模型已就绪，可以上传文件', 'success');
                    // 发布模型就绪事件
                    eventBus.emit(EVENTS.MODELS_READY, { ready: true });
                } else if (data.loading) {
                    this.disableUpload('OCR 模型加载中，请稍候...');
                } else {
                    this.disableUpload('等待 OCR 模型加载...');
                }
            } catch (error) {
                console.log('Model status check failed:', error);
                this.disableUpload('等待后端服务启动...');
            }
        };
        
        await checkStatus();
        
        if (!this.modelsReady) {
            this.modelCheckInterval = setInterval(checkStatus, 2000);
        }
    }

    /**
     * Disable upload functionality
     * 注意：不修改 innerHTML，只修改样式，避免破坏 Step2FileUpload 绑定的事件
     */
    disableUpload(message) {
        this.modelsReady = false;
        if (this.uploadArea) {
            this.uploadArea.style.opacity = '0.5';
            this.uploadArea.style.pointerEvents = 'none';
            // 更新提示文字（如果存在）
            const hint = this.uploadArea.querySelector('p');
            if (hint) {
                hint.textContent = message;
            }
        }
        // 显示状态消息
        this.showStatus(message, 'info');
    }

    /**
     * Enable upload functionality
     * 注意：不修改 innerHTML，只修改样式，避免破坏 Step2FileUpload 绑定的事件
     */
    enableUpload() {
        this.modelsReady = true;
        if (this.uploadArea) {
            this.uploadArea.style.opacity = '1';
            this.uploadArea.style.pointerEvents = 'auto';
            // 恢复提示文字（如果存在）
            const hint = this.uploadArea.querySelector('p');
            if (hint) {
                hint.textContent = '点击或拖拽文件到此处';
            }
        }
    }

    /**
     * Check if upload is allowed
     */
    isUploadAllowed() {
        return this.modelsReady;
    }

    /**
     * Create progress indicator for file processing
     */
    createProgressIndicator() {
        if (!this.uploadArea || !this.uploadArea.parentNode) {
            console.log('UIManager: uploadArea not ready for progress indicator');
            return;
        }
        
        const progressContainer = document.createElement('div');
        progressContainer.id = 'progressContainer';
        progressContainer.style.cssText = `
            margin-top: 20px;
            display: none;
        `;

        const progressBar = document.createElement('div');
        progressBar.id = 'progressBar';
        progressBar.style.cssText = `
            width: 0%;
            height: 8px;
            background: linear-gradient(90deg, #3498db, #2980b9);
            border-radius: 4px;
            transition: width 0.3s ease;
        `;

        const progressText = document.createElement('div');
        progressText.id = 'progressText';
        progressText.style.cssText = `
            margin-top: 8px;
            font-size: 14px;
            color: #666;
            text-align: center;
        `;

        progressContainer.appendChild(progressBar);
        progressContainer.appendChild(progressText);

        this.progressContainer = progressContainer;
        this.progressBar = progressBar;
        this.progressText = progressText;

        this.uploadArea.parentNode.insertBefore(progressContainer, this.uploadArea.nextSibling);
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        if (!this.statusDiv) {
            return;
        }

        this.statusDiv.textContent = message;
        this.statusDiv.className = `status ${type}`;
        this.statusDiv.style.display = 'block';

        if (type === 'success') {
            setTimeout(() => {
                this.statusDiv.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Show progress
     */
    showProgress(progress, message) {
        if (!this.progressContainer) {
            return;
        }

        this.progressContainer.style.display = 'block';
        this.progressBar.style.width = `${progress * 100}%`;
        this.progressText.textContent = message || `${Math.round(progress * 100)}%`;
    }

    /**
     * Hide progress
     */
    hideProgress() {
        if (!this.progressContainer) {
            return;
        }

        this.progressContainer.style.display = 'none';
    }

    /**
     * Show editor section
     */
    showEditor() {
        if (this.editorSection) {
            this.editorSection.style.display = 'block';
        }
    }

    /**
     * Hide editor section
     */
    hideEditor() {
        if (this.editorSection) {
            this.editorSection.style.display = 'none';
        }
    }

    /**
     * Reset UI to initial state
     */
    reset() {
        this.hideProgress();
        this.hideEditor();
        
        const preview = document.getElementById('filePreview');
        if (preview) {
            preview.remove();
        }

        if (this.statusDiv) {
            this.statusDiv.style.display = 'none';
        }

        if (this.fileInput) {
            this.fileInput.value = '';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showStatus(message, 'error');
        this.hideProgress();
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showStatus(message, 'success');
        this.hideProgress();
    }

    /**
     * Show processing message
     */
    showProcessing(message) {
        this.showStatus(message, 'processing');
    }
    
    /**
     * Show timeout message
     */
    showTimeout(message) {
        this.showStatus(message || 'Processing timeout.', 'error');
        this.hideProgress();
    }
    
    /**
     * Show retry message
     */
    showRetry(message, attemptNumber, maxAttempts) {
        const retryMessage = `${message} (Retry ${attemptNumber}/${maxAttempts})`;
        this.showStatus(retryMessage, 'warning');
    }
}
