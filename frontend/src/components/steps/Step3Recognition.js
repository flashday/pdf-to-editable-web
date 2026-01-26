/**
 * Step3Recognition - 步骤3：智能识别组件
 * 轮询 OCR 处理状态，显示识别结果
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

// 轮询配置
const POLL_INTERVAL = 1000; // 1秒
const MAX_POLL_TIME = 300000; // 5分钟超时

export class Step3Recognition {
    constructor(container) {
        this.container = container;
        this.pollTimer = null;
        this.isPolling = false;
        this.startTime = null;
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
        this.stopPolling();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 监听上传完成事件，开始轮询
        eventBus.on(EVENTS.UPLOAD_COMPLETED, (data) => {
            this.startPolling(data.jobId);
        });
    }

    /**
     * 开始轮询
     */
    async startPolling(jobId) {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.startTime = Date.now();
        
        // 记录步骤开始时间
        stateManager.recordStepTime(3, 'start');
        
        // 发布识别开始事件
        eventBus.emit(EVENTS.RECOGNITION_STARTED, { jobId });
        
        this.showProgress('OCR 识别处理中...');
        
        await this.poll(jobId);
    }

    /**
     * 停止轮询
     */
    stopPolling() {
        if (this.pollTimer) {
            clearTimeout(this.pollTimer);
            this.pollTimer = null;
        }
        this.isPolling = false;
    }

    /**
     * 轮询处理状态
     */
    async poll(jobId) {
        if (!this.isPolling) return;
        
        // 检查超时
        if (Date.now() - this.startTime > MAX_POLL_TIME) {
            this.handleError('处理超时，请重试');
            return;
        }
        
        try {
            const res = await fetch(`/api/convert/${jobId}/status`);
            const data = await res.json();
            
            if (data.status === 'completed') {
                await this.handleComplete(jobId, data);
            } else if (data.status === 'error') {
                this.handleError(data.error || '处理失败');
            } else {
                // 继续轮询
                const progress = data.progress || 0;
                const message = data.message || 'OCR 识别处理中...';
                this.showProgress(message, progress);
                
                this.pollTimer = setTimeout(() => {
                    this.poll(jobId);
                }, POLL_INTERVAL);
            }
        } catch (error) {
            console.error('Poll error:', error);
            this.handleError('网络错误: ' + error.message);
        }
    }

    /**
     * 处理完成
     */
    async handleComplete(jobId, statusData) {
        this.stopPolling();
        
        const processTime = ((Date.now() - this.startTime) / 1000).toFixed(1);
        
        // 记录步骤结束时间
        stateManager.recordStepTime(3, 'end');
        
        try {
            // 获取完整结果
            const result = await this.fetchResult(jobId);
            
            if (result.success) {
                // 保存结果到状态
                this.saveResultToState(result.data, jobId);
                
                // 发布识别完成事件
                eventBus.emit(EVENTS.RECOGNITION_COMPLETED, {
                    jobId,
                    data: result.data,
                    duration: processTime
                });
                
                // 通知步骤完成
                eventBus.emit(EVENTS.STEP_COMPLETED, {
                    step: 3,
                    timeDisplay: processTime + 's'
                });
            } else {
                this.handleError(result.error || '获取结果失败');
            }
        } catch (error) {
            this.handleError('获取结果失败: ' + error.message);
        }
    }

    /**
     * 获取处理结果
     */
    async fetchResult(jobId) {
        const res = await fetch(`/api/convert/${jobId}/result`);
        const data = await res.json();
        
        return {
            success: data.status === 'completed',
            data: data,
            error: data.error
        };
    }

    /**
     * 保存结果到状态
     */
    saveResultToState(data, jobId) {
        // 提取 OCR 区域
        const blocks = data.result?.blocks || data.blocks || [];
        const ocrRegions = this.extractOCRRegions(blocks);
        
        stateManager.set('ocrData', data);
        stateManager.set('ocrRegions', ocrRegions);
        stateManager.set('blocks', blocks);
        
        // 置信度报告
        if (data.confidence_report) {
            stateManager.set('confidenceReport', data.confidence_report);
        }
        
        // Markdown 内容
        if (data.markdown) {
            stateManager.set('markdown', data.markdown);
        }
    }

    /**
     * 提取 OCR 区域
     */
    extractOCRRegions(blocks) {
        return blocks.map((block, i) => {
            const coords = block.metadata?.originalCoordinates || null;
            const confidence = block.metadata?.confidence || null;
            const originalStructType = block.metadata?.originalStructType || block.type;
            const editType = block.metadata?.editType || (block.type === 'table' ? 'table' : 'text');
            
            return {
                index: i,
                blockId: block.id,
                type: block.type,
                text: this.getBlockText(block),
                coordinates: coords || { x: 0, y: 0, width: 100, height: 30 },
                hasCoordinates: !!coords,
                tableHtml: block.data?.tableHtml || null,
                confidence: confidence,
                originalStructType: originalStructType,
                editType: editType
            };
        });
    }

    /**
     * 获取 Block 文本
     */
    getBlockText(block) {
        if (block.data?.text) return block.data.text;
        if (block.data?.items) return block.data.items.join(', ');
        return '';
    }

    /**
     * 处理错误
     */
    handleError(message) {
        this.stopPolling();
        
        this.showError(message);
        
        eventBus.emit(EVENTS.RECOGNITION_ERROR, { error: message });
        eventBus.emit(EVENTS.STEP_ERROR, { step: 3, message });
    }

    /**
     * 显示进度
     */
    showProgress(message, percent) {
        const status = document.getElementById('status');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressBarFill');
        
        if (status) {
            status.textContent = message;
            status.className = 'status processing';
        }
        
        if (progressBar && percent !== undefined) {
            progressBar.style.display = 'block';
            if (progressFill) {
                progressFill.style.width = percent + '%';
            }
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
    window.Step3Recognition = Step3Recognition;
}
