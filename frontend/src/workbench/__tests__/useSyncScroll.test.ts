import { describe, it, expect, vi, beforeEach } from 'vitest';
import { findNearestAnchor } from '../hooks/useSyncScroll';
import { AnchorInfo } from '../stores/types';

// Mock workbenchStore
vi.mock('../stores/workbenchStore', () => ({
  useWorkbenchStore: vi.fn(() => ({
    syncScrollEnabled: true,
    toggleSyncScroll: vi.fn(),
    imageHeight: 1000,
    zoomLevel: 100
  }))
}));

describe('useSyncScroll', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('滚动比例计算', () => {
    it('应该正确计算滚动比例', () => {
      const getScrollRatio = (scrollTop: number, scrollHeight: number, clientHeight: number): number => {
        const maxScroll = scrollHeight - clientHeight;
        if (maxScroll <= 0) return 0;
        return scrollTop / maxScroll;
      };

      // 测试各种滚动位置
      expect(getScrollRatio(0, 1000, 500)).toBe(0);
      expect(getScrollRatio(250, 1000, 500)).toBe(0.5);
      expect(getScrollRatio(500, 1000, 500)).toBe(1);
    });

    it('应该处理无法滚动的情况', () => {
      const getScrollRatio = (scrollTop: number, scrollHeight: number, clientHeight: number): number => {
        const maxScroll = scrollHeight - clientHeight;
        if (maxScroll <= 0) return 0;
        return scrollTop / maxScroll;
      };

      // 内容高度小于等于容器高度
      expect(getScrollRatio(0, 500, 500)).toBe(0);
      expect(getScrollRatio(0, 400, 500)).toBe(0);
    });
  });

  describe('滚动位置设置', () => {
    it('应该正确设置滚动位置', () => {
      const setScrollByRatio = (ratio: number, scrollHeight: number, clientHeight: number): number => {
        const maxScroll = scrollHeight - clientHeight;
        return ratio * maxScroll;
      };

      // 测试各种比例
      expect(setScrollByRatio(0, 1000, 500)).toBe(0);
      expect(setScrollByRatio(0.5, 1000, 500)).toBe(250);
      expect(setScrollByRatio(1, 1000, 500)).toBe(500);
    });
  });

  describe('滚动循环防护', () => {
    it('应该防止滚动循环', async () => {
      vi.useFakeTimers();

      let isScrollingFromPdf = false;
      let isScrollingFromEditor = false;
      let pdfScrollCount = 0;
      let editorScrollCount = 0;

      const handlePdfScroll = () => {
        if (isScrollingFromEditor) return;
        isScrollingFromPdf = true;
        pdfScrollCount++;
        
        // 模拟同步到编辑器
        setTimeout(() => {
          isScrollingFromPdf = false;
        }, 60);
      };

      const handleEditorScroll = () => {
        if (isScrollingFromPdf) return;
        isScrollingFromEditor = true;
        editorScrollCount++;
        
        // 模拟同步到 PDF
        setTimeout(() => {
          isScrollingFromEditor = false;
        }, 60);
      };

      // 模拟 PDF 滚动
      handlePdfScroll();
      expect(pdfScrollCount).toBe(1);

      // 在同步期间，编辑器滚动应该被忽略
      handleEditorScroll();
      expect(editorScrollCount).toBe(0);

      // 等待同步完成
      vi.advanceTimersByTime(100);

      // 现在编辑器滚动应该可以触发
      handleEditorScroll();
      expect(editorScrollCount).toBe(1);

      vi.useRealTimers();
    });

    it('应该正确处理快速连续滚动', async () => {
      vi.useFakeTimers();

      let syncCount = 0;
      let debounceTimer: number | null = null;
      const debounceDelay = 50;

      const handleScroll = () => {
        if (debounceTimer) {
          clearTimeout(debounceTimer);
        }
        debounceTimer = window.setTimeout(() => {
          syncCount++;
        }, debounceDelay);
      };

      // 快速连续滚动
      handleScroll();
      handleScroll();
      handleScroll();
      handleScroll();
      handleScroll();

      // 在防抖时间内，同步不应该发生
      expect(syncCount).toBe(0);

      // 等待防抖时间
      vi.advanceTimersByTime(50);

      // 只应该同步一次
      expect(syncCount).toBe(1);

      vi.useRealTimers();
    });
  });

  describe('同步开关', () => {
    it('应该在禁用时不触发同步', () => {
      let syncEnabled = false;
      let syncTriggered = false;

      const handleScroll = () => {
        if (!syncEnabled) return;
        syncTriggered = true;
      };

      handleScroll();
      expect(syncTriggered).toBe(false);

      syncEnabled = true;
      handleScroll();
      expect(syncTriggered).toBe(true);
    });
  });

  describe('边界情况', () => {
    it('应该处理容器不存在的情况', () => {
      const syncScroll = (pdfContainer: HTMLElement | null, editorContainer: HTMLElement | null) => {
        if (!pdfContainer || !editorContainer) return false;
        return true;
      };

      expect(syncScroll(null, null)).toBe(false);
      expect(syncScroll(null, document.createElement('div'))).toBe(false);
      expect(syncScroll(document.createElement('div'), null)).toBe(false);
    });

    it('应该处理零高度容器', () => {
      const getScrollRatio = (scrollTop: number, scrollHeight: number, clientHeight: number): number => {
        const maxScroll = scrollHeight - clientHeight;
        if (maxScroll <= 0) return 0;
        return scrollTop / maxScroll;
      };

      expect(getScrollRatio(0, 0, 0)).toBe(0);
      expect(getScrollRatio(100, 0, 0)).toBe(0);
    });
  });
});


describe('findNearestAnchor', () => {
  const createAnchor = (blockId: string, position: number): AnchorInfo => ({
    blockId,
    coords: { x: 0, y: 0, width: 100, height: 50 },
    position
  });

  it('应该返回 null 当锚点列表为空', () => {
    expect(findNearestAnchor([], 100)).toBeNull();
  });

  it('应该返回 null 当光标在所有锚点之前', () => {
    const anchors = [
      createAnchor('block_001', 100),
      createAnchor('block_002', 200),
    ];
    expect(findNearestAnchor(anchors, 50)).toBeNull();
  });

  it('应该返回第一个锚点当光标正好在第一个锚点位置', () => {
    const anchors = [
      createAnchor('block_001', 100),
      createAnchor('block_002', 200),
    ];
    const result = findNearestAnchor(anchors, 100);
    expect(result?.blockId).toBe('block_001');
  });

  it('应该返回最近的锚点当光标在两个锚点之间', () => {
    const anchors = [
      createAnchor('block_001', 100),
      createAnchor('block_002', 200),
      createAnchor('block_003', 300),
    ];
    const result = findNearestAnchor(anchors, 250);
    expect(result?.blockId).toBe('block_002');
  });

  it('应该返回最后一个锚点当光标在所有锚点之后', () => {
    const anchors = [
      createAnchor('block_001', 100),
      createAnchor('block_002', 200),
    ];
    const result = findNearestAnchor(anchors, 500);
    expect(result?.blockId).toBe('block_002');
  });

  it('应该正确处理单个锚点', () => {
    const anchors = [createAnchor('block_001', 100)];
    
    // 光标在锚点之前
    expect(findNearestAnchor(anchors, 50)).toBeNull();
    
    // 光标在锚点位置
    expect(findNearestAnchor(anchors, 100)?.blockId).toBe('block_001');
    
    // 光标在锚点之后
    expect(findNearestAnchor(anchors, 200)?.blockId).toBe('block_001');
  });

  it('应该处理 null 或 undefined 输入', () => {
    expect(findNearestAnchor(null as unknown as AnchorInfo[], 100)).toBeNull();
    expect(findNearestAnchor(undefined as unknown as AnchorInfo[], 100)).toBeNull();
  });

  it('应该返回位置小于等于光标位置的最后一个锚点', () => {
    const anchors = [
      createAnchor('block_001', 0),
      createAnchor('block_002', 100),
      createAnchor('block_003', 100), // 相同位置
      createAnchor('block_004', 200),
    ];
    
    // 当有多个相同位置的锚点时，返回最后一个
    const result = findNearestAnchor(anchors, 100);
    expect(result?.blockId).toBe('block_003');
  });
});
