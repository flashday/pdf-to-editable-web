/**
 * Step6Confirmation - 步骤6：财务确认组件
 * 显示检查点答案和提取数据，支持确认或驳回
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

export class Step6Confirmation {
    constructor(container) {
        this.container = container;
        this.isJsonExpanded = true;
    }

    /**
     * 显示组件
     */
    show() {
        this.render();
        this.bindEvents();
    }

    /**
     * 隐藏组件
     */
    hide() {
        const container = document.getElementById('step6Container');
        if (container) {
            container.style.display = 'none';
        }
    }

    /**
     * 渲染界面
     */
    render() {
        const editorContainer = document.querySelector('.editor-container');
        if (!editorContainer) return;
        
        // 创建步骤6专用容器
        let step6Container = document.getElementById('step6Container');
        if (!step6Container) {
            step6Container = document.createElement('div');
            step6Container.id = 'step6Container';
            step6Container.style.cssText = 'display: none; padding: 15px;';
            editorContainer.appendChild(step6Container);
        }
        
        const checkpointResults = stateManager.get('checkpointResults') || [];
        const extractedData = stateManager.get('extractedData') || {};
        const corrections = stateManager.get('corrections') || [];
        
        step6Container.innerHTML = `
            <div class="step6-content">
                <h3 style="margin: 0 0 20px 0; color: #333; text-align: center;">📋 财务确认</h3>
                
                <!-- 检查点答案区 -->
                <div class="checkpoint-answers-section" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333; display: flex; align-items: center; gap: 8px;">
                        <span>✅ 检查点验证结果</span>
                        <span style="font-size: 12px; color: #666; font-weight: normal;">(${checkpointResults.length} 项)</span>
                    </h4>
                    <div id="checkpointAnswersList" style="background: #f0f9ff; border: 1px solid #b8daff; border-radius: 8px; padding: 15px;">
                        ${this.renderCheckpointAnswers(checkpointResults)}
                    </div>
                </div>
                
                <!-- 提取数据区 -->
                <div class="extracted-data-section" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333; display: flex; align-items: center; justify-content: space-between;">
                        <span>📊 提取数据 (JSON)</span>
                        <div style="display: flex; gap: 8px;">
                            <button id="toggleJsonBtn" style="background: #6c757d; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                                ${this.isJsonExpanded ? '收起' : '展开'}
                            </button>
                            <button id="copyJsonBtn" style="background: #17a2b8; color: white; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                                📋 复制
                            </button>
                        </div>
                    </h4>
                    <div id="jsonDataContainer" style="background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; ${this.isJsonExpanded ? '' : 'max-height: 100px;'}">
                        <pre id="jsonDataDisplay" style="margin: 0; padding: 15px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; overflow: auto; max-height: 400px;">${JSON.stringify(extractedData, null, 2)}</pre>
                    </div>
                </div>
                
                <!-- 修正记录摘要 -->
                ${corrections.length > 0 ? `
                <div class="corrections-summary" style="margin-bottom: 20px;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">
                        ✏️ 用户修正记录 <span style="font-size: 12px; color: #666; font-weight: normal;">(${corrections.length} 处)</span>
                    </h4>
                    <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 15px;">
                        ${corrections.map((c, idx) => `
                            <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #ffeeba;">
                                <span style="font-weight: 600;">Block #${c.blockIndex + 1}:</span>
                                <span style="color: #856404;">${c.correctedText.substring(0, 50)}${c.correctedText.length > 50 ? '...' : ''}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <!-- 操作按钮 -->
                <div class="action-buttons" style="text-align: center; padding-top: 20px; border-top: 2px solid #ddd;">
                    <button id="confirmFinalBtn" style="background: #28a745; color: white; border: none; padding: 12px 32px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; margin-right: 15px;">
                        ✓ 确认提交
                    </button>
                    <button id="rejectFinalBtn" style="background: #dc3545; color: white; border: none; padding: 12px 32px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600;">
                        ✗ 驳回修改
                    </button>
                </div>
                
                <!-- 提示信息 -->
                <div style="margin-top: 15px; text-align: center; color: #666; font-size: 13px;">
                    <p>确认后将保存最终结果，驳回后将返回预录入步骤重新编辑</p>
                </div>
            </div>
        `;
        
        step6Container.style.display = 'block';
    }

    /**
     * 渲染检查点答案列表
     */
    renderCheckpointAnswers(results) {
        if (!results || results.length === 0) {
            return '<div style="color: #666; text-align: center;">暂无检查点结果</div>';
        }
        
        return results.map((result, idx) => {
            const confidenceColor = result.confidence >= 0.8 ? '#28a745' : result.confidence >= 0.5 ? '#ffc107' : '#dc3545';
            const confidenceIcon = result.confidence >= 0.8 ? '✅' : result.confidence >= 0.5 ? '⚠️' : '❌';
            
            return `
                <div style="margin-bottom: 12px; padding: 12px; background: white; border-radius: 6px; border-left: 4px solid ${confidenceColor};">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <div style="font-weight: 600; color: #333; margin-bottom: 6px;">
                                ${confidenceIcon} Q${idx + 1}: ${result.question}
                            </div>
                            <div style="color: #495057; line-height: 1.5;">
                                ${result.answer}
                            </div>
                        </div>
                        <div style="margin-left: 15px; text-align: right;">
                            <div style="font-size: 12px; color: ${confidenceColor}; font-weight: 600;">
                                ${(result.confidence * 100).toFixed(0)}%
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 展开/收起 JSON
        const toggleBtn = document.getElementById('toggleJsonBtn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleJson());
        }
        
        // 复制 JSON
        const copyBtn = document.getElementById('copyJsonBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyJson());
        }
        
        // 确认按钮
        const confirmBtn = document.getElementById('confirmFinalBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.confirm());
        }
        
        // 驳回按钮
        const rejectBtn = document.getElementById('rejectFinalBtn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => this.reject());
        }
    }

    /**
     * 展开/收起 JSON
     */
    toggleJson() {
        this.isJsonExpanded = !this.isJsonExpanded;
        
        const container = document.getElementById('jsonDataContainer');
        const btn = document.getElementById('toggleJsonBtn');
        
        if (container) {
            container.style.maxHeight = this.isJsonExpanded ? 'none' : '100px';
        }
        if (btn) {
            btn.textContent = this.isJsonExpanded ? '收起' : '展开';
        }
    }

    /**
     * 复制 JSON
     */
    async copyJson() {
        const extractedData = stateManager.get('extractedData') || {};
        const jsonStr = JSON.stringify(extractedData, null, 2);
        
        try {
            await navigator.clipboard.writeText(jsonStr);
            
            const btn = document.getElementById('copyJsonBtn');
            if (btn) {
                const originalText = btn.textContent;
                btn.textContent = '✓ 已复制';
                btn.style.background = '#28a745';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.background = '#17a2b8';
                }, 2000);
            }
        } catch (error) {
            console.error('Copy failed:', error);
            alert('复制失败，请手动复制');
        }
    }

    /**
     * 确认提交
     */
    async confirm() {
        const confirmBtn = document.getElementById('confirmFinalBtn');
        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.textContent = '提交中...';
        }
        
        try {
            const finalResult = {
                jobId: stateManager.get('jobId'),
                filename: stateManager.get('filename'),
                extractedData: stateManager.get('extractedData'),
                checkpointResults: stateManager.get('checkpointResults'),
                corrections: stateManager.get('corrections'),
                status: 'confirmed',
                confirmedAt: new Date().toISOString()
            };
            
            // 保存到后端
            await this.saveFinalResult(finalResult);
            
            stateManager.set('finalResult', finalResult);
            stateManager.set('finalStatus', 'confirmed');
            
            // 显示成功提示
            this.showSuccessMessage();
            
            eventBus.emit(EVENTS.FINAL_CONFIRMED, finalResult);
        } catch (error) {
            console.error('Confirm error:', error);
            alert('提交失败: ' + error.message);
            
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = '✓ 确认提交';
            }
        }
    }

    /**
     * 驳回修改
     */
    reject() {
        if (!confirm('确定要驳回并返回预录入步骤吗？')) {
            return;
        }
        
        stateManager.set('finalStatus', 'rejected');
        eventBus.emit(EVENTS.FINAL_REJECTED);
    }

    /**
     * 保存最终结果到后端
     */
    async saveFinalResult(result) {
        const jobId = stateManager.get('jobId');
        if (!jobId) throw new Error('无任务ID');
        
        const response = await fetch(`/api/final/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(result)
        });
        
        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || '保存失败');
        }
        
        return data;
    }

    /**
     * 显示成功消息
     */
    showSuccessMessage() {
        const container = document.getElementById('step6Container');
        if (!container) return;
        
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 64px; margin-bottom: 20px;">✅</div>
                <h2 style="color: #28a745; margin-bottom: 15px;">提交成功！</h2>
                <p style="color: #666; margin-bottom: 30px;">文档处理已完成，结果已保存</p>
                <div style="display: flex; justify-content: center; gap: 15px;">
                    <button onclick="window.location.reload()" style="background: #3498db; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer;">
                        🔄 处理新文档
                    </button>
                    <button onclick="window.downloadFinalResult()" style="background: #27ae60; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer;">
                        📥 下载结果
                    </button>
                </div>
            </div>
        `;
        
        // 添加下载函数
        window.downloadFinalResult = () => {
            const result = stateManager.get('finalResult');
            if (result) {
                const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `final-result-${result.jobId}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        };
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.Step6Confirmation = Step6Confirmation;
}
