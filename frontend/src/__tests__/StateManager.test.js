/**
 * StateManager 单元测试
 * 测试状态管理器的状态存储和订阅功能
 */

import { StateManager } from '../services/StateManager.js';

// Mock localStorage
const localStorageMock = (() => {
    let store = {};
    return {
        getItem: jest.fn(key => store[key] || null),
        setItem: jest.fn((key, value) => { store[key] = value; }),
        removeItem: jest.fn(key => { delete store[key]; }),
        clear: jest.fn(() => { store = {}; })
    };
})();
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

describe('StateManager', () => {
    let stateManager;

    beforeEach(() => {
        stateManager = new StateManager();
        localStorageMock.clear();
        jest.clearAllMocks();
    });

    describe('get/set', () => {
        test('should set and get state values', () => {
            stateManager.set('jobId', 'test-123');
            expect(stateManager.get('jobId')).toBe('test-123');
        });

        test('should return entire state when no key provided', () => {
            stateManager.set('jobId', 'test-123');
            stateManager.set('filename', 'test.pdf');
            
            const state = stateManager.get();
            expect(state.jobId).toBe('test-123');
            expect(state.filename).toBe('test.pdf');
        });

        test('should return undefined for non-existent keys', () => {
            expect(stateManager.get('nonexistent')).toBeUndefined();
        });
    });

    describe('setMultiple', () => {
        test('should set multiple values at once', () => {
            stateManager.setMultiple({
                jobId: 'job-1',
                filename: 'doc.pdf',
                ocrResult: { text: 'test' }
            });
            
            expect(stateManager.get('jobId')).toBe('job-1');
            expect(stateManager.get('filename')).toBe('doc.pdf');
            expect(stateManager.get('ocrResult')).toEqual({ text: 'test' });
        });
    });

    describe('subscribe', () => {
        test('should notify subscribers on state change', () => {
            const callback = jest.fn();
            stateManager.subscribe('jobId', callback);
            
            stateManager.set('jobId', 'new-job');
            
            expect(callback).toHaveBeenCalledWith('new-job', null);
        });

        test('should pass old and new values to subscriber', () => {
            const callback = jest.fn();
            stateManager.set('jobId', 'old-job');
            stateManager.subscribe('jobId', callback);
            
            stateManager.set('jobId', 'new-job');
            
            expect(callback).toHaveBeenCalledWith('new-job', 'old-job');
        });

        test('should return unsubscribe function', () => {
            const callback = jest.fn();
            const unsubscribe = stateManager.subscribe('jobId', callback);
            
            unsubscribe();
            stateManager.set('jobId', 'test');
            
            expect(callback).not.toHaveBeenCalled();
        });

        test('should not notify when silent=true', () => {
            const callback = jest.fn();
            stateManager.subscribe('jobId', callback);
            
            stateManager.set('jobId', 'test', true);
            
            expect(callback).not.toHaveBeenCalled();
        });
    });

    describe('reset', () => {
        test('should reset all state to initial values', () => {
            stateManager.set('jobId', 'test-job');
            stateManager.set('filename', 'test.pdf');
            stateManager.set('corrections', [{ text: 'fix' }]);
            
            stateManager.reset();
            
            expect(stateManager.get('jobId')).toBeNull();
            expect(stateManager.get('filename')).toBeNull();
            expect(stateManager.get('corrections')).toEqual([]);
        });
    });

    describe('addCorrection', () => {
        test('should add new correction', () => {
            stateManager.addCorrection({
                blockIndex: 0,
                originalText: 'old',
                correctedText: 'new'
            });
            
            const corrections = stateManager.get('corrections');
            expect(corrections).toHaveLength(1);
            expect(corrections[0].correctedText).toBe('new');
        });

        test('should update existing correction for same block', () => {
            stateManager.addCorrection({ blockIndex: 0, correctedText: 'first' });
            stateManager.addCorrection({ blockIndex: 0, correctedText: 'second' });
            
            const corrections = stateManager.get('corrections');
            expect(corrections).toHaveLength(1);
            expect(corrections[0].correctedText).toBe('second');
        });
    });

    describe('getFinalText', () => {
        test('should return finalText if set', () => {
            stateManager.set('finalText', 'Final merged text');
            expect(stateManager.getFinalText()).toBe('Final merged text');
        });

        test('should merge regions with corrections', () => {
            stateManager.set('ocrRegions', [
                { text: 'Block 1' },
                { text: 'Block 2' },
                { text: 'Block 3' }
            ]);
            stateManager.set('corrections', [
                { blockIndex: 1, correctedText: 'Corrected Block 2' }
            ]);
            
            const finalText = stateManager.getFinalText();
            expect(finalText).toContain('Block 1');
            expect(finalText).toContain('Corrected Block 2');
            expect(finalText).toContain('Block 3');
            // The original "Block 2" should be replaced by "Corrected Block 2"
            // Check that the uncorrected version doesn't appear as a standalone block
            const blocks = finalText.split('\n\n');
            expect(blocks.some(b => b === 'Block 2')).toBe(false);
        });
    });

    describe('recordStepTime', () => {
        test('should record start time', () => {
            const before = Date.now();
            stateManager.recordStepTime(1, 'start');
            const after = Date.now();
            
            const timings = stateManager.get('stepTimings');
            expect(timings[1].start).toBeGreaterThanOrEqual(before);
            expect(timings[1].start).toBeLessThanOrEqual(after);
        });

        test('should calculate duration on end', () => {
            stateManager.recordStepTime(1, 'start');
            
            // Simulate some time passing
            const startTime = stateManager.get('stepTimings')[1].start;
            stateManager.state.stepTimings[1].start = startTime - 1000;
            
            stateManager.recordStepTime(1, 'end');
            
            const timings = stateManager.get('stepTimings');
            expect(timings[1].duration).toBeGreaterThanOrEqual(1000);
        });
    });

    describe('getStepDuration', () => {
        test('should return duration for completed step', () => {
            stateManager.set('stepTimings', {
                1: { start: 1000, end: 2500, duration: 1500 }
            }, true);
            
            expect(stateManager.getStepDuration(1)).toBe(1500);
        });

        test('should return null for step without timing', () => {
            expect(stateManager.getStepDuration(99)).toBeNull();
        });
    });

    describe('persist/restore', () => {
        test('should persist state to localStorage', () => {
            stateManager.set('jobId', 'persist-test');
            stateManager.set('filename', 'test.pdf');
            
            stateManager.persist();
            
            expect(localStorageMock.setItem).toHaveBeenCalled();
            const savedData = JSON.parse(localStorageMock.setItem.mock.calls[0][1]);
            expect(savedData.jobId).toBe('persist-test');
        });

        test('should restore state from localStorage', () => {
            const savedState = {
                jobId: 'restored-job',
                filename: 'restored.pdf',
                corrections: [{ blockIndex: 0, correctedText: 'fix' }]
            };
            localStorageMock.getItem.mockReturnValue(JSON.stringify(savedState));
            
            const result = stateManager.restore();
            
            expect(result).toBe(true);
            expect(stateManager.get('jobId')).toBe('restored-job');
        });

        test('should return false when no saved state', () => {
            localStorageMock.getItem.mockReturnValue(null);
            
            const result = stateManager.restore();
            
            expect(result).toBe(false);
        });
    });

    describe('clearStorage', () => {
        test('should remove state from localStorage', () => {
            stateManager.clearStorage();
            expect(localStorageMock.removeItem).toHaveBeenCalled();
        });
    });

    describe('export', () => {
        test('should return deep copy of state', () => {
            stateManager.set('jobId', 'export-test');
            stateManager.set('corrections', [{ text: 'fix' }]);
            
            const exported = stateManager.export();
            exported.jobId = 'modified';
            exported.corrections.push({ text: 'new' });
            
            // Original should be unchanged
            expect(stateManager.get('jobId')).toBe('export-test');
            expect(stateManager.get('corrections')).toHaveLength(1);
        });
    });
});
