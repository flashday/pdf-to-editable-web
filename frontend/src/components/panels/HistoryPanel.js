/**
 * HistoryPanel - 历史缓存面板组件
 * 显示和管理历史任务记录
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

export class HistoryPanel {
    constructor(container) {
        this.container = container || document.getElementById('historyPanel');
        this.jobs = [];
        this.isExpanded = true;
    }

    /**
     * 初始化面板
     */
    init() {
        this.bindEvents();
        this.loadHistory();
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 刷新按钮
        const refreshBtn = document.getElementById('refreshHistoryBtn2');
        if (refreshBtn) {
            refreshBtn.onclick = () => this.loadHistory();
        }
        
        // 监听处理完成事件，刷新列表
        eventBus.on(EVENTS.RECOGNITION_COMPLETED, () => {
            this.loadHistory();
        });
        
        eventBus.on(EVENTS.FINAL_CONFIRMED, () => {
            this.loadHistory();
        });
    }

    /**
     * 加载历史记录
     */
    async loadHistory() {
        try {
            const res = await fetch('/api/jobs/history?limit=10');
            const data = await res.json();
            
            if (data.success && data.jobs) {
                this.jobs = data.jobs;
                this.render();
            } else {
                this.jobs = [];
                this.render();
            }
        } catch (error) {
            console.error('Load history error:', error);
            this.jobs = [];
            this.render();
        }
    }

    /**
     * 渲染面板
     */
    render() {
        const list = document.getElementById('historyPanelList');
        if (!list) return;
        
        if (this.jobs.length === 0) {
            list.innerHTML = '<div class="history-panel-empty">暂无缓存记录</div>';
            return;
        }
        
        list.innerHTML = '';
        
        // 按时间排序：最早的在前
        const sortedJobs = this.jobs.slice().sort((a, b) => a.created_at - b.created_at);
        
        sortedJobs.forEach((job, idx) => {
            const item = this.createJobItem(job, idx + 1);
            list.appendChild(item);
        });
    }

    /**
     * 创建任务项
     */
    createJobItem(job, seq) {
        const item = document.createElement('div');
        item.className = 'history-panel-item';
        item.setAttribute('data-job-id', job.job_id);
        
        // 序号
        const seqSpan = document.createElement('span');
        seqSpan.className = 'item-seq';
        seqSpan.textContent = seq;
        
        // 图标
        const icon = document.createElement('span');
        icon.className = 'item-icon';
        icon.textContent = '📄';
        icon.onclick = () => this.loadJob(job.job_id);
        
        // 信息区
        const info = document.createElement('div');
        info.className = 'item-info';
        info.onclick = () => this.loadJob(job.job_id);
        
        const name = document.createElement('div');
        name.className = 'item-name';
        name.textContent = job.filename || '未知文件';
        name.title = job.filename;
        
        const meta = document.createElement('div');
        meta.className = 'item-meta';
        meta.textContent = this.formatTimeAgo(job.created_at) + ' · ' + Math.round(job.processing_time) + 's';
        
        info.appendChild(name);
        info.appendChild(meta);
        
        // 置信度徽章
        const badge = document.createElement('span');
        badge.className = 'item-badge ' + this.getConfidenceLevel(job.confidence_score);
        badge.textContent = job.confidence_score ? Math.round(job.confidence_score * 100) + '%' : '-';
        
        // 删除按钮
        const delBtn = document.createElement('button');
        delBtn.className = 'item-delete';
        delBtn.textContent = '🗑';
        delBtn.title = '删除';
        delBtn.onclick = (e) => {
            e.stopPropagation();
            this.deleteJob(job.job_id);
        };
        
        item.appendChild(seqSpan);
        item.appendChild(icon);
        item.appendChild(info);
        item.appendChild(badge);
        item.appendChild(delBtn);
        
        return item;
    }

    /**
     * 加载历史任务
     */
    async loadJob(jobId) {
        eventBus.emit(EVENTS.HISTORY_JOB_SELECTED, { jobId });
        
        try {
            const res = await fetch(`/api/jobs/${jobId}/cached-result`);
            const data = await res.json();
            
            if (data.status === 'completed' && data.result) {
                // 保存到状态
                stateManager.set('jobId', jobId);
                stateManager.set('ocrData', data);
                stateManager.set('blocks', data.result.blocks);
                
                if (data.confidence_report) {
                    stateManager.set('confidenceReport', data.confidence_report);
                }
                if (data.markdown) {
                    stateManager.set('markdown', data.markdown);
                }
                
                // 发布加载完成事件
                eventBus.emit(EVENTS.HISTORY_JOB_LOADED, {
                    jobId,
                    data: data
                });
            } else {
                eventBus.emit(EVENTS.UI_ERROR, { 
                    message: data.error || '加载缓存失败' 
                });
            }
        } catch (error) {
            console.error('Load job error:', error);
            eventBus.emit(EVENTS.UI_ERROR, { 
                message: '加载缓存失败: ' + error.message 
            });
        }
    }

    /**
     * 删除历史任务
     */
    async deleteJob(jobId) {
        if (!confirm('确定删除此缓存记录？')) return;
        
        try {
            const res = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' });
            const data = await res.json();
            
            if (data.success) {
                this.loadHistory();
                eventBus.emit(EVENTS.UI_SUCCESS, { message: '已删除' });
            } else {
                eventBus.emit(EVENTS.UI_ERROR, { 
                    message: '删除失败: ' + (data.error || '未知错误') 
                });
            }
        } catch (error) {
            console.error('Delete error:', error);
            eventBus.emit(EVENTS.UI_ERROR, { 
                message: '删除失败: ' + error.message 
            });
        }
    }

    /**
     * 格式化时间
     */
    formatTimeAgo(timestamp) {
        const now = Date.now() / 1000;
        const diff = now - timestamp;
        
        if (diff < 60) return '刚刚';
        if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
        if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
        if (diff < 604800) return Math.floor(diff / 86400) + '天前';
        
        const date = new Date(timestamp * 1000);
        return (date.getMonth() + 1) + '/' + date.getDate();
    }

    /**
     * 获取置信度等级
     */
    getConfidenceLevel(score) {
        if (!score) return 'unknown';
        if (score >= 0.95) return 'excellent';
        if (score >= 0.85) return 'good';
        if (score >= 0.70) return 'fair';
        return 'poor';
    }

    /**
     * 展开/收起面板
     */
    toggle() {
        this.isExpanded = !this.isExpanded;
        if (this.container) {
            this.container.classList.toggle('collapsed', !this.isExpanded);
        }
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.HistoryPanel = HistoryPanel;
}
