import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import VditorWrapper from './VditorWrapper';
import styles from './EditorPanel.module.css';

type EditorMode = 'wysiwyg' | 'sv' | 'ir';

interface EditorPanelProps {
  onCursorBlockChange?: (blockId: string | null) => void;
}

const EditorPanel: React.FC<EditorPanelProps> = ({ onCursorBlockChange }) => {
  const { 
    markdownContent, 
    setMarkdownContent, 
    isLoading, 
    error,
    isDirty,
    anchors,
    activeBlockId
  } = useWorkbenchStore();

  const [editorMode, setEditorMode] = useState<EditorMode>('wysiwyg');
  const vditorRef = useRef<{ scrollToAnchor: (id: string) => void } | null>(null);

  // 处理内容变更
  const handleContentChange = useCallback((content: string) => {
    setMarkdownContent(content);
  }, [setMarkdownContent]);

  // 处理光标位置变化，解析当前所在的 Block ID
  const handleCursorChange = useCallback((position: number) => {
    if (!anchors || anchors.length === 0) return;

    // 找到位置之前最近的锚点
    let nearestAnchor = null;
    for (const anchor of anchors) {
      if (anchor.position <= position) {
        nearestAnchor = anchor;
      } else {
        break;
      }
    }

    const blockId = nearestAnchor?.blockId ?? null;
    if (onCursorBlockChange) {
      onCursorBlockChange(blockId);
    }
  }, [anchors, onCursorBlockChange]);

  // 监听 activeBlockId 变化，滚动到对应位置
  useEffect(() => {
    if (activeBlockId && vditorRef.current) {
      vditorRef.current.scrollToAnchor(`block_${activeBlockId}`);
    }
  }, [activeBlockId]);

  // 切换编辑模式
  const handleModeChange = (mode: EditorMode) => {
    setEditorMode(mode);
  };

  // 加载状态
  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>加载编辑器...</p>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.error}>
          <span className={styles.errorIcon}>⚠️</span>
          <p>{error}</p>
          <button 
            className={styles.retryButton}
            onClick={() => window.location.reload()}
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.title}>
          <span>Markdown 编辑器</span>
          {isDirty && <span className={styles.dirtyIndicator}>●</span>}
        </div>
        <div className={styles.tabs}>
          <button 
            className={editorMode === 'wysiwyg' ? styles.tabActive : styles.tab}
            onClick={() => handleModeChange('wysiwyg')}
            title="所见即所得模式"
          >
            所见即所得
          </button>
          <button 
            className={editorMode === 'sv' ? styles.tabActive : styles.tab}
            onClick={() => handleModeChange('sv')}
            title="分屏预览模式"
          >
            分屏
          </button>
          <button 
            className={editorMode === 'ir' ? styles.tabActive : styles.tab}
            onClick={() => handleModeChange('ir')}
            title="即时渲染模式"
          >
            源码
          </button>
        </div>
      </div>
      <div className={styles.content}>
        <VditorWrapper
          content={markdownContent}
          onChange={handleContentChange}
          onCursorChange={handleCursorChange}
          mode={editorMode}
          placeholder="在此编辑 Markdown 内容..."
        />
      </div>
    </div>
  );
};

export default EditorPanel;
