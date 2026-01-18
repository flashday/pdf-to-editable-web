/**
 * Integration tests for API communication between frontend and backend
 */
import { DocumentProcessor } from '../services/DocumentProcessor.js';

// Mock axios
jest.mock('axios');
import axios from 'axios';
const mockedAxios = axios;

describe('DocumentProcessor API Integration', () => {
    let processor;

    beforeEach(() => {
        processor = new DocumentProcessor();
        jest.clearAllMocks();
    });

    describe('uploadFile API integration', () => {
        test('should upload file and return job ID', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockResponse = {
                data: {
                    job_id: 'test-job-123',
                    status: 'pending',
                    message: 'File uploaded successfully and queued for processing',
                    file_info: {
                        original_filename: 'test.pdf',
                        file_type: 'pdf',
                        file_size: 1024
                    }
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

        test('should handle API error responses', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const mockError = {
                response: {
                    data: {
                        error: 'File validation failed',
                        error_category: 'validation_error',
                        message: 'Invalid file format'
                    },
                    status: 400
                }
            };

            mockedAxios.post.mockRejectedValue(mockError);

            const result = await processor.uploadFile(file);

            expect(result.success).toBe(false);
            expect(result.error).toBe('File validation failed');
        });
    });

    describe('getStatus API integration', () => {
        test('should get processing status', async () => {
            const jobId = 'test-job-123';
            const mockResponse = {
                data: {
                    job_id: jobId,
                    status: 'processing',
                    progress: 50,
                    message: 'Processing document',
                    current_stage: 'ocr_processing',
                    stages_completed: 3,
                    total_stages: 7,
                    estimated_time_remaining: 120
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const status = await processor.getStatus(jobId);

            expect(status.job_id).toBe(jobId);
            expect(status.status).toBe('processing');
            expect(status.progress).toBe(50);
            expect(mockedAxios.get).toHaveBeenCalledWith(`/api/convert/${jobId}/status`);
        });

        test('should handle completed status', async () => {
            const jobId = 'test-job-123';
            const mockResponse = {
                data: {
                    job_id: jobId,
                    status: 'completed',
                    progress: 100,
                    message: 'Processing completed successfully',
                    current_stage: 'completed',
                    stages_completed: 7,
                    total_stages: 7
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const status = await processor.getStatus(jobId);

            expect(status.status).toBe('completed');
            expect(status.progress).toBe(100);
        });

        test('should handle failed status', async () => {
            const jobId = 'test-job-123';
            const mockResponse = {
                data: {
                    job_id: jobId,
                    status: 'failed',
                    progress: 30,
                    message: 'Processing failed',
                    error: 'OCR processing error: Unable to extract text from image'
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const status = await processor.getStatus(jobId);

            expect(status.status).toBe('failed');
            expect(status.error).toContain('OCR processing error');
        });

        test('should handle API errors', async () => {
            const jobId = 'test-job-123';
            const mockError = {
                response: {
                    data: {
                        error: 'Job not found',
                        message: 'Job not found'
                    },
                    status: 404
                }
            };

            mockedAxios.get.mockRejectedValue(mockError);

            const status = await processor.getStatus(jobId);

            expect(status.status).toBe('error');
            expect(status.error).toBe('Job not found');
        });
    });

    describe('getResult API integration', () => {
        test('should get conversion result with confidence report', async () => {
            const jobId = 'test-job-123';
            const mockResponse = {
                data: {
                    job_id: jobId,
                    status: 'completed',
                    result: {
                        time: 1234567890,
                        blocks: [
                            {
                                id: '1',
                                type: 'paragraph',
                                data: { text: 'Test paragraph' }
                            },
                            {
                                id: '2',
                                type: 'header',
                                data: { text: 'Test header', level: 2 }
                            }
                        ],
                        version: '2.28.2'
                    },
                    confidence_report: {
                        confidence_breakdown: {
                            overall: {
                                score: 0.85,
                                level: 'good',
                                description: 'Good - High accuracy with minimal errors'
                            },
                            text_recognition: {
                                score: 0.88,
                                level: 'good',
                                description: 'Good - High accuracy with minimal errors'
                            },
                            layout_detection: {
                                score: 0.82,
                                level: 'good',
                                description: 'Good - High accuracy with minimal errors'
                            }
                        },
                        warnings: [],
                        has_warnings: false,
                        warning_count: 0,
                        overall_assessment: 'Document processed successfully with good confidence.'
                    }
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const result = await processor.getResult(jobId);

            expect(result.success).toBe(true);
            expect(result.data.blocks).toHaveLength(2);
            expect(result.data.confidence_report).toBeDefined();
            expect(result.data.confidence_report.confidence_breakdown.overall.score).toBe(0.85);
            expect(mockedAxios.get).toHaveBeenCalledWith(`/api/convert/${jobId}/result`);
        });

        test('should handle result with warnings', async () => {
            const jobId = 'test-job-123';
            const mockResponse = {
                data: {
                    job_id: jobId,
                    status: 'completed',
                    result: {
                        time: 1234567890,
                        blocks: [],
                        version: '2.28.2'
                    },
                    confidence_report: {
                        confidence_breakdown: {
                            overall: {
                                score: 0.65,
                                level: 'moderate',
                                description: 'Moderate - Some inaccuracies may be present'
                            }
                        },
                        warnings: [
                            {
                                type: 'low_overall_confidence',
                                severity: 'medium',
                                message: 'Document conversion has moderate confidence.',
                                recommendation: 'Review the converted content for any errors.',
                                affected_areas: ['entire_document'],
                                confidence_score: 0.65
                            }
                        ],
                        has_warnings: true,
                        warning_count: 1,
                        overall_assessment: 'Document processed with moderate confidence.'
                    }
                }
            };

            mockedAxios.get.mockResolvedValue(mockResponse);

            const result = await processor.getResult(jobId);

            expect(result.success).toBe(true);
            expect(result.data.confidence_report.has_warnings).toBe(true);
            expect(result.data.confidence_report.warnings).toHaveLength(1);
            expect(result.data.confidence_report.warnings[0].type).toBe('low_overall_confidence');
        });

        test('should handle API errors', async () => {
            const jobId = 'test-job-123';
            const mockError = {
                response: {
                    data: {
                        error: 'Result not available',
                        message: 'Result not available'
                    },
                    status: 404
                }
            };

            mockedAxios.get.mockRejectedValue(mockError);

            const result = await processor.getResult(jobId);

            expect(result.success).toBe(false);
            expect(result.error).toBe('Result not found');
        });
    });

    describe('complete workflow integration', () => {
        test('should handle complete upload -> status -> result workflow', async () => {
            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            const jobId = 'test-job-123';

            // Mock upload
            const uploadResponse = {
                data: {
                    job_id: jobId,
                    status: 'pending',
                    message: 'File uploaded successfully'
                }
            };
            mockedAxios.post.mockResolvedValueOnce(uploadResponse);

            // Mock status check
            const statusResponse = {
                data: {
                    job_id: jobId,
                    status: 'completed',
                    progress: 100,
                    message: 'Processing completed'
                }
            };
            mockedAxios.get.mockResolvedValueOnce(statusResponse);

            // Mock result
            const resultResponse = {
                data: {
                    job_id: jobId,
                    status: 'completed',
                    result: {
                        time: 1234567890,
                        blocks: [],
                        version: '2.28.2'
                    },
                    confidence_report: {
                        confidence_breakdown: {
                            overall: { score: 0.85, level: 'good' }
                        },
                        warnings: [],
                        has_warnings: false
                    }
                }
            };
            mockedAxios.get.mockResolvedValueOnce(resultResponse);

            // Execute workflow
            const uploadResult = await processor.uploadFile(file);
            expect(uploadResult.success).toBe(true);
            expect(uploadResult.jobId).toBe(jobId);

            const status = await processor.getStatus(jobId);
            expect(status.status).toBe('completed');

            const result = await processor.getResult(jobId);
            expect(result.success).toBe(true);
            expect(result.data.confidence_report).toBeDefined();
        });
    });
});
