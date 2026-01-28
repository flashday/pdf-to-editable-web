import React from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import styles from './EditorPanel.module.css';

const EditorPanel: React.FC = () => {
  const { markdownContent, setMarkdownContent, isLoading } = useWorkbenchStore();

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

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMarkdownContent(e.target.value);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span>Markdown 编辑器</span>
        <div className={styles.tabs}>
          <button className={styles.tabActive}>所见即所得</button>
          <button className={styles.tab}>源码</button>
        </div>
      </div>
      <div className={styles.content}>
        {/* TODO: 集成 Vditor 编辑器 */}
        <textarea
          className={styles.textarea}
          value={markdownContent}
          onChange={handleContentChange}
          placeholder="Markdown 内容将在这里显示..."
        />
      </div>
    </div>
  );
};

export default EditorPanel;
