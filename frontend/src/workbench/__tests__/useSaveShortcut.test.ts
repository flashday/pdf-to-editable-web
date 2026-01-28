import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSaveShortcut } from '../hooks/useSaveShortcut';
import { useWorkbenchStore } from '../stores/workbenchStore';

// Mock the store
vi.mock('../stores/workbenchStore', () => ({
  useWorkbenchStore: vi.fn()
}));

describe('useSaveShortcut', () => {
  const mockSaveContent = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
    (useWorkbenchStore as any).mockReturnValue({
      saveContent: mockSaveContent,
      isDirty: true,
      isSaving: false
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should call saveContent on Ctrl+S', async () => {
    renderHook(() => useSaveShortcut());
    
    // Simulate Ctrl+S
    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true
    });
    
    await act(async () => {
      document.dispatchEvent(event);
    });
    
    expect(mockSaveContent).toHaveBeenCalledTimes(1);
  });

  it('should call saveContent on Cmd+S (Mac)', async () => {
    renderHook(() => useSaveShortcut());
    
    // Simulate Cmd+S
    const event = new KeyboardEvent('keydown', {
      key: 's',
      metaKey: true,
      bubbles: true
    });
    
    await act(async () => {
      document.dispatchEvent(event);
    });
    
    expect(mockSaveContent).toHaveBeenCalledTimes(1);
  });

  it('should not call saveContent when not dirty', async () => {
    (useWorkbenchStore as any).mockReturnValue({
      saveContent: mockSaveContent,
      isDirty: false,
      isSaving: false
    });
    
    renderHook(() => useSaveShortcut());
    
    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true
    });
    
    await act(async () => {
      document.dispatchEvent(event);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should not call saveContent when already saving', async () => {
    (useWorkbenchStore as any).mockReturnValue({
      saveContent: mockSaveContent,
      isDirty: true,
      isSaving: true
    });
    
    renderHook(() => useSaveShortcut());
    
    const event = new KeyboardEvent('keydown', {
      key: 's',
      ctrlKey: true,
      bubbles: true
    });
    
    await act(async () => {
      document.dispatchEvent(event);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should not call saveContent on regular S key', async () => {
    renderHook(() => useSaveShortcut());
    
    const event = new KeyboardEvent('keydown', {
      key: 's',
      bubbles: true
    });
    
    await act(async () => {
      document.dispatchEvent(event);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should not call saveContent on Ctrl+other key', async () => {
    renderHook(() => useSaveShortcut());
    
    const event = new KeyboardEvent('keydown', {
      key: 'a',
      ctrlKey: true,
      bubbles: true
    });
    
    await act(async () => {
      document.dispatchEvent(event);
    });
    
    expect(mockSaveContent).not.toHaveBeenCalled();
  });

  it('should return handleSave function', () => {
    const { result } = renderHook(() => useSaveShortcut());
    
    expect(result.current.handleSave).toBeDefined();
    expect(typeof result.current.handleSave).toBe('function');
  });

  it('should cleanup event listener on unmount', () => {
    const removeEventListenerSpy = vi.spyOn(document, 'removeEventListener');
    
    const { unmount } = renderHook(() => useSaveShortcut());
    unmount();
    
    expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
  });
});
