/**
 * Step1ModelLoad - 步骤1：模型加载组件
 * 检测 OCR 模型和 LLM 服务状态
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

export class Step1ModelLoad {
    constructor(container) {
        this.container = container;
        this.checkInterval = null;
        this.isChecking = false;
        this.hasCompletedOnce = false; // 防止重复触发完成事件
        this.services = {
            ocr: { status: 'checking', text: '检测中...' },
            llm: { status: 'checking', text: '检测中...' },
            rag: { status: 'checking', text: '检测中...' }
        };
    }

    /**
     * 显示组件
     */
    show() {
        this.startHealthCheck();
    }

    /**
     * 隐藏组件
     */
    hide() {
        this.stopHealthCheck();
    }

    /**
     * 开始健康检查
     */
    async startHealthCheck() {
        if (this.isChecking) return;
        this.isChecking = true;
        
        // 立即执行一次检查
        await this.checkAllServices();
        
        // 定期检查（每30秒）
        this.checkInterval = setInterval(() => {
            this.checkAllServices();
        }, 30000);
    }

    /**
     * 停止健康检查
     */
    stopHealthCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        this.isChecking = false;
    }

    /**
     * 检查所有服务状态
     */
    async checkAllServices() {
        try {
            // 使用统一的 /api/services/status 端点
            const res = await fetch('/api/services/status');
            const data = await res.json();
            
            // OCR 状态
            if (data.ocr) {
                const ocr = data.ocr;
                if (ocr.loaded) {
                    const timeText = ocr.time ? `就绪 (${ocr.time.toFixed(1)}s)` : '就绪';
                    this.updateServiceStatus('ocr', 'online', timeText);
                } else if (ocr.loading) {
                    this.updateServiceStatus('ocr', 'checking', '加载中...');
                } else {
                    this.updateServiceStatus('ocr', 'offline', '未就绪');
                }
            }
            
            // LLM 状态
            if (data.llm) {
                const llm = data.llm;
                if (llm.loaded) {
                    this.updateServiceStatus('llm', 'online', 'Ollama');
                } else if (llm.loading) {
                    this.updateServiceStatus('llm', 'checking', '加载中...');
                } else {
                    this.updateServiceStatus('llm', 'offline', '未连接');
                }
            }
            
            // RAG 状态
            if (data.rag) {
                const rag = data.rag;
                if (rag.loaded) {
                    const timeText = rag.time ? `就绪 (${rag.time.toFixed(1)}s)` : '就绪';
                    this.updateServiceStatus('rag', 'online', timeText);
                } else if (rag.loading) {
                    this.updateServiceStatus('rag', 'checking', '加载中...');
                } else {
                    this.updateServiceStatus('rag', 'warning', '未启用');
                }
            }
            
            // 判断是否全部就绪（只需要 OCR 就绪即可）
            const allReady = this.services.ocr.status === 'online';
            
            if (allReady) {
                stateManager.set('modelsReady', true);
                eventBus.emit(EVENTS.MODELS_READY);
                eventBus.emit(EVENTS.STEP_COMPLETED, { step: 1 });
            }
        } catch (e) {
            console.error('Service status check failed:', e);
            // 回退到单独检查
            await this.checkOcrService();
            await this.checkLlmService();
            
            const allReady = this.services.ocr.status === 'online';
            if (allReady && !this.hasCompletedOnce) {
                this.hasCompletedOnce = true;
                console.log('Step1ModelLoad (fallback): OCR ready, emitting events');
                stateManager.set('modelsReady', true);
                eventBus.emit(EVENTS.MODELS_READY);
                eventBus.emit(EVENTS.STEP_COMPLETED, { step: 1, timeDisplay: '✓' });
            }
        }
    }

    /**
     * 检查 OCR 服务（回退方法）
     */
    async checkOcrService() {
        try {
            const res = await fetch('/api/health');
            const data = await res.json();
            if (data.status === 'healthy') {
                this.updateServiceStatus('ocr', 'online', '就绪');
            } else {
                this.updateServiceStatus('ocr', 'offline', '未就绪');
            }
        } catch (e) {
            this.updateServiceStatus('ocr', 'offline', '离线');
        }
    }

    /**
     * 检查 LLM 服务（回退方法）
     */
    async checkLlmService() {
        try {
            const res = await fetch('/api/llm/status');
            const data = await res.json();
            
            if (data.success && data.data) {
                const llmData = data.data;
                
                if (llmData.llm_available) {
                    this.updateServiceStatus('llm', 'online', 'Ollama');
                } else {
                    this.updateServiceStatus('llm', 'offline', '未连接');
                }
                
                if (llmData.rag_available) {
                    this.updateServiceStatus('rag', 'online', '就绪');
                } else {
                    this.updateServiceStatus('rag', 'warning', '未启用');
                }
            } else {
                this.updateServiceStatus('llm', 'offline', '不可用');
                this.updateServiceStatus('rag', 'offline', '不可用');
            }
        } catch (e) {
            this.updateServiceStatus('llm', 'offline', '检测失败');
            this.updateServiceStatus('rag', 'offline', '检测失败');
        }
    }

    /**
     * 更新服务状态
     */
    updateServiceStatus(service, status, text) {
        this.services[service] = { status, text };
        this.renderServiceStatus(service, status, text);
        
        stateManager.set(`service_${service}`, { status, text });
        eventBus.emit(EVENTS.SERVICE_STATUS_CHANGED, { service, status, text });
    }

    /**
     * 渲染服务状态到 DOM
     */
    renderServiceStatus(service, status, text) {
        const serviceMap = {
            ocr: { itemId: 'llmOcrStatus', textId: 'llmOcrText' },
            llm: { itemId: 'llmLlmStatus', textId: 'llmLlmText' },
            rag: { itemId: 'llmRagStatus', textId: 'llmRagText' }
        };
        
        const config = serviceMap[service];
        if (!config) return;
        
        const item = document.getElementById(config.itemId);
        const textEl = document.getElementById(config.textId);
        
        if (!item || !textEl) return;
        
        // 更新状态点
        const dot = item.querySelector('.status-dot');
        if (dot) {
            dot.classList.remove('checking', 'online', 'offline', 'warning');
            dot.classList.add(status);
        }
        
        // 更新文本
        textEl.classList.remove('online', 'offline', 'warning');
        textEl.classList.add(status);
        textEl.textContent = text;
    }

    /**
     * 获取服务状态
     */
    getServiceStatus(service) {
        return this.services[service] || { status: 'unknown', text: '未知' };
    }

    /**
     * 检查是否所有必需服务就绪
     */
    isReady() {
        return this.services.ocr.status === 'online';
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.Step1ModelLoad = Step1ModelLoad;
}
