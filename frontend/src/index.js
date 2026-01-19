import { DocumentProcessor } from './services/DocumentProcessor.js';
import { UIManager } from './services/UIManager.js';

class App {
    constructor() {
        this.documentProcessor = new DocumentProcessor();
        this.uiManager = new UIManager();
        this.currentJobId = null;
        this.isProcessing = false;
        this.ocrRegions = [];
        this.ocrData = null;
        this.activeRegionIndex = null;
        this.editingRegionIndex = null;
        this.modifications = new Map();
        this.init();
    }

    init() {
        console.log('App initializing...');
        this.uiManager.initialize();
        this.setupProcessorCallbacks();
        this.setupKeyboardShortcuts();
        this.setupEditPopups();
        console.log('App initialized');
    }

    setupProcessorCallbacks() {
        var self = this;
        this.documentProcessor.setProgressCallback(function(p) { self.uiManager.showProgress(p.progress, p.message); });
        this.documentProcessor.setStatusCallback(function(s) {
            if (s.progress !== undefined) self.uiManager.showProgress(s.progress / 100, s.message);
            else self.uiManager.showProcessing(s.message);
        });
    }

    setupKeyboardShortcuts() {
        var self = this;
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); self.downloadOcrResult(); }
            if (e.key === 'Escape') self.closeAllPopups();
        });
    }

    setupEditPopups() {
        var self = this;
        var overlay = document.getElementById('editOverlay');
        if (overlay) overlay.addEventListener('click', function() { self.closeAllPopups(); });
        var tc = document.getElementById('textEditClose');
        var tca = document.getElementById('textEditCancel');
        var ts = document.getElementById('textEditSave');
        if (tc) tc.addEventListener('click', function() { self.closeTextEdit(); });
        if (tca) tca.addEventListener('click', function() { self.closeTextEdit(); });
        if (ts) ts.addEventListener('click', function() { self.saveTextEdit(); });
        var tbc = document.getElementById('tableEditClose');
        var tbca = document.getElementById('tableEditCancel');
        var tbs = document.getElementById('tableEditSave');
        if (tbc) tbc.addEventListener('click', function() { self.closeTableEdit(); });
        if (tbca) tbca.addEventListener('click', function() { self.closeTableEdit(); });
        if (tbs) tbs.addEventListener('click', function() { self.saveTableEdit(); });
    }

    async handleFileUpload(file) {
        console.log('handleFileUpload called:', file.name);
        if (this.isProcessing) { this.uiManager.showStatus('Processing...', 'warning'); return; }
        try {
            this.isProcessing = true;
            this.uiManager.showProcessing('Uploading...');
            var result = await this.documentProcessor.processFile(file);
            if (result.success) { this.currentJobId = result.jobId; await this.startStatusPolling(result.jobId); }
            else { this.isProcessing = false; this.uiManager.showError(result.error); }
        } catch (e) { this.isProcessing = false; this.uiManager.showError('Upload failed'); }
    }

    async startStatusPolling(jobId) {
        try {
            this.uiManager.showProcessing('Processing with OCR...');
            var result = await this.documentProcessor.pollForCompletion(jobId);
            if (result.success) await this.handleProcessingComplete(result.data, jobId);
            else this.uiManager.showError(result.error);
        } catch (e) { this.uiManager.showError('Processing failed'); }
        finally { this.isProcessing = false; }
    }

    async handleProcessingComplete(data, jobId) {
        this.ocrData = data;
        this.currentJobId = jobId;
        this.modifications.clear();
        this.ocrRegions = this.extractOCRRegions(data.blocks || []);
        await this.loadDocumentImage(jobId);
        this.showMainContent();
        this.drawOCRRegions();
        this.renderBlockList();
        if (data.confidence_report) this.showConfidenceReport(data.confidence_report);
        this.showDownloadButton();
        this.uiManager.showSuccess('Done! Double-click to edit.');
    }

    extractOCRRegions(blocks) {
        var regions = [];
        var self = this;
        blocks.forEach(function(block, i) {
            var coords = block.metadata ? block.metadata.originalCoordinates : null;
            regions.push({
                index: i, blockId: block.id, type: block.type,
                text: self.getBlockText(block),
                coordinates: coords || {x:0,y:0,width:100,height:30},
                hasCoordinates: !!coords,
                tableHtml: block.data ? block.data.tableHtml : null
            });
        });
        return regions;
    }

    getBlockText(block) {
        if (block.data && block.data.text) return block.data.text;
        if (block.data && block.data.items) return block.data.items.join(', ');
        return '';
    }

    async loadDocumentImage(jobId) {
        var img = document.getElementById('documentImage');
        if (!img) return;
        return new Promise(function(resolve) {
            img.onload = resolve; img.onerror = resolve;
            img.src = '/api/convert/' + jobId + '/image?t=' + Date.now();
        });
    }

    showMainContent() {
        var mc = document.getElementById('mainContent');
        if (mc) mc.classList.add('visible');
        this.uiManager.showEditor();
    }

    drawOCRRegions() {
        var wrapper = document.getElementById('imageWrapper');
        var img = document.getElementById('documentImage');
        if (!wrapper || !img || !img.naturalWidth) return;
        wrapper.querySelectorAll('.ocr-region').forEach(function(el) { el.remove(); });
        var scaleX = img.clientWidth / img.naturalWidth;
        var scaleY = img.clientHeight / img.naturalHeight;
        var self = this;
        this.ocrRegions.forEach(function(region, idx) {
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
            var tip = document.createElement('div');
            tip.className = 'ocr-region-tooltip';
            var mod = self.modifications.get(idx);
            var txt = mod ? mod.text : region.text;
            tip.textContent = txt.length > 30 ? txt.substring(0,30) + '...' : txt;
            div.appendChild(tip);
            div.addEventListener('click', function(e) { e.stopPropagation(); self.selectRegion(idx); });
            div.addEventListener('dblclick', function(e) { e.stopPropagation(); self.startEditRegion(idx); });
            if (self.modifications.has(idx)) div.classList.add('modified');
            wrapper.appendChild(div);
        });
    }

    renderBlockList() {
        var list = document.getElementById('blockList');
        if (!list) return;
        list.innerHTML = '';
        if (this.ocrRegions.length === 0) {
            list.innerHTML = '<div style="padding:20px;color:#666;text-align:center;">No blocks</div>';
            return;
        }
        var self = this;
        this.ocrRegions.forEach(function(region, idx) {
            var item = document.createElement('div');
            item.className = 'block-item';
            item.setAttribute('data-region-index', idx);
            if (self.modifications.has(idx)) item.classList.add('modified');
            var mod = self.modifications.get(idx);
            var txt = mod ? mod.text : region.text;
            var html = (mod && mod.tableHtml) ? mod.tableHtml : region.tableHtml;
            var hdr = document.createElement('div');
            hdr.className = 'block-header';
            var type = document.createElement('span');
            type.className = 'block-type ' + region.type;
            type.textContent = self.getTypeLabel(region.type);
            var num = document.createElement('span');
            num.className = 'block-index';
            num.textContent = '#' + (idx + 1);
            hdr.appendChild(type);
            hdr.appendChild(num);
            var cnt = document.createElement('div');
            cnt.className = 'block-content';
            if (region.type === 'table' && html) { cnt.classList.add('table-preview'); cnt.innerHTML = html; }
            else { cnt.textContent = txt || '(empty)'; }
            var meta = document.createElement('div');
            meta.className = 'block-meta';
            var co = region.coordinates;
            meta.textContent = 'Pos:(' + Math.round(co.x) + ',' + Math.round(co.y) + ') Size:' + Math.round(co.width) + 'x' + Math.round(co.height);
            item.appendChild(hdr);
            item.appendChild(cnt);
            item.appendChild(meta);
            item.addEventListener('click', function() { self.selectRegion(idx); });
            item.addEventListener('dblclick', function() { self.startEditRegion(idx); });
            list.appendChild(item);
        });
    }

    getTypeLabel(t) {
        var m = {text:'Text',title:'Title',table:'Table',figure:'Figure',header:'Header',footer:'Footer'};
        return m[t] || t;
    }

    selectRegion(idx) {
        document.querySelectorAll('.ocr-region.active').forEach(function(el) { el.classList.remove('active'); });
        document.querySelectorAll('.block-item.active').forEach(function(el) { el.classList.remove('active'); });
        var r = document.querySelector('.ocr-region[data-region-index="' + idx + '"]');
        if (r) r.classList.add('active');
        var b = document.querySelector('.block-item[data-region-index="' + idx + '"]');
        if (b) { b.classList.add('active'); b.scrollIntoView({behavior:'smooth',block:'center'}); }
        this.activeRegionIndex = idx;
    }

    startEditRegion(idx) {
        var region = this.ocrRegions[idx];
        if (!region) return;
        this.editingRegionIndex = idx;
        this.selectRegion(idx);
        if (region.type === 'table') this.openTableEdit(idx);
        else this.openTextEdit(idx);
    }

    openTextEdit(idx) {
        var region = this.ocrRegions[idx];
        var mod = this.modifications.get(idx);
        var txt = mod ? mod.text : region.text;
        var input = document.getElementById('textEditInput');
        if (input) input.value = txt;
        var ov = document.getElementById('editOverlay');
        if (ov) ov.classList.add('visible');
        var pop = document.getElementById('textEditPopup');
        if (pop) pop.style.display = 'block';
        if (input) input.focus();
    }

    closeTextEdit() {
        var ov = document.getElementById('editOverlay');
        if (ov) ov.classList.remove('visible');
        var pop = document.getElementById('textEditPopup');
        if (pop) pop.style.display = 'none';
        this.editingRegionIndex = null;
    }

    saveTextEdit() {
        var input = document.getElementById('textEditInput');
        var txt = input ? input.value : '';
        var idx = this.editingRegionIndex;
        if (idx !== null) {
            this.modifications.set(idx, {text: txt, tableHtml: null});
            this.updateRegionDisplay(idx);
            this.uiManager.showSuccess('Saved');
        }
        this.closeTextEdit();
    }

    openTableEdit(idx) {
        var region = this.ocrRegions[idx];
        var mod = this.modifications.get(idx);
        var html = (mod && mod.tableHtml) ? mod.tableHtml : (region.tableHtml || '<table><tr><td>No data</td></tr></table>');
        var cnt = document.getElementById('tableEditContent');
        if (cnt) {
            cnt.innerHTML = html;
            cnt.querySelectorAll('td,th').forEach(function(c) { c.contentEditable = 'true'; });
        }
        var ov = document.getElementById('editOverlay');
        if (ov) ov.classList.add('visible');
        var pop = document.getElementById('tableEditPopup');
        if (pop) pop.classList.add('visible');
    }

    closeTableEdit() {
        var ov = document.getElementById('editOverlay');
        if (ov) ov.classList.remove('visible');
        var pop = document.getElementById('tableEditPopup');
        if (pop) pop.classList.remove('visible');
        this.editingRegionIndex = null;
    }

    saveTableEdit() {
        var cnt = document.getElementById('tableEditContent');
        var idx = this.editingRegionIndex;
        if (idx !== null && cnt) {
            cnt.querySelectorAll('td,th').forEach(function(c) { c.removeAttribute('contenteditable'); });
            this.modifications.set(idx, {text: cnt.textContent.trim(), tableHtml: cnt.innerHTML});
            this.updateRegionDisplay(idx);
            this.uiManager.showSuccess('Saved');
        }
        this.closeTableEdit();
    }

    closeAllPopups() { this.closeTextEdit(); this.closeTableEdit(); }

    updateRegionDisplay(idx) {
        var r = document.querySelector('.ocr-region[data-region-index="' + idx + '"]');
        if (r) {
            r.classList.add('modified');
            var tip = r.querySelector('.ocr-region-tooltip');
            if (tip) {
                var mod = this.modifications.get(idx);
                var txt = mod ? mod.text : '';
                tip.textContent = txt.length > 30 ? txt.substring(0,30) + '...' : txt;
            }
        }
        var b = document.querySelector('.block-item[data-region-index="' + idx + '"]');
        if (b) {
            b.classList.add('modified');
            b.classList.add('highlight-flash');
            var cnt = b.querySelector('.block-content');
            if (cnt) {
                var mod = this.modifications.get(idx);
                var region = this.ocrRegions[idx];
                if (region.type === 'table' && mod && mod.tableHtml) cnt.innerHTML = mod.tableHtml;
                else cnt.textContent = (mod && mod.text) ? mod.text : '(empty)';
            }
            b.scrollIntoView({behavior:'smooth',block:'center'});
            setTimeout(function() { b.classList.remove('highlight-flash'); }, 1000);
        }
    }

    showConfidenceReport(cr) {
        if (!cr || !cr.confidence_breakdown) return;
        var div = document.getElementById('confidenceReport');
        if (!div) return;
        var o = cr.confidence_breakdown.overall;
        div.innerHTML = '<h4>Confidence: ' + o.score.toFixed(2) + ' (' + o.level + ')</h4><p>' + o.description + '</p>';
    }

    showDownloadButton() {
        var btns = document.getElementById('downloadButtons');
        if (btns) btns.style.display = 'flex';
        var self = this;
        var b1 = document.getElementById('downloadRawJsonBtn');
        var b2 = document.getElementById('downloadPPStructureBtn');
        var b3 = document.getElementById('downloadRawHtmlBtn');
        var b4 = document.getElementById('downloadOcrBtn');
        if (b1) b1.onclick = function() { self.downloadRawOutput('json'); };
        if (b2) b2.onclick = function() { self.downloadRawOutput('ppstructure'); };
        if (b3) b3.onclick = function() { self.downloadRawOutput('html'); };
        if (b4) b4.onclick = function() { self.downloadOcrResult(); };
    }

    async downloadRawOutput(fmt) {
        if (!this.currentJobId) return;
        try {
            var res = await fetch('/api/convert/' + this.currentJobId + '/raw-output');
            var data = await res.json();
            if (fmt === 'json' && data.raw_json) this.downloadBlob(new Blob([JSON.stringify(data.raw_json,null,2)],{type:'application/json'}), 'raw-' + this.currentJobId + '.json');
            else if (fmt === 'ppstructure' && data.ppstructure_json) this.downloadBlob(new Blob([JSON.stringify(data.ppstructure_json,null,2)],{type:'application/json'}), 'ppstructure-' + this.currentJobId + '.json');
            else if (fmt === 'html' && data.raw_html) this.downloadBlob(new Blob([data.raw_html],{type:'text/html'}), 'raw-' + this.currentJobId + '.html');
        } catch (e) { this.uiManager.showError('Download failed'); }
    }

    downloadBlob(blob, name) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url; a.download = name;
        document.body.appendChild(a); a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    downloadOcrResult() {
        if (!this.ocrData) return;
        var self = this;
        var mods = {};
        this.modifications.forEach(function(v,k) { mods[k] = v; });
        var blocks = this.ocrRegions.map(function(r,i) {
            var m = self.modifications.get(i);
            return {index:i, type:r.type, text:m?m.text:r.text, tableHtml:(m&&m.tableHtml)?m.tableHtml:r.tableHtml, coordinates:r.coordinates, modified:self.modifications.has(i)};
        });
        var data = {jobId:this.currentJobId, timestamp:new Date().toISOString(), blocks:blocks, modifications:mods, summary:{totalBlocks:this.ocrRegions.length, modifiedBlocks:this.modifications.size}};
        this.downloadBlob(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}), 'ocr-result-' + (this.currentJobId||'unknown') + '.json');
    }
}

document.addEventListener('DOMContentLoaded', function() { 
    console.log('DOMContentLoaded - creating App');
    window.app = new App(); 
});
