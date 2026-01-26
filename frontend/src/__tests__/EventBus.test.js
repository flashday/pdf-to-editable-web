/**
 * EventBus 单元测试
 * 测试事件总线的发布订阅功能
 */

import { EventBus, EVENTS } from '../services/EventBus.js';

describe('EventBus', () => {
    let eventBus;

    beforeEach(() => {
        eventBus = new EventBus();
    });

    afterEach(() => {
        eventBus.clear();
    });

    describe('on/emit', () => {
        test('should subscribe and receive events', () => {
            const callback = jest.fn();
            eventBus.on('test:event', callback);
            
            eventBus.emit('test:event', { data: 'test' });
            
            expect(callback).toHaveBeenCalledTimes(1);
            expect(callback).toHaveBeenCalledWith({ data: 'test' });
        });

        test('should support multiple subscribers', () => {
            const callback1 = jest.fn();
            const callback2 = jest.fn();
            
            eventBus.on('test:event', callback1);
            eventBus.on('test:event', callback2);
            
            eventBus.emit('test:event', 'data');
            
            expect(callback1).toHaveBeenCalledWith('data');
            expect(callback2).toHaveBeenCalledWith('data');
        });

        test('should not call callback for different events', () => {
            const callback = jest.fn();
            eventBus.on('event:a', callback);
            
            eventBus.emit('event:b', 'data');
            
            expect(callback).not.toHaveBeenCalled();
        });
    });

    describe('off', () => {
        test('should unsubscribe from events', () => {
            const callback = jest.fn();
            eventBus.on('test:event', callback);
            eventBus.off('test:event', callback);
            
            eventBus.emit('test:event', 'data');
            
            expect(callback).not.toHaveBeenCalled();
        });

        test('should return unsubscribe function from on()', () => {
            const callback = jest.fn();
            const unsubscribe = eventBus.on('test:event', callback);
            
            unsubscribe();
            eventBus.emit('test:event', 'data');
            
            expect(callback).not.toHaveBeenCalled();
        });
    });

    describe('once', () => {
        test('should only trigger callback once', () => {
            const callback = jest.fn();
            eventBus.once('test:event', callback);
            
            eventBus.emit('test:event', 'first');
            eventBus.emit('test:event', 'second');
            
            expect(callback).toHaveBeenCalledTimes(1);
            expect(callback).toHaveBeenCalledWith('first');
        });
    });

    describe('clear', () => {
        test('should remove all listeners', () => {
            const callback1 = jest.fn();
            const callback2 = jest.fn();
            
            eventBus.on('event:a', callback1);
            eventBus.on('event:b', callback2);
            eventBus.clear();
            
            eventBus.emit('event:a', 'data');
            eventBus.emit('event:b', 'data');
            
            expect(callback1).not.toHaveBeenCalled();
            expect(callback2).not.toHaveBeenCalled();
        });
    });

    describe('clearEvent', () => {
        test('should remove listeners for specific event', () => {
            const callback1 = jest.fn();
            const callback2 = jest.fn();
            
            eventBus.on('event:a', callback1);
            eventBus.on('event:b', callback2);
            eventBus.clearEvent('event:a');
            
            eventBus.emit('event:a', 'data');
            eventBus.emit('event:b', 'data');
            
            expect(callback1).not.toHaveBeenCalled();
            expect(callback2).toHaveBeenCalled();
        });
    });

    describe('listenerCount', () => {
        test('should return correct listener count', () => {
            eventBus.on('test:event', () => {});
            eventBus.on('test:event', () => {});
            eventBus.once('test:event', () => {});
            
            expect(eventBus.listenerCount('test:event')).toBe(3);
        });

        test('should return 0 for events with no listeners', () => {
            expect(eventBus.listenerCount('nonexistent')).toBe(0);
        });
    });

    describe('error handling', () => {
        test('should catch errors in callbacks without stopping other callbacks', () => {
            const errorCallback = jest.fn(() => { throw new Error('Test error'); });
            const normalCallback = jest.fn();
            
            eventBus.on('test:event', errorCallback);
            eventBus.on('test:event', normalCallback);
            
            // Should not throw
            expect(() => eventBus.emit('test:event', 'data')).not.toThrow();
            expect(normalCallback).toHaveBeenCalled();
        });
    });

    describe('EVENTS constants', () => {
        test('should have step-related events', () => {
            expect(EVENTS.STEP_CHANGED).toBe('step:changed');
            expect(EVENTS.STEP_COMPLETED).toBe('step:completed');
            expect(EVENTS.STEP_ERROR).toBe('step:error');
        });

        test('should have upload-related events', () => {
            expect(EVENTS.UPLOAD_STARTED).toBe('upload:started');
            expect(EVENTS.UPLOAD_COMPLETED).toBe('upload:completed');
            expect(EVENTS.UPLOAD_ERROR).toBe('upload:error');
        });

        test('should have OCR-related events', () => {
            expect(EVENTS.OCR_STARTED).toBe('ocr:started');
            expect(EVENTS.OCR_COMPLETED).toBe('ocr:completed');
            expect(EVENTS.OCR_ERROR).toBe('ocr:error');
        });
    });
});
