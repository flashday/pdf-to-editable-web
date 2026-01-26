/**
 * Unit tests for SmartExtract component
 * Validates: Requirements 6.1, 6.2, 6.3
 */

// Mock fetch globally
global.fetch = jest.fn();

// Import the component
const SmartExtractPanel = require('../components/SmartExtract.js');

describe('SmartExtractPanel', () => {
    let container;
    let panel;

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();
        
        // Setup DOM
        document.body.innerHTML = '<div id="test-container"></div>';
        container = document.getElementById('test-container');
        
        // Mock successful templates response
        global.fetch.mockResolvedValue({
            json: () => Promise.resolve({
                success: true,
                data: {
                    templates: {
                        invoice: {
                            name: '发票',
                            name_en: 'Invoice',
                            fields: ['发票号码', '开票日期', '金额']
                        },
                        contract: {
                            name: '合同',
                            name_en: 'Contract',
                            fields: ['甲方', '乙方', '合同金额']
                        }
                    }
                }
            })
        });
    });

    afterEach(() => {
        if (panel) {
            panel = null;
        }
        document.body.innerHTML = '';
    });

    describe('Component Rendering', () => {
        test('should render panel structure correctly', async () => {
            panel = new SmartExtractPanel(container);
            
            // Wait for async init
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Check main structure
            expect(container.querySelector('.smart-extract-panel')).toBeTruthy();
            expect(container.querySelector('.panel-header')).toBeTruthy();
            expect(container.querySelector('.panel-body')).toBeTruthy();
        });

        test('should render template select dropdown', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const select = container.querySelector('#template-select');
            expect(select).toBeTruthy();
        });

        test('should render custom field input', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            
            expect(input).toBeTruthy();
            expect(addBtn).toBeTruthy();
        });

        test('should render extract button disabled initially', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const extractBtn = container.querySelector('#extract-btn');
            expect(extractBtn).toBeTruthy();
            expect(extractBtn.disabled).toBe(true);
        });

        test('should add styles to document head', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const styles = document.getElementById('smart-extract-styles');
            expect(styles).toBeTruthy();
        });
    });

    describe('Template Loading', () => {
        test('should load templates from API', async () => {
            panel = new SmartExtractPanel(container, { apiBaseUrl: 'http://test' });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(global.fetch).toHaveBeenCalledWith('http://test/api/templates');
        });

        test('should populate template options after loading', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const select = container.querySelector('#template-select');
            const options = select.querySelectorAll('option');
            
            // Default option + 2 templates
            expect(options.length).toBe(3);
        });

        test('should handle template loading failure gracefully', async () => {
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            // Should not throw
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(container.querySelector('.smart-extract-panel')).toBeTruthy();
        });
    });

    describe('Field Management', () => {
        test('should add custom field when clicking add button', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            
            input.value = '测试字段';
            addBtn.click();
            
            const tags = container.querySelectorAll('.field-tag');
            expect(tags.length).toBe(1);
            expect(tags[0].textContent).toContain('测试字段');
        });

        test('should add custom field on Enter key', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const input = container.querySelector('#custom-field-input');
            input.value = '回车字段';
            
            const event = new KeyboardEvent('keypress', { key: 'Enter' });
            input.dispatchEvent(event);
            
            const tags = container.querySelectorAll('.field-tag');
            expect(tags.length).toBe(1);
        });

        test('should not add duplicate fields', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            
            input.value = '重复字段';
            addBtn.click();
            
            input.value = '重复字段';
            addBtn.click();
            
            const tags = container.querySelectorAll('.field-tag');
            expect(tags.length).toBe(1);
        });

        test('should remove field when clicking remove button', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            
            input.value = '待删除字段';
            addBtn.click();
            
            const removeBtn = container.querySelector('.remove-tag');
            removeBtn.click();
            
            const tags = container.querySelectorAll('.field-tag');
            expect(tags.length).toBe(0);
        });

        test('should populate fields when selecting template', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const select = container.querySelector('#template-select');
            select.value = 'invoice';
            select.dispatchEvent(new Event('change'));
            
            const tags = container.querySelectorAll('.field-tag');
            expect(tags.length).toBe(3); // 发票号码, 开票日期, 金额
        });
    });

    describe('Extract Button State', () => {
        test('should enable extract button when fields and jobId are set', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Add a field
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            input.value = '测试字段';
            addBtn.click();
            
            // Set job ID
            panel.setJobId('test-job-123');
            
            const extractBtn = container.querySelector('#extract-btn');
            expect(extractBtn.disabled).toBe(false);
        });

        test('should disable extract button without jobId', async () => {
            panel = new SmartExtractPanel(container);
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Add a field but no jobId
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            input.value = '测试字段';
            addBtn.click();
            
            const extractBtn = container.querySelector('#extract-btn');
            expect(extractBtn.disabled).toBe(true);
        });
    });

    describe('API Calls', () => {
        test('should call extract API with correct parameters', async () => {
            panel = new SmartExtractPanel(container, { apiBaseUrl: 'http://test' });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Setup for extraction
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            input.value = '测试字段';
            addBtn.click();
            panel.setJobId('test-job-123');
            
            // Mock extract response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        fields: { '测试字段': '测试值' },
                        confidence: 0.95,
                        processing_time: 1.5
                    }
                })
            });
            
            // Trigger extraction
            const extractBtn = container.querySelector('#extract-btn');
            extractBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Check API was called
            expect(global.fetch).toHaveBeenCalledWith(
                'http://test/api/extract-info',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
            );
        });

        test('should display extraction results', async () => {
            panel = new SmartExtractPanel(container, { apiBaseUrl: 'http://test' });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Setup
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            input.value = '金额';
            addBtn.click();
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        fields: { '金额': '1000元' },
                        confidence: 0.9,
                        processing_time: 2.0
                    }
                })
            });
            
            // Extract
            const extractBtn = container.querySelector('#extract-btn');
            extractBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // Check results displayed
            const resultSection = container.querySelector('#result-section');
            expect(resultSection.style.display).toBe('block');
            
            const resultContent = container.querySelector('#result-content');
            expect(resultContent.textContent).toContain('金额');
            expect(resultContent.textContent).toContain('1000元');
        });
    });

    describe('Error Handling', () => {
        test('should display error message on API failure', async () => {
            panel = new SmartExtractPanel(container, { apiBaseUrl: 'http://test' });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Setup
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            input.value = '测试';
            addBtn.click();
            panel.setJobId('test-job-123');
            
            // Mock error response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: false,
                    error: '提取失败'
                })
            });
            
            // Extract
            const extractBtn = container.querySelector('#extract-btn');
            extractBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // Check error displayed
            const errorSection = container.querySelector('#error-section');
            expect(errorSection.style.display).toBe('block');
            
            const errorMessage = container.querySelector('#error-message');
            expect(errorMessage.textContent).toBe('提取失败');
        });

        test('should display network error message', async () => {
            panel = new SmartExtractPanel(container, { apiBaseUrl: 'http://test' });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Setup
            const input = container.querySelector('#custom-field-input');
            const addBtn = container.querySelector('#add-field-btn');
            input.value = '测试';
            addBtn.click();
            panel.setJobId('test-job-123');
            
            // Mock network error
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            // Extract
            const extractBtn = container.querySelector('#extract-btn');
            extractBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // Check error displayed
            const errorSection = container.querySelector('#error-section');
            expect(errorSection.style.display).toBe('block');
            
            const errorMessage = container.querySelector('#error-message');
            expect(errorMessage.textContent).toContain('网络错误');
        });
    });

    describe('Close Button', () => {
        test('should call onClose callback when close button clicked', async () => {
            const onClose = jest.fn();
            panel = new SmartExtractPanel(container, { onClose });
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const closeBtn = container.querySelector('.close-btn');
            closeBtn.click();
            
            expect(onClose).toHaveBeenCalled();
        });
    });
});
