/**
 * Step4PreEntry - 步骤4：预录入组件
 * 允许用户查看和编辑 OCR 识别结果
 */

import { eventBus, EVENTS } from '../../services/EventBus.js';
import { stateManager } from '../../services/StateManager.js';

export class Step4PreEntry {
    constructor(container) {
        this.container = container;
        this.corrections = [];
        this.activeBlockIndex = null;
        this.editingBlockIndex = null;
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
        // 组件隐藏时的清理工作
    }

    /**
     * 渲染界面
     */
    render() {
        const ocrRegions = stateManager.get('ocrRegions') || [];
        const corrections = stateManager.get('corrections') || [];
        
        // 创建修正映射
        const correctionMap = new Map();
        corrections.forEach(c => correctionMap.set(c.blockIndex, c));
        
        // 渲染 Block 列表
        const blockList = document.getElementById('blockList');
        if (!blockList) return;
        
        blockList.innerHTML = '';
        
        if (ocrRegions.length === 0) {
            blockList.innerHTML = '<div style="padding:20px;color:#666;text-align:center;">暂无识别结果</div>';
            return;
        }
        
        ocrRegions.forEach((region, idx) => {
            const correction = correctionMap.get(idx);
            const text = correction ? correction.correctedText : region.text;
            const html = correction ? correction.tableHtml : region.tableHtml;
            const isModified = correctionMap.has(idx);
            
            const item = this.createBlockItem(region, idx, text, html, isModified);
            blockList.appendChild(item);
        });
        
        // 显示确认按钮
        this.renderConfirmButton();
    }

    /**
     * 创建 Block 项
     */
    createBlockItem(region, idx, text, html, isModified) {
        const item = document.createElement('div');
        item.className = 'block-item' + (isModified ? ' modified' : '');
        item.setAttribute('data-region-index', idx);
        
        // 头部
        const header = document.createElement('div');
        header.className = 'block-header';
        
        const editTypeBadge = document.createElement('span');
        editTypeBadge.className = 'block-edit-type ' + region.editType;
        editTypeBadge.textContent = region.editType.toUpperCase();
        
        const structTypeBadge = document.createElement('span');
        structTypeBadge.className = 'block-struct-type';
        structTypeBadge.textContent = region.originalStructType || region.type;
        
        const indexSpan = document.createElement('span');
        indexSpan.className = 'block-index';
        indexSpan.textContent = '#' + (idx + 1);
        
        header.appendChild(editTypeBadge);
        header.appendChild(structTypeBadge);
        header.appendChild(indexSpan);
        
        // 内容
        const content = document.createElement('div');
        content.className = 'block-content';
        if (region.type === 'table' && html) {
            content.classList.add('table-preview');
            content.innerHTML = html;
        } else {
            content.textContent = text || '(空)';
        }
        
        // 元信息
        const meta = document.createElement('div');
        meta.className = 'block-meta';
        const co = region.coordinates;
        let metaText = `位置:(${Math.round(co.x)},${Math.round(co.y)}) 尺寸:${Math.round(co.width)}x${Math.round(co.height)}`;
        if (region.confidence !== null && region.confidence !== undefined) {
            metaText += ` 置信度:${region.confidence}`;
        }
        if (isModified) {
            metaText += ' ✓已修正';
        }
        meta.textContent = metaText;
        
        item.appendChild(header);
        item.appendChild(content);
        item.appendChild(meta);
        
        // 事件
        item.addEventListener('click', () => this.selectBlock(idx));
        item.addEventListener('dblclick', () => this.editBlock(idx));
        
        return item;
    }

    /**
     * 渲染确认按钮
     */
    renderConfirmButton() {
        let confirmArea = document.getElementById('preEntryConfirmArea');
        if (!confirmArea) {
            confirmArea = document.createElement('div');
            confirmArea.id = 'preEntryConfirmArea';
            confirmArea.style.cssText = 'padding: 15px; border-top: 1px solid #ddd; background: #f8f9fa; text-align: center;';
            
            const confirmBtn = document.createElement('button');
            confirmBtn.id = 'preEntryConfirmBtn';
            confirmBtn.textContent = '✓ 确认并进入下一步';
            confirmBtn.style.cssText = 'background: #28a745; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 600;';
            confirmBtn.onclick = () => this.confirmAndProceed();
            
            confirmArea.appendChild(confirmBtn);
            
            const editorContainer = document.querySelector('.editor-container');
            if (editorContainer && editorContainer.parentNode) {
                editorContainer.parentNode.appendChild(confirmArea);
            }
        }
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 监听修正保存事件
        eventBus.on(EVENTS.CORRECTION_SAVED, (correction) => {
            this.updateBlockDisplay(correction.blockIndex);
        });
    }

    /**
     * 选中 Block
     */
    selectBlock(idx) {
        // 移除之前的选中状态
        document.querySelectorAll('.block-item.active').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.ocr-region.active').forEach(el => el.classList.remove('active'));
        
        // 添加新的选中状态
        const blockItem = document.querySelector(`.block-item[data-region-index="${idx}"]`);
        const ocrRegion = document.querySelector(`.ocr-region[data-region-index="${idx}"]`);
        
        if (blockItem) {
            blockItem.classList.add('active');
            blockItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        if (ocrRegion) {
            ocrRegion.classList.add('active');
        }
        
        this.activeBlockIndex = idx;
        eventBus.emit(EVENTS.BLOCK_SELECTED, { index: idx });
    }

    /**
     * 编辑 Block
     */
    editBlock(idx) {
        const ocrRegions = stateManager.get('ocrRegions') || [];
        const region = ocrRegions[idx];
        if (!region) return;
        
        this.editingBlockIndex = idx;
        this.selectBlock(idx);
        
        if (region.type === 'table') {
            this.openTableEdit(idx);
        } else {
            this.openTextEdit(idx);
        }
    }

    /**
     * 打开文本编辑弹窗
     */
    openTextEdit(idx) {
        const ocrRegions = stateManager.get('ocrRegions') || [];
        const corrections = stateManager.get('corrections') || [];
        const region = ocrRegions[idx];
        
        const correction = corrections.find(c => c.blockIndex === idx);
        const text = correction ? correction.correctedText : region.text;
        
        const input = document.getElementById('textEditInput');
        if (input) input.value = text;
        
        const overlay = document.getElementById('editOverlay');
        if (overlay) overlay.classList.add('visible');
        
        const popup = document.getElementById('textEditPopup');
        if (popup) popup.style.display = 'block';
        
        if (input) input.focus();
    }

    /**
     * 打开表格编辑弹窗
     */
    openTableEdit(idx) {
        const ocrRegions = stateManager.get('ocrRegions') || [];
        const corrections = stateManager.get('corrections') || [];
        const region = ocrRegions[idx];
        
        const correction = corrections.find(c => c.blockIndex === idx);
        const html = correction ? correction.tableHtml : (region.tableHtml || '<table><tr><td>无数据</td></tr></table>');
        
        const content = document.getElementById('tableEditContent');
        if (content) {
            content.innerHTML = html;
            content.querySelectorAll('td,th').forEach(cell => {
                cell.contentEditable = 'true';
            });
        }
        
        const overlay = document.getElementById('editOverlay');
        if (overlay) overlay.classList.add('visible');
        
        const popup = document.getElementById('tableEditPopup');
        if (popup) popup.classList.add('visible');
    }

    /**
     * 保存文本修正
     */
    saveTextCorrection() {
        const input = document.getElementById('textEditInput');
        const correctedText = input ? input.value : '';
        const idx = this.editingBlockIndex;
        
        if (idx !== null) {
            const ocrRegions = stateManager.get('ocrRegions') || [];
            const region = ocrRegions[idx];
            
            const correction = {
                blockIndex: idx,
                originalText: region.text,
                correctedText: correctedText,
                tableHtml: null,
                timestamp: new Date().toISOString()
            };
            
            stateManager.addCorrection(correction);
            this.saveToBackend(correction);
            this.updateBlockDisplay(idx);
        }
        
        this.closeTextEdit();
    }

    /**
     * 保存表格修正
     */
    saveTableCorrection() {
        const content = document.getElementById('tableEditContent');
        const idx = this.editingBlockIndex;
        
        if (idx !== null && content) {
            content.querySelectorAll('td,th').forEach(cell => {
                cell.removeAttribute('contenteditable');
            });
            
            const ocrRegions = stateManager.get('ocrRegions') || [];
            const region = ocrRegions[idx];
            
            const correction = {
                blockIndex: idx,
                originalText: region.text,
                correctedText: content.textContent.trim(),
                tableHtml: content.innerHTML,
                timestamp: new Date().toISOString()
            };
            
            stateManager.addCorrection(correction);
            this.saveToBackend(correction);
            this.updateBlockDisplay(idx);
        }
        
        this.closeTableEdit();
    }

    /**
     * 保存修正到后端
     */
    async saveToBackend(correction) {
        const jobId = stateManager.get('jobId');
        if (!jobId) return;
        
        try {
            await fetch(`/api/corrections/${jobId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(correction)
            });
            console.log('Correction saved to backend:', correction.blockIndex);
        } catch (error) {
            console.error('Failed to save correction:', error);
        }
    }

    /**
     * 关闭文本编辑弹窗
     */
    closeTextEdit() {
        const overlay = document.getElementById('editOverlay');
        if (overlay) overlay.classList.remove('visible');
        
        const popup = document.getElementById('textEditPopup');
        if (popup) popup.style.display = 'none';
        
        this.editingBlockIndex = null;
    }

    /**
     * 关闭表格编辑弹窗
     */
    closeTableEdit() {
        const overlay = document.getElementById('editOverlay');
        if (overlay) overlay.classList.remove('visible');
        
        const popup = document.getElementById('tableEditPopup');
        if (popup) popup.classList.remove('visible');
        
        this.editingBlockIndex = null;
    }

    /**
     * 更新 Block 显示
     */
    updateBlockDisplay(idx) {
        const blockItem = document.querySelector(`.block-item[data-region-index="${idx}"]`);
        const ocrRegion = document.querySelector(`.ocr-region[data-region-index="${idx}"]`);
        
        if (blockItem) {
            blockItem.classList.add('modified');
            blockItem.classList.add('highlight-flash');
            
            const corrections = stateManager.get('corrections') || [];
            const correction = corrections.find(c => c.blockIndex === idx);
            
            if (correction) {
                const content = blockItem.querySelector('.block-content');
                if (content) {
                    if (correction.tableHtml) {
                        content.innerHTML = correction.tableHtml;
                    } else {
                        content.textContent = correction.correctedText || '(空)';
                    }
                }
            }
            
            setTimeout(() => blockItem.classList.remove('highlight-flash'), 1000);
        }
        
        if (ocrRegion) {
            ocrRegion.classList.add('modified');
        }
    }

    /**
     * 确认并进入下一步
     */
    confirmAndProceed() {
        // 合并修正后的文本
        const finalText = stateManager.getFinalText();
        stateManager.set('finalText', finalText);
        
        // 发布确认事件
        eventBus.emit(EVENTS.PREENTRY_CONFIRMED, {
            corrections: stateManager.get('corrections'),
            finalText: finalText
        });
        
        // 通知步骤完成
        eventBus.emit(EVENTS.STEP_COMPLETED, { step: 4 });
    }
}

// 兼容非模块环境
if (typeof window !== 'undefined') {
    window.Step4PreEntry = Step4PreEntry;
}
