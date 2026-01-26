/**
 * DocumentQA.js - 文档问答面板组件
 * 
 * 提供问答输入框、回答显示和问答历史记录功能
 */

class DocumentQAPanel {
    constructor(container, options = {}) {
        this.container = container;
        this.options = {
            apiBaseUrl: options.apiBaseUrl || '',
            onAnswer: options.onAnswer || null,
            onClose: options.onClose || null,
            maxHistory: options.maxHistory || 10,
            ...options
        };
        
        this.currentJobId = null;
        this.isLoading = false;
        this.history = [];
        
        this.init();
    }
    
    init() {
        this.render();
        this.bindEvents();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="document-qa-panel">
                <div class="panel-header">
                    <h3>💬 文档问答</h3>
                    <div class="header-actions">
                        <button class="export-btn" title="导出对话日志">📥</button>
                        <button class="close-btn" title="关闭">&times;</button>
                    </div>
                </div>
                
                <div class="panel-body">
                    <!-- 问答历史 -->
                    <div class="qa-history" id="qa-history">
                        <div class="history-placeholder">
                            <p>👋 你好！我可以回答关于这份文档的问题。</p>
                            <p class="hint">试试问我：</p>
                            <ul class="suggestions">
                                <li data-question="这份文档的主要内容是什么？">这份文档的主要内容是什么？</li>
                                <li data-question="文档中提到了哪些关键信息？">文档中提到了哪些关键信息？</li>
                                <li data-question="请总结一下这份文档">请总结一下这份文档</li>
                            </ul>
                        </div>
                    </div>
                    
                    <!-- 输入区域 -->
                    <div class="qa-input-area">
                        <div class="input-wrapper">
                            <textarea id="qa-input" 
                                      placeholder="输入你的问题..." 
                                      rows="2"></textarea>
                            <button id="qa-submit-btn" class="submit-btn" disabled>
                                <span class="btn-icon">➤</span>
                            </button>
                        </div>
                        <div class="input-hint">按 Enter 发送，Shift+Enter 换行</div>
                    </div>
                </div>
            </div>
        `;
        
        this.addStyles();
    }
    
    addStyles() {
        if (document.getElementById('document-qa-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'document-qa-styles';
        style.textContent = `
            .document-qa-panel {
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.15);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 450px;
                width: 100%;
                display: flex;
                flex-direction: column;
                max-height: 500px;
            }
            
            .document-qa-panel .panel-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                border-bottom: 1px solid #eee;
                background: #f8f9fa;
                border-radius: 8px 8px 0 0;
            }
            
            .document-qa-panel .panel-header h3 {
                margin: 0;
                font-size: 16px;
                color: #333;
            }
            
            .document-qa-panel .header-actions {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .document-qa-panel .export-btn {
                background: none;
                border: 1px solid #ddd;
                font-size: 14px;
                cursor: pointer;
                color: #666;
                padding: 4px 8px;
                border-radius: 4px;
                transition: all 0.2s;
            }
            
            .document-qa-panel .export-btn:hover {
                background: #f0f0f0;
                border-color: #ccc;
                color: #333;
            }
            
            .document-qa-panel .export-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            
            .document-qa-panel .close-btn {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
                color: #666;
                padding: 0 4px;
            }
            
            .document-qa-panel .close-btn:hover {
                color: #333;
            }
            
            .document-qa-panel .panel-body {
                display: flex;
                flex-direction: column;
                flex: 1;
                overflow: hidden;
            }
            
            .document-qa-panel .qa-history {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
                min-height: 200px;
            }
            
            .document-qa-panel .history-placeholder {
                color: #666;
                font-size: 14px;
            }
            
            .document-qa-panel .history-placeholder p {
                margin: 0 0 8px 0;
            }
            
            .document-qa-panel .history-placeholder .hint {
                color: #888;
                font-size: 13px;
            }
            
            .document-qa-panel .suggestions {
                list-style: none;
                padding: 0;
                margin: 8px 0 0 0;
            }
            
            .document-qa-panel .suggestions li {
                padding: 8px 12px;
                background: #f0f7ff;
                border-radius: 4px;
                margin-bottom: 6px;
                cursor: pointer;
                font-size: 13px;
                color: #1a73e8;
                transition: background 0.2s;
            }
            
            .document-qa-panel .suggestions li:hover {
                background: #e3f0ff;
            }
            
            .document-qa-panel .qa-item {
                margin-bottom: 16px;
            }
            
            .document-qa-panel .qa-question {
                background: #e8f4fd;
                padding: 10px 14px;
                border-radius: 12px 12px 12px 4px;
                margin-bottom: 8px;
                font-size: 14px;
                color: #1a73e8;
            }
            
            .document-qa-panel .qa-answer {
                background: #f8f9fa;
                padding: 12px 14px;
                border-radius: 12px 12px 4px 12px;
                font-size: 14px;
                color: #333;
                line-height: 1.5;
            }
            
            .document-qa-panel .qa-answer.loading {
                color: #888;
            }
            
            .document-qa-panel .qa-answer .typing-indicator {
                display: inline-flex;
                gap: 4px;
            }
            
            .document-qa-panel .qa-answer .typing-indicator span {
                width: 6px;
                height: 6px;
                background: #888;
                border-radius: 50%;
                animation: typing 1.4s infinite ease-in-out;
            }
            
            .document-qa-panel .qa-answer .typing-indicator span:nth-child(1) {
                animation-delay: 0s;
            }
            
            .document-qa-panel .qa-answer .typing-indicator span:nth-child(2) {
                animation-delay: 0.2s;
            }
            
            .document-qa-panel .qa-answer .typing-indicator span:nth-child(3) {
                animation-delay: 0.4s;
            }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-4px); }
            }
            
            .document-qa-panel .qa-references {
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid #eee;
                font-size: 12px;
                color: #666;
            }
            
            .document-qa-panel .qa-references .ref-label {
                font-weight: 500;
                margin-bottom: 4px;
            }
            
            .document-qa-panel .qa-references .ref-item {
                background: #fff;
                border: 1px solid #e0e0e0;
                padding: 6px 10px;
                border-radius: 4px;
                margin-top: 4px;
                font-style: italic;
            }
            
            .document-qa-panel .qa-meta {
                margin-top: 6px;
                font-size: 11px;
                color: #999;
            }
            
            .document-qa-panel .qa-input-area {
                padding: 12px 16px;
                border-top: 1px solid #eee;
                background: #fafafa;
            }
            
            .document-qa-panel .input-wrapper {
                display: flex;
                gap: 8px;
                align-items: flex-end;
            }
            
            .document-qa-panel .input-wrapper textarea {
                flex: 1;
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                resize: none;
                font-family: inherit;
                line-height: 1.4;
            }
            
            .document-qa-panel .input-wrapper textarea:focus {
                outline: none;
                border-color: #4a90d9;
                box-shadow: 0 0 0 2px rgba(74, 144, 217, 0.2);
            }
            
            .document-qa-panel .submit-btn {
                width: 40px;
                height: 40px;
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            
            .document-qa-panel .submit-btn:hover:not(:disabled) {
                background: #1557b0;
            }
            
            .document-qa-panel .submit-btn:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            
            .document-qa-panel .submit-btn .btn-icon {
                font-size: 16px;
            }
            
            .document-qa-panel .input-hint {
                font-size: 11px;
                color: #999;
                margin-top: 6px;
            }
            
            .document-qa-panel .error-answer {
                color: #dc2626;
                background: #fef2f2;
            }
        `;
        document.head.appendChild(style);
    }
    
    bindEvents() {
        // 关闭按钮
        this.container.querySelector('.close-btn').addEventListener('click', () => {
            if (this.options.onClose) this.options.onClose();
        });
        
        // 导出按钮
        this.container.querySelector('.export-btn').addEventListener('click', () => {
            this.exportConversationLog();
        });
        
        // 输入框
        const input = this.container.querySelector('#qa-input');
        const submitBtn = this.container.querySelector('#qa-submit-btn');
        
        input.addEventListener('input', () => {
            this.updateSubmitButton();
        });
        
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.submitQuestion();
            }
        });
        
        submitBtn.addEventListener('click', () => {
            this.submitQuestion();
        });
        
        // 建议问题点击
        this.container.querySelectorAll('.suggestions li').forEach(li => {
            li.addEventListener('click', () => {
                const question = li.dataset.question;
                input.value = question;
                this.updateSubmitButton();
                this.submitQuestion();
            });
        });
    }
    
    updateSubmitButton() {
        const input = this.container.querySelector('#qa-input');
        const submitBtn = this.container.querySelector('#qa-submit-btn');
        submitBtn.disabled = !input.value.trim() || !this.currentJobId || this.isLoading;
    }
    
    setJobId(jobId) {
        this.currentJobId = jobId;
        this.updateSubmitButton();
    }
    
    async submitQuestion() {
        const input = this.container.querySelector('#qa-input');
        const question = input.value.trim();
        
        if (!question || !this.currentJobId || this.isLoading) return;
        
        // 清空输入
        input.value = '';
        this.updateSubmitButton();
        
        // 隐藏占位符
        const placeholder = this.container.querySelector('.history-placeholder');
        if (placeholder) placeholder.style.display = 'none';
        
        // 添加问题到历史
        this.addQuestionToHistory(question);
        
        // 显示加载状态
        const loadingId = this.addLoadingAnswer();
        
        this.isLoading = true;
        this.updateSubmitButton();
        
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/document-qa`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: this.currentJobId,
                    question: question
                })
            });
            
            const data = await response.json();
            
            // 移除加载状态
            this.removeLoadingAnswer(loadingId);
            
            if (data.success) {
                this.addAnswerToHistory(data.data);
                
                // 保存到历史
                this.history.push({
                    question,
                    answer: data.data
                });
                
                // 限制历史数量
                if (this.history.length > this.options.maxHistory) {
                    this.history.shift();
                }
                
                if (this.options.onAnswer) {
                    this.options.onAnswer(data.data);
                }
            } else {
                this.addErrorAnswer(data.error || '回答失败');
            }
        } catch (error) {
            console.error('QA failed:', error);
            this.removeLoadingAnswer(loadingId);
            this.addErrorAnswer('网络错误，请稍后重试');
        } finally {
            this.isLoading = false;
            this.updateSubmitButton();
        }
    }
    
    addQuestionToHistory(question) {
        const historyContainer = this.container.querySelector('#qa-history');
        
        const item = document.createElement('div');
        item.className = 'qa-item';
        item.innerHTML = `
            <div class="qa-question">${this.escapeHtml(question)}</div>
        `;
        
        historyContainer.appendChild(item);
        this.scrollToBottom();
        
        return item;
    }
    
    addLoadingAnswer() {
        const historyContainer = this.container.querySelector('#qa-history');
        const lastItem = historyContainer.querySelector('.qa-item:last-child');
        
        const loadingId = 'loading-' + Date.now();
        const answerDiv = document.createElement('div');
        answerDiv.className = 'qa-answer loading';
        answerDiv.id = loadingId;
        answerDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        
        lastItem.appendChild(answerDiv);
        this.scrollToBottom();
        
        return loadingId;
    }
    
    removeLoadingAnswer(loadingId) {
        const loading = this.container.querySelector(`#${loadingId}`);
        if (loading) loading.remove();
    }
    
    addAnswerToHistory(result) {
        const historyContainer = this.container.querySelector('#qa-history');
        const lastItem = historyContainer.querySelector('.qa-item:last-child');
        
        let referencesHtml = '';
        if (result.references && result.references.length > 0) {
            referencesHtml = `
                <div class="qa-references">
                    <div class="ref-label">📎 参考原文：</div>
                    ${result.references.map(ref => `
                        <div class="ref-item">"${this.escapeHtml(ref)}"</div>
                    `).join('')}
                </div>
            `;
        }
        
        const confidence = (result.confidence * 100).toFixed(0);
        const time = result.processing_time.toFixed(2);
        
        const answerDiv = document.createElement('div');
        answerDiv.className = 'qa-answer';
        answerDiv.innerHTML = `
            <div class="answer-text">${this.escapeHtml(result.answer)}</div>
            ${referencesHtml}
            <div class="qa-meta">置信度: ${confidence}% | 耗时: ${time}s</div>
        `;
        
        lastItem.appendChild(answerDiv);
        this.scrollToBottom();
    }
    
    addErrorAnswer(message) {
        const historyContainer = this.container.querySelector('#qa-history');
        const lastItem = historyContainer.querySelector('.qa-item:last-child');
        
        const answerDiv = document.createElement('div');
        answerDiv.className = 'qa-answer error-answer';
        answerDiv.innerHTML = `⚠️ ${this.escapeHtml(message)}`;
        
        lastItem.appendChild(answerDiv);
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        const historyContainer = this.container.querySelector('#qa-history');
        historyContainer.scrollTop = historyContainer.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    clearHistory() {
        this.history = [];
        const historyContainer = this.container.querySelector('#qa-history');
        historyContainer.innerHTML = `
            <div class="history-placeholder">
                <p>👋 你好！我可以回答关于这份文档的问题。</p>
                <p class="hint">试试问我：</p>
                <ul class="suggestions">
                    <li data-question="这份文档的主要内容是什么？">这份文档的主要内容是什么？</li>
                    <li data-question="文档中提到了哪些关键信息？">文档中提到了哪些关键信息？</li>
                    <li data-question="请总结一下这份文档">请总结一下这份文档</li>
                </ul>
            </div>
        `;
        
        // 重新绑定建议点击事件
        historyContainer.querySelectorAll('.suggestions li').forEach(li => {
            li.addEventListener('click', () => {
                const question = li.dataset.question;
                const input = this.container.querySelector('#qa-input');
                input.value = question;
                this.updateSubmitButton();
                this.submitQuestion();
            });
        });
    }
    
    /**
     * 导出对话日志为 Markdown 文件
     */
    exportConversationLog() {
        if (this.history.length === 0) {
            alert('暂无对话记录可导出');
            return;
        }
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `document-qa-log-${timestamp}.md`;
        
        // 构建 Markdown 内容
        let content = `# 文档问答对话日志\n\n`;
        content += `**导出时间**: ${new Date().toLocaleString('zh-CN')}\n`;
        content += `**文档 Job ID**: ${this.currentJobId || '未知'}\n`;
        content += `**对话轮数**: ${this.history.length}\n\n`;
        content += `---\n\n`;
        
        this.history.forEach((item, index) => {
            content += `## 对话 ${index + 1}\n\n`;
            content += `### 🙋 用户问题\n\n`;
            content += `${item.question}\n\n`;
            content += `### 🤖 AI 回答\n\n`;
            content += `${item.answer.answer}\n\n`;
            
            // 添加参考原文
            if (item.answer.references && item.answer.references.length > 0) {
                content += `#### 📎 参考原文\n\n`;
                item.answer.references.forEach((ref, refIndex) => {
                    content += `> ${refIndex + 1}. "${ref}"\n\n`;
                });
            }
            
            // 添加元数据
            content += `#### 📊 元数据\n\n`;
            content += `| 指标 | 值 |\n`;
            content += `|------|----|\n`;
            content += `| 置信度 | ${(item.answer.confidence * 100).toFixed(1)}% |\n`;
            content += `| 处理时间 | ${item.answer.processing_time.toFixed(2)}s |\n`;
            content += `| 文档中找到 | ${item.answer.found_in_document ? '是' : '否'} |\n`;
            
            if (item.answer.timestamp) {
                content += `| 回答时间 | ${new Date(item.answer.timestamp).toLocaleString('zh-CN')} |\n`;
            }
            
            content += `\n---\n\n`;
        });
        
        // 添加技术说明
        content += `## 技术说明\n\n`;
        content += `- **LLM 模型**: Ollama gpt-oss:20b (私有化部署)\n`;
        content += `- **RAG 检索**: 基于向量相似度的文档片段检索\n`;
        content += `- **Embedding**: BAAI/bge-small-zh-v1.5 (中文优化，512维向量)\n`;
        content += `- **向量数据库**: ChromaDB\n`;
        
        // 创建下载
        const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log(`对话日志已导出: ${filename}`);
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DocumentQAPanel;
}
