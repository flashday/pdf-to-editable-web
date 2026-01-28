import React, { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useWorkbenchStore } from '../stores/workbenchStore';
import { useSaveShortcut } from '../hooks/useSaveShortcut';
import { useAutoSave } from '../hooks/useAutoSave';
import { useSyncScroll } from '../hooks/useSyncScroll';
import PdfPanel from '../components/PdfPanel/PdfPanel';
import EditorPanel from '../components/EditorPanel/EditorPanel';
import Toolbar from '../components/Toolbar/Toolbar';
import SplitPane from '../components/common/SplitPane';
import styles from './WorkbenchPage.module.css';

const WorkbenchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get('jobId');
  const { 
    setJobId, 
    loadData, 
    isLoading, 
    error, 
    isDirty,
    anchors,
    layoutBlocks,
    setActiveBlockId
  } = useWorkbenchStore();
  
  // 容器引用（用于同步滚动）
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  const editorContainerRef = useRef<HTMLDivElement>(null);
  
  // 启用 Ctrl+S 快捷键保存
  useSaveShortcut();
  
  // 启用自动保存（3 秒防抖）
  useAutoSave({ debounceMs: 3000, enabled: true });
  
  // V2 优化：基于锚点的同步滚动
  const { syncToBlock, syncToAnchor } = useSyncScroll({
    pdfContainerRef,
    editorContainerRef,
    anchors,
    layoutBlocks,
    debounceDelay: 50,
    enabled: true
  });
  
  // 处理 Block 点击事件（从预览面板同步到编辑器）
  const handleBlockClick = (blockId: string) => {
    setActiveBlockId(blockId);
    syncToAnchor(blockId);
  };
  
  // 处理编辑器光标变化事件（从编辑器同步到预览面板）
  const handleEditorCursorChange = (blockId: string | null) => {
    if (blockId) {
      setActiveBlockId(blockId);
      syncToBlock(blockId);
    }
  };

  useEffect(() => {
    if (jobId) {
      setJobId(jobId);
      loadData(jobId);
    }
  }, [jobId, setJobId, loadData]);

  // 页面关闭前提示保存
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (isDirty) {
        event.preventDefault();
        // 现代浏览器会显示标准提示，不会显示自定义消息
        event.returnValue = '您有未保存的更改，确定要离开吗？';
        return event.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [isDirty]);

  const handleBackToTraditional = () => {
    // 返回传统模式
    window.location.href = `/?jobId=${jobId}#step4`;
  };

  if (!jobId) {
    return (
      <div className={styles.errorContainer}>
        <h2>缺少任务 ID</h2>
        <p>请从预录入界面进入精准编辑模式</p>
        <button onClick={() => window.location.href = '/'}>
          返回主页
        </button>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2>加载失败</h2>
        <p>{error}</p>
        <button onClick={handleBackToTraditional}>
          返回传统模式
        </button>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Toolbar onBackClick={handleBackToTraditional} />
      <div className={styles.mainContent}>
        <SplitPane
          left={
            <div ref={pdfContainerRef} style={{ height: '100%', overflow: 'auto' }}>
              <PdfPanel onBlockClick={handleBlockClick} />
            </div>
          }
          right={
            <div ref={editorContainerRef} style={{ height: '100%', overflow: 'auto' }}>
              <EditorPanel onCursorBlockChange={handleEditorCursorChange} />
            </div>
          }
          defaultLeftWidth={50}
          minLeftWidth={30}
          maxLeftWidth={70}
        />
      </div>
      {isLoading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.spinner}></div>
          <p>加载中...</p>
        </div>
      )}
    </div>
  );
};

export default WorkbenchPage;
