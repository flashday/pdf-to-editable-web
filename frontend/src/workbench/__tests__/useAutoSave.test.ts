import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutoSave } from '../hooks/useAutoSave';
import { useWorkbenchStore } from '../stores/workbenchStore';

// Mock the store
vi.mock('../stores/workbenchStore', () => ({
  useWorkbenchStore: vi.fn()
}));

describe('useAutoSave', () => {
  const mockSaveContent = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'initial content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('should auto-save after debounce delay', async () => {
    const { rerender } = renderHook(() => useAutoSave({ debounceMs: 3000 }));
    
    // Simulate content change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    // Before debounce delay
    expect(mockSaveContent).not.toHaveBeenCalled();
    
    // After debounce delay
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    expect(mockSaveContent).toHaveBeenCalledTimes(1);
  });

  it('should not auto-save when disabled', async () => {
    const { rerender } = renderHook(() => useAutoSave({ enabled: false }));
    
    // Simulate content change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should not auto-save when not dirty', async () => {
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'initial content',
      isDirty: false,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    const { rerender } = renderHook(() => useAutoSave());
    
    // Simulate content change but not dirty
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: false,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should not auto-save when already saving', async () => {
    const { rerender } = renderHook(() => useAutoSave());
    
    // Simulate content change while saving
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: true,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should not auto-save without jobId', async () => {
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'initial content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: null
    });
    
    const { rerender } = renderHook(() => useAutoSave());
    
    // Simulate content change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: null
    });
    
    rerender();
    
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should debounce multiple rapid changes', async () => {
    const { rerender } = renderHook(() => useAutoSave({ debounceMs: 1000 }));
    
    // First change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'change 1',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    rerender();
    
    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    
    // Second change before debounce completes
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'change 2',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    rerender();
    
    await act(async () => {
      vi.advanceTimersByTime(500);
    });
    
    // Third change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'change 3',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    rerender();
    
    // Should not have saved yet
    expect(mockSaveContent).not.toHaveBeenCalled();
    
    // Wait for final debounce
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    
    // Should only save once
    expect(mockSaveContent).toHaveBeenCalledTimes(1);
  });

  it('should use custom debounce delay', async () => {
    const { rerender } = renderHook(() => useAutoSave({ debounceMs: 5000 }));
    
    // Simulate content change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    // Before custom delay
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockSaveContent).not.toHaveBeenCalled();
    
    // After custom delay
    await act(async () => {
      vi.advanceTimersByTime(2000);
    });
    expect(mockSaveContent).toHaveBeenCalledTimes(1);
  });

  it('should return saveNow function', () => {
    const { result } = renderHook(() => useAutoSave());
    
    expect(result.current.saveNow).toBeDefined();
    expect(typeof result.current.saveNow).toBe('function');
  });

  it('should return cancelPendingSave function', () => {
    const { result } = renderHook(() => useAutoSave());
    
    expect(result.current.cancelPendingSave).toBeDefined();
    expect(typeof result.current.cancelPendingSave).toBe('function');
  });

  it('should cancel pending save when cancelPendingSave is called', async () => {
    const { result, rerender } = renderHook(() => useAutoSave({ debounceMs: 3000 }));
    
    // Simulate content change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    // Wait a bit
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    
    // Cancel pending save
    act(() => {
      result.current.cancelPendingSave();
    });
    
    // Wait for original debounce time
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    
    // Should not have saved
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should cleanup timeout on unmount', async () => {
    const { rerender, unmount } = renderHook(() => useAutoSave({ debounceMs: 3000 }));
    
    // Simulate content change
    (useWorkbenchStore as any).mockReturnValue({
      markdownContent: 'changed content',
      isDirty: true,
      isSaving: false,
      saveContent: mockSaveContent,
      jobId: 'test-job-123'
    });
    
    rerender();
    
    // Unmount before debounce completes
    unmount();
    
    // Wait for debounce time
    await act(async () => {
      vi.advanceTimersByTime(5000);
    });
    
    // Should not have saved after unmount
    expect(mockSaveContent).not.toHaveBeenCalled();
  });
});
