/**
 * Unit tests for UIManager service
 */
import { UIManager } from '../services/UIManager.js';

describe('UIManager', () => {
    let manager;
    let mockUploadArea;
    let mockFileInput;
    let mockStatusDiv;
    let mockEditorSection;

    beforeEach(() => {
        document.body.innerHTML = `
            <div id="uploadArea"></div>
            <input type="file" id="fileInput">
            <div id="status"></div>
            <div class="editor-section"></div>
        `;

        mockUploadArea = document.getElementById('uploadArea');
        mockFileInput = document.getElementById('fileInput');
        mockStatusDiv = document.getElementById('status');
        mockEditorSection = document.querySelector('.editor-section');

        manager = new UIManager();
        manager.initialize();
    });

    describe('initialize', () => {
        test('should create progress indicator', () => {
            const progressContainer = document.getElementById('progressContainer');
            expect(progressContainer).toBeTruthy();
        });

        test('should setup event listeners', () => {
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            
            expect(uploadArea).toBeTruthy();
            expect(fileInput).toBeTruthy();
        });
    });

    describe('formatFileSize', () => {
        test('should format bytes correctly', () => {
            expect(manager.formatFileSize(0)).toBe('0 Bytes');
            expect(manager.formatFileSize(1024)).toBe('1 KB');
            expect(manager.formatFileSize(1048576)).toBe('1 MB');
            expect(manager.formatFileSize(1073741824)).toBe('1 GB');
        });

        test('should handle large file sizes', () => {
            const size = 5 * 1024 * 1024;
            expect(manager.formatFileSize(size)).toBe('5 MB');
        });
    });

    describe('showStatus', () => {
        test('should display success message', () => {
            manager.showStatus('Success!', 'success');

            expect(mockStatusDiv.textContent).toBe('Success!');
            expect(mockStatusDiv.className).toContain('success');
            expect(mockStatusDiv.style.display).toBe('block');
        });

        test('should display error message', () => {
            manager.showStatus('Error!', 'error');

            expect(mockStatusDiv.textContent).toBe('Error!');
            expect(mockStatusDiv.className).toContain('error');
        });

        test('should display processing message', () => {
            manager.showStatus('Processing...', 'processing');

            expect(mockStatusDiv.textContent).toBe('Processing...');
            expect(mockStatusDiv.className).toContain('processing');
        });
    });

    describe('showProgress', () => {
        test('should display progress bar', () => {
            manager.showProgress(0.5, '50%');

            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            const progressContainer = document.getElementById('progressContainer');

            expect(progressBar.style.width).toBe('50%');
            expect(progressText.textContent).toBe('50%');
            expect(progressContainer.style.display).toBe('block');
        });

        test('should handle progress without custom message', () => {
            manager.showProgress(0.75);

            const progressText = document.getElementById('progressText');
            expect(progressText.textContent).toBe('75%');
        });
    });

    describe('hideProgress', () => {
        test('should hide progress indicator', () => {
            manager.showProgress(0.5, '50%');
            manager.hideProgress();

            const progressContainer = document.getElementById('progressContainer');
            expect(progressContainer.style.display).toBe('none');
        });
    });

    describe('showEditor', () => {
        test('should show editor section', () => {
            mockEditorSection.style.display = 'none';
            manager.showEditor();

            expect(mockEditorSection.style.display).toBe('block');
        });
    });

    describe('hideEditor', () => {
        test('should hide editor section', () => {
            mockEditorSection.style.display = 'block';
            manager.hideEditor();

            expect(mockEditorSection.style.display).toBe('none');
        });
    });

    describe('reset', () => {
        test('should reset UI to initial state', () => {
            manager.showStatus('Test', 'info');
            manager.showProgress(0.5, '50%');
            manager.showEditor();

            manager.reset();

            expect(mockStatusDiv.style.display).toBe('none');
            expect(document.getElementById('progressContainer').style.display).toBe('none');
            expect(mockEditorSection.style.display).toBe('none');
        });
    });

    describe('showError', () => {
        test('should show error and hide progress', () => {
            manager.showProgress(0.5, '50%');
            manager.showError('Test error');

            expect(mockStatusDiv.textContent).toBe('Test error');
            expect(mockStatusDiv.className).toContain('error');
            expect(document.getElementById('progressContainer').style.display).toBe('none');
        });
    });

    describe('showSuccess', () => {
        test('should show success and hide progress', () => {
            manager.showProgress(0.5, '50%');
            manager.showSuccess('Test success');

            expect(mockStatusDiv.textContent).toBe('Test success');
            expect(mockStatusDiv.className).toContain('success');
            expect(document.getElementById('progressContainer').style.display).toBe('none');
        });
    });

    describe('showProcessing', () => {
        test('should show processing message', () => {
            manager.showProcessing('Processing file...');

            expect(mockStatusDiv.textContent).toBe('Processing file...');
            expect(mockStatusDiv.className).toContain('processing');
        });
    });
});
