/**
 * Tests for API Client
 */
import { APIClient } from '../services/APIClient.js';
import axios from 'axios';

// Mock axios
jest.mock('axios');

describe('APIClient', () => {
    let apiClient;
    let mockAxiosInstance;

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();

        // Create mock axios instance
        mockAxiosInstance = {
            get: jest.fn(),
            post: jest.fn(),
            interceptors: {
                response: {
                    use: jest.fn()
                }
            }
        };

        axios.create = jest.fn(() => mockAxiosInstance);

        apiClient = new APIClient('/api');
    });

    describe('uploadFile', () => {
        it('should upload file successfully', async () => {
            const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: {
                    job_id: 'test-job-123',
                    status: 'pending',
                    message: 'File uploaded successfully'
                }
            };

            mockAxiosInstance.post.mockResolvedValue(mockResponse);

            const result = await apiClient.uploadFile(mockFile);

            expect(result).toEqual(mockResponse.data);
            expect(mockAxiosInstance.post).toHaveBeenCalledWith(
                '/convert',
                expect.any(FormData),
                expect.objectContaining({
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                })
            );
        });

        it('should track upload progress', async () => {
            const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: { job_id: 'test-job-123' }
            };
            const progressCallback = jest.fn();

            mockAxiosInstance.post.mockImplementation((url, data, config) => {
                // Simulate progress events
                if (config.onUploadProgress) {
                    config.onUploadProgress({ loaded: 50, total: 100 });
                    config.onUploadProgress({ loaded: 100, total: 100 });
                }
                return Promise.resolve(mockResponse);
            });

            await apiClient.uploadFile(mockFile, progressCallback);

            expect(progressCallback).toHaveBeenCalledWith({
                loaded: 50,
                total: 100,
                progress: 0.5
            });
            expect(progressCallback).toHaveBeenCalledWith({
                loaded: 100,
                total: 100,
                progress: 1.0
            });
        });

        it('should retry on network error', async () => {
            const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: { job_id: 'test-job-123' }
            };

            // Fail twice, then succeed
            mockAxiosInstance.post
                .mockRejectedValueOnce(new Error('Network error'))
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce(mockResponse);

            const result = await apiClient.uploadFile(mockFile);

            expect(result).toEqual(mockResponse.data);
            expect(mockAxiosInstance.post).toHaveBeenCalledTimes(3);
        });

        it('should not retry on client error (400)', async () => {
            const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
            const error = new Error('Bad request');
            error.response = { status: 400, data: { error: 'Invalid file' } };

            mockAxiosInstance.post.mockRejectedValue(error);

            await expect(apiClient.uploadFile(mockFile)).rejects.toThrow();
            expect(mockAxiosInstance.post).toHaveBeenCalledTimes(1);
        });
    });

    describe('getJobStatus', () => {
        it('should get job status successfully', async () => {
            const mockResponse = {
                data: {
                    job_id: 'test-job-123',
                    status: 'processing',
                    progress: 50
                }
            };

            mockAxiosInstance.get.mockResolvedValue(mockResponse);

            const result = await apiClient.getJobStatus('test-job-123');

            expect(result).toEqual(mockResponse.data);
            expect(mockAxiosInstance.get).toHaveBeenCalledWith('/convert/test-job-123/status');
        });

        it('should retry on server error', async () => {
            const mockResponse = {
                data: { job_id: 'test-job-123', status: 'processing' }
            };
            const error = new Error('Server error');
            error.response = { status: 500 };

            // Fail once, then succeed
            mockAxiosInstance.get
                .mockRejectedValueOnce(error)
                .mockResolvedValueOnce(mockResponse);

            const result = await apiClient.getJobStatus('test-job-123');

            expect(result).toEqual(mockResponse.data);
            expect(mockAxiosInstance.get).toHaveBeenCalledTimes(2);
        });
    });

    describe('getJobResult', () => {
        it('should get job result successfully', async () => {
            const mockResponse = {
                data: {
                    job_id: 'test-job-123',
                    status: 'completed',
                    result: {
                        blocks: []
                    }
                }
            };

            mockAxiosInstance.get.mockResolvedValue(mockResponse);

            const result = await apiClient.getJobResult('test-job-123');

            expect(result).toEqual(mockResponse.data);
            expect(mockAxiosInstance.get).toHaveBeenCalledWith('/convert/test-job-123/result');
        });
    });

    describe('healthCheck', () => {
        it('should perform health check', async () => {
            const mockResponse = {
                data: { status: 'healthy' }
            };

            mockAxiosInstance.get.mockResolvedValue(mockResponse);

            const result = await apiClient.healthCheck();

            expect(result).toEqual(mockResponse.data);
            expect(mockAxiosInstance.get).toHaveBeenCalledWith('/health');
        });
    });

    describe('error handling', () => {
        it('should handle response errors with user-friendly messages', () => {
            const error = new Error('Test error');
            error.response = {
                status: 400,
                data: { error: 'Invalid input' }
            };

            const handledError = apiClient.handleResponseError(error);

            expect(handledError).rejects.toHaveProperty('userMessage');
        });

        it('should handle network errors', () => {
            const error = new Error('Network error');
            error.request = {};

            const handledError = apiClient.handleResponseError(error);

            expect(handledError).rejects.toHaveProperty('userMessage');
        });
    });
});
