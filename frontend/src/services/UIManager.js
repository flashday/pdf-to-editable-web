/**
 * Enhanced UI Manager for better user experience
 */
export class UIManager {
    constructor() {
        this.uploadArea = null;
        this.fileInput = null;
        this.statusDiv = null;
        this.editorSection = null;
        this.progressContainer = null;
        this.progressBar = null;
        this.progressText = null;
    }

    /**
     * Initialize UI components
     */
    initialize() {
        // Get DOM elements after DOM is ready
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.statusDiv = document.getElementById('status');
        this.editorSection = document.querySelector('.editor-section');
        
        console.log('UIManager initialize:', {
            uploadArea: !!this.uploadArea,
            fileInput: !!this.fileInput,
            statusDiv: !!this.statusDiv
        });
        
        this.createProgressIndicator();
        this.setupEventListeners();
    }

    /**
     * Create progress indicator for file processing
     */
    createProgressIndicator() {
        const progressContainer = document.createElement('div');
        progressContainer.id = 'progressContainer';
        progressContainer.style.cssText = `
            margin-top: 20px;
            display: none;
        `;

        const progressBar = document.createElement('div');
        progressBar.id = 'progressBar';
        progressBar.style.cssText = `
            width: 0%;
            height: 8px;
            background: linear-gradient(90deg, #3498db, #2980b9);
            border-radius: 4px;
            transition: width 0.3s ease;
        `;

        const progressText = document.createElement('div');
        progressText.id = 'progressText';
        progressText.style.cssText = `
            margin-top: 8px;
            font-size: 14px;
            color: #666;
            text-align: center;
        `;

        progressContainer.appendChild(progressBar);
        progressContainer.appendChild(progressText);

        this.progressContainer = progressContainer;
        this.progressBar = progressBar;
        this.progressText = progressText;

        this.uploadArea.parentNode.insertBefore(progressContainer, this.uploadArea.nextSibling);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        if (!this.uploadArea || !this.fileInput) {
            console.error('UIManager: uploadArea or fileInput not found!');
            return;
        }

        console.log('UIManager: Setting up event listeners');

        this.uploadArea.addEventListener('click', () => {
            console.log('Upload area clicked');
            this.fileInput.click();
        });

        this.fileInput.addEventListener('change', (e) => {
            console.log('File input changed');
            const file = e.target.files[0];
            if (file) {
                this.onFileSelected(file);
            }
        });

        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.uploadArea.classList.add('dragover');
        });

        this.uploadArea.addEventListener('dragleave', () => {
            this.uploadArea.classList.remove('dragover');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) {
                this.onFileSelected(file);
            }
        });
    }

    /**
     * Handle file selection
     */
    onFileSelected(file) {
        this.showFilePreview(file);
        this.showStatus(`Selected: ${file.name} (${this.formatFileSize(file.size)})`, 'info');
        
        // Trigger file upload through the app
        if (window.app && typeof window.app.handleFileUpload === 'function') {
            window.app.handleFileUpload(file);
        }
    }

    /**
     * Show file preview
     */
    showFilePreview(file) {
        const existingPreview = document.getElementById('filePreview');
        if (existingPreview) {
            existingPreview.remove();
        }

        const preview = document.createElement('div');
        preview.id = 'filePreview';
        preview.style.cssText = `
            margin-top: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        const icon = this.getFileIcon(file.type);
        const info = document.createElement('div');
        info.innerHTML = `
            <div style="font-weight: 500;">${file.name}</div>
            <div style="font-size: 12px; color: #666;">${this.formatFileSize(file.size)}</div>
        `;

        preview.appendChild(icon);
        preview.appendChild(info);

        this.uploadArea.parentNode.insertBefore(preview, this.uploadArea.nextSibling);
    }

    /**
     * Get file icon based on type
     */
    getFileIcon(type) {
        const icon = document.createElement('div');
        icon.style.cssText = `
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            border-radius: 4px;
        `;

        if (type === 'application/pdf') {
            icon.style.background = '#dc2626';
            icon.textContent = '📄';
        } else if (type.startsWith('image/')) {
            icon.style.background = '#2563eb';
            icon.textContent = '🖼️';
        } else {
            icon.style.background = '#6b7280';
            icon.textContent = '📄';
        }

        return icon;
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Show status message
     */
    showStatus(message, type = 'info') {
        if (!this.statusDiv) {
            return;
        }

        this.statusDiv.textContent = message;
        this.statusDiv.className = `status ${type}`;
        this.statusDiv.style.display = 'block';

        if (type === 'success') {
            setTimeout(() => {
                this.statusDiv.style.display = 'none';
            }, 5000);
        }
    }

    /**
     * Show progress
     */
    showProgress(progress, message) {
        if (!this.progressContainer) {
            return;
        }

        this.progressContainer.style.display = 'block';
        this.progressBar.style.width = `${progress * 100}%`;
        this.progressText.textContent = message || `${Math.round(progress * 100)}%`;
    }

    /**
     * Hide progress
     */
    hideProgress() {
        if (!this.progressContainer) {
            return;
        }

        this.progressContainer.style.display = 'none';
    }

    /**
     * Show editor section
     */
    showEditor() {
        if (this.editorSection) {
            this.editorSection.style.display = 'block';
        }
    }

    /**
     * Hide editor section
     */
    hideEditor() {
        if (this.editorSection) {
            this.editorSection.style.display = 'none';
        }
    }

    /**
     * Reset UI to initial state
     */
    reset() {
        this.hideProgress();
        this.hideEditor();
        
        const preview = document.getElementById('filePreview');
        if (preview) {
            preview.remove();
        }

        if (this.statusDiv) {
            this.statusDiv.style.display = 'none';
        }

        if (this.fileInput) {
            this.fileInput.value = '';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        this.showStatus(message, 'error');
        this.hideProgress();
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showStatus(message, 'success');
        this.hideProgress();
    }

    /**
     * Show processing message
     */
    showProcessing(message) {
        this.showStatus(message, 'processing');
    }
    
    /**
     * Show timeout message
     */
    showTimeout(message) {
        this.showStatus(message || 'Processing timeout. The operation took too long to complete.', 'error');
        this.hideProgress();
    }
    
    /**
     * Show retry message
     */
    showRetry(message, attemptNumber, maxAttempts) {
        const retryMessage = `${message} (Retry ${attemptNumber}/${maxAttempts})`;
        this.showStatus(retryMessage, 'warning');
    }
}
