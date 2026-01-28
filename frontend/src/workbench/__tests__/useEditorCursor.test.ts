import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock workbenchStore
vi.mock('../stores/workbenchStore', () => ({
  useWorkbenchStore: vi.fn(() => ({
    anchors: [
      { blockId: '001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: '002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 },
      { blockId: '003', coords: { x: 0, y: 200, width: 100, height: 50 }, position: 200 }
    ],
    setActiveBlockId: vi.fn()
  }))
}));

describe('useEditorCursor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('反向定位准确性（Editor -> PDF）', () => {
    it('应该正确解析光标位置对应的 Block ID', () => {
      const anchors = [
        { blockId: '001', position: 0 },
        { blockId: '002', position: 100 },
        { blockId: '003', position: 200 }
      ];

      // 模拟 getBlockIdAtPosition 逻辑
      const getBlockIdAtPosition = (position: number) => {
        let nearestAnchor = null;
        for (const anchor of anchors) {
          if (anchor.position <= position) {
            nearestAnchor = anchor;
          } else {
            break;
          }
        }
        return nearestAnchor?.blockId ?? null;
      };

      // 测试各种光标位置
      expect(getBlockIdAtPosition(0)).toBe('001');
      expect(getBlockIdAtPosition(50)).toBe('001');
      expect(getBlockIdAtPosition(99)).toBe('001');
      expect(getBlockIdAtPosition(100)).toBe('002');
      expect(getBlockIdAtPosition(150)).toBe('002');
      expect(getBlockIdAtPosition(199)).toBe('002');
      expect(getBlockIdAtPosition(200)).toBe('003');
      expect(getBlockIdAtPosition(500)).toBe('003');
    });

    it('应该处理光标在第一个锚点之前的情况', () => {
      const anchors = [
        { blockId: '001', position: 50 },
        { blockId: '002', position: 100 }
      ];

      const getBlockIdAtPosition = (position: number) => {
        let nearestAnchor = null;
        for (const anchor of anchors) {
          if (anchor.position <= position) {
            nearestAnchor = anchor;
          } else {
            break;
          }
        }
        return nearestAnchor?.blockId ?? null;
      };

      // 光标在第一个锚点之前，应该返回 null
      expect(getBlockIdAtPosition(0)).toBeNull();
      expect(getBlockIdAtPosition(49)).toBeNull();
      expect(getBlockIdAtPosition(50)).toBe('001');
    });

    it('应该正确处理防抖逻辑', async () => {
      vi.useFakeTimers();
      
      let lastBlockId: string | null = null;
      const debounceDelay = 100;
      let debounceTimer: number | null = null;

      const updateBlockId = (blockId: string | null) => {
        if (debounceTimer) {
          clearTimeout(debounceTimer);
        }
        debounceTimer = window.setTimeout(() => {
          lastBlockId = blockId;
        }, debounceDelay);
      };

      // 快速连续更新
      updateBlockId('001');
      updateBlockId('002');
      updateBlockId('003');

      // 在防抖时间内，lastBlockId 应该还是 null
      expect(lastBlockId).toBeNull();

      // 等待防抖时间
      vi.advanceTimersByTime(100);

      // 只有最后一次更新生效
      expect(lastBlockId).toBe('003');

      vi.useRealTimers();
    });
  });

  describe('PDF 滚动计算', () => {
    it('应该正确计算滚动目标位置', () => {
      const layoutBlocks = [
        { id: '001', bbox: { x: 50, y: 100, width: 200, height: 80 } },
        { id: '002', bbox: { x: 50, y: 300, width: 200, height: 150 } }
      ];

      const containerWidth = 800;
      const containerHeight = 600;
      const zoomLevel = 100;

      const calculateScrollTarget = (blockId: string) => {
        const block = layoutBlocks.find(b => b.id === blockId);
        if (!block) return null;

        const scale = zoomLevel / 100;
        const targetX = block.bbox.x * scale;
        const targetY = block.bbox.y * scale;

        return {
          scrollLeft: targetX - containerWidth / 2 + (block.bbox.width * scale) / 2,
          scrollTop: targetY - containerHeight / 2 + (block.bbox.height * scale) / 2
        };
      };

      const target1 = calculateScrollTarget('001');
      expect(target1).not.toBeNull();
      // Block 001: x=50, y=100, width=200, height=80
      // scrollLeft = 50 - 400 + 100 = -250
      // scrollTop = 100 - 300 + 40 = -160
      expect(target1?.scrollLeft).toBe(-250);
      expect(target1?.scrollTop).toBe(-160);

      const target2 = calculateScrollTarget('002');
      expect(target2).not.toBeNull();
      // Block 002: x=50, y=300, width=200, height=150
      // scrollLeft = 50 - 400 + 100 = -250
      // scrollTop = 300 - 300 + 75 = 75
      expect(target2?.scrollLeft).toBe(-250);
      expect(target2?.scrollTop).toBe(75);
    });

    it('应该正确处理缩放后的滚动位置', () => {
      const block = { id: '001', bbox: { x: 100, y: 200, width: 300, height: 100 } };
      const containerWidth = 800;
      const containerHeight = 600;

      const calculateScrollTargetWithZoom = (zoomLevel: number) => {
        const scale = zoomLevel / 100;
        const targetX = block.bbox.x * scale;
        const targetY = block.bbox.y * scale;

        return {
          scrollLeft: targetX - containerWidth / 2 + (block.bbox.width * scale) / 2,
          scrollTop: targetY - containerHeight / 2 + (block.bbox.height * scale) / 2
        };
      };

      // 100% 缩放
      const target100 = calculateScrollTargetWithZoom(100);
      expect(target100.scrollLeft).toBe(100 - 400 + 150); // -150
      expect(target100.scrollTop).toBe(200 - 300 + 50);   // -50

      // 150% 缩放
      const target150 = calculateScrollTargetWithZoom(150);
      expect(target150.scrollLeft).toBe(150 - 400 + 225); // -25
      expect(target150.scrollTop).toBe(300 - 300 + 75);   // 75

      // 50% 缩放
      const target50 = calculateScrollTargetWithZoom(50);
      expect(target50.scrollLeft).toBe(50 - 400 + 75);    // -275
      expect(target50.scrollTop).toBe(100 - 300 + 25);    // -175
    });
  });

  describe('边界情况', () => {
    it('应该处理空锚点数组', () => {
      const getBlockIdAtPosition = (anchors: any[], position: number) => {
        if (!anchors || anchors.length === 0) return null;
        let nearestAnchor = null;
        for (const anchor of anchors) {
          if (anchor.position <= position) {
            nearestAnchor = anchor;
          } else {
            break;
          }
        }
        return nearestAnchor?.blockId ?? null;
      };

      expect(getBlockIdAtPosition([], 100)).toBeNull();
      expect(getBlockIdAtPosition(null as any, 100)).toBeNull();
    });

    it('应该处理无效的 Block ID', () => {
      const layoutBlocks = [
        { id: '001', bbox: { x: 0, y: 0, width: 100, height: 50 } }
      ];

      const findBlock = (blockId: string) => {
        return layoutBlocks.find(b => b.id === blockId) ?? null;
      };

      expect(findBlock('001')).not.toBeNull();
      expect(findBlock('invalid')).toBeNull();
      expect(findBlock('')).toBeNull();
    });
  });
});
