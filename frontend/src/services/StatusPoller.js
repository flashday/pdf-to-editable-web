/**
 * Status Poller Service for real-time status updates
 * Implements polling with timeout handling and retry mechanisms
 */

export class StatusPoller {
    constructor(apiClient, options = {}) {
        this.apiClient = apiClient;
        
        // Configuration options
        this.pollingInterval = options.pollingInterval || 2000; // 2 seconds
        this.maxPollingAttempts = options.maxPollingAttempts || 150; // 5 minutes
        this.timeoutDuration = options.timeoutDuration || 300000; // 5 minutes
        this.retryOnError = options.retryOnError !== false; // Default true
        this.maxConsecutiveErrors = options.maxConsecutiveErrors || 3;
        
        // State
        this.isPolling = false;
        this.pollingTimer = null;
        this.currentJobId = null;
        this.pollingAttempts = 0;
        this.consecutiveErrors = 0;
        this.startTime = null;
        
        // Callbacks
        this.onStatusUpdate = null;
        this.onComplete = null;
        this.onError = null;
        this.onTimeout = null;
        this.onProgress = null;
    }

    /**
     * Start polling for job status
     * @param {string} jobId - Job identifier
     * @param {Object} callbacks - Callback functions
     * @returns {Promise<void>}
     */
    async startPolling(jobId, callbacks = {}) {
        // Stop any existing polling
        this.stopPolling();
        
        // Set callbacks
        this.onStatusUpdate = callbacks.onStatusUpdate || null;
        this.onComplete = callbacks.onComplete || null;
        this.onError = callbacks.onError || null;
        this.onTimeout = callbacks.onTimeout || null;
        this.onProgress = callbacks.onProgress || null;
        
        // Initialize state
        this.currentJobId = jobId;
        this.isPolling = true;
        this.pollingAttempts = 0;
        this.consecutiveErrors = 0;
        this.startTime = Date.now();
        
        // Start polling loop
        await this.pollStatus();
    }

    /**
     * Stop polling
     */
    stopPolling() {
        this.isPolling = false;
        
        if (this.pollingTimer) {
            clearTimeout(this.pollingTimer);
            this.pollingTimer = null;
        }
        
        this.currentJobId = null;
        this.pollingAttempts = 0;
        this.consecutiveErrors = 0;
        this.startTime = null;
    }

    /**
     * Poll for status update
     * @private
     */
    async pollStatus() {
        if (!this.isPolling || !this.currentJobId) {
            return;
        }
        
        // Check for timeout
        if (this.hasTimedOut()) {
            this.handleTimeout();
            return;
        }
        
        // Check for max attempts
        if (this.pollingAttempts >= this.maxPollingAttempts) {
            this.handleTimeout();
            return;
        }
        
        this.pollingAttempts++;
        
        try {
            // Get status from API
            const statusData = await this.apiClient.getJobStatus(this.currentJobId);
            
            // Reset consecutive errors on success
            this.consecutiveErrors = 0;
            
            // Process status update
            await this.processStatusUpdate(statusData);
            
        } catch (error) {
            this.handlePollingError(error);
        }
    }

    /**
     * Process status update
     * @param {Object} statusData - Status data from API
     * @private
     */
    async processStatusUpdate(statusData) {
        const { status, progress, message, completed, failed, error } = statusData;
        
        // Notify status update callback
        if (this.onStatusUpdate) {
            this.onStatusUpdate(statusData);
        }
        
        // Notify progress callback
        if (this.onProgress && progress !== undefined) {
            this.onProgress({
                progress: progress,
                message: message,
                stage: status
            });
        }
        
        // Check for completion
        if (completed) {
            this.handleCompletion(statusData);
            return;
        }
        
        // Check for failure
        if (failed) {
            this.handleFailure(error || 'Processing failed');
            return;
        }
        
        // Continue polling
        this.scheduleNextPoll();
    }

    /**
     * Handle polling error
     * @param {Error} error - Error object
     * @private
     */
    handlePollingError(error) {
        this.consecutiveErrors++;
        
        console.error(`Status polling error (attempt ${this.consecutiveErrors}):`, error);
        
        // Check if we should stop retrying
        if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
            this.handleFailure(
                `Failed to get status after ${this.maxConsecutiveErrors} consecutive errors: ${error.message}`
            );
            return;
        }
        
        // Continue polling with exponential backoff
        const backoffDelay = this.pollingInterval * Math.pow(1.5, this.consecutiveErrors - 1);
        this.scheduleNextPoll(backoffDelay);
    }

    /**
     * Schedule next poll
     * @param {number} delay - Delay in milliseconds (optional)
     * @private
     */
    scheduleNextPoll(delay = this.pollingInterval) {
        if (!this.isPolling) {
            return;
        }
        
        this.pollingTimer = setTimeout(() => {
            this.pollStatus();
        }, delay);
    }

    /**
     * Handle completion
     * @param {Object} statusData - Final status data
     * @private
     */
    handleCompletion(statusData) {
        this.stopPolling();
        
        if (this.onComplete) {
            this.onComplete(statusData);
        }
    }

    /**
     * Handle failure
     * @param {string} errorMessage - Error message
     * @private
     */
    handleFailure(errorMessage) {
        this.stopPolling();
        
        if (this.onError) {
            this.onError(errorMessage);
        }
    }

    /**
     * Handle timeout
     * @private
     */
    handleTimeout() {
        this.stopPolling();
        
        const elapsedTime = Date.now() - this.startTime;
        const timeoutMessage = `Processing timeout after ${Math.round(elapsedTime / 1000)} seconds. ` +
                             `The operation took too long to complete.`;
        
        if (this.onTimeout) {
            this.onTimeout(timeoutMessage);
        } else if (this.onError) {
            this.onError(timeoutMessage);
        }
    }

    /**
     * Check if polling has timed out
     * @returns {boolean}
     * @private
     */
    hasTimedOut() {
        if (!this.startTime) {
            return false;
        }
        
        const elapsedTime = Date.now() - this.startTime;
        return elapsedTime >= this.timeoutDuration;
    }

    /**
     * Get current polling state
     * @returns {Object}
     */
    getState() {
        return {
            isPolling: this.isPolling,
            jobId: this.currentJobId,
            attempts: this.pollingAttempts,
            consecutiveErrors: this.consecutiveErrors,
            elapsedTime: this.startTime ? Date.now() - this.startTime : 0
        };
    }

    /**
     * Reset poller state
     */
    reset() {
        this.stopPolling();
    }
}
