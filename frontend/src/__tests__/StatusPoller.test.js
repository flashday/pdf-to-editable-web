/**
 * Tests for StatusPoller service
 */
import { StatusPoller } from '../services/StatusPoller.js';

describe('StatusPoller', () => {
    let statusPoller;
    let mockApiClient;
    let callbacks;

    beforeEach(() => {
        jest.useFakeTimers();
        
        // Create mock API client
        mockApiClient = {
            getJobStatus: jest.fn(),
            getJobResult: jest.fn()
        };
        
        // Create callbacks
        callbacks = {
            onStatusUpdate: jest.fn(),
            onComplete: jest.fn(),
            onError: jest.fn(),
            onTimeout: jest.fn(),
            onProgress: jest.fn()
        };
        
        // Create status poller with short intervals for testing
        statusPoller = new StatusPoller(mockApiClient, {
            pollingInterval: 100,
            maxPollingAttempts: 10,
            timeoutDuration: 5000,
            maxConsecutiveErrors: 3
        });
    });

    afterEach(() => {
        statusPoller.stopPolling();
        jest.useRealTimers();
    });

    describe('startPolling', () => {
        it('should start polling for job status', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward one polling interval
            await jest.advanceTimersByTimeAsync(100);

            expect(mockApiClient.getJobStatus).toHaveBeenCalledWith('test-job-123');
            expect(callbacks.onStatusUpdate).toHaveBeenCalledWith(mockStatus);
            expect(callbacks.onProgress).toHaveBeenCalledWith({
                progress: 0.5,
                message: 'Processing document',
                stage: 'processing'
            });
        });

        it('should handle completion', async () => {
            const mockStatus = {
                status: 'completed',
                progress: 1.0,
                message: 'Processing completed',
                completed: true,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward one polling interval
            await jest.advanceTimersByTimeAsync(100);

            expect(callbacks.onComplete).toHaveBeenCalledWith(mockStatus);
            expect(statusPoller.isPolling).toBe(false);
        });

        it('should handle failure', async () => {
            const mockStatus = {
                status: 'failed',
                progress: 0.3,
                message: 'Processing failed',
                completed: false,
                failed: true,
                error: 'OCR processing error'
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward one polling interval
            await jest.advanceTimersByTimeAsync(100);

            expect(callbacks.onError).toHaveBeenCalledWith('OCR processing error');
            expect(statusPoller.isPolling).toBe(false);
        });

        it('should retry on network error', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            // Fail once, then succeed
            mockApiClient.getJobStatus
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward through first attempt and retry
            await jest.advanceTimersByTimeAsync(100); // First attempt fails
            await jest.advanceTimersByTimeAsync(150); // Retry with backoff

            // Should have been called at least twice (initial + retry)
            expect(mockApiClient.getJobStatus.mock.calls.length).toBeGreaterThanOrEqual(2);
            expect(callbacks.onStatusUpdate).toHaveBeenCalledWith(mockStatus);
        });

        it('should stop after max consecutive errors', async () => {
            mockApiClient.getJobStatus.mockRejectedValue(new Error('Network error'));

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward through all error attempts
            for (let i = 0; i < 3; i++) {
                await jest.advanceTimersByTimeAsync(100 * Math.pow(1.5, i));
            }

            expect(callbacks.onError).toHaveBeenCalled();
            expect(statusPoller.isPolling).toBe(false);
        });

        it('should handle timeout', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward past timeout duration
            await jest.advanceTimersByTimeAsync(6000);

            expect(callbacks.onTimeout).toHaveBeenCalled();
            expect(statusPoller.isPolling).toBe(false);
        });

        it('should stop after max polling attempts', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward through all polling attempts
            for (let i = 0; i < 11; i++) {
                await jest.advanceTimersByTimeAsync(100);
            }

            expect(callbacks.onTimeout).toHaveBeenCalled();
            expect(statusPoller.isPolling).toBe(false);
        });
    });

    describe('stopPolling', () => {
        it('should stop polling', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward one interval
            await jest.advanceTimersByTimeAsync(100);

            const callCountBeforeStop = mockApiClient.getJobStatus.mock.calls.length;

            // Stop polling
            statusPoller.stopPolling();

            // Fast-forward more time
            await jest.advanceTimersByTimeAsync(1000);

            // Should not have been called again after stopping
            expect(mockApiClient.getJobStatus.mock.calls.length).toBe(callCountBeforeStop);
            expect(statusPoller.isPolling).toBe(false);
        });
    });

    describe('getState', () => {
        it('should return current polling state', () => {
            const state = statusPoller.getState();

            expect(state).toHaveProperty('isPolling');
            expect(state).toHaveProperty('jobId');
            expect(state).toHaveProperty('attempts');
            expect(state).toHaveProperty('consecutiveErrors');
            expect(state).toHaveProperty('elapsedTime');
        });

        it('should track polling attempts', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward through multiple polls
            await jest.advanceTimersByTimeAsync(100);
            await jest.advanceTimersByTimeAsync(100);
            await jest.advanceTimersByTimeAsync(100);

            const state = statusPoller.getState();
            // Should have at least 3 attempts
            expect(state.attempts).toBeGreaterThanOrEqual(3);
        });
    });

    describe('reset', () => {
        it('should reset poller state', async () => {
            const mockStatus = {
                status: 'processing',
                progress: 0.5,
                message: 'Processing document',
                completed: false,
                failed: false
            };

            mockApiClient.getJobStatus.mockResolvedValue(mockStatus);

            statusPoller.startPolling('test-job-123', callbacks);

            // Fast-forward one interval
            await jest.advanceTimersByTimeAsync(100);

            // Reset
            statusPoller.reset();

            const state = statusPoller.getState();
            expect(state.isPolling).toBe(false);
            expect(state.jobId).toBeNull();
            expect(state.attempts).toBe(0);
        });
    });
});
