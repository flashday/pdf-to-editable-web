import { useEffect, useCallback } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';

/**
 * 保存快捷键 Hook
 * 
 * 功能：
 * - 监听 Ctrl+S / Cmd+S 快捷键
 * - 触发保存操作
 * - 阻止浏览器默认保存行为
 */
export function useSaveShortcut() {
  const { saveContent, isDirty, isSaving } = useWorkbenchStore();

  const handleSave = useCallback(async () => {
    if (!isDirty || isSaving) return;
    await saveContent();
  }, [saveContent, isDirty, isSaving]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // 检测 Ctrl+S (Windows/Linux) 或 Cmd+S (Mac)
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSave();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleSave]);

  return { handleSave };
}

export default useSaveShortcut;
