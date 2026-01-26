/**
 * Step2FileUpload - 步骤2：文件上传组件
 * 处理文件拖拽、选择和上传
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
    }

    /**
     * 显示组件
     */
    show() {
        this.bindEvents();
    }

    /**
     * 隐藏组件
     */
    hide() {
        this.unbindEvents();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        
        if (this.uploadArea) {
            this.uploadArea.addEventListener('click', this.handleAreaClick.bind(this));
            this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
            this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
            this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        }
        
        if (this.fileInput) {
            this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        }
    }

    /**
     * 解绑事件
     */
    unbindEvents() {
        // 事件会在元素销毁时自动清理
    }

    /**
     * 处理上传区域点击
     */
    handleAreaClick() {
        if (this.fileInput) {
            this.fileInput.click();
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
        const files = e.target.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    /**
     * 处理文件
     */
    async processFile(file) {
        // 验证文件
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }
        
        // 保存文件信息到状态
        stateManager.set('filename', file.name);
        stateManager.set('fileSize', file.size);
        stateManager.set('fileType', file.type);
        
        // 发布文件选择事件
        eventBus.emit(EVENTS.FILE_SELECTED, {
            name: file.name,
            size: file.size,
            type: file.type
        });
        
        // 开始上传
        await this.uploadFile(file);
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
    async uploadFile(file) {
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
            
            // 使用 XMLHttpRequest 以支持进度
            const result = await this.uploadWithProgress(formData);
            
            if (result.success) {
                const uploadTime = ((Date.now() - startTime) / 1000).toFixed(1);
                
                // 保存 jobId
                stateManager.set('jobId', result.jobId);
                
                // 记录步骤结束时间
                stateManager.recordStepTime(2, 'end');
                
                // 发布上传完成事件
                eventBus.emit(EVENTS.UPLOAD_COMPLETED, {
                    jobId: result.jobId,
                    duration: uploadTime
                });
                
                // 通知步骤完成
                eventBus.emit(EVENTS.STEP_COMPLETED, { 
                    step: 2, 
                    timeDisplay: uploadTime + 's' 
                });
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
        }
        if (progressFill) {
            progressFill.style.width = percent + '%';
        }
        if (status) {
            status.textContent = message;
            status.className = 'status processing';
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
        }
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.Step2FileUpload = Step2FileUpload;
}
