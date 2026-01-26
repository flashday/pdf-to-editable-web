/**
 * EventBus - 事件总线
 * 用于组件间通信的发布订阅模式实现
 */

// 预定义事件常量
export const EVENTS = {
    // 步骤相关
    STEP_CHANGED: 'step:changed',
    STEP_COMPLETED: 'step:completed',
    STEP_ERROR: 'step:error',
    
    // 模型/服务相关
    MODELS_READY: 'models:ready',
    SERVICE_STATUS_CHANGED: 'service:status_changed',
    
    // 文件上传相关
    FILE_SELECTED: 'file:selected',
    UPLOAD_STARTED: 'upload:started',
    UPLOAD_COMPLETED: 'upload:completed',
    UPLOAD_ERROR: 'upload:error',
    
    // OCR 识别相关
    RECOGNITION_STARTED: 'recognition:started',
    RECOGNITION_COMPLETED: 'recognition:completed',
    RECOGNITION_ERROR: 'recognition:error',
    OCR_STARTED: 'ocr:started',
    OCR_PROGRESS: 'ocr:progress',
    OCR_COMPLETED: 'ocr:completed',
    OCR_ERROR: 'ocr:error',
    
    // 预录入相关
    BLOCK_SELECTED: 'block:selected',
    BLOCK_EDITED: 'block:edited',
    CORRECTION_SAVED: 'correction:saved',
    PREENTRY_CONFIRMED: 'preentry:confirmed',
    
    // 数据提取相关
    TEMPLATE_SELECTED: 'template:selected',
    TEMPLATE_SAVED: 'template:saved',
    TEMPLATE_DELETED: 'template:deleted',
    EXTRACTION_STARTED: 'extraction:started',
    EXTRACTION_COMPLETED: 'extraction:completed',
    CHECKPOINT_STARTED: 'checkpoint:started',
    CHECKPOINT_COMPLETED: 'checkpoint:completed',
    CHECKPOINT_CONFIG_CHANGED: 'checkpoint:config_changed',
    
    // 最终确认相关
    FINAL_CONFIRMED: 'final:confirmed',
    FINAL_REJECTED: 'final:rejected',
    
    // 任务/历史相关
    JOB_LOADED: 'job:loaded',
    JOB_RESET: 'job:reset',
    HISTORY_JOB_SELECTED: 'history:job_selected',
    HISTORY_JOB_LOADED: 'history:job_loaded',
    
    // UI 相关
    PANEL_OPENED: 'panel:opened',
    PANEL_CLOSED: 'panel:closed',
    NOTIFICATION: 'notification',
    UI_ERROR: 'ui:error',
    UI_SUCCESS: 'ui:success'
};

export class EventBus {
    constructor() {
        this.listeners = new Map();
        this.onceListeners = new Map();
    }

    /**
     * 订阅事件
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     * @returns {Function} - 取消订阅的函数
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
        
        // 返回取消订阅函数
        return () => this.off(event, callback);
    }

    /**
     * 订阅一次性事件
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    once(event, callback) {
        if (!this.onceListeners.has(event)) {
            this.onceListeners.set(event, new Set());
        }
        this.onceListeners.get(event).add(callback);
    }

    /**
     * 取消订阅
     * @param {string} event - 事件名称
     * @param {Function} callback - 回调函数
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
        if (this.onceListeners.has(event)) {
            this.onceListeners.get(event).delete(callback);
        }
    }

    /**
     * 发布事件
     * @param {string} event - 事件名称
     * @param {*} data - 事件数据
     */
    emit(event, data) {
        // 调用普通监听器
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`EventBus: Error in listener for "${event}":`, error);
                }
            });
        }
        
        // 调用一次性监听器
        if (this.onceListeners.has(event)) {
            this.onceListeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`EventBus: Error in once listener for "${event}":`, error);
                }
            });
            this.onceListeners.delete(event);
        }
    }

    /**
     * 清除所有监听器
     */
    clear() {
        this.listeners.clear();
        this.onceListeners.clear();
    }

    /**
     * 清除指定事件的所有监听器
     * @param {string} event - 事件名称
     */
    clearEvent(event) {
        this.listeners.delete(event);
        this.onceListeners.delete(event);
    }

    /**
     * 获取事件监听器数量
     * @param {string} event - 事件名称
     * @returns {number}
     */
    listenerCount(event) {
        let count = 0;
        if (this.listeners.has(event)) {
            count += this.listeners.get(event).size;
        }
        if (this.onceListeners.has(event)) {
            count += this.onceListeners.get(event).size;
        }
        return count;
    }
}

// 创建全局单例
export const eventBus = new EventBus();

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.EventBus = EventBus;
    window.EVENTS = EVENTS;
    window.eventBus = eventBus;
}
