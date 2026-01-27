/**
 * globalFunctions.js - 全局函数
 * 从 index.html 抽取的全局函数
 */

// 当前视图模式
window.currentViewMode = 'block';
window.markdownCache = null;

// ============================================================
// 历史面板相关
// ============================================================

window.loadHistoryPanel = async function() {
    console.log('loadHistoryPanel called');
    var list = document.getElementById('historyPanelList');
    if (!list) { console.error('historyPanelList not found'); return; }
    
    list.innerHTML = '<div class="history-panel-empty">加载中...</div>';
    
    try {
        var res = await fetch('/api/jobs/history?limit=10');
        var data = await res.json();
        console.log('History data:', data);
        
        if (data.success && data.jobs && data.jobs.length > 0) {
            var sortedJobs = data.jobs.slice().sort(function(a, b) {
                return a.created_at - b.created_at;
            });
            list.innerHTML = sortedJobs.map(function(job, idx) {
                var seq = idx + 1;
                return '<div class="history-panel-item" data-job-id="' + job.job_id + '">' +
                    '<span class="item-seq">' + seq + '</span>' +
                    '<span class="item-icon" onclick="window.loadCachedJob(\'' + job.job_id + '\')">📄</span>' +
                    '<div class="item-info" onclick="window.loadCachedJob(\'' + job.job_id + '\')">' +
                        '<div class="item-name" title="' + job.filename + '">' + job.filename + '</div>' +
                        '<div class="item-meta">' + Math.round(job.processing_time) + 's</div>' +
                    '</div>' +
                    '<span class="item-badge">' + (job.confidence_score ? Math.round(job.confidence_score * 100) + '%' : '-') + '</span>' +
                    '<button class="item-delete" onclick="event.stopPropagation();window.deleteHistoryJob(\'' + job.job_id + '\')" title="删除">🗑</button>' +
                '</div>';
            }).join('');
        } else {
            list.innerHTML = '<div class="history-panel-empty">暂无缓存记录</div>';
        }
    } catch(e) {
        console.error('loadHistoryPanel error:', e);
        list.innerHTML = '<div class="history-panel-empty">加载失败</div>';
    }
};

window.deleteHistoryJob = async function(jobId) {
    if (!confirm('确定删除此缓存记录？')) return;
    try {
        var res = await fetch('/api/jobs/' + jobId, { method: 'DELETE' });
        var data = await res.json();
        if (data.success) {
            console.log('Deleted job:', jobId);
            window.loadHistoryPanel();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch(e) {
        console.error('Delete error:', e);
        alert('删除失败: ' + e.message);
    }
};

window.loadCachedJob = async function(jobId) {
    console.log('Loading cached job:', jobId);
    
    // 安全的步骤状态更新函数
    var setStepStatus = function(step, status, time) {
        if (window.app && typeof window.app.setStepStatus === 'function') {
            window.app.setStepStatus(step, status, time);
        } else {
            // 直接操作 DOM 作为后备方案
            var stepEl = document.getElementById('step' + step);
            if (stepEl) {
                stepEl.classList.remove('completed', 'active', 'waiting', 'error');
                if (status) stepEl.classList.add(status);
            }
            var timeEl = document.getElementById('step' + step + 'Time');
            if (timeEl && time !== undefined) timeEl.textContent = time;
        }
    };
    
    try {
        // 更新步骤状态：从缓存加载，跳过步骤1-3
        setStepStatus(1, 'completed', '✓');
        setStepStatus(2, 'completed', '缓存');
        setStepStatus(3, 'completed', '缓存');
        setStepStatus(4, 'active', '加载中...');
        
        // 立即隐藏上传区域，显示主内容区域（左右分栏）
        var uploadSection = document.querySelector('.upload-section');
        if (uploadSection) {
            uploadSection.style.display = 'none';
            console.log('loadCachedJob: upload-section hidden');
        }
        
        // 显示主内容区域（左边图片，右边编辑器）
        var mainContent = document.getElementById('mainContent');
        if (mainContent) {
            mainContent.classList.add('visible');
            mainContent.style.display = 'flex';
            mainContent.style.flexDirection = 'row';
            mainContent.style.width = '100%';
            mainContent.style.height = 'calc(100vh - 200px)';
            mainContent.style.minHeight = '500px';
            console.log('loadCachedJob: mainContent visible with flex row');
        }
        
        // 确保左侧图像面板可见
        var imagePanel = document.querySelector('.image-panel');
        if (imagePanel) {
            imagePanel.style.display = 'flex';
            imagePanel.style.flex = '0 0 50%';
            imagePanel.style.width = '50%';
            imagePanel.style.maxWidth = '50%';
            console.log('loadCachedJob: image-panel visible (50%)');
        }
        
        // 确保右侧编辑器面板可见
        var editorPanel = document.querySelector('.editor-panel');
        if (editorPanel) {
            editorPanel.style.display = 'flex';
            editorPanel.style.flex = '0 0 50%';
            editorPanel.style.width = '50%';
            editorPanel.style.maxWidth = '50%';
            console.log('loadCachedJob: editor-panel visible (50%)');
        }
        
        var res = await fetch('/api/jobs/' + jobId + '/cached-result');
        var data = await res.json();
        console.log('Cached result:', data);
        if (data.status === 'completed' && data.result) {
            console.log('✅ 缓存加载成功！blocks: ' + data.result.blocks.length);
            if (window.app && typeof window.app.handleProcessingComplete === 'function') {
                var processedData = {
                    blocks: data.result.blocks,
                    confidence_report: data.confidence_report,
                    markdown: data.markdown,
                    cached: true
                };
                await window.app.handleProcessingComplete(processedData, jobId);
                setStepStatus(4, 'completed', '✓');
                
                // 确保确认按钮被渲染
                if (window.app && typeof window.app.renderStep4ConfirmButton === 'function') {
                    console.log('loadCachedJob: Calling renderStep4ConfirmButton');
                    window.app.renderStep4ConfirmButton();
                } else {
                    console.log('loadCachedJob: renderStep4ConfirmButton not available, creating button directly');
                    window.createStep4ConfirmButton();
                }
            } else {
                console.error('window.app.handleProcessingComplete not available');
                alert('❌ 应用未完全加载，请刷新页面后重试');
            }
        } else {
            setStepStatus(4, 'error', '失败');
            // 恢复上传区域显示
            if (uploadSection) uploadSection.style.display = 'block';
            alert('❌ 加载失败: ' + (data.error || '未知错误'));
        }
    } catch(e) {
        console.error('Error:', e);
        setStepStatus(4, 'error', '失败');
        // 恢复上传区域显示
        var uploadSection = document.querySelector('.upload-section');
        if (uploadSection) uploadSection.style.display = 'block';
        alert('❌ 加载失败: ' + e.message);
    }
};

// ============================================================
// 服务状态检查
// ============================================================

window.checkAllServicesStatus = async function() {
    console.log('checkAllServicesStatus called');
    
    try {
        var res = await fetch('/api/services/status');
        var data = await res.json();
        console.log('Services status:', data);
        
        // OCR 状态
        if (data.ocr) {
            if (data.ocr.loaded) {
                var timeStr = data.ocr.time > 0 ? ' (' + data.ocr.time.toFixed(1) + 's)' : '';
                window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'online', '就绪' + timeStr);
            } else if (data.ocr.loading) {
                window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'checking', '加载中...');
            } else {
                window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'offline', data.ocr.error || '未就绪');
            }
        }
        
        // LLM 状态
        if (data.llm) {
            if (data.llm.loaded) {
                window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'online', 'Ollama');
            } else if (data.llm.loading) {
                window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'checking', '检测中...');
            } else {
                window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'offline', data.llm.error || '未连接');
            }
        }
        
        // RAG 状态
        if (data.rag) {
            if (data.rag.loaded) {
                var ragTimeStr = data.rag.time > 0 ? ' (' + data.rag.time.toFixed(1) + 's)' : '';
                window.updateStatusItem('llmRagStatus', 'llmRagText', 'online', '就绪' + ragTimeStr);
            } else if (data.rag.loading) {
                window.updateStatusItem('llmRagStatus', 'llmRagText', 'checking', '加载中...');
            } else {
                window.updateStatusItem('llmRagStatus', 'llmRagText', 'warning', data.rag.error || '未启用');
            }
        }
        
        // 如果还有服务在加载中，继续轮询
        if (!data.all_ready) {
            setTimeout(window.checkAllServicesStatus, 3000);
        }
    } catch (e) {
        console.log('Services status check failed:', e.message);
        window.checkAllServicesStatusFallback();
    }
};

window.checkAllServicesStatusFallback = async function() {
    try {
        var healthRes = await fetch('/api/health');
        var healthData = await healthRes.json();
        if (healthData.status === 'healthy') {
            window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'online', '就绪');
        } else {
            window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'warning', '加载中');
        }
    } catch (e) {
        window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'offline', '离线');
    }
    
    try {
        var llmRes = await fetch('/api/llm/status');
        var llmData = await llmRes.json();
        
        if (llmData.success && llmData.data) {
            var d = llmData.data;
            if (d.llm_available || d.available) {
                window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'online', d.model || 'Ollama');
            } else {
                window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'offline', '未连接');
            }
            if (d.rag_available) {
                window.updateStatusItem('llmRagStatus', 'llmRagText', 'online', '就绪');
            } else {
                window.updateStatusItem('llmRagStatus', 'llmRagText', 'warning', '未启用');
            }
        } else {
            window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'offline', '不可用');
            window.updateStatusItem('llmRagStatus', 'llmRagText', 'offline', '不可用');
        }
    } catch (e) {
        window.updateStatusItem('llmLlmStatus', 'llmLlmText', 'offline', '检测失败');
        window.updateStatusItem('llmRagStatus', 'llmRagText', 'offline', '检测失败');
    }
};

window.updateStatusItem = function(itemId, textId, status, text) {
    var item = document.getElementById(itemId);
    var textEl = document.getElementById(textId);
    if (!item || !textEl) return;
    
    var dot = item.querySelector('.status-dot');
    if (dot) {
        dot.classList.remove('checking', 'online', 'offline', 'warning');
        dot.classList.add(status);
    }
    textEl.classList.remove('online', 'offline', 'warning');
    textEl.classList.add(status);
    textEl.textContent = text;
};

// ============================================================
// 视图切换
// ============================================================

window.switchViewMode = async function(mode) {
    console.log('Switching view mode to:', mode);
    window.currentViewMode = mode;
    
    var blockBtn = document.getElementById('blockModeBtn');
    var mdBtn = document.getElementById('markdownModeBtn');
    var blockList = document.getElementById('blockList');
    var mdView = document.getElementById('markdownView');
    var ocrRegions = document.querySelectorAll('.ocr-region');
    
    if (mode === 'block') {
        blockBtn.classList.add('active');
        mdBtn.classList.remove('active');
        blockList.style.display = 'flex';
        mdView.style.display = 'none';
        ocrRegions.forEach(function(r) { r.style.display = 'block'; });
    } else {
        blockBtn.classList.remove('active');
        mdBtn.classList.add('active');
        blockList.style.display = 'none';
        mdView.style.display = 'block';
        ocrRegions.forEach(function(r) { r.style.display = 'none'; });
        await window.loadMarkdownView();
    }
};

window.loadMarkdownView = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    var mdContent = document.getElementById('markdownContent');
    
    if (!jobId) {
        mdContent.innerHTML = '<div class="markdown-loading">请先上传文件或选择历史任务</div>';
        return;
    }
    
    if (window.markdownCache && window.markdownCache.jobId === jobId) {
        mdContent.innerHTML = window.markdownCache.html;
        return;
    }
    
    mdContent.innerHTML = '<div class="markdown-loading">⏳ 加载Markdown中...</div>';
    
    try {
        var res = await fetch('/api/convert/' + jobId + '/markdown');
        var data = await res.json();
        
        if (data.markdown) {
            var html = window.renderMarkdown(data.markdown);
            mdContent.innerHTML = html;
            window.markdownCache = { jobId: jobId, html: html, raw: data.markdown };
        } else {
            mdContent.innerHTML = '<div class="markdown-loading">❌ Markdown不可用</div>';
        }
    } catch(e) {
        console.error('Load markdown error:', e);
        mdContent.innerHTML = '<div class="markdown-loading">❌ 加载失败: ' + e.message + '</div>';
    }
};

window.renderMarkdown = function(md) {
    if (typeof marked !== 'undefined') {
        marked.setOptions({ gfm: true, breaks: true, tables: true });
        return marked.parse(md);
    } else {
        return '<pre>' + md.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>';
    }
};

// ============================================================
// 下载函数
// ============================================================

window.downloadMarkdown = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    if (!jobId) { alert('无任务ID'); return; }
    
    try {
        if (window.markdownCache && window.markdownCache.jobId === jobId && window.markdownCache.raw) {
            window.downloadBlob(new Blob([window.markdownCache.raw], {type: 'text/markdown'}), 'ocr-result-' + jobId + '.md');
            return;
        }
        
        var res = await fetch('/api/convert/' + jobId + '/markdown');
        var data = await res.json();
        if (data.markdown) {
            window.downloadBlob(new Blob([data.markdown], {type: 'text/markdown'}), 'ocr-result-' + jobId + '.md');
        } else {
            alert('Markdown不可用');
        }
    } catch(e) {
        alert('下载失败: ' + e.message);
    }
};

window.downloadConfidenceLog = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    if (!jobId) { alert('无任务ID'); return; }
    try {
        var res = await fetch('/api/convert/' + jobId + '/confidence-log');
        var data = await res.json();
        if (data.confidence_log) {
            window.downloadBlob(new Blob([data.confidence_log], {type: 'text/markdown'}), 'confidence-log-' + jobId + '.md');
        } else {
            alert('错误: ' + (data.error || '日志不可用'));
        }
    } catch(e) {
        alert('下载失败: ' + e.message);
    }
};

window.downloadPPStructure = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    if (!jobId) { alert('无任务ID'); return; }
    try {
        var res = await fetch('/api/convert/' + jobId + '/raw-output');
        var data = await res.json();
        if (data.ppstructure_json) {
            window.downloadBlob(new Blob([JSON.stringify(data.ppstructure_json, null, 2)], {type: 'application/json'}), 'ppstructure-' + jobId + '.json');
        } else {
            alert('错误: 布局JSON不可用');
        }
    } catch(e) { alert('下载失败: ' + e.message); }
};

window.downloadOriginalFile = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    if (!jobId) { alert('无任务ID'); return; }
    try {
        var res = await fetch('/api/convert/' + jobId + '/original-file');
        if (!res.ok) {
            var errData = await res.json();
            alert('错误: ' + (errData.error || '下载失败'));
            return;
        }
        var contentDisposition = res.headers.get('Content-Disposition');
        var filename = 'original-' + jobId;
        if (contentDisposition) {
            var match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
            }
        }
        var blob = await res.blob();
        window.downloadBlob(blob, filename);
    } catch(e) {
        console.error('Download original file error:', e);
        alert('下载失败: ' + e.message);
    }
};

window.downloadRawOcrJson = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    if (!jobId) { alert('无任务ID'); return; }
    try {
        var res = await fetch('/api/convert/' + jobId + '/raw-output');
        var data = await res.json();
        if (data.raw_json) {
            window.downloadBlob(new Blob([JSON.stringify(data.raw_json, null, 2)], {type: 'application/json'}), 'raw-ocr-' + jobId + '.json');
        } else {
            alert('错误: OCR结果JSON不可用');
        }
    } catch(e) { alert('下载失败: ' + e.message); }
};

window.downloadRawHtml = async function() {
    var jobId = window.app ? window.app.currentJobId : null;
    if (!jobId) { alert('无任务ID'); return; }
    try {
        var res = await fetch('/api/convert/' + jobId + '/raw-output');
        var data = await res.json();
        if (data.raw_html) {
            window.downloadBlob(new Blob([data.raw_html], {type: 'text/html'}), 'raw-ocr-' + jobId + '.html');
        } else {
            alert('错误: HTML结果不可用');
        }
    } catch(e) { alert('下载失败: ' + e.message); }
};

window.downloadBlob = function(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
};

// ============================================================
// 步骤4确认按钮
// ============================================================

window.createStep4ConfirmButton = function() {
    console.log('createStep4ConfirmButton: Creating confirm button');
    var confirmArea = document.getElementById('step4ConfirmArea');
    
    // 如果已存在，先移除
    if (confirmArea) {
        confirmArea.remove();
    }
    
    // 创建确认区域
    confirmArea = document.createElement('div');
    confirmArea.id = 'step4ConfirmArea';
    confirmArea.style.cssText = 'padding: 15px; border-top: 2px solid #28a745; background: linear-gradient(to right, #f8f9fa, #e8f5e9); text-align: center; display: flex; justify-content: center; gap: 15px; align-items: center; flex-shrink: 0; min-height: 60px; position: sticky; bottom: 0; z-index: 100;';
    
    // 提示文字
    var hint = document.createElement('span');
    hint.style.cssText = 'color: #666; font-size: 13px;';
    hint.textContent = '预录入完成后，点击确认进入下一步 →';
    
    // 确认按钮
    var confirmBtn = document.createElement('button');
    confirmBtn.id = 'step4ConfirmBtn';
    confirmBtn.textContent = '✓ 确认并进入步骤5（数据提取）';
    confirmBtn.style.cssText = 'background: #28a745; color: white; border: none; padding: 12px 28px; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.2s; box-shadow: 0 2px 4px rgba(40,167,69,0.3);';
    confirmBtn.onmouseover = function() { 
        this.style.background = '#218838'; 
        this.style.transform = 'translateY(-1px)';
        this.style.boxShadow = '0 4px 8px rgba(40,167,69,0.4)';
    };
    confirmBtn.onmouseout = function() { 
        this.style.background = '#28a745'; 
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 2px 4px rgba(40,167,69,0.3)';
    };
    confirmBtn.onclick = function(e) { 
        e.preventDefault();
        e.stopPropagation();
        console.log('Step 4 confirm button clicked!');
        window.confirmStep4AndProceed();
    };
    
    confirmArea.appendChild(hint);
    confirmArea.appendChild(confirmBtn);
    
    // 添加到编辑器面板底部
    var editorPanel = document.querySelector('.editor-panel');
    if (editorPanel) {
        editorPanel.appendChild(confirmArea);
        console.log('createStep4ConfirmButton: Button added to editor panel');
        
        // 确保按钮可见 - 滚动到底部
        setTimeout(function() {
            confirmArea.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }, 100);
    } else {
        console.error('createStep4ConfirmButton: editor-panel not found!');
    }
};

window.confirmStep4AndProceed = function() {
    console.log('confirmStep4AndProceed: Proceeding to Step 5');
    
    // 确保 finalText 已经计算并保存到全局 stateManager
    if (window.stateManager) {
        // 先从 window.app 同步数据到 stateManager
        if (window.app) {
            if (window.app.ocrRegions && window.app.ocrRegions.length > 0) {
                window.stateManager.set('ocrRegions', window.app.ocrRegions);
                console.log('confirmStep4AndProceed: synced ocrRegions, count:', window.app.ocrRegions.length);
            }
            if (window.app.ocrData) {
                window.stateManager.set('ocrData', window.app.ocrData);
                console.log('confirmStep4AndProceed: synced ocrData');
            }
            if (window.app.currentJobId) {
                window.stateManager.set('jobId', window.app.currentJobId);
            }
        }
        
        var finalText = window.stateManager.getFinalText();
        window.stateManager.set('finalText', finalText);
        console.log('confirmStep4AndProceed: finalText saved, length:', finalText ? finalText.length : 0);
    }
    
    // 更新步骤状态
    if (window.app && typeof window.app.setStepStatus === 'function') {
        window.app.setStepStatus(4, 'completed', '✓');
        window.app.setStepStatus(5, 'active');
    } else {
        // 直接操作 DOM
        var step4 = document.getElementById('step4');
        var step5 = document.getElementById('step5');
        if (step4) {
            step4.classList.remove('active');
            step4.classList.add('completed');
        }
        if (step5) {
            step5.classList.remove('waiting');
            step5.classList.add('active');
        }
    }
    
    // 切换到步骤5界面
    window.switchToStep5UI();
};

window.switchToStep5UI = function() {
    console.log('switchToStep5UI: Switching to Step 5');
    
    // 隐藏步骤4相关界面
    var blockList = document.getElementById('blockList');
    var confirmArea = document.getElementById('step4ConfirmArea');
    var imagePanel = document.querySelector('.image-panel');
    var downloadButtons = document.getElementById('downloadButtons');
    var confidenceReport = document.getElementById('confidenceReport');
    var editModeToggle = document.getElementById('editModeToggle');
    var markdownView = document.getElementById('markdownView');
    
    if (blockList) blockList.style.display = 'none';
    if (confirmArea) confirmArea.style.display = 'none';
    if (imagePanel) imagePanel.style.display = 'none';
    if (downloadButtons) downloadButtons.style.display = 'none';
    if (confidenceReport) confidenceReport.style.display = 'none';
    if (editModeToggle) editModeToggle.style.display = 'none';
    if (markdownView) markdownView.style.display = 'none';
    
    // 隐藏 OCR 区域标记
    document.querySelectorAll('.ocr-region').forEach(function(el) { el.style.display = 'none'; });
    
    // 显示步骤5界面
    if (window.step5Component && typeof window.step5Component.show === 'function') {
        window.step5Component.show();
    } else {
        console.error('switchToStep5UI: step5Component not found, please refresh the page');
        alert('步骤5组件未加载，请刷新页面');
    }
};

// ============================================================
// 页面初始化
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        window.loadHistoryPanel();
        window.checkAllServicesStatus();
    }, 200);
});
