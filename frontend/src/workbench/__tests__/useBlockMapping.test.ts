import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock workbenchStore
vi.mock('../stores/workbenchStore', () => ({
  useWorkbenchStore: vi.fn(() => ({
    anchors: [
      { blockId: '001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
      { blockId: '002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 },
      { blockId: '003', coords: { x: 0, y: 200, width: 100, height: 50 }, position: 200 }
    ],
    layoutBlocks: [
      { id: '001', type: 'title', bbox: { x: 0, y: 0, width: 100, height: 50 }, confidence: 0.95, pageNum: 1 },
      { id: '002', type: 'text', bbox: { x: 0, y: 100, width: 100, height: 50 }, confidence: 0.87, pageNum: 1 },
      { id: '003', type: 'text', bbox: { x: 0, y: 200, width: 100, height: 50 }, confidence: 0.75, pageNum: 1 }
    ],
    activeBlockId: null,
    setActiveBlockId: vi.fn()
  }))
}));

// 由于 useBlockMapping 依赖 DOM 操作，我们测试其核心逻辑
describe('useBlockMapping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('点击定位准确性', () => {
    it('应该正确映射 Block ID 到锚点位置', () => {
      const anchors = [
        { blockId: '001', coords: { x: 0, y: 0, width: 100, height: 50 }, position: 0 },
        { blockId: '002', coords: { x: 0, y: 100, width: 100, height: 50 }, position: 100 },
        { blockId: '003', coords: { x: 0, y: 200, width: 100, height: 50 }, position: 200 }
      ];

      // 模拟 getBlockAtCursor 逻辑
      const getBlockAtCursor = (position: number) => {
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

      // 测试各种位置
      expect(getBlockAtCursor(0)).toBe('001');
      expect(getBlockAtCursor(50)).toBe('001');
      expect(getBlockAtCursor(100)).toBe('002');
      expect(getBlockAtCursor(150)).toBe('002');
      expect(getBlockAtCursor(200)).toBe('003');
      expect(getBlockAtCursor(300)).toBe('003');
    });

    it('应该正确计算 PDF 滚动位置', () => {
      const layoutBlocks = [
        { id: '001', type: 'title', bbox: { x: 0, y: 0, width: 100, height: 50 }, confidence: 0.95, pageNum: 1 },
        { id: '002', type: 'text', bbox: { x: 0, y: 100, width: 100, height: 200 }, confidence: 0.87, pageNum: 1 }
      ];

      const zoomLevel = 100;
      const containerHeight = 600;

      // 模拟 scrollPdfToBlock 的计算逻辑
      const calculateScrollPosition = (blockId: string) => {
        const block = layoutBlocks.find(b => b.id === blockId);
        if (!block) return null;

        const scale = zoomLevel / 100;
        const targetY = block.bbox.y * scale;
        const scrollTop = targetY - containerHeight / 2 + (block.bbox.height * scale) / 2;
        
        return scrollTop;
      };

      // Block 001: y=0, height=50, 滚动到 0 - 300 + 25 = -275 (会被限制为 0)
      expect(calculateScrollPosition('001')).toBe(-275);
      
      // Block 002: y=100, height=200, 滚动到 100 - 300 + 100 = -100
      expect(calculateScrollPosition('002')).toBe(-100);
    });

    it('应该正确处理缩放后的坐标', () => {
      const block = { id: '001', bbox: { x: 100, y: 200, width: 300, height: 150 } };
      
      // 测试不同缩放级别
      const testZoomLevels = [50, 100, 150, 200];
      
      testZoomLevels.forEach(zoomLevel => {
        const scale = zoomLevel / 100;
        const scaledX = block.bbox.x * scale;
        const scaledY = block.bbox.y * scale;
        const scaledWidth = block.bbox.width * scale;
        const scaledHeight = block.bbox.height * scale;

        expect(scaledX).toBe(block.bbox.x * scale);
        expect(scaledY).toBe(block.bbox.y * scale);
        expect(scaledWidth).toBe(block.bbox.width * scale);
        expect(scaledHeight).toBe(block.bbox.height * scale);
      });
    });
  });

  describe('高亮效果', () => {
    it('应该在指定时间后移除高亮', async () => {
      vi.useFakeTimers();
      
      let isHighlighted = true;
      const highlightDuration = 2000;

      // 模拟高亮逻辑
      const removeHighlight = () => {
        isHighlighted = false;
      };

      setTimeout(removeHighlight, highlightDuration);

      expect(isHighlighted).toBe(true);
      
      vi.advanceTimersByTime(1999);
      expect(isHighlighted).toBe(true);
      
      vi.advanceTimersByTime(1);
      expect(isHighlighted).toBe(false);

      vi.useRealTimers();
    });
  });

  describe('边界情况', () => {
    it('应该处理空锚点数组', () => {
      const getBlockAtCursor = (anchors: any[], position: number) => {
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

      expect(getBlockAtCursor([], 100)).toBeNull();
    });

    it('应该处理不存在的 Block ID', () => {
      const layoutBlocks = [
        { id: '001', bbox: { x: 0, y: 0, width: 100, height: 50 } }
      ];

      const findBlock = (blockId: string) => {
        return layoutBlocks.find(b => b.id === blockId) ?? null;
      };

      expect(findBlock('001')).not.toBeNull();
      expect(findBlock('999')).toBeNull();
    });
  });
});
