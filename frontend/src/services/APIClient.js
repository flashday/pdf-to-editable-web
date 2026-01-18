/**
 * API Client for backend communication
 * Provides centralized API communication with error handling and retry logic
 */
import axios from 'axios';

export class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.timeout = 30000; // 30 seconds
        
        // Create axios instance with default config
        this.client = axios.create({
            baseURL: this.baseURL,
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // Add response interceptor for error handling
        this.client.interceptors.response.use(
            response => response,
            error => this.handleResponseError(error)
        );
    }

    /**
     * Handle response errors with user-friendly messages
     * @param {Error} error - Axios error object
     * @returns {Promise<never>}
     */
    handleResponseError(error) {
        if (error.response) {
            // Server responded with error status
            const status = error.response.status;
            const data = error.response.data;
            
            let message = data.error || data.message || 'An error occurred';
            
            // Add context based on status code
            if (status === 400) {
                message = `Invalid request: ${message}`;
            } else if (status === 404) {
                message = `Not found: ${message}`;
            } else if (status === 413) {
                message = `File too large: ${message}`;
            } else if (status === 422) {
                message = `Validation error: ${message}`;
            } else if (status === 500) {
                message = `Server error: ${message}`;
            } else if (status === 503) {
                message = `Service unavailable: ${message}`;
            }
            
            error.userMessage = message;
        } else if (error.request) {
            // Request made but no response received
            error.userMessage = 'Network error: Unable to reach the server. Please check your connection.';
        } else {
            // Error in request setup
            error.userMessage = `Request error: ${error.message}`;
        }
        
        return Promise.reject(error);
    }

    /**
     * Execute request with retry logic
     * @param {Function} requestFn - Request function to execute
     * @param {number} retries - Number of retries remaining
     * @returns {Promise<any>}
     */
    async executeWithRetry(requestFn, retries = this.maxRetries) {
        try {
            return await requestFn();
        } catch (error) {
            // Don't retry on client errors (4xx)
            if (error.response && error.response.status >= 400 && error.response.status < 500) {
                throw error;
            }
            
            // Retry on network errors or server errors (5xx)
            if (retries > 0) {
                const delay = this.retryDelay * Math.pow(2, this.maxRetries - retries);
                await this.sleep(delay);
                return this.executeWithRetry(requestFn, retries - 1);
            }
            
            throw error;
        }
    }

    /**
     * Upload file with progress tracking
     * @param {File} file - File to upload
     * @param {Function} onProgress - Progress callback
     * @returns {Promise<Object>}
     */
    async uploadFile(file, onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);

        return this.executeWithRetry(async () => {
            const response = await this.client.post('/convert', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                onUploadProgress: (progressEvent) => {
                    if (onProgress && progressEvent.total) {
                        const percentCompleted = progressEvent.loaded / progressEvent.total;
                        onProgress({
                            loaded: progressEvent.loaded,
                            total: progressEvent.total,
                            progress: percentCompleted
                        });
                    }
                }
            });
            
            return response.data;
        });
    }

    /**
     * Get job status
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>}
     */
    async getJobStatus(jobId) {
        return this.executeWithRetry(async () => {
            const response = await this.client.get(`/convert/${jobId}/status`);
            return response.data;
        });
    }

    /**
     * Get job result
     * @param {string} jobId - Job identifier
     * @returns {Promise<Object>}
     */
    async getJobResult(jobId) {
        return this.executeWithRetry(async () => {
            const response = await this.client.get(`/convert/${jobId}/result`);
            return response.data;
        });
    }

    /**
     * Health check
     * @returns {Promise<Object>}
     */
    async healthCheck() {
        const response = await this.client.get('/health');
        return response.data;
    }

    /**
     * Sleep utility
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
