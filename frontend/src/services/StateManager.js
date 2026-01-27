/**
 * StateManager - 全局状态管理器
 * 管理应用状态和步骤间数据传递
 */

import { eventBus, EVENTS } from './EventBus.js';

export class StateManager {
    constructor() {
        this.state = {
            // 任务信息
            jobId: null,
            filename: null,
            
            // 步骤 3 输出：OCR 结果
            ocrResult: null,
            ocrData: null,  // 原始 OCR 数据（包含 blocks）
            ocrRegions: [],
            documentImageUrl: null,
            confidenceReport: null,
            
            // 步骤 4 输出：预录入修正
            corrections: [],
            finalText: null,
            
            // 步骤 5 输出：数据提取
            selectedTemplate: null,
            extractedData: null,
            checkpointResults: [],
            
            // 步骤 6 输出：最终结果
            finalResult: null,
            finalStatus: null, // 'confirmed' | 'rejected'
            
            // 步骤时间记录
            stepTimings: {},
            
            // 缓存标记
            isFromCache: false
        };
        
        this.subscribers = new Map();
        this.storageKey = 'pdf_ocr_state';
    }

    /**
     * 获取状态值
     * @param {string} key - 状态键
     * @returns {*}
     */
    get(key) {
        if (key) {
            return this.state[key];
        }
        return { ...this.state };
    }

    /**
     * 设置状态值
     * @param {string} key - 状态键
     * @param {*} value - 状态值
     * @param {boolean} silent - 是否静默更新（不触发事件）
     */
    set(key, value, silent = false) {
        const oldValue = this.state[key];
        this.state[key] = value;
        
        if (!silent) {
            // 通知订阅者
            if (this.subscribers.has(key)) {
                this.subscribers.get(key).forEach(callback => {
                    try {
                        callback(value, oldValue);
                    } catch (error) {
                        console.error(`StateManager: Error in subscriber for "${key}":`, error);
                    }
                });
            }
            
            // 发布状态变更事件
            eventBus.emit('state:changed', { key, value, oldValue });
        }
    }

    /**
     * 批量设置状态
     * @param {Object} updates - 状态更新对象
     * @param {boolean} silent - 是否静默更新
     */
    setMultiple(updates, silent = false) {
        Object.entries(updates).forEach(([key, value]) => {
            this.set(key, value, silent);
        });
    }

    /**
     * 订阅状态变化
     * @param {string} key - 状态键
     * @param {Function} callback - 回调函数
     * @returns {Function} - 取消订阅函数
     */
    subscribe(key, callback) {
        if (!this.subscribers.has(key)) {
            this.subscribers.set(key, new Set());
        }
        this.subscribers.get(key).add(callback);
        
        return () => {
            if (this.subscribers.has(key)) {
                this.subscribers.get(key).delete(callback);
            }
        };
    }

    /**
     * 重置状态（新任务时）
     */
    reset() {
        this.state = {
            jobId: null,
            filename: null,
            ocrResult: null,
            ocrData: null,
            ocrRegions: [],
            documentImageUrl: null,
            confidenceReport: null,
            corrections: [],
            finalText: null,
            selectedTemplate: null,
            extractedData: null,
            checkpointResults: [],
            finalResult: null,
            finalStatus: null,
            stepTimings: {},
            isFromCache: false
        };
        
        eventBus.emit(EVENTS.JOB_RESET);
    }

    /**
     * 添加修正记录
     * @param {Object} correction - 修正记录
     */
    addCorrection(correction) {
        const corrections = [...this.state.corrections];
        
        // 检查是否已存在同一 block 的修正
        const existingIndex = corrections.findIndex(c => c.blockIndex === correction.blockIndex);
        if (existingIndex >= 0) {
            corrections[existingIndex] = correction;
        } else {
            corrections.push(correction);
        }
        
        this.set('corrections', corrections);
        eventBus.emit(EVENTS.CORRECTION_SAVED, correction);
    }

    /**
     * 获取修正后的文本
     * @returns {string}
     */
    getFinalText() {
        if (this.state.finalText) {
            return this.state.finalText;
        }
        
        // 合并原始文本和修正
        const regions = this.state.ocrRegions || [];
        const corrections = this.state.corrections || [];
        
        console.log('getFinalText: regions count:', regions.length);
        console.log('getFinalText: corrections count:', corrections.length);
        
        const correctionMap = new Map();
        corrections.forEach(c => correctionMap.set(c.blockIndex, c.correctedText));
        
        const texts = regions.map((region, index) => {
            if (correctionMap.has(index)) {
                return correctionMap.get(index);
            }
            return region.text || '';
        });
        
        const result = texts.join('\n\n').trim();
        console.log('getFinalText: result length:', result.length);
        
        // 如果 regions 中没有文本，尝试从 ocrData 获取
        if (!result && this.state.ocrData) {
            console.log('getFinalText: trying to get text from ocrData');
            const blocks = this.state.ocrData.blocks || [];
            const blockTexts = blocks.map(block => {
                if (block.data && block.data.text) return block.data.text;
                if (block.data && block.data.items) return block.data.items.join(', ');
                return '';
            }).filter(t => t);
            return blockTexts.join('\n\n');
        }
        
        return result;
    }

    /**
     * 记录步骤时间
     * @param {number} step - 步骤号
     * @param {string} type - 'start' | 'end'
     */
    recordStepTime(step, type) {
        const timings = { ...this.state.stepTimings };
        if (!timings[step]) {
            timings[step] = {};
        }
        timings[step][type] = Date.now();
        
        if (type === 'end' && timings[step].start) {
            timings[step].duration = timings[step].end - timings[step].start;
        }
        
        this.set('stepTimings', timings, true);
    }

    /**
     * 获取步骤耗时
     * @param {number} step - 步骤号
     * @returns {number|null} - 毫秒数
     */
    getStepDuration(step) {
        const timings = this.state.stepTimings[step];
        return timings ? timings.duration : null;
    }

    /**
     * 保存到本地存储
     */
    persist() {
        try {
            const dataToSave = {
                jobId: this.state.jobId,
                filename: this.state.filename,
                corrections: this.state.corrections,
                selectedTemplate: this.state.selectedTemplate,
                stepTimings: this.state.stepTimings,
                savedAt: Date.now()
            };
            localStorage.setItem(this.storageKey, JSON.stringify(dataToSave));
        } catch (error) {
            console.error('StateManager: Failed to persist state:', error);
        }
    }

    /**
     * 从本地存储恢复
     * @returns {boolean} - 是否成功恢复
     */
    restore() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const data = JSON.parse(saved);
                // 只恢复部分状态
                if (data.jobId) {
                    this.set('jobId', data.jobId, true);
                    this.set('filename', data.filename, true);
                    this.set('corrections', data.corrections || [], true);
                    this.set('selectedTemplate', data.selectedTemplate, true);
                    this.set('stepTimings', data.stepTimings || {}, true);
                    return true;
                }
            }
        } catch (error) {
            console.error('StateManager: Failed to restore state:', error);
        }
        return false;
    }

    /**
     * 清除本地存储
     */
    clearStorage() {
        try {
            localStorage.removeItem(this.storageKey);
        } catch (error) {
            console.error('StateManager: Failed to clear storage:', error);
        }
    }

    /**
     * 导出当前状态（用于调试）
     * @returns {Object}
     */
    export() {
        return JSON.parse(JSON.stringify(this.state));
    }
}

// 创建全局单例
export const stateManager = new StateManager();

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.StateManager = StateManager;
    window.stateManager = stateManager;
}
