/**
 * Step2FileUpload - 步骤2：文件上传组件 (V3 重构版)
 * 
 * 职责：
 * - 处理文件拖拽、选择和上传
 * - 检查模型状态
 * - 触发 EventBus 事件
 * 
 * 这是唯一的上传事件处理入口，UIManager 不再处理上传事件
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

// 支持的文件类型
const SUPPORTED_TYPES = {
    'application/pdf': 'PDF',
    'image/jpeg': 'JPG',
    'image/jpg': 'JPG',
    'image/png': 'PNG'
};

// 最大文件大小 (50MB)
const MAX_FILE_SIZE = 50 * 1024 * 1024;

export class Step2FileUpload {
    constructor(container) {
        this.container = container;
        this.uploadArea = null;
        this.fileInput = null;
        this.isUploading = false;
        this.modelsReady = false;
        
        // 绑定方法到实例
        this.handleAreaClick = this.handleAreaClick.bind(this);
        this.handleDragOver = this.handleDragOver.bind(this);
        this.handleDragLeave = this.handleDragLeave.bind(this);
        this.handleDrop = this.handleDrop.bind(this);
        this.handleFileSelect = this.handleFileSelect.bind(this);
    }

    /**
     * 显示组件
     */
    show() {
        this.bindEvents();
        this.listenForModelReady();
    }

    /**
     * 隐藏组件
     */
    hide() {
        this.unbindEvents();
    }

    /**
     * 监听模型就绪事件
     */
    listenForModelReady() {
        eventBus.on(EVENTS.MODELS_READY, (data) => {
            console.log('Step2FileUpload: MODELS_READY received', data);
            this.modelsReady = true;
        });
    }

    /**
     * 绑定事件
     * 注意：方案B - 事件绑定已移至 index.html 内联脚本，此处禁用
     */
    bindEvents() {
        // 方案B：事件绑定已移至 index.html 内联脚本
        // 为避免冲突，此处不再绑定事件
        console.log('Step2FileUpload.bindEvents: DISABLED (using inline script in index.html)');
        return;
        
        /* 原代码已禁用
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        
        console.log('Step2FileUpload.bindEvents:', {
            uploadArea: !!this.uploadArea,
            fileInput: !!this.fileInput
        });
        
        if (this.uploadArea) {
            this.uploadArea.addEventListener('click', this.handleAreaClick);
            this.uploadArea.addEventListener('dragover', this.handleDragOver);
            this.uploadArea.addEventListener('dragleave', this.handleDragLeave);
            this.uploadArea.addEventListener('drop', this.handleDrop);
        }
        
        if (this.fileInput) {
            this.fileInput.addEventListener('change', this.handleFileSelect);
        }
        
        console.log('Step2FileUpload: Events bound successfully');
        */
    }

    /**
     * 解绑事件
     */
    unbindEvents() {
        if (this.uploadArea) {
            this.uploadArea.removeEventListener('click', this.handleAreaClick);
            this.uploadArea.removeEventListener('dragover', this.handleDragOver);
            this.uploadArea.removeEventListener('dragleave', this.handleDragLeave);
            this.uploadArea.removeEventListener('drop', this.handleDrop);
        }
        
        if (this.fileInput) {
            this.fileInput.removeEventListener('change', this.handleFileSelect);
        }
    }

    /**
     * 处理上传区域点击
     */
    handleAreaClick(e) {
        console.log('=== Step2FileUpload: Upload area clicked ===');
        console.log('Event:', e.type, 'target:', e.target);
        e.preventDefault();
        e.stopPropagation();
        if (this.fileInput) {
            console.log('Step2FileUpload: Triggering file input click');
            this.fileInput.click();
        } else {
            console.error('Step2FileUpload: fileInput is null!');
        }
    }

    /**
     * 处理拖拽悬停
     */
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        if (this.uploadArea) {
            this.uploadArea.classList.add('dragover');
        }
    }

    /**
     * 处理拖拽离开
     */
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        if (this.uploadArea) {
            this.uploadArea.classList.remove('dragover');
        }
    }

    /**
     * 处理文件拖放
     */
    handleDrop(e) {
        console.log('Step2FileUpload: File dropped');
        e.preventDefault();
        e.stopPropagation();
        
        if (this.uploadArea) {
            this.uploadArea.classList.remove('dragover');
        }
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    /**
     * 处理文件选择
     */
    handleFileSelect(e) {
        console.log('Step2FileUpload: File selected via input');
        const files = e.target.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    /**
     * 处理文件 - 主入口
     */
    async processFile(file) {
        console.log('=== Step2FileUpload.processFile called ===');
        console.log('file:', file.name, file.size, file.type);
        
        // 检查模型是否就绪（通过 UIManager 的状态）
        if (window.app && window.app.uiManager && !window.app.uiManager.isUploadAllowed()) {
            this.showError('OCR 模型尚未加载完成，请稍候再试');
            return;
        }
        
        // 验证文件
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }
        
        // 显示文件预览
        this.showFilePreview(file);
        
        // 保存文件信息到状态
        stateManager.set('filename', file.name);
        stateManager.set('fileSize', file.size);
        stateManager.set('fileType', file.type);
        
        // 获取选中的单据类型ID
        const documentTypeSelect = document.getElementById('documentTypeSelect');
        let documentTypeId = documentTypeSelect ? documentTypeSelect.value : null;
        if (documentTypeId && documentTypeId.trim() === '') {
            documentTypeId = null;
        }
        
        // 发布文件选择事件
        eventBus.emit(EVENTS.FILE_SELECTED, {
            name: file.name,
            size: file.size,
            type: file.type,
            documentTypeId: documentTypeId
        });
        
        // 开始上传
        await this.uploadFile(file, documentTypeId);
    }

    /**
     * 显示文件预览
     */
    showFilePreview(file) {
        const existingPreview = document.getElementById('filePreview');
        if (existingPreview) {
            existingPreview.remove();
        }

        const preview = document.createElement('div');
        preview.id = 'filePreview';
        preview.style.cssText = `
            margin-top: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        const icon = document.createElement('div');
        icon.style.cssText = `
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            border-radius: 4px;
        `;

        if (file.type === 'application/pdf') {
            icon.style.background = '#dc2626';
            icon.textContent = '📄';
        } else if (file.type.startsWith('image/')) {
            icon.style.background = '#2563eb';
            icon.textContent = '🖼️';
        } else {
            icon.style.background = '#6b7280';
            icon.textContent = '📄';
        }

        const info = document.createElement('div');
        const sizeMB = (file.size / 1024 / 1024).toFixed(2);
        info.innerHTML = `
            <div style="font-weight: 500;">${file.name}</div>
            <div style="font-size: 12px; color: #666;">${sizeMB} MB</div>
        `;

        preview.appendChild(icon);
        preview.appendChild(info);

        if (this.uploadArea && this.uploadArea.parentNode) {
            this.uploadArea.parentNode.insertBefore(preview, this.uploadArea.nextSibling);
        }
    }

    /**
     * 验证文件
     */
    validateFile(file) {
        // 检查文件类型
        if (!SUPPORTED_TYPES[file.type]) {
            return {
                valid: false,
                error: `不支持的文件类型: ${file.type}。支持: PDF, JPG, PNG`
            };
        }
        
        // 检查文件大小
        if (file.size > MAX_FILE_SIZE) {
            const sizeMB = (file.size / 1024 / 1024).toFixed(1);
            return {
                valid: false,
                error: `文件过大: ${sizeMB}MB。最大支持: 50MB`
            };
        }
        
        return { valid: true };
    }

    /**
     * 上传文件
     */
    async uploadFile(file, documentTypeId) {
        if (this.isUploading) {
            this.showError('正在上传中，请稍候...');
            return;
        }
        
        this.isUploading = true;
        const startTime = Date.now();
        
        // 记录步骤开始时间
        stateManager.recordStepTime(2, 'start');
        
        // 发布上传开始事件
        eventBus.emit(EVENTS.UPLOAD_STARTED, { filename: file.name });
        
        // 显示进度
        this.showProgress(0, '准备上传...');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            console.log('Step2FileUpload: documentTypeId =', documentTypeId);
            
            if (documentTypeId) {
                formData.append('document_type_id', documentTypeId);
                console.log('Step2FileUpload: Added document_type_id to FormData:', documentTypeId);
            }
            
            // 使用 XMLHttpRequest 以支持进度
            const result = await this.uploadWithProgress(formData);
            
            if (result.success) {
                const uploadTime = ((Date.now() - startTime) / 1000).toFixed(1);
                
                // 保存 jobId
                stateManager.set('jobId', result.jobId);
                
                // 保存单据类型ID到状态
                if (documentTypeId) {
                    stateManager.set('selectedDocumentTypeId', documentTypeId);
                }
                
                // 记录步骤结束时间
                stateManager.recordStepTime(2, 'end');
                
                console.log('=== Step2FileUpload: Emitting UPLOAD_COMPLETED ===');
                console.log('jobId:', result.jobId, 'duration:', uploadTime);
                
                // 发布上传完成事件 - 这会触发 Step3Recognition 开始轮询
                eventBus.emit(EVENTS.UPLOAD_COMPLETED, {
                    jobId: result.jobId,
                    duration: uploadTime,
                    documentTypeId: documentTypeId
                });
                
                // 通知步骤完成
                eventBus.emit(EVENTS.STEP_COMPLETED, { 
                    step: 2, 
                    timeDisplay: uploadTime + 's' 
                });
                
                this.showSuccess('上传成功');
            } else {
                throw new Error(result.error || '上传失败');
            }
        } catch (error) {
            console.error('Upload error:', error);
            this.showError('上传失败: ' + error.message);
            
            eventBus.emit(EVENTS.UPLOAD_ERROR, { error: error.message });
            eventBus.emit(EVENTS.STEP_ERROR, { step: 2, message: error.message });
        } finally {
            this.isUploading = false;
        }
    }

    /**
     * 带进度的上传
     */
    uploadWithProgress(formData) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // 进度事件
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    this.showProgress(percent, `上传中... ${percent}%`);
                }
            });
            
            // 完成事件
            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve({
                            success: response.success !== false,
                            jobId: response.job_id || response.jobId,
                            error: response.error
                        });
                    } catch (e) {
                        reject(new Error('解析响应失败'));
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}`));
                }
            });
            
            // 错误事件
            xhr.addEventListener('error', () => {
                reject(new Error('网络错误'));
            });
            
            // 发送请求
            xhr.open('POST', '/api/convert');
            xhr.send(formData);
        });
    }

    /**
     * 显示进度
     */
    showProgress(percent, message) {
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressBarFill');
        const status = document.getElementById('status');
        
        if (progressBar) {
            progressBar.style.display = 'block';
            progressBar.style.width = percent + '%';
        }
        if (progressFill) {
            progressFill.style.width = percent + '%';
        }
        if (status) {
            status.textContent = message;
            status.className = 'status processing';
            status.style.display = 'block';
        }
    }

    /**
     * 显示错误
     */
    showError(message) {
        const status = document.getElementById('status');
        if (status) {
            status.textContent = message;
            status.className = 'status error';
            status.style.display = 'block';
        }
        
        eventBus.emit(EVENTS.UI_ERROR, { message });
    }

    /**
     * 显示成功
     */
    showSuccess(message) {
        const status = document.getElementById('status');
        if (status) {
            status.textContent = message;
            status.className = 'status success';
            status.style.display = 'block';
        }
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.Step2FileUpload = Step2FileUpload;
}
