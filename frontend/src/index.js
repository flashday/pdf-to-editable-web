/**
 * Enhanced main application entry point with split-view layout
 * Left: Original document image with OCR region overlays
 * Right: Editable HTML content (方案 A+B)
 */
import { DocumentProcessor } from './services/DocumentProcessor.js';
import { EditorManager } from './services/EditorManager.js';
import { HTMLEditorManager } from './services/HTMLEditorManager.js';
import { UIManager } from './services/UIManager.js';

class App {
    constructor() {
        this.documentProcessor = new DocumentProcessor();
        this.editorManager = new EditorManager();
        this.htmlEditorManager = new HTMLEditorManager();
        this.uiManager = new UIManager();
        this.currentJobId = null;
        this.pollingInterval = null;
        this.isProcessing = false;
        this.ocrRegions = []; // Store OCR regions with coordinates
        this.ocrData = null;  // Store full OCR data for download
        this.activeRegionIndex = null;
        this.useHTMLEditor = true; // 使用新的 HTML 编辑器
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

    setupProcessorCallbacks() {
        this.documentProcessor.setProgressCallback((progressInfo) => {
            this.handleUploadProgress(progressInfo);
        });
        this.documentProcessor.setStatusCallback((statusInfo) => {
            this.handleStatusUpdate(statusInfo);
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.saveCurrentContent();
            }
            if (e.key === 'Escape' && this.isProcessing) {
                this.cancelProcessing();
            }
        });
    }

    handleUploadProgress(progressInfo) {
        const { progress, message } = progressInfo;
        this.uiManager.showProgress(progress, message);
    }

    handleStatusUpdate(statusInfo) {
        const { status, progress, message, estimated_remaining_seconds } = statusInfo;
        let statusMessage = message || `Processing: ${status}`;
        
        if (estimated_remaining_seconds !== undefined && estimated_remaining_seconds > 0) {
            const minutes = Math.floor(estimated_remaining_seconds / 60);
            const seconds = estimated_remaining_seconds % 60;
            statusMessage += minutes > 0 ? ` (Est. ${minutes}m ${seconds}s remaining)` : ` (Est. ${seconds}s remaining)`;
        }
        
        if (progress !== undefined) {
            this.uiManager.showProgress(progress / 100, statusMessage);
        } else {
            this.uiManager.showProcessing(statusMessage);
        }
        console.log('Processing status:', statusInfo);
    }

    async handleFileUpload(file) {
        if (this.isProcessing) {
            this.uiManager.showStatus('A document is already being processed. Please wait.', 'warning');
            return;
        }

        try {
            this.isProcessing = true;
            this.uiManager.showProcessing('Preparing upload...');
            
            const result = await this.documentProcessor.processFile(file);
            
            if (result.success) {
                this.currentJobId = result.jobId;
                if (result.notification) {
                    this.uiManager.showStatus(result.notification, 'info');
                }
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

    async startStatusPolling(jobId) {
        try {
            this.uiManager.showProcessing('Processing document with OCR...');
            const result = await this.documentProcessor.pollForCompletion(jobId);
            
            if (result.success) {
                await this.handleProcessingComplete(result.data, jobId);
            } else {
                if (result.error?.toLowerCase().includes('timeout')) {
                    this.uiManager.showTimeout(result.error);
                } else {
                    this.uiManager.showError(result.error);
                }
            }
        } catch (error) {
            console.error('Status polling error:', error);
            if (error.message?.toLowerCase().includes('timeout')) {
                this.uiManager.showTimeout(error.message);
            } else {
                this.uiManager.showError(`Processing failed: ${error.message || 'Unknown error'}`);
            }
        } finally {
            this.isProcessing = false;
        }
    }

    async handleProcessingComplete(data, jobId) {
        try {
            this.uiManager.showProcessing('Loading converted content...');
            
            // Store OCR data for download
            this.ocrData = data;
            this.currentJobId = jobId;
            
            // Store OCR regions for overlay drawing
            this.ocrRegions = this.extractOCRRegions(data.blocks || []);
            
            // Load document image
            await this.loadDocumentImage(jobId);
            
            // Load content based on editor mode
            if (this.useHTMLEditor) {
                await this.loadHTMLContent(jobId);
            } else {
                await this.editorManager.loadContent(data);
            }
            
            // Show main content area (split view)
            this.showMainContent();
            
            // Draw OCR region overlays on the image
            this.drawOCRRegions();
            
            // Show confidence report
            if (data.confidence_report) {
                this.showConfidenceReport(data.confidence_report);
            }
            
            // Show download button
            this.showDownloadButton();
            
            this.uiManager.showSuccess('Document converted successfully! Click on text to edit, click on tables to open editor.');
            
            console.log('Document conversion complete:', {
                blocksCount: data.blocks?.length || 0,
                regionsCount: this.ocrRegions.length,
                editorMode: this.useHTMLEditor ? 'HTML' : 'Editor.js'
            });
        } catch (error) {
            console.error('Result loading error:', error);
            this.uiManager.showError(`Failed to load result: ${error.message || 'Unknown error'}`);
        }
    }
    
    /**
     * Load HTML content from backend
     */
    async loadHTMLContent(jobId) {
        try {
            console.log('Loading HTML content for job:', jobId);
            const response = await fetch(`/api/convert/${jobId}/editable-html`);
            const data = await response.json();
            
            if (!response.ok) {
                console.warn('Failed to load editable HTML, falling back to Editor.js');
                this.useHTMLEditor = false;
                await this.editorManager.loadContent(this.ocrData);
                return;
            }
            
            if (data.editable_html) {
                console.log('Received editable HTML, length:', data.editable_html.length);
                
                // 从完整 HTML 中提取 body 内容
                const parser = new DOMParser();
                const doc = parser.parseFromString(data.editable_html, 'text/html');
                const bodyContent = doc.body.innerHTML;
                
                console.log('Extracted body content, length:', bodyContent.length);
                
                // 确保 HTMLEditorManager 已初始化
                if (!this.htmlEditorManager.container) {
                    console.log('Initializing HTMLEditorManager...');
                    this.htmlEditorManager.initialize('editor');
                }
                
                this.htmlEditorManager.loadContent(bodyContent);
                
                // 设置区域点击回调，用于高亮左侧图像
                this.htmlEditorManager.setRegionClickCallback((regionId, bbox) => {
                    this.highlightImageRegion(regionId, bbox);
                });
                
                // 设置表格修改回调，同步到 ocrData
                this.htmlEditorManager.setTableModifiedCallback((regionId, tableHtml) => {
                    this.onTableModified(regionId, tableHtml);
                });
                
                console.log('HTML content loaded successfully');
            } else {
                console.warn('No editable_html in response, falling back to Editor.js');
                this.useHTMLEditor = false;
                await this.editorManager.loadContent(this.ocrData);
            }
        } catch (error) {
            console.error('Failed to load HTML content:', error);
            // 回退到 Editor.js
            this.useHTMLEditor = false;
            await this.editorManager.loadContent(this.ocrData);
        }
    }
    
    /**
     * Highlight region on the left image panel
     */
    highlightImageRegion(regionId, bbox) {
        // 清除之前的高亮
        document.querySelectorAll('#imageWrapper .ocr-region.active').forEach(el => {
            el.classList.remove('active');
        });
        
        // 找到对应的图像区域并高亮
        // 由于 HTML 编辑器的 regionId 是按 y 坐标排序的，需要通过 bbox 匹配
        const imageWrapper = document.getElementById('imageWrapper');
        const imageElement = document.getElementById('documentImage');
        
        if (!imageWrapper || !imageElement || !bbox) return;
        
        const scaleX = imageElement.clientWidth / imageElement.naturalWidth;
        const scaleY = imageElement.clientHeight / imageElement.naturalHeight;
        
        // 查找最接近的区域
        const regions = imageWrapper.querySelectorAll('.ocr-region');
        let closestRegion = null;
        let minDistance = Infinity;
        
        regions.forEach(region => {
            const left = parseFloat(region.style.left);
            const top = parseFloat(region.style.top);
            
            const targetX = bbox.x * scaleX;
            const targetY = bbox.y * scaleY;
            
            const distance = Math.sqrt(Math.pow(left - targetX, 2) + Math.pow(top - targetY, 2));
            
            if (distance < minDistance) {
                minDistance = distance;
                closestRegion = region;
            }
        });
        
        if (closestRegion && minDistance < 50) {
            closestRegion.classList.add('active');
            closestRegion.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    /**
     * Show download button and setup click handler
     */
    showDownloadButton() {
        const downloadButtons = document.getElementById('downloadButtons');
        if (downloadButtons) {
            downloadButtons.style.display = 'flex';
        }
        
        // Setup click handlers for all download buttons
        const rawJsonBtn = document.getElementById('downloadRawJsonBtn');
        const rawHtmlBtn = document.getElementById('downloadRawHtmlBtn');
        const ocrBtn = document.getElementById('downloadOcrBtn');
        
        if (rawJsonBtn) {
            rawJsonBtn.onclick = () => this.downloadRawOutput('json');
        }
        if (rawHtmlBtn) {
            rawHtmlBtn.onclick = () => this.downloadRawOutput('html');
        }
        if (ocrBtn) {
            ocrBtn.onclick = () => this.downloadOcrResult();
        }
    }
    
    /**
     * Download raw PaddleOCR output (JSON or HTML)
     */
    async downloadRawOutput(format) {
        if (!this.currentJobId) {
            this.uiManager.showError('No job ID available');
            return;
        }
        
        try {
            // Fetch raw output from backend
            const response = await fetch(`/api/convert/${this.currentJobId}/raw-output`);
            const data = await response.json();
            
            if (!response.ok) {
                this.uiManager.showError(data.error || 'Failed to fetch raw output');
                return;
            }
            
            if (format === 'json') {
                if (!data.raw_json) {
                    this.uiManager.showError('Raw JSON not available');
                    return;
                }
                // Download JSON
                const blob = new Blob([JSON.stringify(data.raw_json, null, 2)], { type: 'application/json' });
                this.downloadBlob(blob, `paddleocr-raw-${this.currentJobId}.json`);
            } else if (format === 'html') {
                if (!data.raw_html) {
                    this.uiManager.showError('Raw HTML not available');
                    return;
                }
                // Download HTML
                const blob = new Blob([data.raw_html], { type: 'text/html' });
                this.downloadBlob(blob, `paddleocr-raw-${this.currentJobId}.html`);
            }
            
            console.log(`Downloaded raw ${format} output`);
        } catch (error) {
            console.error('Failed to download raw output:', error);
            this.uiManager.showError(`Download failed: ${error.message}`);
        }
    }
    
    /**
     * Helper function to download a blob
     */
    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    /**
     * Download OCR result as JSON file
     */
    downloadOcrResult() {
        if (!this.ocrData) {
            this.uiManager.showError('No OCR data available');
            return;
        }
        
        // 获取表格修改
        const tableModifications = this.htmlEditorManager?.getModifications() || {};
        
        // Prepare download data with all OCR information
        const downloadData = {
            jobId: this.currentJobId,
            timestamp: new Date().toISOString(),
            blocks: this.ocrData.blocks?.map(block => {
                const blockData = {
                    id: block.id,
                    type: block.type,
                    text: block.data?.text || block.data?.items?.join('\n') || '',
                    coordinates: block.metadata?.originalCoordinates || null,
                    estimatedFontSize: block.metadata?.estimatedFontSize || null,
                    confidence: block.metadata?.confidence || null,
                    classification: block.metadata?.originalClassification || null
                };
                
                // 如果是表格且有修改，添加修改后的 HTML
                if (block.type === 'table' && block.data?.tableHtml) {
                    blockData.tableHtml = block.data.tableHtml;
                }
                
                return blockData;
            }) || [],
            // 添加表格修改记录
            tableModifications: tableModifications,
            confidenceReport: this.ocrData.confidence_report || null,
            summary: {
                totalBlocks: this.ocrData.blocks?.length || 0,
                totalRegions: this.ocrRegions?.length || 0,
                modifiedTables: Object.keys(tableModifications).length
            }
        };
        
        // Create and download JSON file
        const blob = new Blob([JSON.stringify(downloadData, null, 2)], { type: 'application/json' });
        this.downloadBlob(blob, `ocr-result-${this.currentJobId || 'unknown'}.json`);
        
        console.log('OCR result downloaded with', Object.keys(tableModifications).length, 'table modifications');
    }
    
    /**
     * Handle table modification from HTMLEditorManager
     */
    onTableModified(regionId, tableHtml) {
        console.log('Table modified, regionId:', regionId);
        
        // 尝试找到对应的 block 并更新
        if (this.ocrData?.blocks) {
            // 表格通常是 type === 'table' 的块
            const tableBlocks = this.ocrData.blocks.filter(b => b.type === 'table');
            const tableIndex = parseInt(regionId, 10);
            
            if (tableBlocks[tableIndex]) {
                if (!tableBlocks[tableIndex].data) {
                    tableBlocks[tableIndex].data = {};
                }
                tableBlocks[tableIndex].data.tableHtml = tableHtml;
                tableBlocks[tableIndex].data.modified = true;
                console.log('Updated table block:', tableIndex);
            }
        }
        
        this.uiManager.showSuccess('表格已保存');
    }

    /**
     * Extract OCR regions with coordinates from blocks
     */
    extractOCRRegions(blocks) {
        const regions = [];
        blocks.forEach((block, index) => {
            // Backend uses 'originalCoordinates' in metadata
            const coords = block.metadata?.originalCoordinates;
            if (coords) {
                regions.push({
                    index,
                    blockId: block.id,
                    type: block.type,
                    text: this.getBlockText(block),
                    coordinates: coords
                });
            }
        });
        console.log(`Extracted ${regions.length} OCR regions from ${blocks.length} blocks`);
        return regions;
    }

    /**
     * Get text content from a block
     */
    getBlockText(block) {
        if (block.data?.text) return block.data.text;
        if (block.data?.items) return block.data.items.join(', ');
        if (block.data?.content) return JSON.stringify(block.data.content).substring(0, 50);
        return `Block ${block.type}`;
    }

    /**
     * Load document image from backend
     */
    async loadDocumentImage(jobId) {
        const imageElement = document.getElementById('documentImage');
        const bgImageElement = document.getElementById('editorBgImg');
        if (!imageElement) return;
        
        const imageUrl = `/api/convert/${jobId}/image?t=${Date.now()}`;
        
        return new Promise((resolve, reject) => {
            imageElement.onload = () => {
                console.log('Document image loaded:', imageElement.naturalWidth, 'x', imageElement.naturalHeight);
                resolve();
            };
            imageElement.onerror = () => {
                console.warn('Failed to load document image');
                resolve(); // Don't fail the whole process
            };
            imageElement.src = imageUrl;
            
            // 同时设置右侧编辑器的背景图像
            if (bgImageElement) {
                bgImageElement.src = imageUrl;
            }
        });
    }

    /**
     * Show main content area with split view
     */
    showMainContent() {
        const mainContent = document.getElementById('mainContent');
        if (mainContent) {
            mainContent.classList.add('visible');
        }
        // Also show editor section for UIManager compatibility
        this.uiManager.showEditor();
    }

    /**
     * Draw OCR region overlays on the document image
     */
    drawOCRRegions() {
        const imageWrapper = document.getElementById('imageWrapper');
        const imageElement = document.getElementById('documentImage');
        
        if (!imageWrapper || !imageElement || !imageElement.naturalWidth) {
            console.warn('Cannot draw OCR regions: image not ready');
            return;
        }
        
        // Remove existing region overlays
        imageWrapper.querySelectorAll('.ocr-region').forEach(el => el.remove());
        
        // Calculate scale factor between natural image size and displayed size
        const scaleX = imageElement.clientWidth / imageElement.naturalWidth;
        const scaleY = imageElement.clientHeight / imageElement.naturalHeight;
        
        console.log('Drawing OCR regions:', {
            naturalSize: `${imageElement.naturalWidth}x${imageElement.naturalHeight}`,
            displaySize: `${imageElement.clientWidth}x${imageElement.clientHeight}`,
            scale: `${scaleX.toFixed(3)}x${scaleY.toFixed(3)}`,
            regionsCount: this.ocrRegions.length
        });
        
        this.ocrRegions.forEach((region, idx) => {
            const coords = region.coordinates;
            if (!coords) return;
            
            const regionDiv = document.createElement('div');
            regionDiv.className = 'ocr-region';
            regionDiv.dataset.regionIndex = idx;
            regionDiv.dataset.blockId = region.blockId;
            regionDiv.dataset.text = region.text; // 存储文本用于编辑
            
            // Scale coordinates to match displayed image size
            regionDiv.style.left = `${coords.x * scaleX}px`;
            regionDiv.style.top = `${coords.y * scaleY}px`;
            regionDiv.style.width = `${coords.width * scaleX}px`;
            regionDiv.style.height = `${coords.height * scaleY}px`;
            
            // Add tooltip
            const tooltip = document.createElement('div');
            tooltip.className = 'ocr-region-tooltip';
            tooltip.textContent = region.text.substring(0, 30) + (region.text.length > 30 ? '...' : '');
            regionDiv.appendChild(tooltip);
            
            // Add click handler to highlight corresponding editor block
            regionDiv.addEventListener('click', () => this.highlightEditorBlock(idx, region.blockId));
            regionDiv.addEventListener('mouseenter', () => this.onRegionHover(idx, true));
            regionDiv.addEventListener('mouseleave', () => this.onRegionHover(idx, false));
            
            imageWrapper.appendChild(regionDiv);
        });
    }
    
    /**
     * Handle region hover
     */
    onRegionHover(regionIndex, isEntering) {
        // Could add additional hover effects here
    }

    /**
     * Highlight corresponding editor block when region is clicked
     */
    highlightEditorBlock(regionIndex, blockId) {
        // Remove previous active state
        document.querySelectorAll('.ocr-region.active').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.ce-block.highlighted').forEach(el => el.classList.remove('highlighted'));
        
        // Add active state to clicked region
        const regionEl = document.querySelector(`.ocr-region[data-region-index="${regionIndex}"]`);
        if (regionEl) {
            regionEl.classList.add('active');
        }
        
        // Find and highlight corresponding editor block
        const editorBlocks = document.querySelectorAll('.ce-block');
        if (editorBlocks[regionIndex]) {
            editorBlocks[regionIndex].classList.add('highlighted');
            editorBlocks[regionIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        this.activeRegionIndex = regionIndex;
    }

    /**
     * Show confidence report
     */
    showConfidenceReport(confidenceReport) {
        if (!confidenceReport?.confidence_breakdown) return;

        const reportDiv = document.getElementById('confidenceReport');
        if (!reportDiv) return;

        const breakdown = confidenceReport.confidence_breakdown;
        const overall = breakdown.overall;

        let html = `
            <h4>📊 Confidence: ${overall.score.toFixed(2)} (${overall.level})</h4>
            <p>${overall.description}</p>
        `;

        if (confidenceReport.warnings?.length > 0) {
            html += `
                <div style="margin-top: 8px;">
                    <strong style="color: #e67e22;">⚠️ Warnings:</strong>
                    <ul>
                        ${confidenceReport.warnings.map(w => `<li>${w.message}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        reportDiv.innerHTML = html;
    }

    initializeEditor() {
        this.editorManager.initialize();
        // 同时初始化 HTML 编辑器
        this.htmlEditorManager.initialize('editor');
    }

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

    cancelProcessing() {
        if (this.isProcessing) {
            this.documentProcessor.stopPolling();
            this.isProcessing = false;
            this.uiManager.showStatus('Processing cancelled', 'warning');
        }
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
