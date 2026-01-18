/**
 * Document processing service for handling file uploads and API communication
 * Implements comprehensive error handling, progress tracking, and retry mechanisms
 */
import axios from 'axios';
import { StatusPoller } from './StatusPoller.js';

export class DocumentProcessor {
    constructor() {
        this.baseURL = '/api';
        this.supportedTypes = ['application/pdf', 'image/jpeg', 'image/png'];
        this.maxFileSize = 10 * 1024 * 1024; // 10MB
        this.maxRetries = 3;
        this.retryDelay = 1000; // Initial retry delay in ms
        this.pollingInterval = 2000; // Status polling interval in ms
        this.maxPollingAttempts = 150; // 5 minutes with 2-second intervals
        this.progressCallback = null;
        this.statusCallback = null;
        
        // Create status poller
        this.statusPoller = new StatusPoller(this, {
            pollingInterval: this.pollingInterval,
            maxPollingAttempts: this.maxPollingAttempts,
            timeoutDuration: 300000, // 5 minutes
            maxConsecutiveErrors: 3
        });
    }

    /**
     * Set progress callback for upload tracking
     * @param {Function} callback - Progress callback function
     */
    setProgressCallback(callback) {
        this.progressCallback = callback;
    }

    /**
     * Set status callback for processing updates
     * @param {Function} callback - Status callback function
     */
    setStatusCallback(callback) {
        this.statusCallback = callback;
    }

    /**
     * Process uploaded file through the conversion pipeline
     * @param {File} file - The uploaded file
     * @returns {Promise<Object>} Processing result with job ID
     */
    async processFile(file) {
        try {
            // Validate file
            const validation = this.validateFile(file);
            if (!validation.valid) {
                return { success: false, error: validation.error };
            }

            // Upload file and start processing with retry logic
            const uploadResult = await this.uploadFileWithRetry(file);
            if (!uploadResult.success) {
                return uploadResult;
            }

            // Return job ID for status polling
            return {
                success: true,
                jobId: uploadResult.jobId,
                message: uploadResult.message,
                notification: uploadResult.notification
            };

        } catch (error) {
            return { 
                success: false, 
                error: this.formatErrorMessage(error)
            };
        }
    }

    /**
     * Validate file type and size
     * @param {File} file - File to validate
     * @returns {Object} Validation result
     */
    validateFile(file) {
        if (!this.supportedTypes.includes(file.type)) {
            return {
                valid: false,
                error: 'Unsupported file type. Please upload PDF, JPG, or PNG files.'
            };
        }

        if (file.size > this.maxFileSize) {
            return {
                valid: false,
                error: 'File size exceeds 10MB limit.'
            };
        }

        return { valid: true };
    }

    /**
     * Upload file to backend with progress tracking
     * @param {File} file - File to upload
     * @returns {Promise<Object>} Upload result
     */
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axios.post(`${this.baseURL}/convert`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                onUploadProgress: (progressEvent) => {
                    if (this.progressCallback && progressEvent.total) {
                        const percentCompleted = progressEvent.loaded / progressEvent.total;
                        this.progressCallback({
                            stage: 'upload',
                            progress: percentCompleted,
                            loaded: progressEvent.loaded,
                            total: progressEvent.total,
                            message: `Uploading: ${Math.round(percentCompleted * 100)}%`
                        });
                    }
                }
            });

            return {
                success: true,
                jobId: response.data.job_id,
                message: response.data.message,
                notification: response.data.notification
            };
        } catch (error) {
            return {
                success: false,
                error: this.extractErrorMessage(error)
            };
        }
    }

    /**
     * Upload file with automatic retry on failure
     * @param {File} file - File to upload
     * @returns {Promise<Object>} Upload result
     */
    async uploadFileWithRetry(file) {
        let lastError = null;
        
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                const result = await this.uploadFile(file);
                
                if (result.success) {
                    return result;
                }
                
                // If it's a validation error, don't retry
                if (this.isValidationError(result.error)) {
                    return result;
                }
                
                lastError = result.error;
                
                // Wait before retrying (exponential backoff)
                if (attempt < this.maxRetries - 1) {
                    const delay = this.retryDelay * Math.pow(2, attempt);
                    await this.sleep(delay);
                }
                
            } catch (error) {
                lastError = this.formatErrorMessage(error);
                
                // Wait before retrying
                if (attempt < this.maxRetries - 1) {
                    const delay = this.retryDelay * Math.pow(2, attempt);
                    await this.sleep(delay);
                }
            }
        }
        
        return {
            success: false,
            error: `Upload failed after ${this.maxRetries} attempts: ${lastError}`
        };
    }

    /**
     * Poll for processing completion with status updates using StatusPoller
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>} Final result
     */
    async pollForCompletion(jobId) {
        return new Promise((resolve, reject) => {
            this.statusPoller.startPolling(jobId, {
                onStatusUpdate: (statusData) => {
                    // Notify status callback if provided
                    if (this.statusCallback) {
                        this.statusCallback(statusData);
                    }
                },
                onProgress: (progressInfo) => {
                    // Notify progress callback if provided
                    if (this.progressCallback) {
                        this.progressCallback({
                            stage: 'processing',
                            progress: progressInfo.progress,
                            message: progressInfo.message
                        });
                    }
                },
                onComplete: async (statusData) => {
                    try {
                        // Get final result
                        const result = await this.getResult(jobId);
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                },
                onError: (errorMessage) => {
                    resolve({
                        success: false,
                        error: errorMessage
                    });
                },
                onTimeout: (timeoutMessage) => {
                    resolve({
                        success: false,
                        error: timeoutMessage
                    });
                }
            });
        });
    }

    /**
     * Stop polling for status updates
     */
    stopPolling() {
        this.statusPoller.stopPolling();
    }

    /**
     * Get current polling state
     * @returns {Object}
     */
    getPollingState() {
        return this.statusPoller.getState();
    }

    /**
     * Get processing status for a job with retry logic
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>} Status information
     */
    async getStatus(jobId) {
        let lastError = null;
        
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                const response = await axios.get(`${this.baseURL}/convert/${jobId}/status`);
                return response.data;
            } catch (error) {
                lastError = error;
                
                // If it's a 404, the job doesn't exist - don't retry
                if (error.response?.status === 404) {
                    return {
                        status: 'error',
                        error: 'Job not found',
                        progress: 0
                    };
                }
                
                // Wait before retrying
                if (attempt < this.maxRetries - 1) {
                    await this.sleep(this.retryDelay * Math.pow(2, attempt));
                }
            }
        }
        
        console.error('Failed to get status after retries:', lastError);
        return {
            status: 'error',
            error: this.extractErrorMessage(lastError) || 'Failed to get status',
            progress: 0
        };
    }

    /**
     * Alias for getStatus - used by StatusPoller
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>} Status information
     */
    async getJobStatus(jobId) {
        return this.getStatus(jobId);
    }

    /**
     * Get conversion result for a job with retry logic
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>} Conversion result
     */
    async getResult(jobId) {
        let lastError = null;
        
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                const response = await axios.get(`${this.baseURL}/convert/${jobId}/result`);
                const data = response.data;

                return {
                    success: true,
                    data: {
                        ...data.result,
                        confidence_report: data.confidence_report
                    }
                };
            } catch (error) {
                lastError = error;
                
                // If it's a 404, the result doesn't exist - don't retry
                if (error.response?.status === 404) {
                    return {
                        success: false,
                        error: 'Result not found'
                    };
                }
                
                // Wait before retrying
                if (attempt < this.maxRetries - 1) {
                    await this.sleep(this.retryDelay * Math.pow(2, attempt));
                }
            }
        }
        
        console.error('Failed to get result after retries:', lastError);
        return {
            success: false,
            error: this.extractErrorMessage(lastError) || 'Failed to get result'
        };
    }

    /**
     * Extract user-friendly error message from error object
     * @param {Error} error - Error object
     * @returns {string} Error message
     */
    extractErrorMessage(error) {
        if (error.response?.data?.error) {
            return error.response.data.error;
        }
        if (error.response?.data?.message) {
            return error.response.data.message;
        }
        if (error.message) {
            return error.message;
        }
        return 'An unexpected error occurred';
    }

    /**
     * Format error message for display
     * @param {Error|string} error - Error object or message
     * @returns {string} Formatted error message
     */
    formatErrorMessage(error) {
        if (typeof error === 'string') {
            return error;
        }
        return this.extractErrorMessage(error);
    }

    /**
     * Check if error is a validation error (should not retry)
     * @param {string} errorMessage - Error message
     * @returns {boolean} True if validation error
     */
    isValidationError(errorMessage) {
        const validationKeywords = [
            'unsupported file type',
            'file size exceeds',
            'invalid file',
            'no file provided',
            'file type',
            'size limit'
        ];
        
        const lowerMessage = errorMessage.toLowerCase();
        return validationKeywords.some(keyword => lowerMessage.includes(keyword));
    }

    /**
     * Sleep utility for delays
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}