/**
 * Unit tests for EditorManager service
 */
import { EditorManager } from '../services/EditorManager.js';

// Mock Editor.js
jest.mock('@editorjs/editorjs');
import EditorJS from '@editorjs/editorjs';

describe('EditorManager', () => {
    let manager;
    let mockEditor;

    beforeEach(() => {
        mockEditor = {
            isReady: Promise.resolve(),
            render: jest.fn().mockResolvedValue(undefined),
            save: jest.fn().mockResolvedValue({ 
                time: Date.now(),
                blocks: [],
                version: '2.28.2'
            }),
            clear: jest.fn(),
            destroy: jest.fn()
        };

        EditorJS.mockImplementation(() => mockEditor);
        
        manager = new EditorManager();
        jest.clearAllMocks();
    });

    describe('initialize', () => {
        test('should create Editor.js instance with default config', () => {
            manager.initialize();

            expect(EditorJS).toHaveBeenCalledWith(
                expect.objectContaining({
                    holder: 'editor',
                    tools: expect.any(Object),
                    placeholder: expect.any(String),
                    readOnly: false
                })
            );
            expect(manager.editor).toBe(mockEditor);
        });
        
        test('should merge custom configuration', () => {
            const customConfig = {
                readOnly: true,
                placeholder: 'Custom placeholder'
            };
            
            manager.initialize(customConfig);
            
            expect(EditorJS).toHaveBeenCalledWith(
                expect.objectContaining({
                    readOnly: true,
                    placeholder: 'Custom placeholder'
                })
            );
        });
    });

    describe('loadContent', () => {
        test('should load content into editor', async () => {
            const testData = {
                time: 1234567890,
                blocks: [
                    { id: '1', type: 'paragraph', data: { text: 'Test content' } }
                ]
            };

            manager.initialize();
            await manager.loadContent(testData);

            expect(mockEditor.clear).toHaveBeenCalled();
            expect(mockEditor.render).toHaveBeenCalledWith(
                expect.objectContaining({
                    blocks: expect.arrayContaining([
                        expect.objectContaining({
                            type: 'paragraph',
                            data: { text: 'Test content' }
                        })
                    ])
                })
            );
        });

        test('should initialize editor if not already initialized', async () => {
            const testData = { blocks: [] };

            await manager.loadContent(testData);

            expect(EditorJS).toHaveBeenCalled();
            expect(mockEditor.render).toHaveBeenCalled();
        });

        test('should handle render errors', async () => {
            const testData = { blocks: [] };
            mockEditor.render.mockRejectedValue(new Error('Render failed'));

            manager.initialize();

            await expect(manager.loadContent(testData)).rejects.toThrow('Failed to load converted content');
        });
        
        test('should normalize and sort blocks with position metadata', async () => {
            const testData = {
                blocks: [
                    { 
                        id: '2', 
                        type: 'paragraph', 
                        data: { text: 'Second' },
                        metadata: { originalCoordinates: { x: 0, y: 200 } }
                    },
                    { 
                        id: '1', 
                        type: 'header', 
                        data: { text: 'First', level: 1 },
                        metadata: { originalCoordinates: { x: 0, y: 100 } }
                    }
                ]
            };

            manager.initialize();
            await manager.loadContent(testData);

            const renderCall = mockEditor.render.mock.calls[0][0];
            expect(renderCall.blocks[0].id).toBe('1'); // Header should be first
            expect(renderCall.blocks[1].id).toBe('2'); // Paragraph should be second
        });
    });

    describe('getContent', () => {
        test('should return editor content', async () => {
            const expectedContent = {
                time: 1234567890,
                blocks: [{ id: '1', type: 'paragraph', data: { text: 'Test' } }],
                version: '2.28.2'
            };

            mockEditor.save.mockResolvedValue(expectedContent);
            manager.initialize();

            const content = await manager.getContent();

            expect(content).toEqual(expectedContent);
            expect(mockEditor.save).toHaveBeenCalled();
        });

        test('should return null if no editor', async () => {
            const content = await manager.getContent();

            expect(content).toBeNull();
        });
    });

    describe('clearContent', () => {
        test('should clear editor content and reset state', async () => {
            manager.initialize();
            manager.editingState.hasUnsavedChanges = true;
            
            await manager.clearContent();

            expect(mockEditor.clear).toHaveBeenCalled();
            expect(manager.currentData).toBeNull();
            expect(manager.editingState.hasUnsavedChanges).toBe(false);
        });
    });
    
    describe('editing state management', () => {
        test('should track editing state', () => {
            manager.editingState.isEditing = true;
            manager.editingState.hasUnsavedChanges = true;
            
            const state = manager.getEditingState();
            
            expect(state.isEditing).toBe(true);
            expect(state.hasUnsavedChanges).toBe(true);
        });
        
        test('should check for unsaved changes', () => {
            manager.editingState.hasUnsavedChanges = true;
            expect(manager.hasUnsavedChanges()).toBe(true);
            
            manager.markAsSaved();
            expect(manager.hasUnsavedChanges()).toBe(false);
        });
    });
    
    describe('table operations', () => {
        beforeEach(() => {
            const tableContent = {
                time: Date.now(),
                blocks: [
                    {
                        id: 'table-1',
                        type: 'table',
                        data: {
                            withHeadings: true,
                            content: [
                                ['Header 1', 'Header 2'],
                                ['Cell 1', 'Cell 2']
                            ]
                        }
                    }
                ],
                version: '2.28.2'
            };
            
            mockEditor.save.mockResolvedValue(tableContent);
        });
        
        test('should get table blocks', async () => {
            manager.initialize();
            
            const tables = await manager.getTableBlocks();
            
            expect(tables).toHaveLength(1);
            expect(tables[0].id).toBe('table-1');
            expect(tables[0].data.content).toHaveLength(2);
        });
        
        test('should validate table structure', () => {
            const validTable = [
                ['A', 'B', 'C'],
                ['1', '2', '3']
            ];
            
            const result = manager.validateTableStructure(validTable);
            
            expect(result.isValid).toBe(true);
            expect(result.details.rows).toBe(2);
            expect(result.details.columns).toBe(3);
        });
        
        test('should detect invalid table structure', () => {
            const invalidTable = [
                ['A', 'B', 'C'],
                ['1', '2'] // Missing column
            ];
            
            const result = manager.validateTableStructure(invalidTable);
            
            expect(result.isValid).toBe(false);
            expect(result.error).toContain('same number of columns');
        });
        
        test('should get table statistics', async () => {
            manager.initialize();
            
            const stats = await manager.getTableStatistics('table-1');
            
            expect(stats).not.toBeNull();
            expect(stats.rows).toBe(2);
            expect(stats.columns).toBe(2);
            expect(stats.totalCells).toBe(4);
            expect(stats.hasHeadings).toBe(true);
        });
    });

    describe('destroy', () => {
        test('should destroy editor instance and reset state', () => {
            manager.initialize();
            manager.currentData = { blocks: [] };
            manager.editingState.hasUnsavedChanges = true;
            
            manager.destroy();

            expect(mockEditor.destroy).toHaveBeenCalled();
            expect(manager.editor).toBeNull();
            expect(manager.currentData).toBeNull();
            expect(manager.editingState.hasUnsavedChanges).toBe(false);
        });
    });
});
