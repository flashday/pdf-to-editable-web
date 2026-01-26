/**
 * StepManager - 步骤管理器
 * 管理 6 步工作流的状态和切换
 */

import { eventBus, EVENTS } from './EventBus.js';
import { stateManager } from './StateManager.js';

// 步骤状态枚举
export const STEP_STATUS = {
    PENDING: 'pending',
    WAITING: 'waiting',
    ACTIVE: 'active',
    COMPLETED: 'completed',
    ERROR: 'error'
};

// 步骤配置
export const STEPS = [
    { id: 1, name: '模型加载', icon: '1', allowBack: false },
    { id: 2, name: '上传文件', icon: '2', allowBack: false },
    { id: 3, name: '智能识别', icon: '3', allowBack: false },
    { id: 4, name: '预录入', icon: '4', allowBack: false },
    { id: 5, name: '数据提取', icon: '5', allowBack: true },
    { id: 6, name: '财务确认', icon: '6', allowBack: true }
];

export class StepManager {
    constructor() {
        this.currentStep = 1;
        this.stepStatus = {};
        this.stepTimings = {};
        this.stepComponents = {};
        
        // 初始化步骤状态
        STEPS.forEach(step => {
            this.stepStatus[step.id] = STEP_STATUS.PENDING;
        });
        
        this.setupEventListeners();
    }

    /**
     * 设置事件监听
     */
    setupEventListeners() {
        // 监听驳回事件，返回步骤 4
        eventBus.on(EVENTS.FINAL_REJECTED, () => {
            this.goToStep(4);
        });
    }

    /**
     * 注册步骤组件
     * @param {number} stepId - 步骤 ID
     * @param {Object} component - 步骤组件实例
     */
    registerComponent(stepId, component) {
        this.stepComponents[stepId] = component;
    }

    /**
     * 获取当前步骤
     * @returns {number}
     */
    getCurrentStep() {
        return this.currentStep;
    }

    /**
     * 获取步骤状态
     * @param {number} stepId - 步骤 ID
     * @returns {string}
     */
    getStepStatus(stepId) {
        return this.stepStatus[stepId] || STEP_STATUS.PENDING;
    }

    /**
     * 检查是否可以进入指定步骤
     * @param {number} stepId - 步骤 ID
     * @returns {boolean}
     */
    canEnterStep(stepId) {
        // 步骤 1 总是可以进入
        if (stepId === 1) return true;
        
        // 其他步骤需要前一步完成
        const prevStatus = this.stepStatus[stepId - 1];
        return prevStatus === STEP_STATUS.COMPLETED;
    }

    /**
     * 切换到指定步骤
     * @param {number} stepId - 步骤 ID
     * @param {boolean} force - 是否强制切换（跳过检查）
     * @returns {boolean} - 是否成功切换
     */
    goToStep(stepId, force = false) {
        if (!force && !this.canEnterStep(stepId)) {
            console.warn(`StepManager: Cannot enter step ${stepId}, previous step not completed`);
            return false;
        }
        
        const previousStep = this.currentStep;
        this.currentStep = stepId;
        
        // 更新状态
        this.updateStepStatus(stepId, STEP_STATUS.ACTIVE);
        
        // 记录开始时间
        stateManager.recordStepTime(stepId, 'start');
        
        // 发布事件
        eventBus.emit(EVENTS.STEP_CHANGED, {
            from: previousStep,
            to: stepId,
            status: this.stepStatus[stepId]
        });
        
        // 渲染进度条
        this.renderProgressBar();
        
        // 激活对应组件
        this.activateStepComponent(stepId);
        
        return true;
    }

    /**
     * 完成当前步骤，进入下一步
     * @param {string} timeDisplay - 显示的时间文本
     */
    completeCurrentStep(timeDisplay) {
        const currentStep = this.currentStep;
        
        // 记录结束时间
        stateManager.recordStepTime(currentStep, 'end');
        
        // 更新状态为完成
        this.updateStepStatus(currentStep, STEP_STATUS.COMPLETED, timeDisplay);
        
        // 发布完成事件
        eventBus.emit(EVENTS.STEP_COMPLETED, {
            step: currentStep,
            duration: stateManager.getStepDuration(currentStep)
        });
        
        // 如果不是最后一步，进入下一步
        if (currentStep < STEPS.length) {
            this.goToStep(currentStep + 1);
        }
    }

    /**
     * 标记当前步骤为错误
     * @param {string} message - 错误信息
     */
    setStepError(message) {
        this.updateStepStatus(this.currentStep, STEP_STATUS.ERROR, '失败');
        
        eventBus.emit(EVENTS.STEP_ERROR, {
            step: this.currentStep,
            message
        });
    }

    /**
     * 返回上一步（仅步骤 5、6 支持）
     * @returns {boolean}
     */
    goBack() {
        const currentStepConfig = STEPS.find(s => s.id === this.currentStep);
        if (!currentStepConfig || !currentStepConfig.allowBack) {
            console.warn(`StepManager: Step ${this.currentStep} does not allow going back`);
            return false;
        }
        
        // 步骤 6 驳回返回步骤 4
        if (this.currentStep === 6) {
            return this.goToStep(4, true);
        }
        
        // 其他情况返回上一步
        return this.goToStep(this.currentStep - 1, true);
    }

    /**
     * 更新步骤状态
     * @param {number} stepId - 步骤 ID
     * @param {string} status - 状态
     * @param {string} timeDisplay - 时间显示文本
     */
    updateStepStatus(stepId, status, timeDisplay) {
        this.stepStatus[stepId] = status;
        
        if (timeDisplay !== undefined) {
            this.stepTimings[stepId] = timeDisplay;
        }
        
        this.renderProgressBar();
    }

    /**
     * 激活步骤组件
     * @param {number} stepId - 步骤 ID
     */
    activateStepComponent(stepId) {
        // 隐藏所有步骤组件
        Object.values(this.stepComponents).forEach(component => {
            if (component && typeof component.hide === 'function') {
                component.hide();
            }
        });
        
        // 显示当前步骤组件
        const component = this.stepComponents[stepId];
        if (component && typeof component.show === 'function') {
            component.show();
        }
    }

    /**
     * 渲染步骤进度条
     */
    renderProgressBar() {
        STEPS.forEach(step => {
            const stepEl = document.getElementById(`step${step.id}`);
            if (!stepEl) return;
            
            // 移除所有状态类
            stepEl.classList.remove('completed', 'active', 'waiting', 'error', 'pending');
            
            // 添加当前状态类
            const status = this.stepStatus[step.id];
            if (status) {
                stepEl.classList.add(status);
            }
            
            // 更新时间显示
            const timeEl = document.getElementById(`step${step.id}Time`);
            if (timeEl && this.stepTimings[step.id]) {
                timeEl.textContent = this.stepTimings[step.id];
            }
        });
    }

    /**
     * 重置所有步骤
     */
    reset() {
        this.currentStep = 1;
        STEPS.forEach(step => {
            this.stepStatus[step.id] = STEP_STATUS.PENDING;
        });
        this.stepTimings = {};
        this.renderProgressBar();
    }

    /**
     * 从缓存加载时快速完成前几步
     * @param {number} targetStep - 目标步骤
     */
    fastForwardTo(targetStep) {
        for (let i = 1; i < targetStep; i++) {
            this.updateStepStatus(i, STEP_STATUS.COMPLETED, '缓存');
        }
        this.goToStep(targetStep, true);
    }

    /**
     * 获取步骤配置
     * @param {number} stepId - 步骤 ID
     * @returns {Object|null}
     */
    getStepConfig(stepId) {
        return STEPS.find(s => s.id === stepId) || null;
    }

    /**
     * 获取所有步骤状态
     * @returns {Object}
     */
    getAllStatus() {
        return { ...this.stepStatus };
    }
}

// 创建全局单例
export const stepManager = new StepManager();

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.StepManager = StepManager;
    window.stepManager = stepManager;
    window.STEP_STATUS = STEP_STATUS;
    window.STEPS = STEPS;
}
