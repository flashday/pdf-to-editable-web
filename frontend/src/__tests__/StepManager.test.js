/**
 * StepManager 单元测试
 * 测试步骤管理器的步骤切换和状态管理
 */

import { StepManager, STEP_STATUS, STEPS } from '../services/StepManager.js';
import { eventBus, EVENTS } from '../services/EventBus.js';
import { stateManager } from '../services/StateManager.js';

// Mock DOM elements
const mockElements = {};
const createMockElement = (id) => {
    const el = {
        id,
        classList: {
            classes: new Set(),
            add: jest.fn(function(cls) { this.classes.add(cls); }),
            remove: jest.fn(function(...classes) { classes.forEach(c => this.classes.delete(c)); }),
            contains: jest.fn(function(cls) { return this.classes.has(cls); })
        },
        style: {},
        textContent: '',
        querySelector: jest.fn(() => createMockElement('child'))
    };
    return el;
};

// Mock document.getElementById
document.getElementById = jest.fn((id) => {
    if (!mockElements[id]) {
        mockElements[id] = createMockElement(id);
    }
    return mockElements[id];
});

describe('StepManager', () => {
    let stepManager;

    beforeEach(() => {
        stepManager = new StepManager();
        eventBus.clear();
        jest.clearAllMocks();
        Object.keys(mockElements).forEach(key => delete mockElements[key]);
    });

    describe('STEPS configuration', () => {
        test('should have 6 steps defined', () => {
            expect(STEPS).toHaveLength(6);
        });

        test('should have correct step names', () => {
            expect(STEPS[0].name).toBe('模型加载');
            expect(STEPS[1].name).toBe('上传文件');
            expect(STEPS[2].name).toBe('智能识别');
            expect(STEPS[3].name).toBe('预录入');
            expect(STEPS[4].name).toBe('数据提取');
            expect(STEPS[5].name).toBe('财务确认');
        });

        test('should allow back only for steps 5 and 6', () => {
            expect(STEPS[0].allowBack).toBe(false);
            expect(STEPS[1].allowBack).toBe(false);
            expect(STEPS[2].allowBack).toBe(false);
            expect(STEPS[3].allowBack).toBe(false);
            expect(STEPS[4].allowBack).toBe(true);
            expect(STEPS[5].allowBack).toBe(true);
        });
    });

    describe('STEP_STATUS', () => {
        test('should have all status values', () => {
            expect(STEP_STATUS.PENDING).toBe('pending');
            expect(STEP_STATUS.WAITING).toBe('waiting');
            expect(STEP_STATUS.ACTIVE).toBe('active');
            expect(STEP_STATUS.COMPLETED).toBe('completed');
            expect(STEP_STATUS.ERROR).toBe('error');
        });
    });

    describe('getCurrentStep', () => {
        test('should return 1 initially', () => {
            expect(stepManager.getCurrentStep()).toBe(1);
        });
    });

    describe('getStepStatus', () => {
        test('should return PENDING for all steps initially', () => {
            for (let i = 1; i <= 6; i++) {
                expect(stepManager.getStepStatus(i)).toBe(STEP_STATUS.PENDING);
            }
        });
    });

    describe('canEnterStep', () => {
        test('should always allow entering step 1', () => {
            expect(stepManager.canEnterStep(1)).toBe(true);
        });

        test('should not allow entering step 2 if step 1 not completed', () => {
            expect(stepManager.canEnterStep(2)).toBe(false);
        });

        test('should allow entering step 2 after step 1 completed', () => {
            stepManager.updateStepStatus(1, STEP_STATUS.COMPLETED);
            expect(stepManager.canEnterStep(2)).toBe(true);
        });
    });

    describe('goToStep', () => {
        test('should go to step 1', () => {
            const result = stepManager.goToStep(1);
            expect(result).toBe(true);
            expect(stepManager.getCurrentStep()).toBe(1);
        });

        test('should not go to step 2 without completing step 1', () => {
            const result = stepManager.goToStep(2);
            expect(result).toBe(false);
            expect(stepManager.getCurrentStep()).toBe(1);
        });

        test('should go to step 2 with force=true', () => {
            const result = stepManager.goToStep(2, true);
            expect(result).toBe(true);
            expect(stepManager.getCurrentStep()).toBe(2);
        });

        test('should emit STEP_CHANGED event', () => {
            const callback = jest.fn();
            eventBus.on(EVENTS.STEP_CHANGED, callback);
            
            stepManager.goToStep(1);
            
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({
                from: 1,
                to: 1
            }));
        });

        test('should update step status to ACTIVE', () => {
            stepManager.goToStep(1);
            expect(stepManager.getStepStatus(1)).toBe(STEP_STATUS.ACTIVE);
        });
    });

    describe('completeCurrentStep', () => {
        test('should mark current step as completed', () => {
            stepManager.goToStep(1);
            stepManager.completeCurrentStep('1.5s');
            
            expect(stepManager.getStepStatus(1)).toBe(STEP_STATUS.COMPLETED);
        });

        test('should emit STEP_COMPLETED event', () => {
            const callback = jest.fn();
            eventBus.on(EVENTS.STEP_COMPLETED, callback);
            
            stepManager.goToStep(1);
            stepManager.completeCurrentStep('1.5s');
            
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({
                step: 1
            }));
        });

        test('should advance to next step', () => {
            stepManager.goToStep(1);
            stepManager.completeCurrentStep('1.5s');
            
            expect(stepManager.getCurrentStep()).toBe(2);
        });

        test('should not advance past step 6', () => {
            stepManager.fastForwardTo(6);
            stepManager.completeCurrentStep('1.5s');
            
            expect(stepManager.getCurrentStep()).toBe(6);
        });
    });

    describe('setStepError', () => {
        test('should mark current step as error', () => {
            stepManager.goToStep(1);
            stepManager.setStepError('Test error');
            
            expect(stepManager.getStepStatus(1)).toBe(STEP_STATUS.ERROR);
        });

        test('should emit STEP_ERROR event', () => {
            const callback = jest.fn();
            eventBus.on(EVENTS.STEP_ERROR, callback);
            
            stepManager.goToStep(1);
            stepManager.setStepError('Test error');
            
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({
                step: 1,
                message: 'Test error'
            }));
        });
    });

    describe('goBack', () => {
        test('should not allow going back from step 1-4', () => {
            for (let i = 1; i <= 4; i++) {
                stepManager.goToStep(i, true);
                expect(stepManager.goBack()).toBe(false);
            }
        });

        test('should allow going back from step 5', () => {
            stepManager.fastForwardTo(5);
            const result = stepManager.goBack();
            
            expect(result).toBe(true);
            expect(stepManager.getCurrentStep()).toBe(4);
        });

        test('should go to step 4 when rejecting from step 6', () => {
            stepManager.fastForwardTo(6);
            const result = stepManager.goBack();
            
            expect(result).toBe(true);
            expect(stepManager.getCurrentStep()).toBe(4);
        });
    });

    describe('registerComponent', () => {
        test('should register step component', () => {
            const mockComponent = { show: jest.fn(), hide: jest.fn() };
            stepManager.registerComponent(1, mockComponent);
            
            expect(stepManager.stepComponents[1]).toBe(mockComponent);
        });
    });

    describe('activateStepComponent', () => {
        test('should call show on active component and hide on others', () => {
            const comp1 = { show: jest.fn(), hide: jest.fn() };
            const comp2 = { show: jest.fn(), hide: jest.fn() };
            
            stepManager.registerComponent(1, comp1);
            stepManager.registerComponent(2, comp2);
            
            stepManager.activateStepComponent(1);
            
            expect(comp1.show).toHaveBeenCalled();
            expect(comp2.hide).toHaveBeenCalled();
        });
    });

    describe('reset', () => {
        test('should reset to initial state', () => {
            stepManager.fastForwardTo(5);
            stepManager.reset();
            
            expect(stepManager.getCurrentStep()).toBe(1);
            for (let i = 1; i <= 6; i++) {
                expect(stepManager.getStepStatus(i)).toBe(STEP_STATUS.PENDING);
            }
        });
    });

    describe('fastForwardTo', () => {
        test('should mark previous steps as completed', () => {
            stepManager.fastForwardTo(4);
            
            expect(stepManager.getStepStatus(1)).toBe(STEP_STATUS.COMPLETED);
            expect(stepManager.getStepStatus(2)).toBe(STEP_STATUS.COMPLETED);
            expect(stepManager.getStepStatus(3)).toBe(STEP_STATUS.COMPLETED);
            expect(stepManager.getCurrentStep()).toBe(4);
        });
    });

    describe('getStepConfig', () => {
        test('should return step configuration', () => {
            const config = stepManager.getStepConfig(1);
            
            expect(config).toEqual(expect.objectContaining({
                id: 1,
                name: '模型加载'
            }));
        });

        test('should return null for invalid step', () => {
            expect(stepManager.getStepConfig(99)).toBeNull();
        });
    });

    describe('getAllStatus', () => {
        test('should return copy of all step statuses', () => {
            stepManager.updateStepStatus(1, STEP_STATUS.COMPLETED);
            stepManager.updateStepStatus(2, STEP_STATUS.ACTIVE);
            
            const statuses = stepManager.getAllStatus();
            
            expect(statuses[1]).toBe(STEP_STATUS.COMPLETED);
            expect(statuses[2]).toBe(STEP_STATUS.ACTIVE);
            
            // Should be a copy
            statuses[1] = 'modified';
            expect(stepManager.getStepStatus(1)).toBe(STEP_STATUS.COMPLETED);
        });
    });

    describe('FINAL_REJECTED event handling', () => {
        test('should go to step 4 on FINAL_REJECTED', () => {
            // Create a new StepManager to ensure fresh event listeners
            const testStepManager = new StepManager();
            testStepManager.fastForwardTo(6);
            
            // Emit the event - the StepManager should handle it
            eventBus.emit(EVENTS.FINAL_REJECTED);
            
            // The event handler calls goToStep(4)
            expect(testStepManager.getCurrentStep()).toBe(4);
        });
    });
});
