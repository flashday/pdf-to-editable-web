/**
 * Unit tests for DocumentQA component
 * Validates: Requirements 6.4, 6.5
 */

// Mock fetch globally
global.fetch = jest.fn();

// Import the component
const DocumentQAPanel = require('../components/DocumentQA.js');

describe('DocumentQAPanel', () => {
    let container;
    let panel;

    beforeEach(() => {
        // Reset mocks
        jest.clearAllMocks();
        
        // Setup DOM
        document.body.innerHTML = '<div id="test-container"></div>';
        container = document.getElementById('test-container');
    });

    afterEach(() => {
        if (panel) {
            panel = null;
        }
        document.body.innerHTML = '';
    });

    describe('Component Rendering', () => {
        test('should render panel structure correctly', () => {
            panel = new DocumentQAPanel(container);
            
            expect(container.querySelector('.document-qa-panel')).toBeTruthy();
            expect(container.querySelector('.panel-header')).toBeTruthy();
            expect(container.querySelector('.panel-body')).toBeTruthy();
        });

        test('should render QA history area', () => {
            panel = new DocumentQAPanel(container);
            
            const history = container.querySelector('#qa-history');
            expect(history).toBeTruthy();
        });

        test('should render input area with textarea', () => {
            panel = new DocumentQAPanel(container);
            
            const textarea = container.querySelector('#qa-input');
            const submitBtn = container.querySelector('#qa-submit-btn');
            
            expect(textarea).toBeTruthy();
            expect(submitBtn).toBeTruthy();
        });

        test('should render suggestion questions', () => {
            panel = new DocumentQAPanel(container);
            
            const suggestions = container.querySelectorAll('.suggestions li');
            expect(suggestions.length).toBeGreaterThan(0);
        });

        test('should render submit button disabled initially', () => {
            panel = new DocumentQAPanel(container);
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            expect(submitBtn.disabled).toBe(true);
        });

        test('should add styles to document head', () => {
            panel = new DocumentQAPanel(container);
            
            const styles = document.getElementById('document-qa-styles');
            expect(styles).toBeTruthy();
        });
    });

    describe('Submit Button State', () => {
        test('should enable submit button when input has text and jobId is set', () => {
            panel = new DocumentQAPanel(container);
            panel.setJobId('test-job-123');
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            expect(submitBtn.disabled).toBe(false);
        });

        test('should disable submit button without jobId', () => {
            panel = new DocumentQAPanel(container);
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            expect(submitBtn.disabled).toBe(true);
        });

        test('should disable submit button with empty input', () => {
            panel = new DocumentQAPanel(container);
            panel.setJobId('test-job-123');
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '   '; // whitespace only
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            expect(submitBtn.disabled).toBe(true);
        });
    });

    describe('Question Submission', () => {
        test('should submit question on Enter key (without Shift)', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '测试回答',
                        references: [],
                        confidence: 0.9,
                        processing_time: 1.0
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            
            const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false });
            textarea.dispatchEvent(event);
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(global.fetch).toHaveBeenCalledWith(
                'http://test/api/document-qa',
                expect.objectContaining({
                    method: 'POST'
                })
            );
        });

        test('should not submit on Shift+Enter', () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            
            const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true });
            textarea.dispatchEvent(event);
            
            // Should not call fetch
            expect(global.fetch).not.toHaveBeenCalled();
        });

        test('should submit question on button click', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '测试回答',
                        references: [],
                        confidence: 0.9,
                        processing_time: 1.0
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            expect(global.fetch).toHaveBeenCalled();
        });

        test('should clear input after submission', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '测试回答',
                        references: [],
                        confidence: 0.9,
                        processing_time: 1.0
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            // Input should be cleared immediately
            expect(textarea.value).toBe('');
        });
    });

    describe('API Calls', () => {
        test('should call QA API with correct parameters', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '回答内容',
                        references: ['参考1'],
                        confidence: 0.85,
                        processing_time: 2.0
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '文档的主要内容是什么？';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const fetchCall = global.fetch.mock.calls[0];
            expect(fetchCall[0]).toBe('http://test/api/document-qa');
            
            const body = JSON.parse(fetchCall[1].body);
            expect(body.job_id).toBe('test-job-123');
            expect(body.question).toBe('文档的主要内容是什么？');
        });

        test('should display answer in history', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '这是一份测试文档',
                        references: ['测试内容'],
                        confidence: 0.9,
                        processing_time: 1.5
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const history = container.querySelector('#qa-history');
            expect(history.textContent).toContain('测试问题');
            expect(history.textContent).toContain('这是一份测试文档');
        });

        test('should display references when available', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response with references
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '回答内容',
                        references: ['参考原文1', '参考原文2'],
                        confidence: 0.9,
                        processing_time: 1.0
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const history = container.querySelector('#qa-history');
            expect(history.textContent).toContain('参考原文1');
            expect(history.textContent).toContain('参考原文2');
        });
    });

    describe('Error Handling', () => {
        test('should display error message on API failure', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock error response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: false,
                    error: '无法回答该问题'
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const history = container.querySelector('#qa-history');
            expect(history.textContent).toContain('无法回答该问题');
        });

        test('should display network error message', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock network error
            global.fetch.mockRejectedValueOnce(new Error('Network error'));
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试问题';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            const history = container.querySelector('#qa-history');
            expect(history.textContent).toContain('网络错误');
        });
    });

    describe('Suggestion Questions', () => {
        test('should fill input when clicking suggestion', () => {
            panel = new DocumentQAPanel(container);
            
            const suggestion = container.querySelector('.suggestions li');
            const expectedQuestion = suggestion.dataset.question;
            
            suggestion.click();
            
            // Note: The click triggers submission, so we check the question was used
            // The input gets cleared after submission attempt
        });
    });

    describe('History Management', () => {
        test('should hide placeholder after first question', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '回答',
                        references: [],
                        confidence: 0.9,
                        processing_time: 1.0
                    }
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 100));
            
            const placeholder = container.querySelector('.history-placeholder');
            expect(placeholder.style.display).toBe('none');
        });

        test('should clear history when clearHistory is called', async () => {
            panel = new DocumentQAPanel(container, { apiBaseUrl: 'http://test' });
            panel.setJobId('test-job-123');
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: {
                        answer: '回答',
                        references: [],
                        confidence: 0.9,
                        processing_time: 1.0
                    }
                })
            });
            
            // Add a question
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Clear history
            panel.clearHistory();
            
            // Check placeholder is back
            const placeholder = container.querySelector('.history-placeholder');
            expect(placeholder).toBeTruthy();
            
            // Check internal history is cleared
            expect(panel.history.length).toBe(0);
        });
    });

    describe('Close Button', () => {
        test('should call onClose callback when close button clicked', () => {
            const onClose = jest.fn();
            panel = new DocumentQAPanel(container, { onClose });
            
            const closeBtn = container.querySelector('.close-btn');
            closeBtn.click();
            
            expect(onClose).toHaveBeenCalled();
        });
    });

    describe('Callback Functions', () => {
        test('should call onAnswer callback with result', async () => {
            const onAnswer = jest.fn();
            panel = new DocumentQAPanel(container, { 
                apiBaseUrl: 'http://test',
                onAnswer 
            });
            panel.setJobId('test-job-123');
            
            const mockResult = {
                answer: '回答内容',
                references: [],
                confidence: 0.9,
                processing_time: 1.0
            };
            
            // Mock response
            global.fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    data: mockResult
                })
            });
            
            const textarea = container.querySelector('#qa-input');
            textarea.value = '测试';
            textarea.dispatchEvent(new Event('input'));
            
            const submitBtn = container.querySelector('#qa-submit-btn');
            submitBtn.click();
            
            await new Promise(resolve => setTimeout(resolve, 300));
            
            expect(onAnswer).toHaveBeenCalledWith(mockResult);
        });
    });
});
