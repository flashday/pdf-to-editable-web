/**
 * 编辑器光标监听 Hook
 * 用于监听编辑器中的光标位置变化，实现 Editor -> PDF 的定位
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';
import { getBlockIdAtPosition } from '../utils/anchorParser';

interface UseEditorCursorOptions {
  /** 防抖延迟（毫秒） */
  debounceDelay?: number;
  /** 是否启用 */
  enabled?: boolean;
}

interface UseEditorCursorReturn {
  /** 当前光标位置 */
  cursorPosition: number;
  /** 当前光标所在的 Block ID */
  currentBlockId: string | null;
  /** 手动更新光标位置 */
  updateCursorPosition: (position: number) => void;
  /** 从选区获取光标位置 */
  getCursorPositionFromSelection: () => number;
}

export function useEditorCursor(options: UseEditorCursorOptions = {}): UseEditorCursorReturn {
  const { debounceDelay = 100, enabled = true } = options;

  const { anchors, setActiveBlockId } = useWorkbenchStore();
  
  const [cursorPosition, setCursorPosition] = useState(0);
  const [currentBlockId, setCurrentBlockId] = useState<string | null>(null);
  
  const debounceTimerRef = useRef<number | null>(null);
  const lastBlockIdRef = useRef<string | null>(null);

  /**
   * 从当前选区获取光标位置
   */
  const getCursorPositionFromSelection = useCallback((): number => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      return 0;
    }

    const range = selection.getRangeAt(0);
    
    // 获取编辑器容器
    const editorContainer = document.querySelector('.vditor-content') || 
                           document.querySelector('.vditor-wysiwyg') ||
                           document.querySelector('.vditor-sv');
    
    if (!editorContainer) {
      return 0;
    }

    // 计算光标在文档中的位置
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(editorContainer);
    preCaretRange.setEnd(range.startContainer, range.startOffset);
    
    return preCaretRange.toString().length;
  }, []);

  /**
   * 更新光标位置并解析 Block ID
   */
  const updateCursorPosition = useCallback((position: number) => {
    if (!enabled) return;

    // 清除之前的防抖定时器
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // 防抖处理
    debounceTimerRef.current = window.setTimeout(() => {
      setCursorPosition(position);

      // 解析当前位置对应的 Block ID
      const blockId = getBlockIdAtPosition(anchors, position);
      setCurrentBlockId(blockId);

      // 只有当 Block ID 变化时才更新 Store
      if (blockId !== lastBlockIdRef.current) {
        lastBlockIdRef.current = blockId;
        setActiveBlockId(blockId);
      }
    }, debounceDelay);
  }, [anchors, debounceDelay, enabled, setActiveBlockId]);

  /**
   * 监听选区变化
   */
  useEffect(() => {
    if (!enabled) return;

    const handleSelectionChange = () => {
      const position = getCursorPositionFromSelection();
      updateCursorPosition(position);
    };

    // 监听选区变化事件
    document.addEventListener('selectionchange', handleSelectionChange);

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [enabled, getCursorPositionFromSelection, updateCursorPosition]);

  return {
    cursorPosition,
    currentBlockId,
    updateCursorPosition,
    getCursorPositionFromSelection
  };
}

export default useEditorCursor;
