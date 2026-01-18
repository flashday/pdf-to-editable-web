/**
 * Editor.js management service for rendering and editing converted content
 * Enhanced with custom configuration for PDF content
 */
import EditorJS from '@editorjs/editorjs';
import Header from '@editorjs/header';
import Paragraph from '@editorjs/paragraph';
import Table from '@editorjs/table';
import Image from '@editorjs/image';

export class EditorManager {
    constructor() {
        this.editor = null;
        this.currentData = null;
        this.editingState = {
            isEditing: false,
            currentBlockId: null,
            hasUnsavedChanges: false
        };
        
        // Custom configuration optimized for PDF content
        this.editorConfig = {
            holder: 'editor',
            tools: {
                header: {
                    class: Header,
                    config: {
                        placeholder: 'Enter a header',
                        levels: [1, 2, 3, 4, 5, 6],
                        defaultLevel: 2
                    },
                    inlineToolbar: true
                },
                paragraph: {
                    class: Paragraph,
                    config: {
                        placeholder: 'Enter paragraph text',
                        preserveBlank: true
                    },
                    inlineToolbar: true
                },
                table: {
                    class: Table,
                    config: {
                        rows: 2,
                        cols: 3,
                        withHeadings: false
                    },
                    inlineToolbar: true
                },
                image: {
                    class: Image,
                    config: {
                        endpoints: {
                            byFile: '/api/upload-image'
                        },
                        captionPlaceholder: 'Image caption',
                        buttonContent: 'Select an image',
                        uploader: {
                            uploadByFile: this._handleImageUpload.bind(this)
                        }
                    }
                }
            },
            placeholder: 'Upload a document to start editing...',
            readOnly: false,
            minHeight: 300,
            autofocus: false,
            
            // Custom configuration for PDF content
            onChange: this._handleContentChange.bind(this),
            onReady: this._handleEditorReady.bind(this),
            
            // Preserve block order and structure
            defaultBlock: 'paragraph',
            
            // Enable inline toolbar for better editing experience
            inlineToolbar: ['bold', 'italic', 'link'],
            
            // Logging for debugging
            logLevel: 'ERROR'
        };
    }
    
    /**
     * Handle image upload for image blocks
     * @param {File} file - Image file to upload
     * @returns {Promise<Object>} Upload result with file URL
     * @private
     */
    async _handleImageUpload(file) {
        // Placeholder for image upload functionality
        // In production, this would upload to the backend
        return {
            success: 1,
            file: {
                url: URL.createObjectURL(file),
                name: file.name,
                size: file.size
            }
        };
    }
    
    /**
     * Handle editor ready event
     * @private
     */
    _handleEditorReady() {
        console.log('Editor.js is ready');
        this.editingState.isEditing = false;
    }
    
    /**
     * Handle content change event
     * @param {Object} api - Editor.js API
     * @param {Object} event - Change event details
     * @private
     */
    async _handleContentChange(api, event) {
        this.editingState.hasUnsavedChanges = true;
        this.editingState.isEditing = true;
        
        // Track which block is being edited
        if (event && event.type === 'block-changed') {
            this.editingState.currentBlockId = event.detail?.target?.id || null;
        }
        
        // Save current state
        try {
            this.currentData = await this.editor.save();
        } catch (error) {
            console.error('Failed to save editor state:', error);
        }
    }
    
    /**
     * Enable editing for a specific block
     * @param {string} blockId - ID of the block to edit
     * @returns {Promise<boolean>} True if editing was enabled
     */
    async enableBlockEditing(blockId) {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            // Get the block index
            const content = await this.editor.save();
            const blockIndex = content.blocks.findIndex(b => b.id === blockId);
            
            if (blockIndex === -1) {
                console.warn(`Block ${blockId} not found`);
                return false;
            }
            
            // Focus on the block using Editor.js API
            // Note: Editor.js doesn't have a direct focus API, but blocks are editable by default
            this.editingState.isEditing = true;
            this.editingState.currentBlockId = blockId;
            
            return true;
        } catch (error) {
            console.error('Failed to enable block editing:', error);
            return false;
        }
    }
    
    /**
     * Disable editing (set editor to read-only mode)
     * @returns {Promise<boolean>} True if editing was disabled
     */
    async disableEditing() {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            // Editor.js doesn't support dynamic read-only mode change
            // We need to reinitialize with readOnly: true
            const content = await this.editor.save();
            
            this.editor.destroy();
            
            const readOnlyConfig = {
                ...this.editorConfig,
                readOnly: true
            };
            
            this.editor = new EditorJS(readOnlyConfig);
            await this.editor.isReady;
            await this.editor.render(content);
            
            this.editingState.isEditing = false;
            this.editingState.currentBlockId = null;
            
            return true;
        } catch (error) {
            console.error('Failed to disable editing:', error);
            return false;
        }
    }
    
    /**
     * Enable editing (set editor to editable mode)
     * @returns {Promise<boolean>} True if editing was enabled
     */
    async enableEditing() {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            // Get current content
            const content = await this.editor.save();
            
            // Destroy and reinitialize with readOnly: false
            this.editor.destroy();
            
            const editableConfig = {
                ...this.editorConfig,
                readOnly: false
            };
            
            this.editor = new EditorJS(editableConfig);
            await this.editor.isReady;
            await this.editor.render(content);
            
            this.editingState.isEditing = true;
            
            return true;
        } catch (error) {
            console.error('Failed to enable editing:', error);
            return false;
        }
    }
    
    /**
     * Check if editor is in editing mode
     * @returns {boolean} True if editor is editable
     */
    isEditing() {
        return !this.editorConfig.readOnly && this.editingState.isEditing;
    }
    
    /**
     * Get currently focused/editing block ID
     * @returns {string|null} Block ID or null
     */
    getCurrentBlockId() {
        return this.editingState.currentBlockId;
    }
    
    /**
     * Save current editing state
     * @returns {Promise<Object>} Saved content
     */
    async saveEditingState() {
        if (!this.editor) {
            return null;
        }
        
        try {
            const content = await this.getContent();
            this.editingState.hasUnsavedChanges = false;
            return content;
        } catch (error) {
            console.error('Failed to save editing state:', error);
            return null;
        }
    }
    
    /**
     * Get all table blocks from the editor
     * @returns {Promise<Array>} Array of table blocks with their indices
     */
    async getTableBlocks() {
        const content = await this.getContent();
        if (!content || !content.blocks) {
            return [];
        }
        
        const tableBlocks = [];
        content.blocks.forEach((block, index) => {
            if (block.type === 'table') {
                tableBlocks.push({
                    index,
                    id: block.id,
                    data: block.data,
                    metadata: block.metadata
                });
            }
        });
        
        return tableBlocks;
    }
    
    /**
     * Validate table structure integrity
     * Ensures all rows have the same number of columns
     * @param {Array<Array<string>>} tableContent - Table content array
     * @returns {Object} Validation result with isValid flag and details
     */
    validateTableStructure(tableContent) {
        if (!Array.isArray(tableContent) || tableContent.length === 0) {
            return {
                isValid: false,
                error: 'Table content must be a non-empty array',
                details: null
            };
        }
        
        // Check if all rows are arrays
        if (!tableContent.every(row => Array.isArray(row))) {
            return {
                isValid: false,
                error: 'All table rows must be arrays',
                details: null
            };
        }
        
        // Get expected column count from first row
        const expectedColumns = tableContent[0].length;
        
        if (expectedColumns === 0) {
            return {
                isValid: false,
                error: 'Table must have at least one column',
                details: null
            };
        }
        
        // Check all rows have the same column count
        const inconsistentRows = [];
        tableContent.forEach((row, index) => {
            if (row.length !== expectedColumns) {
                inconsistentRows.push({
                    rowIndex: index,
                    expected: expectedColumns,
                    actual: row.length
                });
            }
        });
        
        if (inconsistentRows.length > 0) {
            return {
                isValid: false,
                error: 'All table rows must have the same number of columns',
                details: {
                    expectedColumns,
                    inconsistentRows
                }
            };
        }
        
        return {
            isValid: true,
            error: null,
            details: {
                rows: tableContent.length,
                columns: expectedColumns,
                totalCells: tableContent.length * expectedColumns
            }
        };
    }
    
    /**
     * Update a specific table block
     * @param {string} blockId - ID of the table block to update
     * @param {Object} newTableData - New table data
     * @returns {Promise<boolean>} True if update was successful
     */
    async updateTableBlock(blockId, newTableData) {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            // Validate table structure
            if (newTableData.content) {
                const validation = this.validateTableStructure(newTableData.content);
                if (!validation.isValid) {
                    console.error('Table structure validation failed:', validation.error);
                    return false;
                }
            }
            
            // Get current content
            const content = await this.editor.save();
            
            // Find and update the table block
            const blockIndex = content.blocks.findIndex(b => b.id === blockId);
            if (blockIndex === -1) {
                console.error(`Table block ${blockId} not found`);
                return false;
            }
            
            // Ensure it's actually a table block
            if (content.blocks[blockIndex].type !== 'table') {
                console.error(`Block ${blockId} is not a table block`);
                return false;
            }
            
            // Update the table data while preserving metadata
            content.blocks[blockIndex].data = {
                ...content.blocks[blockIndex].data,
                ...newTableData
            };
            
            // Re-render the editor with updated content
            await this.editor.clear();
            await this.editor.render(content);
            
            this.editingState.hasUnsavedChanges = true;
            
            return true;
        } catch (error) {
            console.error('Failed to update table block:', error);
            return false;
        }
    }
    
    /**
     * Add a row to a table block
     * @param {string} blockId - ID of the table block
     * @param {number} position - Position to insert row (default: end)
     * @returns {Promise<boolean>} True if row was added
     */
    async addTableRow(blockId, position = -1) {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            const content = await this.editor.save();
            const blockIndex = content.blocks.findIndex(b => b.id === blockId);
            
            if (blockIndex === -1 || content.blocks[blockIndex].type !== 'table') {
                return false;
            }
            
            const tableData = content.blocks[blockIndex].data;
            const columnCount = tableData.content[0]?.length || 1;
            
            // Create new empty row
            const newRow = Array(columnCount).fill('');
            
            // Insert row at specified position
            if (position === -1 || position >= tableData.content.length) {
                tableData.content.push(newRow);
            } else {
                tableData.content.splice(position, 0, newRow);
            }
            
            // Update the table
            return await this.updateTableBlock(blockId, tableData);
        } catch (error) {
            console.error('Failed to add table row:', error);
            return false;
        }
    }
    
    /**
     * Remove a row from a table block
     * @param {string} blockId - ID of the table block
     * @param {number} rowIndex - Index of row to remove
     * @returns {Promise<boolean>} True if row was removed
     */
    async removeTableRow(blockId, rowIndex) {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            const content = await this.editor.save();
            const blockIndex = content.blocks.findIndex(b => b.id === blockId);
            
            if (blockIndex === -1 || content.blocks[blockIndex].type !== 'table') {
                return false;
            }
            
            const tableData = content.blocks[blockIndex].data;
            
            // Don't allow removing the last row
            if (tableData.content.length <= 1) {
                console.warn('Cannot remove the last row from table');
                return false;
            }
            
            // Remove the row
            tableData.content.splice(rowIndex, 1);
            
            // Update the table
            return await this.updateTableBlock(blockId, tableData);
        } catch (error) {
            console.error('Failed to remove table row:', error);
            return false;
        }
    }
    
    /**
     * Add a column to a table block
     * @param {string} blockId - ID of the table block
     * @param {number} position - Position to insert column (default: end)
     * @returns {Promise<boolean>} True if column was added
     */
    async addTableColumn(blockId, position = -1) {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            const content = await this.editor.save();
            const blockIndex = content.blocks.findIndex(b => b.id === blockId);
            
            if (blockIndex === -1 || content.blocks[blockIndex].type !== 'table') {
                return false;
            }
            
            const tableData = content.blocks[blockIndex].data;
            
            // Add empty cell to each row
            tableData.content.forEach(row => {
                if (position === -1 || position >= row.length) {
                    row.push('');
                } else {
                    row.splice(position, 0, '');
                }
            });
            
            // Update the table
            return await this.updateTableBlock(blockId, tableData);
        } catch (error) {
            console.error('Failed to add table column:', error);
            return false;
        }
    }
    
    /**
     * Remove a column from a table block
     * @param {string} blockId - ID of the table block
     * @param {number} columnIndex - Index of column to remove
     * @returns {Promise<boolean>} True if column was removed
     */
    async removeTableColumn(blockId, columnIndex) {
        if (!this.editor) {
            return false;
        }
        
        try {
            await this.editor.isReady;
            
            const content = await this.editor.save();
            const blockIndex = content.blocks.findIndex(b => b.id === blockId);
            
            if (blockIndex === -1 || content.blocks[blockIndex].type !== 'table') {
                return false;
            }
            
            const tableData = content.blocks[blockIndex].data;
            
            // Don't allow removing the last column
            if (tableData.content[0]?.length <= 1) {
                console.warn('Cannot remove the last column from table');
                return false;
            }
            
            // Remove the column from each row
            tableData.content.forEach(row => {
                row.splice(columnIndex, 1);
            });
            
            // Update the table
            return await this.updateTableBlock(blockId, tableData);
        } catch (error) {
            console.error('Failed to remove table column:', error);
            return false;
        }
    }
    
    /**
     * Get table statistics
     * @param {string} blockId - ID of the table block
     * @returns {Promise<Object|null>} Table statistics or null
     */
    async getTableStatistics(blockId) {
        const content = await this.getContent();
        if (!content || !content.blocks) {
            return null;
        }
        
        const block = content.blocks.find(b => b.id === blockId);
        if (!block || block.type !== 'table') {
            return null;
        }
        
        const tableContent = block.data.content || [];
        const rows = tableContent.length;
        const columns = tableContent[0]?.length || 0;
        
        let nonEmptyCells = 0;
        let totalCharacters = 0;
        
        tableContent.forEach(row => {
            row.forEach(cell => {
                if (cell && cell.trim()) {
                    nonEmptyCells++;
                    totalCharacters += cell.length;
                }
            });
        });
        
        return {
            rows,
            columns,
            totalCells: rows * columns,
            nonEmptyCells,
            emptyCells: (rows * columns) - nonEmptyCells,
            totalCharacters,
            averageCellLength: nonEmptyCells > 0 ? totalCharacters / nonEmptyCells : 0,
            hasHeadings: block.data.withHeadings || false
        };
    }

    /**
     * Initialize the Editor.js instance with custom configuration
     * Supports optional configuration overrides for specific use cases
     * @param {Object} customConfig - Optional custom configuration to merge
     */
    initialize(customConfig = {}) {
        // Merge custom configuration with default configuration
        const finalConfig = {
            ...this.editorConfig,
            ...customConfig,
            tools: {
                ...this.editorConfig.tools,
                ...(customConfig.tools || {})
            }
        };
        
        this.editor = new EditorJS(finalConfig);
        
        // Wait for editor to be ready
        this.editor.isReady
            .then(() => {
                console.log('Editor.js initialized successfully');
            })
            .catch((error) => {
                console.error('Editor.js initialization failed:', error);
            });
    }

    /**
     * Load content into the editor with proper data structure handling
     * Supports both Editor.js format and backend conversion format
     * @param {Object} editorData - Editor.js compatible data or backend response
     */
    async loadContent(editorData) {
        if (!this.editor) {
            this.initialize();
        }

        try {
            await this.editor.isReady;
            
            // Normalize data structure to ensure compatibility
            const normalizedData = this._normalizeEditorData(editorData);
            
            // Validate data before rendering
            if (!this._validateEditorData(normalizedData)) {
                throw new Error('Invalid editor data structure');
            }
            
            // Clear existing content first
            await this.editor.clear();
            
            // Render new content
            await this.editor.render(normalizedData);
            
            // Store current data
            this.currentData = normalizedData;
            this.editingState.hasUnsavedChanges = false;
            
            console.log(`Loaded ${normalizedData.blocks?.length || 0} blocks into editor`);
        } catch (error) {
            console.error('Failed to load content into editor:', error);
            throw new Error('Failed to load converted content');
        }
    }
    
    /**
     * Normalize editor data to ensure proper structure
     * Handles both direct Editor.js format and backend response format
     * @param {Object} data - Raw data from backend or Editor.js
     * @returns {Object} Normalized Editor.js data
     * @private
     */
    _normalizeEditorData(data) {
        // If data already has blocks array, use it directly
        if (data && Array.isArray(data.blocks)) {
            return {
                time: data.time || Date.now(),
                blocks: this._sortAndPrepareBlocks(data.blocks),
                version: data.version || this.editorConfig.version || '2.28.2'
            };
        }
        
        // If data is an array, treat it as blocks array
        if (Array.isArray(data)) {
            return {
                time: Date.now(),
                blocks: this._sortAndPrepareBlocks(data),
                version: '2.28.2'
            };
        }
        
        // If data has a different structure, try to extract blocks
        if (data && typeof data === 'object') {
            // Check for common backend response patterns
            if (data.data && Array.isArray(data.data.blocks)) {
                return this._normalizeEditorData(data.data);
            }
            
            if (data.result && Array.isArray(data.result.blocks)) {
                return this._normalizeEditorData(data.result);
            }
        }
        
        // Default empty structure
        return {
            time: Date.now(),
            blocks: [],
            version: '2.28.2'
        };
    }
    
    /**
     * Sort and prepare blocks for rendering
     * Preserves document flow and logical order from original document
     * @param {Array} blocks - Array of Editor.js blocks
     * @returns {Array} Sorted and prepared blocks
     * @private
     */
    _sortAndPrepareBlocks(blocks) {
        if (!Array.isArray(blocks) || blocks.length === 0) {
            return [];
        }
        
        // Create a copy to avoid mutating original
        const blocksCopy = blocks.map(block => ({ ...block }));
        
        // Sort blocks by their original position if metadata is available
        const sortedBlocks = blocksCopy.sort((a, b) => {
            // Check if blocks have position metadata
            const aCoords = a.metadata?.originalCoordinates;
            const bCoords = b.metadata?.originalCoordinates;
            
            if (aCoords && bCoords) {
                // Sort by Y position first (top to bottom)
                if (Math.abs(aCoords.y - bCoords.y) > 10) {
                    return aCoords.y - bCoords.y;
                }
                // If Y positions are similar, sort by X position (left to right)
                return aCoords.x - bCoords.x;
            }
            
            // If no position metadata, maintain original order
            return 0;
        });
        
        // Apply visual hierarchy enhancements
        return sortedBlocks.map((block, index) => {
            return this._enhanceBlockForRendering(block, index, sortedBlocks);
        });
    }
    
    /**
     * Enhance block with rendering metadata
     * Adds visual hierarchy information and rendering hints
     * @param {Object} block - Editor.js block
     * @param {number} index - Block index in sorted array
     * @param {Array} allBlocks - All blocks for context
     * @returns {Object} Enhanced block
     * @private
     */
    _enhanceBlockForRendering(block, index, allBlocks) {
        const enhanced = { ...block };
        
        // Ensure block has an ID
        if (!enhanced.id) {
            enhanced.id = `block-${index}-${Date.now()}`;
        }
        
        // Add rendering metadata
        if (!enhanced.metadata) {
            enhanced.metadata = {};
        }
        
        enhanced.metadata.renderIndex = index;
        enhanced.metadata.isFirstBlock = index === 0;
        enhanced.metadata.isLastBlock = index === allBlocks.length - 1;
        
        // Determine visual hierarchy level
        enhanced.metadata.hierarchyLevel = this._determineHierarchyLevel(block, index, allBlocks);
        
        // Add spacing hints based on block type and position
        enhanced.metadata.spacingHint = this._determineSpacing(block, index, allBlocks);
        
        return enhanced;
    }
    
    /**
     * Determine visual hierarchy level for a block
     * @param {Object} block - Editor.js block
     * @param {number} index - Block index
     * @param {Array} allBlocks - All blocks
     * @returns {number} Hierarchy level (0-6, where 0 is highest)
     * @private
     */
    _determineHierarchyLevel(block, index, allBlocks) {
        // Headers have explicit hierarchy
        if (block.type === 'header' && block.data.level) {
            return block.data.level;
        }
        
        // Tables are at level 3 (subsection level)
        if (block.type === 'table') {
            return 3;
        }
        
        // Images are at level 4
        if (block.type === 'image') {
            return 4;
        }
        
        // Paragraphs are at level 5 (body text)
        if (block.type === 'paragraph') {
            return 5;
        }
        
        // Lists are at level 5
        if (block.type === 'list') {
            return 5;
        }
        
        // Default to level 5
        return 5;
    }
    
    /**
     * Determine spacing for a block based on context
     * @param {Object} block - Editor.js block
     * @param {number} index - Block index
     * @param {Array} allBlocks - All blocks
     * @returns {string} Spacing hint ('none', 'small', 'medium', 'large')
     * @private
     */
    _determineSpacing(block, index, allBlocks) {
        // First block has no top spacing
        if (index === 0) {
            return 'none';
        }
        
        const previousBlock = allBlocks[index - 1];
        
        // Large spacing after headers
        if (previousBlock.type === 'header') {
            return 'large';
        }
        
        // Medium spacing after tables
        if (previousBlock.type === 'table') {
            return 'medium';
        }
        
        // Medium spacing before headers
        if (block.type === 'header') {
            return 'medium';
        }
        
        // Small spacing between paragraphs
        if (block.type === 'paragraph' && previousBlock.type === 'paragraph') {
            return 'small';
        }
        
        // Default medium spacing
        return 'medium';
    }
    
    /**
     * Validate editor data structure
     * @param {Object} data - Editor data to validate
     * @returns {boolean} True if valid
     * @private
     */
    _validateEditorData(data) {
        if (!data || typeof data !== 'object') {
            return false;
        }
        
        if (!Array.isArray(data.blocks)) {
            return false;
        }
        
        // Validate each block has required fields
        for (const block of data.blocks) {
            if (!block.type || !block.data) {
                console.warn('Invalid block structure:', block);
                return false;
            }
        }
        
        return true;
    }

    /**
     * Get current editor content
     * @returns {Promise<Object>} Editor.js data
     */
    async getContent() {
        if (!this.editor) {
            return null;
        }

        try {
            await this.editor.isReady;
            const content = await this.editor.save();
            this.currentData = content;
            return content;
        } catch (error) {
            console.error('Failed to get editor content:', error);
            return null;
        }
    }

    /**
     * Clear editor content
     */
    async clearContent() {
        if (!this.editor) {
            return;
        }

        try {
            await this.editor.isReady;
            this.editor.clear();
            this.currentData = null;
            this.editingState.hasUnsavedChanges = false;
            this.editingState.currentBlockId = null;
        } catch (error) {
            console.error('Failed to clear editor content:', error);
        }
    }
    
    /**
     * Get editing state
     * @returns {Object} Current editing state
     */
    getEditingState() {
        return { ...this.editingState };
    }
    
    /**
     * Get blocks in their current render order
     * @returns {Promise<Array>} Array of blocks in render order
     */
    async getBlocksInRenderOrder() {
        const content = await this.getContent();
        if (!content || !content.blocks) {
            return [];
        }
        
        return content.blocks;
    }
    
    /**
     * Get block count by type
     * @returns {Promise<Object>} Object with counts by block type
     */
    async getBlockStatistics() {
        const content = await this.getContent();
        if (!content || !content.blocks) {
            return {};
        }
        
        const stats = {};
        for (const block of content.blocks) {
            stats[block.type] = (stats[block.type] || 0) + 1;
        }
        
        return {
            total: content.blocks.length,
            byType: stats
        };
    }
    
    /**
     * Check if there are unsaved changes
     * @returns {boolean} True if there are unsaved changes
     */
    hasUnsavedChanges() {
        return this.editingState.hasUnsavedChanges;
    }
    
    /**
     * Mark content as saved
     */
    markAsSaved() {
        this.editingState.hasUnsavedChanges = false;
    }

    /**
     * Destroy editor instance
     */
    destroy() {
        if (this.editor) {
            this.editor.destroy();
            this.editor = null;
            this.currentData = null;
            this.editingState = {
                isEditing: false,
                currentBlockId: null,
                hasUnsavedChanges: false
            };
        }
    }
}