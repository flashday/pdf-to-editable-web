import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useWorkbenchStore } from '../stores/workbenchStore';
import PdfPanel from '../components/PdfPanel/PdfPanel';
import EditorPanel from '../components/EditorPanel/EditorPanel';
import Toolbar from '../components/Toolbar/Toolbar';
import SplitPane from '../components/common/SplitPane';
import styles from './WorkbenchPage.module.css';

const WorkbenchPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get('jobId');
  const { setJobId, loadData, isLoading, error } = useWorkbenchStore();

  useEffect(() => {
    if (jobId) {
      setJobId(jobId);
      loadData(jobId);
    }
  }, [jobId, setJobId, loadData]);

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
          left={<PdfPanel />}
          right={<EditorPanel />}
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
