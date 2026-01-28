/**
 * 同步滚动 Hook
 * 实现 PDF 面板与编辑器面板的双向同步滚动
 * 
 * V2 优化：基于锚点的最近邻同步滚动
 * - 支持基于锚点的精确定位
 * - 保留比例同步作为回退方案
 * - 提供 syncToBlock 和 syncToAnchor 方法
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';
import { AnchorInfo, LayoutBlock } from '../stores/types';

interface UseSyncScrollOptions {
  /** PDF 容器引用 */
  pdfContainerRef: React.RefObject<HTMLElement>;
  /** 编辑器容器引用 */
  editorContainerRef: React.RefObject<HTMLElement>;
  /** 锚点列表 */
  anchors: AnchorInfo[];
  /** Block 列表 */
  layoutBlocks: LayoutBlock[];
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
  /** 同步到指定 Block（滚动预览面板） */
  syncToBlock: (blockId: string) => void;
  /** 同步到指定锚点（滚动编辑器） */
  syncToAnchor: (anchorId: string) => void;
  /** 获取当前 Block ID */
  getCurrentBlockId: () => string | null;
  /** 手动同步 PDF 到编辑器（比例同步回退） */
  syncPdfToEditor: () => void;
  /** 手动同步编辑器到 PDF（比例同步回退） */
  syncEditorToPdf: () => void;
}

/**
 * 核心算法：找到最近的锚点
 * 返回位置小于等于光标位置的最后一个锚点
 * 如果光标位置在所有锚点之前，返回 null
 * 
 * @param anchors 已排序的锚点列表
 * @param cursorPosition 光标位置
 * @returns 最近的锚点或 null
 */
export function findNearestAnchor(
  anchors: AnchorInfo[],
  cursorPosition: number
): AnchorInfo | null {
  if (!anchors || anchors.length === 0) {
    return null;
  }

  let nearest: AnchorInfo | null = null;
  for (const anchor of anchors) {
    if (anchor.position <= cursorPosition) {
      nearest = anchor;
    } else {
      break;
    }
  }
  return nearest;
}

export function useSyncScroll(options: UseSyncScrollOptions): UseSyncScrollReturn {
  const {
    pdfContainerRef,
    editorContainerRef,
    anchors,
    layoutBlocks,
    debounceDelay = 50,
    enabled = true
  } = options;

  const { syncScrollEnabled, toggleSyncScroll, zoomLevel } = useWorkbenchStore();
  
  const [isSyncing, setIsSyncing] = useState(false);
  
  // 当前 Block ID 追踪
  const currentBlockIdRef = useRef<string | null>(null);
  
  // 用于防止滚动循环
  const isScrollingFromPdfRef = useRef(false);
  const isScrollingFromEditorRef = useRef(false);
  const pdfScrollTimerRef = useRef<number | null>(null);
  const editorScrollTimerRef = useRef<number | null>(null);

  /**
   * 计算滚动比例（比例同步回退方案）
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
   * 根据 Block ID 获取 Block 信息
   */
  const getBlockById = useCallback((blockId: string): LayoutBlock | null => {
    return layoutBlocks.find(block => block.id === blockId) ?? null;
  }, [layoutBlocks]);

  /**
   * 根据 Block ID 获取锚点信息
   */
  const getAnchorByBlockId = useCallback((blockId: string): AnchorInfo | null => {
    return anchors.find(anchor => anchor.blockId === blockId) ?? null;
  }, [anchors]);

  /**
   * 同步到指定 Block（滚动预览面板到 Block 的 Bounding Box 位置）
   * Requirements: 2.2
   */
  const syncToBlock = useCallback((blockId: string) => {
    if (!pdfContainerRef.current) return;

    const block = getBlockById(blockId);
    if (!block) {
      console.warn(`Block not found: ${blockId}`);
      return;
    }

    isScrollingFromEditorRef.current = true;
    setIsSyncing(true);

    const container = pdfContainerRef.current;
    const scale = zoomLevel / 100;
    
    // 计算 Block 在缩放后的位置
    const blockTop = block.bbox.y * scale;
    const blockHeight = block.bbox.height * scale;
    const containerHeight = container.clientHeight;
    
    // 将 Block 滚动到容器中央
    const targetScrollTop = blockTop - (containerHeight / 2) + (blockHeight / 2);
    
    container.scrollTo({
      top: Math.max(0, targetScrollTop),
      behavior: 'smooth'
    });

    // 更新当前 Block ID
    currentBlockIdRef.current = blockId;

    // 重置标志
    setTimeout(() => {
      isScrollingFromEditorRef.current = false;
      setIsSyncing(false);
    }, debounceDelay + 100);
  }, [pdfContainerRef, getBlockById, zoomLevel, debounceDelay]);

  /**
   * 同步到指定锚点（滚动编辑器到锚点位置）
   * Requirements: 2.3
   */
  const syncToAnchor = useCallback((anchorId: string) => {
    if (!editorContainerRef.current) return;

    const anchor = getAnchorByBlockId(anchorId);
    if (!anchor) {
      console.warn(`Anchor not found for block: ${anchorId}`);
      return;
    }

    isScrollingFromPdfRef.current = true;
    setIsSyncing(true);

    const container = editorContainerRef.current;
    
    // 尝试找到编辑器中对应位置的元素
    // 这里使用一个简化的方法：基于锚点位置计算滚动比例
    // 实际实现可能需要与 Vditor 编辑器集成来获取精确位置
    const totalLength = container.scrollHeight;
    const containerHeight = container.clientHeight;
    
    // 估算锚点在编辑器中的相对位置
    // 这是一个简化的实现，实际可能需要更精确的位置计算
    const editorContent = container.querySelector('.vditor-ir, .vditor-wysiwyg, .vditor-sv');
    if (editorContent) {
      // 尝试找到包含锚点的元素
      const anchorElements = editorContent.querySelectorAll('[data-block-id]');
      for (const el of anchorElements) {
        if (el.getAttribute('data-block-id') === anchorId) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          currentBlockIdRef.current = anchorId;
          setTimeout(() => {
            isScrollingFromPdfRef.current = false;
            setIsSyncing(false);
          }, debounceDelay + 100);
          return;
        }
      }
    }
    
    // 回退：基于位置比例滚动
    // 假设 Markdown 内容长度与滚动高度成正比
    const markdownLength = anchors.length > 0 
      ? Math.max(...anchors.map(a => a.position)) + 100 
      : totalLength;
    const ratio = anchor.position / markdownLength;
    const targetScrollTop = ratio * (totalLength - containerHeight);
    
    container.scrollTo({
      top: Math.max(0, targetScrollTop),
      behavior: 'smooth'
    });

    currentBlockIdRef.current = anchorId;

    setTimeout(() => {
      isScrollingFromPdfRef.current = false;
      setIsSyncing(false);
    }, debounceDelay + 100);
  }, [editorContainerRef, getAnchorByBlockId, anchors, debounceDelay]);

  /**
   * 获取当前 Block ID
   */
  const getCurrentBlockId = useCallback((): string | null => {
    return currentBlockIdRef.current;
  }, []);

  /**
   * 同步 PDF 滚动到编辑器（比例同步回退）
   * Requirements: 2.5
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
   * 同步编辑器滚动到 PDF（比例同步回退）
   * Requirements: 2.5
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
   * Requirements: 2.6
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
   * Requirements: 2.6
   */
  const handleEditorScroll = useCallback(() => {
    if (!syncScrollEnabled || !enabled) return;
    if (isScrollingFromPdfRef.current) return;

    // 防抖处理
    if (editorScrollTimerRef.current) {
      clearTimeout(editorScrollTimerRef.current);
    }

    editorScrollTimerRef.current = window.setTimeout(() => {
      // 尝试获取编辑器光标位置
      // 如果无法获取，回退到比例同步
      const editorContainer = editorContainerRef.current;
      if (editorContainer) {
        // 尝试从编辑器获取光标位置
        // 这里使用滚动位置作为近似值
        const scrollRatio = getScrollRatio(editorContainer);
        const estimatedPosition = Math.floor(scrollRatio * 10000); // 估算位置
        
        const nearestAnchor = findNearestAnchor(anchors, estimatedPosition);
        if (nearestAnchor && anchors.length > 0) {
          // 基于锚点同步
          syncToBlock(nearestAnchor.blockId);
        } else {
          // 回退到比例同步
          syncEditorToPdf();
        }
      }
    }, debounceDelay);
  }, [syncScrollEnabled, enabled, debounceDelay, editorContainerRef, anchors, getScrollRatio, syncToBlock, syncEditorToPdf]);

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
    syncToBlock,
    syncToAnchor,
    getCurrentBlockId,
    syncPdfToEditor,
    syncEditorToPdf
  };
}

export default useSyncScroll;
