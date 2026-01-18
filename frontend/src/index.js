/**
 * Enhanced main application entry point with complete end-to-end workflow
 * Connects frontend upload to backend processing pipeline and Editor.js rendering
 */
import { DocumentProcessor } from './services/DocumentProcessor.js';
import { EditorManager } from './services/EditorManager.js';
import { UIManager } from './services/UIManager.js';

class App {
    constructor() {
        this.documentProcessor = new DocumentProcessor();
        this.editorManager = new EditorManager();
        this.uiManager = new UIManager();
        this.currentJobId = null;
        this.pollingInterval = null;
        this.isProcessing = false;
        this.init();
    }

    init() {
        this.uiManager.initialize();
        this.initializeEditor();
        this.setupProcessorCallbacks();
        this.setupKeyboardShortcuts();
        console.log('PDF to Editable Web Layout System initialized');
        console.log('Ready to accept PDF, JPG, or PNG files (max 10MB)');
    }

    /**
     * Setup callbacks for document processor
     */
    setupProcessorCallbacks() {
        // Set progress callback for upload tracking
        this.documentProcessor.setProgressCallback((progressInfo) => {
            this.handleUploadProgress(progressInfo);
        });

        // Set status callback for processing updates
        this.documentProcessor.setStatusCallback((statusInfo) => {
            this.handleStatusUpdate(statusInfo);
        });
    }

    /**
     * Setup keyboard shortcuts for better UX
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + S to save current content
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.saveCurrentContent();
            }
            
            // Escape to cancel current operation
            if (e.key === 'Escape' && this.isProcessing) {
                this.cancelProcessing();
            }
        });
    }

    /**
     * Handle upload progress updates
     * @param {Object} progressInfo - Progress information
     */
    handleUploadProgress(progressInfo) {
        const { progress, message } = progressInfo;
        this.uiManager.showProgress(progress, message);
    }

    /**
     * Handle processing status updates
     * @param {Object} statusInfo - Status information
     */
    handleStatusUpdate(statusInfo) {
        const { status, progress, message, stage, estimated_remaining_seconds } = statusInfo;
        
        // Build status message with stage information
        let statusMessage = message || `Processing: ${status}`;
        
        // Add estimated time remaining if available
        if (estimated_remaining_seconds !== undefined && estimated_remaining_seconds > 0) {
            const minutes = Math.floor(estimated_remaining_seconds / 60);
            const seconds = estimated_remaining_seconds % 60;
            
            if (minutes > 0) {
                statusMessage += ` (Est. ${minutes}m ${seconds}s remaining)`;
            } else {
                statusMessage += ` (Est. ${seconds}s remaining)`;
            }
        }
        
        // Update UI with current status
        if (progress !== undefined) {
            // Progress is in percentage (0-100)
            const progressDecimal = progress / 100;
            this.uiManager.showProgress(progressDecimal, statusMessage);
        } else {
            this.uiManager.showProcessing(statusMessage);
        }
        
        // Log status for debugging
        console.log('Processing status:', { 
            status, 
            progress, 
            stage, 
            message,
            estimated_remaining_seconds 
        });
    }

    /**
     * Handle file upload with comprehensive error handling
     * Implements complete workflow: upload -> OCR processing -> Editor.js rendering
     * @param {File} file - File to upload
     */
    async handleFileUpload(file) {
        if (this.isProcessing) {
            this.uiManager.showStatus('A document is already being processed. Please wait.', 'warning');
            return;
        }

        try {
            this.isProcessing = true;
            this.uiManager.showProcessing('Preparing upload...');
            
            // Process file (upload and get job ID)
            const result = await this.documentProcessor.processFile(file);
            
            if (result.success) {
                this.currentJobId = result.jobId;
                
                // Show notification if provided (e.g., multi-page PDF warning)
                if (result.notification) {
                    this.uiManager.showStatus(result.notification, 'info');
                }
                
                // Start polling for processing status
                await this.startStatusPolling(result.jobId);
            } else {
                this.isProcessing = false;
                this.uiManager.showError(result.error);
            }
        } catch (error) {
            this.isProcessing = false;
            console.error('File upload error:', error);
            this.uiManager.showError(`Upload failed: ${error.message || 'Unknown error'}`);
        }
    }

    /**
     * Start polling for processing status
     * Monitors OCR processing and triggers Editor.js rendering on completion
     * @param {string} jobId - Job identifier
     */
    async startStatusPolling(jobId) {
        try {
            this.uiManager.showProcessing('Processing document with OCR...');
            
            // Poll for completion
            const result = await this.documentProcessor.pollForCompletion(jobId);
            
            if (result.success) {
                await this.handleProcessingComplete(result.data);
            } else {
                // Check if it's a timeout error
                if (result.error && result.error.toLowerCase().includes('timeout')) {
                    this.uiManager.showTimeout(result.error);
                } else {
                    this.uiManager.showError(result.error);
                }
            }
        } catch (error) {
            console.error('Status polling error:', error);
            
            // Check if it's a timeout error
            if (error.message && error.message.toLowerCase().includes('timeout')) {
                this.uiManager.showTimeout(error.message);
            } else {
                this.uiManager.showError(`Processing failed: ${error.message || 'Unknown error'}`);
            }
        } finally {
            this.isProcessing = false;
        }
    }

    /**
     * Handle processing completion - integrate OCR results with Editor.js
     * @param {Object} data - Conversion result data with Editor.js blocks
     */
    async handleProcessingComplete(data) {
        try {
            this.uiManager.showProcessing('Loading converted content into editor...');
            
            // Load content into Editor.js
            await this.editorManager.loadContent(data);
            
            // Show editor section
            this.uiManager.showEditor();
            this.uiManager.showSuccess('Document converted successfully! You can now edit the content.');
            
            // Show confidence report if available
            if (data.confidence_report) {
                this.showConfidenceReport(data.confidence_report);
            }
            
            // Log successful conversion
            console.log('Document conversion complete:', {
                blocksCount: data.blocks?.length || 0,
                hasConfidenceReport: !!data.confidence_report
            });
        } catch (error) {
            console.error('Result loading error:', error);
            this.uiManager.showError(`Failed to load result: ${error.message || 'Unknown error'}`);
        }
    }

    /**
     * Show confidence report for conversion results
     * @param {Object} confidenceReport - Confidence report data
     */
    showConfidenceReport(confidenceReport) {
        if (!confidenceReport || !confidenceReport.confidence_breakdown) {
            return;
        }

        const reportDiv = document.createElement('div');
        reportDiv.id = 'confidenceReport';
        reportDiv.style.cssText = `
            margin-top: 20px;
            padding: 15px;
            background: #f0f9ff;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        `;

        const breakdown = confidenceReport.confidence_breakdown;
        const overall = breakdown.overall;

        let html = `
            <h4 style="margin: 0 0 10px 0; color: #2c3e50;">
                Processing Confidence: ${overall.score.toFixed(2)} (${overall.level})
            </h4>
            <p style="margin: 0 0 10px 0; color: #666;">${overall.description}</p>
        `;

        if (confidenceReport.warnings && confidenceReport.warnings.length > 0) {
            html += `
                <div style="margin-top: 10px;">
                    <strong style="color: #e67e22;">⚠️ Warnings:</strong>
                    <ul style="margin: 5px 0 0 20px; color: #666;">
                        ${confidenceReport.warnings.map(w => `
                            <li>${w.message}</li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        reportDiv.innerHTML = html;

        const editorSection = document.querySelector('.editor-section');
        if (editorSection) {
            // Remove existing report if present
            const existingReport = document.getElementById('confidenceReport');
            if (existingReport) {
                existingReport.remove();
            }
            
            editorSection.insertBefore(reportDiv, editorSection.firstChild);
        }
    }

    /**
     * Initialize editor
     */
    initializeEditor() {
        this.editorManager.initialize();
    }

    /**
     * Save current editor content
     * @returns {Promise<Object|null>} Saved content or null
     */
    async saveCurrentContent() {
        try {
            const content = await this.editorManager.getContent();
            if (content) {
                console.log('Content saved:', content);
                this.uiManager.showSuccess('Content saved successfully!');
                return content;
            }
        } catch (error) {
            console.error('Failed to save content:', error);
            this.uiManager.showError('Failed to save content');
        }
        return null;
    }

    /**
     * Cancel current processing operation
     */
    cancelProcessing() {
        if (this.isProcessing) {
            this.documentProcessor.stopPolling();
            this.isProcessing = false;
            this.currentJobId = null;
            this.uiManager.showStatus('Processing cancelled', 'info');
            this.uiManager.hideProgress();
            console.log('Processing cancelled by user');
        }
    }

    /**
     * Get current editor content for export
     * @returns {Promise<Object|null>} Editor content
     */
    async getEditorContent() {
        return await this.editorManager.getContent();
    }

    /**
     * Check if editor has unsaved changes
     * @returns {boolean} True if there are unsaved changes
     */
    hasUnsavedChanges() {
        return this.editorManager.hasUnsavedChanges();
    }

    /**
     * Reset application state
     */
    reset() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }

        this.currentJobId = null;
        this.isProcessing = false;
        this.uiManager.reset();
        this.editorManager.clearContent();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
