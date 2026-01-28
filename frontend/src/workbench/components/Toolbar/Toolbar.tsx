import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import SaveStatus from './SaveStatus';
import styles from './Toolbar.module.css';

interface ToolbarProps {
  onBackClick: () => void;
}

const Toolbar: React.FC<ToolbarProps> = ({ onBackClick }) => {
  const { 
    jobId, 
    zoomLevel, 
    setZoomLevel, 
    saveContent, 
    isDirty,
    isSaving 
  } = useWorkbenchStore();

  const handleZoomIn = () => {
    setZoomLevel(Math.min(zoomLevel + 10, 200));
  };

  const handleZoomOut = () => {
    setZoomLevel(Math.max(zoomLevel - 10, 50));
  };

  const handleSave = async () => {
    if (!isDirty || isSaving) return;
    await saveContent();
  };

  return (
    <div className={styles.toolbar}>
      <div className={styles.leftSection}>
        <button 
          className={styles.backButton}
          onClick={onBackClick}
          title="返回传统模式"
        >
          ← 返回
        </button>
        <span className={styles.title}>精准作业台</span>
        {jobId && <span className={styles.jobId}>任务: {jobId.slice(0, 8)}...</span>}
      </div>

      <div className={styles.centerSection}>
        <div className={styles.zoomControls}>
          <button onClick={handleZoomOut} disabled={zoomLevel <= 50}>−</button>
          <span>{zoomLevel}%</span>
          <button onClick={handleZoomIn} disabled={zoomLevel >= 200}>+</button>
        </div>
      </div>

      <div className={styles.rightSection}>
        <SaveStatus />
        <button 
          className={`${styles.saveButton} ${isDirty ? styles.dirty : ''}`}
          onClick={handleSave}
          disabled={!isDirty || isSaving}
        >
          {isSaving ? '保存中...' : '保存'}
        </button>
      </div>
    </div>
  );
};

export default Toolbar;
