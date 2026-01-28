/**
 * 同步滚动 Hook
 * 实现 PDF 面板与编辑器面板的双向同步滚动
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';

interface UseSyncScrollOptions {
  /** PDF 容器引用 */
  pdfContainerRef: React.RefObject<HTMLElement>;
  /** 编辑器容器引用 */
  editorContainerRef: React.RefObject<HTMLElement>;
  /** 防抖延迟（毫秒） */
  debounceDelay?: number;
  /** 是否启用 */
  enabled?: boolean;
}

interface UseSyncScrollReturn {
  /** 是否正在同步 */
  isSyncing: boolean;
  /** 同步滚动是否启用 */
  syncEnabled: boolean;
  /** 切换同步滚动 */
  toggleSync: () => void;
  /** 手动同步 PDF 到编辑器 */
  syncPdfToEditor: () => void;
  /** 手动同步编辑器到 PDF */
  syncEditorToPdf: () => void;
}

export function useSyncScroll(options: UseSyncScrollOptions): UseSyncScrollReturn {
  const {
    pdfContainerRef,
    editorContainerRef,
    debounceDelay = 50,
    enabled = true
  } = options;

  const { syncScrollEnabled, toggleSyncScroll } = useWorkbenchStore();
  
  const [isSyncing, setIsSyncing] = useState(false);
  
  // 用于防止滚动循环
  const isScrollingFromPdfRef = useRef(false);
  const isScrollingFromEditorRef = useRef(false);
  const pdfScrollTimerRef = useRef<number | null>(null);
  const editorScrollTimerRef = useRef<number | null>(null);

  /**
   * 计算滚动比例
   */
  const getScrollRatio = useCallback((container: HTMLElement): number => {
    const maxScroll = container.scrollHeight - container.clientHeight;
    if (maxScroll <= 0) return 0;
    return container.scrollTop / maxScroll;
  }, []);

  /**
   * 设置滚动位置（基于比例）
   */
  const setScrollByRatio = useCallback((container: HTMLElement, ratio: number) => {
    const maxScroll = container.scrollHeight - container.clientHeight;
    container.scrollTop = ratio * maxScroll;
  }, []);

  /**
   * 同步 PDF 滚动到编辑器
   */
  const syncPdfToEditor = useCallback(() => {
    if (!pdfContainerRef.current || !editorContainerRef.current) return;
    if (isScrollingFromEditorRef.current) return;

    isScrollingFromPdfRef.current = true;
    setIsSyncing(true);

    const ratio = getScrollRatio(pdfContainerRef.current);
    setScrollByRatio(editorContainerRef.current, ratio);

    // 重置标志
    setTimeout(() => {
      isScrollingFromPdfRef.current = false;
      setIsSyncing(false);
    }, debounceDelay + 10);
  }, [pdfContainerRef, editorContainerRef, getScrollRatio, setScrollByRatio, debounceDelay]);

  /**
   * 同步编辑器滚动到 PDF
   */
  const syncEditorToPdf = useCallback(() => {
    if (!pdfContainerRef.current || !editorContainerRef.current) return;
    if (isScrollingFromPdfRef.current) return;

    isScrollingFromEditorRef.current = true;
    setIsSyncing(true);

    const ratio = getScrollRatio(editorContainerRef.current);
    setScrollByRatio(pdfContainerRef.current, ratio);

    // 重置标志
    setTimeout(() => {
      isScrollingFromEditorRef.current = false;
      setIsSyncing(false);
    }, debounceDelay + 10);
  }, [pdfContainerRef, editorContainerRef, getScrollRatio, setScrollByRatio, debounceDelay]);

  /**
   * PDF 滚动事件处理
   */
  const handlePdfScroll = useCallback(() => {
    if (!syncScrollEnabled || !enabled) return;
    if (isScrollingFromEditorRef.current) return;

    // 防抖处理
    if (pdfScrollTimerRef.current) {
      clearTimeout(pdfScrollTimerRef.current);
    }

    pdfScrollTimerRef.current = window.setTimeout(() => {
      syncPdfToEditor();
    }, debounceDelay);
  }, [syncScrollEnabled, enabled, debounceDelay, syncPdfToEditor]);

  /**
   * 编辑器滚动事件处理
   */
  const handleEditorScroll = useCallback(() => {
    if (!syncScrollEnabled || !enabled) return;
    if (isScrollingFromPdfRef.current) return;

    // 防抖处理
    if (editorScrollTimerRef.current) {
      clearTimeout(editorScrollTimerRef.current);
    }

    editorScrollTimerRef.current = window.setTimeout(() => {
      syncEditorToPdf();
    }, debounceDelay);
  }, [syncScrollEnabled, enabled, debounceDelay, syncEditorToPdf]);

  // 绑定滚动事件
  useEffect(() => {
    const pdfContainer = pdfContainerRef.current;
    const editorContainer = editorContainerRef.current;

    if (!pdfContainer || !editorContainer) return;

    pdfContainer.addEventListener('scroll', handlePdfScroll, { passive: true });
    editorContainer.addEventListener('scroll', handleEditorScroll, { passive: true });

    return () => {
      pdfContainer.removeEventListener('scroll', handlePdfScroll);
      editorContainer.removeEventListener('scroll', handleEditorScroll);

      // 清理定时器
      if (pdfScrollTimerRef.current) {
        clearTimeout(pdfScrollTimerRef.current);
      }
      if (editorScrollTimerRef.current) {
        clearTimeout(editorScrollTimerRef.current);
      }
    };
  }, [pdfContainerRef, editorContainerRef, handlePdfScroll, handleEditorScroll]);

  return {
    isSyncing,
    syncEnabled: syncScrollEnabled,
    toggleSync: toggleSyncScroll,
    syncPdfToEditor,
    syncEditorToPdf
  };
}

export default useSyncScroll;
