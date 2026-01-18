/**
 * Unit tests for DocumentProcessor service
 */
import { DocumentProcessor } from '../services/DocumentProcessor.js';

// Mock axios
jest.mock('axios');
import axios from 'axios';
const mockedAxios = axios;

describe('DocumentProcessor', () => {
    let processor;

    beforeEach(() => {
        processor = new DocumentProcessor();
        jest.clearAllMocks();
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    describe('validateFile', () => {
        test('should accept valid PDF file', () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            Object.defineProperty(file, 'size', { value: 1024 });

            const result = processor.validateFile(file);

            expect(result.valid).toBe(true);
        });

        test('should accept valid JPG file', () => {
            const file = new File(['content'], 'test.jpg', { type: 'image/jpeg' });
            Object.defineProperty(file, 'size', { value: 1024 });

            const result = processor.validateFile(file);

            expect(result.valid).toBe(true);
        });

        test('should accept valid PNG file', () => {
            const file = new File(['content'], 'test.png', { type: 'image/png' });
            Object.defineProperty(file, 'size', { value: 1024 });

            const result = processor.validateFile(file);

            expect(result.valid).toBe(true);
        });

        test('should reject invalid file type', () => {
            const file = new File(['content'], 'test.txt', { type: 'text/plain' });
            Object.defineProperty(file, 'size', { value: 1024 });

            const result = processor.validateFile(file);

            expect(result.valid).toBe(false);
            expect(result.error).toContain('Unsupported file type');
        });

        test('should reject oversized file', () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            Object.defineProperty(file, 'size', { value: 11 * 1024 * 1024 }); // 11MB

            const result = processor.validateFile(file);

            expect(result.valid).toBe(false);
            expect(result.error).toContain('File size exceeds 10MB limit');
        });
    });

    describe('uploadFile', () => {
        test('should upload file successfully', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: { 
                    job_id: 'test-job-123',
                    message: 'File uploaded successfully'
                }
            };

            mockedAxios.post.mockResolvedValue(mockResponse);

            const result = await processor.uploadFile(file);

            expect(result.success).toBe(true);
            expect(result.jobId).toBe('test-job-123');
            expect(mockedAxios.post).toHaveBeenCalledWith(
                '/api/convert',
                expect.any(FormData),
                expect.objectContaining({
                    headers: { 'Content-Type': 'multipart/form-data' }
                })
            );
        });

        test('should track upload progress', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: { job_id: 'test-job-123' }
            };
            const progressCallback = jest.fn();

            processor.setProgressCallback(progressCallback);

            mockedAxios.post.mockImplementation((url, data, config) => {
                // Simulate progress
                if (config.onUploadProgress) {
                    config.onUploadProgress({ loaded: 50, total: 100 });
                }
                return Promise.resolve(mockResponse);
            });

            await processor.uploadFile(file);

            expect(progressCallback).toHaveBeenCalledWith(
                expect.objectContaining({
                    stage: 'upload',
                    progress: 0.5
                })
            );
        });

        test('should handle upload failure', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockError = {
                response: { data: { message: 'Upload failed' } }
            };

            mockedAxios.post.mockRejectedValue(mockError);

            const result = await processor.uploadFile(file);

            expect(result.success).toBe(false);
            expect(result.error).toBe('Upload failed');
        });
    });

    describe('uploadFileWithRetry', () => {
        test('should retry on network error', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: { job_id: 'test-job-123' }
            };

            // Fail twice, then succeed
            mockedAxios.post
                .mockRejectedValueOnce(new Error('Network error'))
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce(mockResponse);

            const resultPromise = processor.uploadFileWithRetry(file);
            
            // Fast-forward through retry delays
            await jest.runAllTimersAsync();
            
            const result = await resultPromise;

            expect(result.success).toBe(true);
            expect(mockedAxios.post).toHaveBeenCalledTimes(3);
        });

        test('should not retry on validation error', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockError = {
                response: { 
                    data: { error: 'Unsupported file type' } 
                }
            };

            mockedAxios.post.mockRejectedValue(mockError);

            const result = await processor.uploadFileWithRetry(file);

            expect(result.success).toBe(false);
            expect(mockedAxios.post).toHaveBeenCalledTimes(1);
        });

        test('should fail after max retries', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });

            mockedAxios.post.mockRejectedValue(new Error('Network error'));

            const resultPromise = processor.uploadFileWithRetry(file);
            
            // Fast-forward through all retry delays
            await jest.runAllTimersAsync();
            
            const result = await resultPromise;

            expect(result.success).toBe(false);
            expect(result.error).toContain('Upload failed after 3 attempts');
            expect(mockedAxios.post).toHaveBeenCalledTimes(3);
        });
    });

    describe('getStatus', () => {
        test('should get status successfully', async () => {
            const mockResponse = {
                data: {
                    status: 'processing',
                    progress: 50,
                    message: 'Processing document'
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const result = await processor.getStatus('test-job-123');

            expect(result.status).toBe('processing');
            expect(result.progress).toBe(50);
        });

        test('should retry on network error', async () => {
            const mockResponse = {
                data: { status: 'processing' }
            };

            // Fail once, then succeed
            mockedAxios.get
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce(mockResponse);

            const resultPromise = processor.getStatus('test-job-123');
            
            // Fast-forward through retry delay
            await jest.runAllTimersAsync();
            
            const result = await resultPromise;

            expect(result.status).toBe('processing');
            expect(mockedAxios.get).toHaveBeenCalledTimes(2);
        });

        test('should not retry on 404 error', async () => {
            const mockError = {
                response: { status: 404 }
            };

            mockedAxios.get.mockRejectedValue(mockError);

            const result = await processor.getStatus('test-job-123');

            expect(result.status).toBe('error');
            expect(result.error).toBe('Job not found');
            expect(mockedAxios.get).toHaveBeenCalledTimes(1);
        });
    });

    describe('getResult', () => {
        test('should get result successfully', async () => {
            const mockResponse = {
                data: {
                    result: {
                        blocks: []
                    },
                    confidence_report: {
                        overall: { score: 0.85 }
                    }
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const result = await processor.getResult('test-job-123');

            expect(result.success).toBe(true);
            expect(result.data).toHaveProperty('confidence_report');
        });

        test('should retry on server error', async () => {
            const mockResponse = {
                data: {
                    result: { blocks: [] }
                }
            };
            const mockError = {
                response: { status: 500 }
            };

            // Fail once, then succeed
            mockedAxios.get
                .mockRejectedValueOnce(mockError)
                .mockResolvedValueOnce(mockResponse);

            const resultPromise = processor.getResult('test-job-123');
            
            // Fast-forward through retry delay
            await jest.runAllTimersAsync();
            
            const result = await resultPromise;

            expect(result.success).toBe(true);
            expect(mockedAxios.get).toHaveBeenCalledTimes(2);
        });
    });

    describe('processFile', () => {
        test('should process file successfully', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            Object.defineProperty(file, 'size', { value: 1024 });
            
            const mockResponse = {
                data: { 
                    job_id: 'test-job-123',
                    message: 'File uploaded successfully'
                }
            };

            mockedAxios.post.mockResolvedValue(mockResponse);

            const result = await processor.processFile(file);

            expect(result.success).toBe(true);
            expect(result.jobId).toBe('test-job-123');
        });

        test('should return validation error', async () => {
            const file = new File(['content'], 'test.txt', { type: 'text/plain' });
            Object.defineProperty(file, 'size', { value: 1024 });

            const result = await processor.processFile(file);

            expect(result.success).toBe(false);
            expect(result.error).toContain('Unsupported file type');
        });
    });

    describe('error handling', () => {
        test('should extract error message from response', () => {
            const error = {
                response: {
                    data: { error: 'Test error message' }
                }
            };

            const message = processor.extractErrorMessage(error);

            expect(message).toBe('Test error message');
        });

        test('should identify validation errors', () => {
            expect(processor.isValidationError('Unsupported file type')).toBe(true);
            expect(processor.isValidationError('File size exceeds limit')).toBe(true);
            expect(processor.isValidationError('Network error')).toBe(false);
        });
    });
});
