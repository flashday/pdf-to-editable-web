/**
 * 骨架屏组件
 * 任务 21.1: 添加加载骨架屏
 */
import React from 'react';
import styles from './Skeleton.module.css';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'rectangular' | 'circular';
  animation?: 'pulse' | 'wave' | 'none';
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = '1em',
  variant = 'text',
  animation = 'pulse',
  className = '',
}) => {
  const style: React.CSSProperties = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div
      className={`${styles.skeleton} ${styles[variant]} ${styles[animation]} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
};

// PDF 面板骨架屏
export const PdfPanelSkeleton: React.FC = () => (
  <div className={styles.pdfPanelSkeleton}>
    <div className={styles.toolbar}>
      <Skeleton width={100} height={32} variant="rectangular" />
      <Skeleton width={150} height={32} variant="rectangular" />
      <Skeleton width={100} height={32} variant="rectangular" />
    </div>
    <div className={styles.imageArea}>
      <Skeleton width="100%" height="100%" variant="rectangular" />
    </div>
  </div>
);

// 编辑器面板骨架屏
export const EditorPanelSkeleton: React.FC = () => (
  <div className={styles.editorPanelSkeleton}>
    <div className={styles.toolbar}>
      <Skeleton width={200} height={36} variant="rectangular" />
    </div>
    <div className={styles.editorArea}>
      <Skeleton width="80%" height={24} />
      <Skeleton width="100%" height={24} />
      <Skeleton width="60%" height={24} />
      <Skeleton width="90%" height={24} />
      <Skeleton width="100%" height={24} />
      <Skeleton width="70%" height={24} />
      <Skeleton width="85%" height={24} />
      <Skeleton width="100%" height={24} />
    </div>
  </div>
);

// 完整工作台骨架屏
export const WorkbenchSkeleton: React.FC = () => (
  <div className={styles.workbenchSkeleton}>
    <div className={styles.header}>
      <Skeleton width={200} height={40} variant="rectangular" />
      <Skeleton width={120} height={36} variant="rectangular" />
    </div>
    <div className={styles.content}>
      <div className={styles.leftPanel}>
        <PdfPanelSkeleton />
      </div>
      <div className={styles.rightPanel}>
        <EditorPanelSkeleton />
      </div>
    </div>
  </div>
);

export default Skeleton;
