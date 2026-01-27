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
        // 同时获取历史记录和单据类型配置
        var [historyRes, docTypesRes] = await Promise.all([
            fetch('/api/jobs/history?limit=10'),
            fetch('/api/document-types')
        ]);
        var data = await historyRes.json();
        var docTypesData = await docTypesRes.json();
        console.log('History data:', data);
        
        // 构建单据类型ID到名称的映射
        var docTypeMap = {};
        if (docTypesData.success && docTypesData.data) {
            docTypesData.data.forEach(function(dt) {
                docTypeMap[dt.id] = dt.name;
            });
        }
        
        // 格式化日期时间
        function formatDateTime(timestamp) {
            if (!timestamp) return '-';
            var date = new Date(timestamp * 1000);
            var year = date.getFullYear();
            var month = String(date.getMonth() + 1).padStart(2, '0');
            var day = String(date.getDate()).padStart(2, '0');
            var hour = String(date.getHours()).padStart(2, '0');
            var minute = String(date.getMinutes()).padStart(2, '0');
            return year + '-' + month + '-' + day + ' ' + hour + ':' + minute;
        }
        
        // 获取置信度等级
        function getConfidenceLevel(score) {
            if (!score) return 'unknown';
            if (score >= 0.95) return 'excellent';
            if (score >= 0.85) return 'good';
            if (score >= 0.70) return 'fair';
            return 'poor';
        }
        
        if (data.success && data.jobs && data.jobs.length > 0) {
            var sortedJobs = data.jobs.slice().sort(function(a, b) {
                return a.created_at - b.created_at;
            });
            list.innerHTML = sortedJobs.map(function(job, idx) {
                var seq = idx + 1;
                var docTypeName = job.document_type_id && docTypeMap[job.document_type_id] 
                    ? docTypeMap[job.document_type_id] 
                    : '未分类';
                var confidenceLevel = getConfidenceLevel(job.confidence_score);
                var confidenceText = job.confidence_score ? Math.round(job.confidence_score * 100) + '%' : '-';
                
                return '<div class="history-panel-item" data-job-id="' + job.job_id + '" onclick="window.loadCachedJobAndClose(\'' + job.job_id + '\')">' +
                    '<span class="item-seq" style="background:#495057;color:#fff!important;">' + seq + '</span>' +
                    '<span class="item-icon">📄</span>' +
                    '<div class="item-info">' +
                        '<div class="item-name" title="' + job.filename + '">' + job.filename + '</div>' +
                        '<div class="item-meta-row">' +
                            '<span class="item-doctype">📋 ' + docTypeName + '</span>' +
                            '<span class="item-time">🕐 ' + formatDateTime(job.created_at) + '</span>' +
                            '<span class="item-meta">⏱ ' + Math.round(job.processing_time) + 's</span>' +
                        '</div>' +
                    '</div>' +
                    '<span class="item-badge ' + confidenceLevel + '">' + confidenceText + '</span>' +
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

// 加载缓存并关闭弹窗
window.loadCachedJobAndClose = async function(jobId) {
    // 先关闭弹窗
    if (window.hideHistoryModal) {
        window.hideHistoryModal();
    }
    // 然后加载缓存
    await window.loadCachedJob(jobId);
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
    console.log('[DEBUG] loadCachedJob START:', jobId);
    
    try {
        // 更新步骤状态：从缓存加载，跳过步骤1-3
        window.updateStepStatus(1, 'completed', '✓');
        window.updateStepStatus(2, 'completed', '缓存');
        window.updateStepStatus(3, 'completed', '缓存');
        window.updateStepStatus(4, 'active', '加载中...');
        
        // 立即隐藏上传区域，显示主内容区域（左右分栏）
        var uploadSection = document.querySelector('.upload-section');
        if (uploadSection) {
            uploadSection.style.display = 'none';
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
        }
        
        // 确保左侧图像面板可见
        var imagePanel = document.querySelector('.image-panel');
        if (imagePanel) {
            imagePanel.style.display = 'flex';
            imagePanel.style.flex = '0 0 50%';
            imagePanel.style.width = '50%';
            imagePanel.style.maxWidth = '50%';
        }
        
        // 确保右侧编辑器面板可见
        var editorPanel = document.querySelector('.editor-panel');
        if (editorPanel) {
            editorPanel.style.display = 'flex';
            editorPanel.style.flex = '0 0 50%';
            editorPanel.style.width = '50%';
            editorPanel.style.maxWidth = '50%';
        }
        
        var res = await fetch('/api/jobs/' + jobId + '/cached-result');
        var data = await res.json();
        console.log('[DEBUG] Cached result loaded, blocks:', data.result?.blocks?.length || 0);
        
        if (data.status === 'completed' && data.result) {
            // 恢复单据类型选择（在 handleProcessingComplete 之前设置）
            if (data.document_type_id && window.stateManager) {
                console.log('[DEBUG] Setting document_type_id:', data.document_type_id);
                window.stateManager.set('selectedDocumentTypeId', data.document_type_id);
                
                // 更新下拉框选择
                var typeSelect = document.getElementById('documentTypeSelect');
                if (typeSelect) {
                    typeSelect.value = data.document_type_id;
                }
            }
            
            if (window.app && typeof window.app.handleProcessingComplete === 'function') {
                var processedData = {
                    blocks: data.result.blocks,
                    confidence_report: data.confidence_report,
                    markdown: data.markdown,
                    cached: true,
                    document_type_id: data.document_type_id
                };
                await window.app.handleProcessingComplete(processedData, jobId);
                window.updateStepStatus(4, 'completed', '✓');
                
                // 确保确认按钮被渲染
                if (window.app && typeof window.app.renderStep4ConfirmButton === 'function') {
                    window.app.renderStep4ConfirmButton();
                } else {
                    window.createStep4ConfirmButton();
                }
            } else {
                console.error('[DEBUG] window.app.handleProcessingComplete not available');
                alert('❌ 应用未完全加载，请刷新页面后重试');
            }
        } else {
            window.updateStepStatus(4, 'error', '失败');
            if (uploadSection) uploadSection.style.display = 'block';
            alert('❌ 加载失败: ' + (data.error || '未知错误'));
        }
    } catch(e) {
        console.error('[DEBUG] loadCachedJob error:', e);
        window.updateStepStatus(4, 'error', '失败');
        var uploadSection = document.querySelector('.upload-section');
        if (uploadSection) uploadSection.style.display = 'block';
        alert('❌ 加载失败: ' + e.message);
    }
    console.log('[DEBUG] loadCachedJob DONE');
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
        
        // 检查是否所有服务都返回 loaded: false 且没有 loading
        // 这种情况说明后端是通过 start_backend.py 启动的，没有更新状态变量
        // 需要使用 fallback 逻辑来检测实际状态
        var allNotLoaded = data.ocr && !data.ocr.loaded && !data.ocr.loading &&
                          data.llm && !data.llm.loaded && !data.llm.loading &&
                          data.rag && !data.rag.loaded && !data.rag.loading;
        
        if (allNotLoaded) {
            console.log('All services report not loaded, using fallback detection');
            window.checkAllServicesStatusFallback();
            return;
        }
        
        // OCR 状态
        if (data.ocr) {
            if (data.ocr.loaded) {
                var timeStr = data.ocr.time > 0 ? ' (' + data.ocr.time.toFixed(1) + 's)' : '';
                window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'online', '就绪' + timeStr);
                
                // OCR 就绪后，更新步骤1为完成，步骤2为激活
                window.updateStepStatus(1, 'completed', '✓');
                window.updateStepStatus(2, 'active');
            } else if (data.ocr.loading) {
                window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'checking', '加载中...');
                window.updateStepStatus(1, 'active', '加载中...');
            } else {
                window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'offline', data.ocr.error || '未就绪');
                window.updateStepStatus(1, 'waiting', '等待中...');
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

// 更新步骤状态的全局函数 - 统一入口
window.updateStepStatus = function(stepNum, status, time) {
    console.log('[DEBUG] updateStepStatus:', stepNum, status, time);
    var step = document.getElementById('step' + stepNum);
    if (!step) {
        console.warn('[DEBUG] Step element not found: step' + stepNum);
        return;
    }
    
    // 移除所有状态类
    step.classList.remove('completed', 'active', 'waiting', 'error');
    
    // 添加新状态
    if (status) {
        step.classList.add(status);
    }
    
    // 更新时间显示
    if (time !== undefined) {
        var timeEl = document.getElementById('step' + stepNum + 'Time');
        if (timeEl) {
            timeEl.textContent = time;
        }
    }
    
    // 更新 workflow-steps 的 data-current-step 属性（用于进度线）
    // 当步骤变为 active 或 completed 时，更新进度线到该步骤
    var workflowSteps = document.getElementById('workflowSteps');
    if (workflowSteps) {
        if (status === 'active') {
            // 激活状态：进度线到当前步骤
            workflowSteps.setAttribute('data-current-step', stepNum);
            console.log('[DEBUG] Progress line updated to step', stepNum);
        } else if (status === 'completed') {
            // 完成状态：检查是否需要更新进度线
            // 只有当完成的步骤大于等于当前进度时才更新
            var currentStep = parseInt(workflowSteps.getAttribute('data-current-step') || '1');
            if (stepNum >= currentStep) {
                workflowSteps.setAttribute('data-current-step', stepNum);
                console.log('[DEBUG] Progress line updated to completed step', stepNum);
            }
        }
    }
    
    console.log('[DEBUG] updateStepStatus DONE - step' + stepNum + ' is now', status);
};

window.checkAllServicesStatusFallback = async function() {
    var ocrReady = false;
    
    try {
        var healthRes = await fetch('/api/health');
        var healthData = await healthRes.json();
        if (healthData.status === 'healthy') {
            window.updateStatusItem('llmOcrStatus', 'llmOcrText', 'online', '就绪');
            ocrReady = true;
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
    
    // 更新步骤状态
    if (ocrReady) {
        window.updateStepStatus(1, 'completed', '✓');
        window.updateStepStatus(2, 'active');
    } else {
        window.updateStepStatus(1, 'active', '检测中...');
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
    
    console.log('switchViewMode elements:', {
        blockBtn: !!blockBtn,
        mdBtn: !!mdBtn,
        blockList: !!blockList,
        mdView: !!mdView
    });
    
    if (mode === 'block') {
        if (blockBtn) blockBtn.classList.add('active');
        if (mdBtn) mdBtn.classList.remove('active');
        if (blockList) blockList.style.display = 'flex';
        if (mdView) mdView.style.display = 'none';
        ocrRegions.forEach(function(r) { r.style.display = 'block'; });
    } else {
        if (blockBtn) blockBtn.classList.remove('active');
        if (mdBtn) mdBtn.classList.add('active');
        if (blockList) blockList.style.display = 'none';
        if (mdView) mdView.style.display = 'block';
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
    console.log('createStep4ConfirmButton: Showing top confirm button only');
    
    // 只显示顶部的蓝色确认按钮，不再创建底部的绿色按钮
    var confirmBtn = document.getElementById('confirmStep5Btn');
    if (confirmBtn) {
        confirmBtn.style.display = 'inline-block';
        confirmBtn.style.visibility = 'visible';
        console.log('createStep4ConfirmButton: Top button shown');
    }
};

window.confirmStep4AndProceed = function() {
    console.log('[DEBUG] confirmStep4AndProceed START');
    
    // 确保 finalText 已经计算并保存到全局 stateManager
    if (window.stateManager) {
        // 先从 window.app 同步数据到 stateManager（兼容旧代码）
        if (window.app) {
            if (window.app.ocrRegions && window.app.ocrRegions.length > 0) {
                window.stateManager.set('ocrRegions', window.app.ocrRegions);
                console.log('[DEBUG] synced ocrRegions, count:', window.app.ocrRegions.length);
            }
            if (window.app.ocrData) {
                window.stateManager.set('ocrData', window.app.ocrData);
            }
            if (window.app.currentJobId) {
                window.stateManager.set('jobId', window.app.currentJobId);
            }
        }
        
        var finalText = window.stateManager.getFinalText();
        window.stateManager.set('finalText', finalText);
        console.log('[DEBUG] finalText saved, length:', finalText ? finalText.length : 0);
    }
    
    // 更新步骤状态 - 使用统一入口
    window.updateStepStatus(4, 'completed', '✓');
    window.updateStepStatus(5, 'active');
    
    // 切换到步骤5界面
    window.switchToStep5UI();
    console.log('[DEBUG] confirmStep4AndProceed DONE');
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
// OCR 区域处理 - 统一入口
// ============================================================

/**
 * 从 blocks 数据中提取 OCR 区域信息
 * @param {Array} blocks - OCR 识别的 blocks 数组
 * @returns {Array} - 区域信息数组
 */
window.extractOCRRegions = function(blocks) {
    console.log('[DEBUG] extractOCRRegions called, blocks:', blocks ? blocks.length : 0);
    var regions = [];
    if (!blocks || !Array.isArray(blocks)) return regions;
    
    blocks.forEach(function(block, i) {
        var coords = block.metadata ? block.metadata.originalCoordinates : null;
        var confidence = block.metadata ? block.metadata.confidence : null;
        var originalStructType = block.metadata ? block.metadata.originalStructType : block.type;
        var editType = block.metadata ? block.metadata.editType : (block.type === 'table' ? 'table' : 'text');
        var text = '';
        if (block.data && block.data.text) text = block.data.text;
        else if (block.data && block.data.items) text = block.data.items.join(', ');
        
        regions.push({
            index: i,
            blockId: block.id,
            type: block.type,
            text: text,
            coordinates: coords || {x:0, y:0, width:100, height:30},
            hasCoordinates: !!coords,
            tableHtml: block.data ? block.data.tableHtml : null,
            confidence: confidence,
            originalStructType: originalStructType,
            editType: editType
        });
    });
    return regions;
};

/**
 * 绘制 OCR 区域框到图片上
 * @param {Array} blocks - OCR 识别的 blocks 数组（可选，如果不传则从 stateManager 获取）
 */
window.drawOCRRegions = function(blocks) {
    console.log('[DEBUG] drawOCRRegions called');
    var wrapper = document.getElementById('imageWrapper');
    var img = document.getElementById('documentImage');
    
    if (!wrapper || !img) {
        console.error('[DEBUG] drawOCRRegions: wrapper or img not found');
        return;
    }
    
    // 等待图片加载完成
    if (!img.naturalWidth) {
        console.log('[DEBUG] drawOCRRegions: waiting for image to load...');
        img.onload = function() {
            window.drawOCRRegions(blocks);
        };
        return;
    }
    
    // 清除旧的区域框
    wrapper.querySelectorAll('.ocr-region').forEach(function(el) { el.remove(); });
    
    var scaleX = img.clientWidth / img.naturalWidth;
    var scaleY = img.clientHeight / img.naturalHeight;
    
    // 获取区域数据：优先使用传入的 blocks，否则从 stateManager 获取
    var regions;
    if (blocks && Array.isArray(blocks)) {
        regions = window.extractOCRRegions(blocks);
    } else if (window.stateManager) {
        regions = window.stateManager.get('ocrRegions') || [];
    } else if (window.app && window.app.ocrRegions) {
        regions = window.app.ocrRegions;
    } else {
        regions = [];
    }
    
    console.log('[DEBUG] drawOCRRegions: Drawing', regions.length, 'regions, scale:', scaleX.toFixed(2), scaleY.toFixed(2));
    
    regions.forEach(function(region, idx) {
        if (!region.hasCoordinates) return;
        
        var c = region.coordinates;
        var div = document.createElement('div');
        div.className = 'ocr-region';
        div.setAttribute('data-region-index', idx);
        div.setAttribute('data-region-type', region.type);
        div.style.left = (c.x * scaleX) + 'px';
        div.style.top = (c.y * scaleY) + 'px';
        div.style.width = (c.width * scaleX) + 'px';
        div.style.height = (c.height * scaleY) + 'px';
        
        // 索引标签
        var indexLabel = document.createElement('span');
        indexLabel.className = 'ocr-region-index';
        indexLabel.textContent = '#' + (idx + 1);
        div.appendChild(indexLabel);
        
        // 提示框
        var tip = document.createElement('div');
        tip.className = 'ocr-region-tooltip';
        var txt = region.text || '';
        tip.textContent = txt.length > 30 ? txt.substring(0, 30) + '...' : txt;
        div.appendChild(tip);
        
        // 点击事件 - 选中对应的 block
        div.addEventListener('click', function(e) {
            e.stopPropagation();
            // 移除其他选中状态
            document.querySelectorAll('.ocr-region.active').forEach(function(el) { el.classList.remove('active'); });
            document.querySelectorAll('.block-item.active').forEach(function(el) { el.classList.remove('active'); });
            // 添加选中状态
            div.classList.add('active');
            var blockItem = document.querySelector('.block-item[data-region-index="' + idx + '"]');
            if (blockItem) {
                blockItem.classList.add('active');
                blockItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
        
        wrapper.appendChild(div);
    });
    
    console.log('[DEBUG] drawOCRRegions: Done');
};

/**
 * 渲染 Block 列表
 * @param {Array} blocks - OCR 识别的 blocks 数组
 */
window.renderBlockList = function(blocks) {
    console.log('[DEBUG] renderBlockList called, blocks:', blocks ? blocks.length : 0);
    
    var list = document.getElementById('blockList');
    if (!list) {
        console.error('[DEBUG] blockList element NOT FOUND!');
        return;
    }
    
    list.innerHTML = '';
    
    if (!blocks || blocks.length === 0) {
        list.innerHTML = '<div style="padding:20px;color:#666;text-align:center;">No blocks</div>';
        return;
    }
    
    var regions = window.extractOCRRegions(blocks);
    console.log('[DEBUG] Rendering', regions.length, 'blocks');
    
    regions.forEach(function(region, idx) {
        var item = document.createElement('div');
        item.className = 'block-item';
        item.setAttribute('data-region-index', idx);
        
        // Header
        var hdr = document.createElement('div');
        hdr.className = 'block-header';
        
        // Edit type badge
        var editTypeBadge = document.createElement('span');
        editTypeBadge.className = 'block-edit-type ' + region.editType;
        editTypeBadge.textContent = region.editType.toUpperCase();
        
        // Struct type badge
        var structTypeBadge = document.createElement('span');
        structTypeBadge.className = 'block-struct-type';
        structTypeBadge.textContent = region.originalStructType || region.type;
        
        // Index
        var num = document.createElement('span');
        num.className = 'block-index';
        num.textContent = '#' + (idx + 1);
        
        hdr.appendChild(editTypeBadge);
        hdr.appendChild(structTypeBadge);
        hdr.appendChild(num);
        
        // Content
        var cnt = document.createElement('div');
        cnt.className = 'block-content';
        if (region.type === 'table' && region.tableHtml) {
            cnt.classList.add('table-preview');
            cnt.innerHTML = region.tableHtml;
        } else {
            cnt.textContent = region.text || '(empty)';
        }
        
        // Meta
        var meta = document.createElement('div');
        meta.className = 'block-meta';
        var co = region.coordinates;
        var metaText = 'Pos:(' + Math.round(co.x) + ',' + Math.round(co.y) + ') Size:' + Math.round(co.width) + 'x' + Math.round(co.height);
        if (region.confidence !== null && region.confidence !== undefined) {
            metaText += ' Conf:' + region.confidence;
        } else {
            metaText += ' Conf:-';
        }
        meta.textContent = metaText;
        
        item.appendChild(hdr);
        item.appendChild(cnt);
        item.appendChild(meta);
        
        // 点击事件 - 选中对应的区域框
        item.addEventListener('click', function() {
            // 移除其他选中状态
            document.querySelectorAll('.ocr-region.active').forEach(function(el) { el.classList.remove('active'); });
            document.querySelectorAll('.block-item.active').forEach(function(el) { el.classList.remove('active'); });
            // 添加选中状态
            item.classList.add('active');
            var ocrRegion = document.querySelector('.ocr-region[data-region-index="' + idx + '"]');
            if (ocrRegion) {
                ocrRegion.classList.add('active');
            }
        });
        
        // 双击事件 - 打开编辑弹窗
        item.addEventListener('dblclick', function() {
            window.startEditRegion(idx, region);
        });
        
        list.appendChild(item);
    });
    
    console.log('[DEBUG] renderBlockList: Done, rendered', regions.length, 'items');
};

// ============================================================
// 编辑弹窗相关函数
// ============================================================

window.editingRegionIndex = null;
window.editingRegionData = null;

/**
 * 开始编辑区域
 */
window.startEditRegion = function(idx, region) {
    console.log('[DEBUG] startEditRegion:', idx, region ? region.type : 'no region');
    window.editingRegionIndex = idx;
    window.editingRegionData = region;
    
    // 如果没有传入 region，尝试从 app 获取
    if (!region && window.app && window.app.ocrRegions) {
        region = window.app.ocrRegions[idx];
        window.editingRegionData = region;
    }
    
    if (!region) {
        console.error('[DEBUG] startEditRegion: region not found');
        return;
    }
    
    if (region.type === 'table') {
        window.openTableEdit(idx, region);
    } else {
        window.openTextEdit(idx, region);
    }
};

/**
 * 打开文本编辑弹窗
 */
window.openTextEdit = function(idx, region) {
    var txt = region.text || '';
    var input = document.getElementById('textEditInput');
    if (input) input.value = txt;
    var ov = document.getElementById('editOverlay');
    if (ov) ov.classList.add('visible');
    var pop = document.getElementById('textEditPopup');
    if (pop) pop.style.display = 'block';
    if (input) input.focus();
};

/**
 * 关闭文本编辑弹窗
 */
window.closeTextEdit = function() {
    var ov = document.getElementById('editOverlay');
    if (ov) ov.classList.remove('visible');
    var pop = document.getElementById('textEditPopup');
    if (pop) pop.style.display = 'none';
    window.editingRegionIndex = null;
    window.editingRegionData = null;
};

/**
 * 保存文本编辑
 */
window.saveTextEdit = function() {
    var input = document.getElementById('textEditInput');
    var txt = input ? input.value : '';
    var idx = window.editingRegionIndex;
    
    if (idx !== null && window.app) {
        // 更新 modifications
        if (!window.app.modifications) {
            window.app.modifications = new Map();
        }
        window.app.modifications.set(idx, {text: txt, tableHtml: null});
        
        // 更新显示
        if (window.app.ocrRegions && window.app.ocrRegions[idx]) {
            window.app.ocrRegions[idx].text = txt;
        }
        
        // 更新 block-item 显示
        var blockItem = document.querySelector('.block-item[data-region-index="' + idx + '"]');
        if (blockItem) {
            blockItem.classList.add('modified');
            var cnt = blockItem.querySelector('.block-content');
            if (cnt) cnt.textContent = txt;
        }
        
        console.log('[DEBUG] Text saved for region', idx);
    }
    
    window.closeTextEdit();
};

/**
 * 打开表格编辑弹窗
 */
window.openTableEdit = function(idx, region) {
    var html = region.tableHtml || '<table><tr><td>No data</td></tr></table>';
    var cnt = document.getElementById('tableEditContent');
    if (cnt) {
        cnt.innerHTML = html;
        cnt.querySelectorAll('td,th').forEach(function(c) { c.contentEditable = 'true'; });
    }
    var ov = document.getElementById('editOverlay');
    if (ov) ov.classList.add('visible');
    var pop = document.getElementById('tableEditPopup');
    if (pop) pop.classList.add('visible');
};

/**
 * 关闭表格编辑弹窗
 */
window.closeTableEdit = function() {
    var ov = document.getElementById('editOverlay');
    if (ov) ov.classList.remove('visible');
    var pop = document.getElementById('tableEditPopup');
    if (pop) pop.classList.remove('visible');
    window.editingRegionIndex = null;
    window.editingRegionData = null;
};

/**
 * 保存表格编辑
 */
window.saveTableEdit = function() {
    var cnt = document.getElementById('tableEditContent');
    var idx = window.editingRegionIndex;
    
    if (idx !== null && cnt && window.app) {
        cnt.querySelectorAll('td,th').forEach(function(c) { c.removeAttribute('contenteditable'); });
        
        // 更新 modifications
        if (!window.app.modifications) {
            window.app.modifications = new Map();
        }
        window.app.modifications.set(idx, {text: cnt.textContent.trim(), tableHtml: cnt.innerHTML});
        
        // 更新 ocrRegions
        if (window.app.ocrRegions && window.app.ocrRegions[idx]) {
            window.app.ocrRegions[idx].text = cnt.textContent.trim();
            window.app.ocrRegions[idx].tableHtml = cnt.innerHTML;
        }
        
        // 更新 block-item 显示
        var blockItem = document.querySelector('.block-item[data-region-index="' + idx + '"]');
        if (blockItem) {
            blockItem.classList.add('modified');
            var content = blockItem.querySelector('.block-content');
            if (content) content.innerHTML = cnt.innerHTML;
        }
        
        console.log('[DEBUG] Table saved for region', idx);
    }
    
    window.closeTableEdit();
};

/**
 * 关闭所有弹窗
 */
window.closeAllPopups = function() {
    window.closeTextEdit();
    window.closeTableEdit();
};

/**
 * 显示置信度报告
 * @param {Object} cr - 置信度报告对象
 */
window.showConfidenceReport = function(cr) {
    if (!cr || !cr.confidence_breakdown) return;
    
    var div = document.getElementById('confidenceReport');
    if (!div) return;
    
    var o = cr.confidence_breakdown.overall;
    var scoreDisplay = String(o.score);
    
    var levelMap = {
        'excellent': '优秀',
        'good': '良好',
        'fair': '一般',
        'poor': '较差'
    };
    var descMap = {
        'Excellent - Very high accuracy expected': '优秀 - 预期准确率非常高',
        'Good - High accuracy with minimal errors': '良好 - 准确率高，错误极少',
        'Fair - Moderate accuracy, review recommended': '一般 - 准确率中等，建议复核',
        'Poor - Low accuracy, manual review required': '较差 - 准确率低，需人工复核'
    };
    
    var levelCn = levelMap[o.level] || o.level;
    var descCn = descMap[o.description] || o.description;
    
    div.innerHTML = '<div class="confidence-info"><h4>置信度: ' + scoreDisplay + ' (' + levelCn + ')</h4><p>' + descCn + '</p></div>';
};

/**
 * 显示步骤4界面
 */
window.showStep4UI = function() {
    console.log('[DEBUG] showStep4UI: Switching to Step 4 layout');
    
    // 隐藏上传区域
    var uploadSection = document.querySelector('.upload-section');
    if (uploadSection) uploadSection.style.display = 'none';
    
    // 显示主内容区域
    var mainContent = document.getElementById('mainContent');
    if (mainContent) {
        mainContent.classList.add('visible');
        mainContent.style.display = 'flex';
    }
    
    // 显示图像面板
    var imagePanel = document.querySelector('.image-panel');
    if (imagePanel) imagePanel.style.display = 'flex';
    
    // 显示编辑器面板
    var editorPanel = document.querySelector('.editor-panel');
    if (editorPanel) editorPanel.style.display = 'flex';
    
    // 显示 blockList
    var blockList = document.getElementById('blockList');
    if (blockList) blockList.style.display = 'flex';
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
