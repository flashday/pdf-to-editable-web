/**
 * Block 映射 Hook
 * 用于管理 PDF Bounding Box 与 Markdown 锚点之间的映射关系
 */

import { useCallback, useEffect, useRef } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';
import { getBlockIdAtPosition, getAnchorByBlockId } from '../utils/anchorParser';

interface UseBlockMappingOptions {
  /** 高亮持续时间（毫秒） */
  highlightDuration?: number;
  /** 滚动行为 */
  scrollBehavior?: ScrollBehavior;
  /** 编辑器容器引用 */
  editorContainerRef?: React.RefObject<HTMLElement>;
  /** PDF 容器引用 */
  pdfContainerRef?: React.RefObject<HTMLElement>;
}

interface UseBlockMappingReturn {
  /** 滚动编辑器到指定 Block */
  scrollEditorToBlock: (blockId: string) => void;
  /** 滚动 PDF 到指定 Block */
  scrollPdfToBlock: (blockId: string) => void;
  /** 根据光标位置获取 Block ID */
  getBlockAtCursor: (position: number) => string | null;
  /** 高亮编辑器中的 Block */
  highlightEditorBlock: (blockId: string) => void;
  /** 高亮 PDF 中的 Block */
  highlightPdfBlock: (blockId: string) => void;
}

export function useBlockMapping(options: UseBlockMappingOptions = {}): UseBlockMappingReturn {
  const {
    highlightDuration = 2000,
    scrollBehavior = 'smooth',
    editorContainerRef,
    pdfContainerRef
  } = options;

  const { anchors, layoutBlocks, activeBlockId } = useWorkbenchStore();
  
  // 高亮定时器引用
  const editorHighlightTimerRef = useRef<number | null>(null);
  const pdfHighlightTimerRef = useRef<number | null>(null);

  /**
   * 滚动编辑器到指定 Block
   */
  const scrollEditorToBlock = useCallback((blockId: string) => {
    if (!editorContainerRef?.current) return;

    const anchorElement = editorContainerRef.current.querySelector(`#block_${blockId}`);
    if (anchorElement) {
      anchorElement.scrollIntoView({ behavior: scrollBehavior, block: 'center' });
    } else {
      // 如果找不到锚点元素，尝试通过位置滚动
      const anchor = getAnchorByBlockId(anchors, blockId);
      if (anchor) {
        // 计算滚动位置（基于锚点在文档中的相对位置）
        const container = editorContainerRef.current;
        const scrollRatio = anchor.position / (container.scrollHeight || 1);
        container.scrollTo({
          top: scrollRatio * container.scrollHeight,
          behavior: scrollBehavior
        });
      }
    }
  }, [anchors, editorContainerRef, scrollBehavior]);

  /**
   * 滚动 PDF 到指定 Block
   */
  const scrollPdfToBlock = useCallback((blockId: string) => {
    if (!pdfContainerRef?.current) return;

    const block = layoutBlocks.find(b => b.id === blockId);
    if (!block) return;

    const container = pdfContainerRef.current;
    const { zoomLevel } = useWorkbenchStore.getState();
    const scale = zoomLevel / 100;

    // 计算 Block 在缩放后的位置
    const targetY = block.bbox.y * scale;
    const containerHeight = container.clientHeight;
    
    // 滚动到 Block 中心位置
    container.scrollTo({
      top: targetY - containerHeight / 2 + (block.bbox.height * scale) / 2,
      behavior: scrollBehavior
    });
  }, [layoutBlocks, pdfContainerRef, scrollBehavior]);

  /**
   * 根据光标位置获取 Block ID
   */
  const getBlockAtCursor = useCallback((position: number): string | null => {
    return getBlockIdAtPosition(anchors, position);
  }, [anchors]);

  /**
   * 高亮编辑器中的 Block
   */
  const highlightEditorBlock = useCallback((blockId: string) => {
    if (!editorContainerRef?.current) return;

    // 清除之前的高亮定时器
    if (editorHighlightTimerRef.current) {
      clearTimeout(editorHighlightTimerRef.current);
    }

    // 移除之前的高亮
    const previousHighlight = editorContainerRef.current.querySelector('.block-highlight');
    if (previousHighlight) {
      previousHighlight.classList.remove('block-highlight');
    }

    // 添加新的高亮
    const anchorElement = editorContainerRef.current.querySelector(`#block_${blockId}`);
    if (anchorElement) {
      // 高亮锚点后面的内容（通常是下一个兄弟元素）
      const nextElement = anchorElement.nextElementSibling;
      if (nextElement) {
        nextElement.classList.add('block-highlight');
        
        // 设置定时器移除高亮
        editorHighlightTimerRef.current = window.setTimeout(() => {
          nextElement.classList.remove('block-highlight');
        }, highlightDuration);
      }
    }
  }, [editorContainerRef, highlightDuration]);

  /**
   * 高亮 PDF 中的 Block
   */
  const highlightPdfBlock = useCallback((blockId: string) => {
    if (!pdfContainerRef?.current) return;

    // 清除之前的高亮定时器
    if (pdfHighlightTimerRef.current) {
      clearTimeout(pdfHighlightTimerRef.current);
    }

    // 移除之前的高亮
    const previousHighlight = pdfContainerRef.current.querySelector('.bbox-highlight');
    if (previousHighlight) {
      previousHighlight.classList.remove('bbox-highlight');
    }

    // 添加新的高亮
    const bboxElement = pdfContainerRef.current.querySelector(`[data-block-id="${blockId}"]`);
    if (bboxElement) {
      bboxElement.classList.add('bbox-highlight');
      
      // 设置定时器移除高亮
      pdfHighlightTimerRef.current = window.setTimeout(() => {
        bboxElement.classList.remove('bbox-highlight');
      }, highlightDuration);
    }
  }, [pdfContainerRef, highlightDuration]);

  // 监听 activeBlockId 变化，自动滚动和高亮
  useEffect(() => {
    if (activeBlockId) {
      scrollEditorToBlock(activeBlockId);
      highlightEditorBlock(activeBlockId);
    }
  }, [activeBlockId, scrollEditorToBlock, highlightEditorBlock]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (editorHighlightTimerRef.current) {
        clearTimeout(editorHighlightTimerRef.current);
      }
      if (pdfHighlightTimerRef.current) {
        clearTimeout(pdfHighlightTimerRef.current);
      }
    };
  }, []);

  return {
    scrollEditorToBlock,
    scrollPdfToBlock,
    getBlockAtCursor,
    highlightEditorBlock,
    highlightPdfBlock
  };
}

export default useBlockMapping;
