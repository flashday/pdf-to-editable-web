import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import styles from './PdfPanel.module.css';

const PdfPanel: React.FC = () => {
  const { jobId, layoutBlocks, zoomLevel, isLoading } = useWorkbenchStore();

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>加载 PDF 预览...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span>PDF 预览</span>
        <span className={styles.blockCount}>
          {layoutBlocks.length} 个区块
        </span>
      </div>
      <div className={styles.content}>
        {/* TODO: 实现 PDF 图像渲染和 Bounding Box 叠加 */}
        <div className={styles.placeholder}>
          <p>PDF 渲染区域</p>
          <p className={styles.hint}>缩放: {zoomLevel}%</p>
          {jobId && (
            <img 
              src={`/api/convert/${jobId}/image`}
              alt="PDF Preview"
              style={{ 
                maxWidth: '100%',
                transform: `scale(${zoomLevel / 100})`,
                transformOrigin: 'top left'
              }}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default PdfPanel;
