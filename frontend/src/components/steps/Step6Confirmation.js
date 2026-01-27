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
        console.log('Step6Confirmation: Showing Step 6 UI');
        
        // 更新步骤状态 - 将步骤6设为激活状态
        this.updateStepStatus();
        
        // 更新左侧面板标题为"财务确认"
        const editorPanelHeader = document.querySelector('.editor-panel-header > span');
        if (editorPanelHeader) editorPanelHeader.textContent = '📋 财务确认';
        
        // 隐藏步骤5界面
        const step5Container = document.getElementById('step5Container');
        if (step5Container) step5Container.style.display = 'none';
        
        // 确保步骤4的元素也隐藏
        const blockList = document.getElementById('blockList');
        const confirmArea = document.getElementById('preEntryConfirmArea');
        const imagePanel = document.querySelector('.image-panel');
        const downloadButtons = document.getElementById('downloadButtons');
        const confidenceReport = document.getElementById('confidenceReport');
        const editModeToggle = document.getElementById('editModeToggle');
        
        if (blockList) blockList.style.display = 'none';
        if (confirmArea) confirmArea.style.display = 'none';
        if (imagePanel) imagePanel.style.display = 'none';
        if (downloadButtons) downloadButtons.style.display = 'none';
        if (confidenceReport) confidenceReport.style.display = 'none';
        if (editModeToggle) editModeToggle.style.display = 'none';
        
        this.render();
        this.bindEvents();
    }
    
    /**
     * 更新步骤状态
     */
    updateStepStatus() {
        console.log('Step6: Updating step status');
        
        // 使用全局统一的 updateStepStatus 函数（确保进度线正确更新）
        if (typeof window.updateStepStatus === 'function') {
            window.updateStepStatus(5, 'completed', '✓');
            window.updateStepStatus(6, 'active');
            console.log('Step6: Updated status via window.updateStepStatus');
            return;
        }
        
        // 备用方法: 通过 window.app
        if (window.app && typeof window.app.setStepStatus === 'function') {
            window.app.setStepStatus(5, 'completed', '✓');
            window.app.setStepStatus(6, 'active');
            console.log('Step6: Updated status via window.app');
            return;
        }
        
        // 最后备用: 直接操作 DOM
        console.log('Step6: Updating status via DOM (fallback)');
        
        // 更新步骤5为完成
        const step5 = document.getElementById('step5');
        if (step5) {
            step5.classList.remove('active', 'waiting', 'error');
            step5.classList.add('completed');
            const step5Time = document.getElementById('step5Time');
            if (step5Time) step5Time.textContent = '✓';
        }
        
        // 更新步骤6为激活
        const step6 = document.getElementById('step6');
        if (step6) {
            step6.classList.remove('completed', 'waiting', 'error');
            step6.classList.add('active');
        }
        
        // 更新进度线
        const workflowSteps = document.getElementById('workflowSteps');
        if (workflowSteps) {
            workflowSteps.setAttribute('data-current-step', '6');
        }
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
            step6Container.style.cssText = 'display: none; padding: 15px; height: 100%; overflow: auto;';
            editorContainer.appendChild(step6Container);
        }
        
        // 使用全局 stateManager 确保获取到步骤5保存的数据
        const globalStateManager = window.stateManager || stateManager;
        
        const checkpointResults = globalStateManager.get('checkpointResults') || [];
        const extractedData = globalStateManager.get('extractedData') || {};
        const corrections = globalStateManager.get('corrections') || [];
        const selectedTemplate = globalStateManager.get('selectedTemplate');
        
        console.log('Step6: Rendering with data from stateManager');
        console.log('Step6: checkpointResults:', checkpointResults.length);
        console.log('Step6: extractedData:', Object.keys(extractedData).length, 'fields');
        console.log('Step6: selectedTemplate:', selectedTemplate ? selectedTemplate.name : 'none');
        
        // 计算统计信息
        const totalFields = Object.keys(extractedData).length;
        const foundFields = Object.values(extractedData).filter(v => v && v !== '未找到' && v !== 'null' && v !== null).length;
        const avgConfidence = checkpointResults.length > 0 
            ? (checkpointResults.reduce((sum, r) => sum + (r.confidence || 0), 0) / checkpointResults.length * 100).toFixed(0)
            : 0;
        
        step6Container.innerHTML = `
            <div class="step6-content" style="display: flex; flex-direction: column; height: 100%; gap: 15px;">
                <!-- 标题栏 -->
                <div class="step6-header" style="flex-shrink: 0; text-align: center; padding-bottom: 10px; border-bottom: 2px solid #e9ecef;">
                    <h3 style="margin: 0 0 8px 0; color: #333; font-size: 18px;">📋 财务确认</h3>
                    <div style="display: flex; justify-content: center; gap: 20px; font-size: 13px; color: #666;">
                        <span>📄 模板: <strong style="color: #3498db;">${selectedTemplate ? selectedTemplate.name : '自定义'}</strong></span>
                        <span>📊 字段: <strong style="color: #28a745;">${foundFields}/${totalFields}</strong></span>
                        <span>✅ 检查点: <strong style="color: #17a2b8;">${checkpointResults.length}</strong></span>
                        <span>📈 平均置信度: <strong style="color: ${avgConfidence >= 80 ? '#28a745' : avgConfidence >= 50 ? '#ffc107' : '#dc3545'};">${avgConfidence}%</strong></span>
                    </div>
                </div>
                
                <!-- 上半部：检查点问答结果 -->
                <div class="checkpoint-section" style="flex: 0.8; min-height: 180px; display: flex; flex-direction: column; overflow: hidden;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-shrink: 0;">
                        <h4 style="margin: 0; color: #333; font-size: 15px;">
                            ✅ 检查点验证结果
                            <span style="font-size: 12px; color: #666; font-weight: normal; margin-left: 8px;">(${checkpointResults.length} 项问答)</span>
                        </h4>
                    </div>
                    <div id="checkpointAnswersList" style="flex: 1; background: linear-gradient(135deg, #f0f9ff 0%, #e8f4fd 100%); border: 1px solid #b8daff; border-radius: 10px; padding: 12px; overflow-y: auto;">
                        ${this.renderCheckpointAnswers(checkpointResults)}
                    </div>
                </div>
                
                <!-- 下半部：提取数据 JSON -->
                <div class="extracted-data-section" style="flex: 1.2; min-height: 280px; display: flex; flex-direction: column; overflow: hidden;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-shrink: 0;">
                        <h4 style="margin: 0; color: #333; font-size: 15px;">
                            📊 关键词提取结果
                            <span style="font-size: 12px; color: #666; font-weight: normal; margin-left: 8px;">(表格格式)</span>
                        </h4>
                        <div style="display: flex; gap: 8px;">
                            <button id="toggleViewBtn" style="background: #6c757d; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                                { } JSON视图
                            </button>
                            <button id="copyJsonBtn" style="background: #17a2b8; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;">
                                📋 复制JSON
                            </button>
                        </div>
                    </div>
                    <div id="extractedDataContainer" style="flex: 1; background: #f8f9fa; border: 1px solid #ddd; border-radius: 10px; overflow: hidden;">
                        <div id="jsonView" style="display: none; height: 100%; overflow: auto;">
                            <pre id="jsonDataDisplay" style="margin: 0; padding: 15px; font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 13px; line-height: 1.6; color: #333;">${this.formatJsonWithHighlight(extractedData)}</pre>
                        </div>
                        <div id="tableView" style="height: 100%; overflow: auto; padding: 15px;">
                            ${this.renderExtractedDataTable(extractedData)}
                        </div>
                    </div>
                </div>
                
                <!-- 修正记录（如果有） -->
                ${corrections.length > 0 ? `
                <div class="corrections-summary" style="flex-shrink: 0; background: #fff3cd; border: 1px solid #ffc107; border-radius: 10px; padding: 12px;">
                    <h4 style="margin: 0 0 8px 0; color: #856404; font-size: 14px;">
                        ✏️ 用户修正记录 <span style="font-size: 12px; font-weight: normal;">(${corrections.length} 处)</span>
                    </h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${corrections.slice(0, 5).map((c, idx) => `
                            <span style="background: #ffeeba; padding: 4px 10px; border-radius: 4px; font-size: 12px;">
                                Block #${c.blockIndex + 1}: ${c.correctedText.substring(0, 20)}${c.correctedText.length > 20 ? '...' : ''}
                            </span>
                        `).join('')}
                        ${corrections.length > 5 ? `<span style="color: #856404; font-size: 12px;">+${corrections.length - 5} 更多</span>` : ''}
                    </div>
                </div>
                ` : ''}
                
                <!-- 操作按钮 - 暂时隐藏 -->
                <!-- 
                <div class="action-buttons" style="flex-shrink: 0; display: flex; justify-content: center; gap: 20px; padding: 15px 0; border-top: 2px solid #e9ecef;">
                    <button id="confirmFinalBtn" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border: none; padding: 12px 40px; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 600; box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3); transition: all 0.2s;">
                        ✓ 确认提交
                    </button>
                    <button id="rejectFinalBtn" style="background: linear-gradient(135deg, #dc3545 0%, #e74c3c 100%); color: white; border: none; padding: 12px 40px; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 600; box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3); transition: all 0.2s;">
                        ✗ 驳回修改
                    </button>
                    <button id="backToStep5Btn" style="background: #6c757d; color: white; border: none; padding: 12px 30px; border-radius: 8px; cursor: pointer; font-size: 14px;">
                        ← 返回上一步
                    </button>
                </div>
                -->
            </div>
        `;
        
        step6Container.style.display = 'block';
    }
    
    /**
     * 格式化 JSON 并高亮显示
     */
    formatJsonWithHighlight(data) {
        const jsonStr = JSON.stringify(data, null, 2);
        // 高亮 key 和 value
        return jsonStr
            .replace(/"([^"]+)":/g, '<span style="color: #881391;">"$1"</span>:')
            .replace(/: "([^"]+)"/g, ': <span style="color: #1a1aa6;">"$1"</span>')
            .replace(/: (null)/g, ': <span style="color: #999; font-style: italic;">$1</span>')
            .replace(/: (\d+\.?\d*)/g, ': <span style="color: #098658;">$1</span>');
    }
    
    /**
     * 渲染提取数据表格视图
     */
    renderExtractedDataTable(data) {
        if (!data || Object.keys(data).length === 0) {
            return '<div style="color: #666; text-align: center; padding: 20px;">暂无提取数据</div>';
        }
        
        let html = '<table style="width: 100%; border-collapse: collapse; font-size: 13px;">';
        html += '<thead><tr style="background: #e9ecef;"><th style="padding: 10px; border: 1px solid #ddd; text-align: left; width: 35%;">字段名</th><th style="padding: 10px; border: 1px solid #ddd; text-align: left;">提取值</th><th style="padding: 10px; border: 1px solid #ddd; text-align: center; width: 80px;">状态</th></tr></thead>';
        html += '<tbody>';
        
        Object.entries(data).forEach(([key, value]) => {
            const isEmpty = value === null || value === undefined || value === '' || value === '未找到' || value === 'null';
            const statusIcon = isEmpty ? '⚠️' : '✅';
            const statusColor = isEmpty ? '#ffc107' : '#28a745';
            const rowBg = isEmpty ? '#fff8e1' : '#ffffff';
            const displayValue = isEmpty ? '<span style="color: #999; font-style: italic;">未找到</span>' : value;
            
            html += `<tr style="background: ${rowBg};">
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: 500; color: #333;">${key}</td>
                <td style="padding: 10px; border: 1px solid #ddd; color: #495057;">${displayValue}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: ${statusColor};">${statusIcon}</td>
            </tr>`;
        });
        
        html += '</tbody></table>';
        return html;
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
        // 切换视图（JSON/表格）
        const toggleViewBtn = document.getElementById('toggleViewBtn');
        if (toggleViewBtn) {
            toggleViewBtn.addEventListener('click', () => this.toggleView());
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
        
        // 返回上一步按钮
        const backBtn = document.getElementById('backToStep5Btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => this.backToStep5());
        }
    }
    
    /**
     * 切换 JSON/表格视图
     */
    toggleView() {
        const jsonView = document.getElementById('jsonView');
        const tableView = document.getElementById('tableView');
        const toggleBtn = document.getElementById('toggleViewBtn');
        
        if (jsonView && tableView && toggleBtn) {
            if (jsonView.style.display !== 'none') {
                jsonView.style.display = 'none';
                tableView.style.display = 'block';
                toggleBtn.textContent = '{ } JSON视图';
            } else {
                jsonView.style.display = 'block';
                tableView.style.display = 'none';
                toggleBtn.textContent = '📋 表格视图';
            }
        }
    }
    
    /**
     * 返回步骤5
     */
    backToStep5() {
        console.log('Step6Confirmation: Returning to Step 5');
        
        // 隐藏步骤6界面
        const step6Container = document.getElementById('step6Container');
        if (step6Container) step6Container.style.display = 'none';
        
        // 显示步骤5界面
        if (window.step5Component) {
            window.step5Component.show();
        }
        
        // 更新步骤状态
        if (window.app) {
            window.app.setStepStatus(5, 'active');
            window.app.setStepStatus(6, 'waiting');
        }
    }

    /**
     * 复制 JSON
     */
    async copyJson() {
        const globalStateManager = window.stateManager || stateManager;
        const extractedData = globalStateManager.get('extractedData') || {};
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
        
        const globalStateManager = window.stateManager || stateManager;
        
        try {
            const finalResult = {
                jobId: globalStateManager.get('jobId'),
                filename: globalStateManager.get('filename'),
                extractedData: globalStateManager.get('extractedData'),
                checkpointResults: globalStateManager.get('checkpointResults'),
                corrections: globalStateManager.get('corrections'),
                status: 'confirmed',
                confirmedAt: new Date().toISOString()
            };
            
            // 保存到后端
            await this.saveFinalResult(finalResult);
            
            globalStateManager.set('finalResult', finalResult);
            globalStateManager.set('finalStatus', 'confirmed');
            
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
        
        const globalStateManager = window.stateManager || stateManager;
        globalStateManager.set('finalStatus', 'rejected');
        eventBus.emit(EVENTS.FINAL_REJECTED);
        
        // 返回步骤4
        this.returnToStep4();
    }
    
    /**
     * 返回步骤4界面
     */
    returnToStep4() {
        console.log('Step6Confirmation: Returning to Step 4');
        
        // 隐藏步骤6界面
        const step6Container = document.getElementById('step6Container');
        if (step6Container) step6Container.style.display = 'none';
        
        // 显示步骤4界面元素
        const blockList = document.getElementById('blockList');
        const confirmArea = document.getElementById('preEntryConfirmArea');
        const imagePanel = document.querySelector('.image-panel');
        const downloadButtons = document.getElementById('downloadButtons');
        const confidenceReport = document.getElementById('confidenceReport');
        const editModeToggle = document.getElementById('editModeToggle');
        
        if (blockList) blockList.style.display = 'block';
        if (confirmArea) confirmArea.style.display = 'block';
        if (imagePanel) imagePanel.style.display = 'flex';
        if (downloadButtons) downloadButtons.style.display = 'flex';
        if (confidenceReport) confidenceReport.style.display = 'block';
        if (editModeToggle) editModeToggle.style.display = 'flex';
        
        // 更新步骤状态
        if (window.app) {
            window.app.setStepStatus(4, 'active');
            window.app.setStepStatus(5, 'waiting');
            window.app.setStepStatus(6, 'waiting');
        }
    }

    /**
     * 保存最终结果到后端
     */
    async saveFinalResult(result) {
        const globalStateManager = window.stateManager || stateManager;
        const jobId = globalStateManager.get('jobId');
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
            const globalSM = window.stateManager || stateManager;
            const result = globalSM.get('finalResult');
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
