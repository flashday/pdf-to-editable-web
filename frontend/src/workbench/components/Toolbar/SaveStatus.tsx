import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import styles from './SaveStatus.module.css';

const SaveStatus: React.FC = () => {
  const { isDirty, isSaving, lastSavedAt, saveError } = useWorkbenchStore();

  const formatTime = (date: Date | null) => {
    if (!date) return '';
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  if (saveError) {
    return (
      <div className={`${styles.status} ${styles.error}`}>
        <span className={styles.icon}>⚠</span>
        <span>保存失败</span>
      </div>
    );
  }

  if (isSaving) {
    return (
      <div className={`${styles.status} ${styles.saving}`}>
        <span className={styles.spinner}></span>
        <span>保存中...</span>
      </div>
    );
  }

  if (isDirty) {
    return (
      <div className={`${styles.status} ${styles.dirty}`}>
        <span className={styles.icon}>●</span>
        <span>未保存更改</span>
      </div>
    );
  }

  if (lastSavedAt) {
    return (
      <div className={`${styles.status} ${styles.saved}`}>
        <span className={styles.icon}>✓</span>
        <span>已保存 {formatTime(lastSavedAt)}</span>
      </div>
    );
  }

  return null;
};

export default SaveStatus;
