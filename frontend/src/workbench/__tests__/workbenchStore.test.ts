import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkbenchStore } from '../stores/workbenchStore';

describe('workbenchStore', () => {
  beforeEach(() => {
    // 重置 store 状态
    useWorkbenchStore.getState().reset();
  });

  describe('setJobId', () => {
    it('should set jobId correctly', () => {
      const store = useWorkbenchStore.getState();
      store.setJobId('test-job-123');
      expect(useWorkbenchStore.getState().jobId).toBe('test-job-123');
    });
  });

  describe('setLayoutBlocks', () => {
    it('should set layout blocks correctly', () => {
      const store = useWorkbenchStore.getState();
      const blocks = [
        {
          id: 'block_001',
          type: 'text' as const,
          bbox: { x: 0, y: 0, width: 100, height: 50 },
          confidence: 0.95,
          pageNum: 1
        }
      ];
      store.setLayoutBlocks(blocks);
      expect(useWorkbenchStore.getState().layoutBlocks).toEqual(blocks);
    });
  });

  describe('setMarkdownContent', () => {
    it('should set markdown content and mark as dirty', () => {
      const store = useWorkbenchStore.getState();
      store.setMarkdownContent('# Test Content');
      
      const state = useWorkbenchStore.getState();
      expect(state.markdownContent).toBe('# Test Content');
      expect(state.isDirty).toBe(true);
    });

    it('should not mark as dirty if content matches original', () => {
      // 先设置原始内容
      useWorkbenchStore.setState({ originalMarkdown: '# Original' });
      
      const store = useWorkbenchStore.getState();
      store.setMarkdownContent('# Original');
      
      expect(useWorkbenchStore.getState().isDirty).toBe(false);
    });
  });

  describe('setActiveBlockId', () => {
    it('should set active block id', () => {
      const store = useWorkbenchStore.getState();
      store.setActiveBlockId('block_001');
      expect(useWorkbenchStore.getState().activeBlockId).toBe('block_001');
    });

    it('should allow setting to null', () => {
      const store = useWorkbenchStore.getState();
      store.setActiveBlockId('block_001');
      store.setActiveBlockId(null);
      expect(useWorkbenchStore.getState().activeBlockId).toBeNull();
    });
  });

  describe('setHoveredBlockId', () => {
    it('should set hovered block id', () => {
      const store = useWorkbenchStore.getState();
      store.setHoveredBlockId('block_002');
      expect(useWorkbenchStore.getState().hoveredBlockId).toBe('block_002');
    });
  });

  describe('setZoomLevel', () => {
    it('should set zoom level within bounds', () => {
      const store = useWorkbenchStore.getState();
      store.setZoomLevel(150);
      expect(useWorkbenchStore.getState().zoomLevel).toBe(150);
    });

    it('should clamp zoom level to minimum 50%', () => {
      const store = useWorkbenchStore.getState();
      store.setZoomLevel(30);
      expect(useWorkbenchStore.getState().zoomLevel).toBe(50);
    });

    it('should clamp zoom level to maximum 200%', () => {
      const store = useWorkbenchStore.getState();
      store.setZoomLevel(250);
      expect(useWorkbenchStore.getState().zoomLevel).toBe(200);
    });
  });

  describe('toggleSyncScroll', () => {
    it('should toggle sync scroll state', () => {
      const store = useWorkbenchStore.getState();
      expect(useWorkbenchStore.getState().syncScrollEnabled).toBe(false);
      
      store.toggleSyncScroll();
      expect(useWorkbenchStore.getState().syncScrollEnabled).toBe(true);
      
      store.toggleSyncScroll();
      expect(useWorkbenchStore.getState().syncScrollEnabled).toBe(false);
    });
  });

  describe('reset', () => {
    it('should reset all state to initial values', () => {
      const store = useWorkbenchStore.getState();
      
      // 修改一些状态
      store.setJobId('test-job');
      store.setMarkdownContent('# Test');
      store.setZoomLevel(150);
      store.setActiveBlockId('block_001');
      
      // 重置
      store.reset();
      
      const state = useWorkbenchStore.getState();
      expect(state.jobId).toBeNull();
      expect(state.markdownContent).toBe('');
      expect(state.zoomLevel).toBe(100);
      expect(state.activeBlockId).toBeNull();
      expect(state.isDirty).toBe(false);
    });
  });
});
