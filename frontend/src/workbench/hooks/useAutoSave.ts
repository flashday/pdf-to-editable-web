import { useEffect, useRef, useCallback } from 'react';
import { useWorkbenchStore } from '../stores/workbenchStore';

interface UseAutoSaveOptions {
  /** 防抖延迟时间（毫秒），默认 3000ms */
  debounceMs?: number;
  /** 是否启用自动保存，默认 true */
  enabled?: boolean;
}

/**
 * 自动保存 Hook
 * 
 * 功能：
 * - 监听内容变化
 * - 3 秒防抖自动保存
 * - 可配置启用/禁用
 */
export function useAutoSave(options: UseAutoSaveOptions = {}) {
  const { debounceMs = 3000, enabled = true } = options;
  
  const { 
    markdownContent, 
    isDirty, 
    isSaving, 
    saveContent,
    jobId 
  } = useWorkbenchStore();
  
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastContentRef = useRef<string>(markdownContent);

  // 清除定时器
  const clearAutoSaveTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // 触发自动保存
  const triggerAutoSave = useCallback(async () => {
    if (!isDirty || isSaving || !jobId) return;
    
    try {
      await saveContent();
    } catch (error) {
      console.error('Auto-save failed:', error);
    }
  }, [isDirty, isSaving, jobId, saveContent]);

  // 监听内容变化，设置防抖保存
  useEffect(() => {
    if (!enabled || !jobId) return;
    
    // 检查内容是否真的变化了
    if (markdownContent === lastContentRef.current) return;
    lastContentRef.current = markdownContent;
    
    // 如果没有脏数据，不需要保存
    if (!isDirty) return;
    
    // 清除之前的定时器
    clearAutoSaveTimeout();
    
    // 设置新的防抖定时器
    timeoutRef.current = setTimeout(() => {
      triggerAutoSave();
    }, debounceMs);
    
    return () => {
      clearAutoSaveTimeout();
    };
  }, [markdownContent, isDirty, enabled, jobId, debounceMs, clearAutoSaveTimeout, triggerAutoSave]);

  // 组件卸载时清除定时器
  useEffect(() => {
    return () => {
      clearAutoSaveTimeout();
    };
  }, [clearAutoSaveTimeout]);

  return {
    /** 手动触发保存（跳过防抖） */
    saveNow: triggerAutoSave,
    /** 取消待执行的自动保存 */
    cancelPendingSave: clearAutoSaveTimeout,
    /** 是否有待执行的自动保存 */
    hasPendingSave: timeoutRef.current !== null
  };
}

export default useAutoSave;
