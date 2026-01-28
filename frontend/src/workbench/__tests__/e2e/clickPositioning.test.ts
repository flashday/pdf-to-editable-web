/**
 * 端到端集成测试 - 点击定位准确性
 * 任务 19.3: 测试点击定位准确性
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3**
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { parseAnchors, getBlockIdAtPosition } from '../../utils/anchorParser';
import { api } from '../../services/api';

// Mock API
vi.mock('../../services/api', () => ({
  api: {
    getLayoutWithAnchors: vi.fn(),
    getMarkdownWithAnchors: vi.fn(),
    saveMarkdown: vi.fn(),
    getImageUrl: vi.fn((jobId: string) => `/temp/${jobId}_page1.png`),
  },
}));

describe('E2E: 点击定位准确性测试', () => {
  const mockJobId = 'test-job-positioning';

  // 模拟多个 Block 的布局数据
  const mockBlocks = [
    {
      id: 'block_001',
      type: 'title',
      bbox: { x: 50, y: 50, width: 500, height: 40 },
      confidence: 0.95,
      pageNum: 1,
    },
    {
      id: 'block_002',
      type: 'text',
      bbox: { x: 50, y: 100, width: 500, height: 150 },
      confidence: 0.88,
      pageNum: 1,
    },
    {
      id: 'block_003',
      type: 'table',
      bbox: { x: 50, y: 260, width: 500, height: 200 },
      confidence: 0.75,
      pageNum: 1,
    },
    {
      id: 'block_004',
      type: 'text',
      bbox: { x: 50, y: 470, width: 500, height: 100 },
      confidence: 0.92,
      pageNum: 1,
    },
    {
      id: 'block_005',
      type: 'figure',
      bbox: { x: 50, y: 580, width: 300, height: 200 },
      confidence: 0.85,
      pageNum: 1,
    },
  ];

  // 模拟带锚点的 Markdown（使用 V2 新格式）
  const mockMarkdown = `<!-- @block:block_001 50,50,500,40 -->
# 文档标题

<!-- @block:block_002 50,100,500,150 -->
这是第一段正文内容，包含一些测试文本。

<!-- @block:block_003 50,260,500,200 -->
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| A1  | B1  | C1  |
| A2  | B2  | C2  |

<!-- @block:block_004 50,470,500,100 -->
这是第二段正文内容。

<!-- @block:block_005 50,580,300,200 -->
![图片描述](image.png)`;

  beforeEach(() => {
    useWorkbenchStore.getState().reset();
    
    vi.mocked(api.getLayoutWithAnchors).mockResolvedValue({
      success: true,
      data: { blocks: mockBlocks, imageWidth: 612, imageHeight: 792 },
    });
    
    vi.mocked(api.getMarkdownWithAnchors).mockResolvedValue({
      success: true,
      data: {
        markdown: mockMarkdown,
        anchors: [
          { blockId: 'block_001', position: 0 },
          { blockId: 'block_002', position: 80 },
          { blockId: 'block_003', position: 180 },
          { blockId: 'block_004', position: 350 },
          { blockId: 'block_005', position: 450 },
        ],
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('PDF -> Editor 点击定位', () => {
    it('应该在点击 Block 后更新 activeBlockId', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      // 模拟点击 block_002
      act(() => {
        result.current.setActiveBlockId('block_002');
      });

      expect(result.current.activeBlockId).toBe('block_002');
    });

    it('应该能够依次点击不同的 Block', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      // 点击第一个 Block
      act(() => {
        result.current.setActiveBlockId('block_001');
      });
      expect(result.current.activeBlockId).toBe('block_001');

      // 点击第三个 Block
      act(() => {
        result.current.setActiveBlockId('block_003');
      });
      expect(result.current.activeBlockId).toBe('block_003');

      // 点击第五个 Block
      act(() => {
        result.current.setActiveBlockId('block_005');
      });
      expect(result.current.activeBlockId).toBe('block_005');
    });

    it('应该能够取消选中', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      act(() => {
        result.current.setActiveBlockId('block_002');
      });
      expect(result.current.activeBlockId).toBe('block_002');

      act(() => {
        result.current.setActiveBlockId(null);
      });
      expect(result.current.activeBlockId).toBeNull();
    });
  });

  describe('Editor -> PDF 点击定位', () => {
    it('应该根据光标位置找到正确的 Block ID', () => {
      const anchors = parseAnchors(mockMarkdown);
      
      // 验证锚点解析正确
      expect(anchors.length).toBe(5);
      
      // 光标在第一个锚点位置（新格式 blockId 包含完整的 block_xxx）
      expect(getBlockIdAtPosition(anchors, anchors[0].position)).toBe('block_001');
      
      // 光标在第一个锚点之后、第二个锚点之前
      const pos1 = Math.floor((anchors[0].position + anchors[1].position) / 2);
      expect(getBlockIdAtPosition(anchors, pos1)).toBe('block_001');
      
      // 光标在第二个锚点之后
      const pos2 = anchors[1].position + 10;
      expect(getBlockIdAtPosition(anchors, pos2)).toBe('block_002');
      
      // 光标在第三个锚点之后
      const pos3 = anchors[2].position + 10;
      expect(getBlockIdAtPosition(anchors, pos3)).toBe('block_003');
      
      // 光标在最后一个锚点之后
      const pos5 = anchors[4].position + 10;
      expect(getBlockIdAtPosition(anchors, pos5)).toBe('block_005');
    });

    it('应该在光标位置变化时更新 activeBlockId', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      const anchors = parseAnchors(mockMarkdown);
      
      // 模拟光标移动到每个锚点位置之后（新格式 blockId 包含完整的 block_xxx）
      const expectedBlockIds = ['block_001', 'block_002', 'block_003', 'block_004', 'block_005'];

      anchors.forEach((anchor, index) => {
        const blockId = getBlockIdAtPosition(anchors, anchor.position + 5);
        act(() => {
          result.current.setActiveBlockId(blockId);
        });
        expect(result.current.activeBlockId).toBe(expectedBlockIds[index]);
      });
    });
  });

  describe('锚点解析准确性', () => {
    it('应该正确解析所有锚点', () => {
      const anchors = parseAnchors(mockMarkdown);
      
      expect(anchors).toHaveLength(5);
      // 新格式 blockId 包含完整的 block_xxx
      expect(anchors.map(a => a.blockId)).toEqual([
        'block_001', 'block_002', 'block_003', 'block_004', 'block_005'
      ]);
    });

    it('应该正确解析锚点坐标', () => {
      const anchors = parseAnchors(mockMarkdown);
      
      expect(anchors[0].coords).toEqual({ x: 50, y: 50, width: 500, height: 40 });
      expect(anchors[2].coords).toEqual({ x: 50, y: 260, width: 500, height: 200 });
    });

    it('应该正确记录锚点位置', () => {
      const anchors = parseAnchors(mockMarkdown);
      
      // 验证位置是递增的
      for (let i = 1; i < anchors.length; i++) {
        expect(anchors[i].position).toBeGreaterThan(anchors[i - 1].position);
      }
    });
  });

  describe('Block 坐标与锚点坐标一致性', () => {
    it('应该验证 Block 坐标与锚点坐标匹配', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      const anchors = parseAnchors(mockMarkdown);
      const blocks = result.current.layoutBlocks;

      // 验证每个 Block 的坐标与对应锚点的坐标一致
      blocks.forEach(block => {
        const anchor = anchors.find(a => a.blockId === block.id);
        if (anchor) {
          expect(block.bbox.x).toBe(anchor.coords.x);
          expect(block.bbox.y).toBe(anchor.coords.y);
          expect(block.bbox.width).toBe(anchor.coords.width);
          expect(block.bbox.height).toBe(anchor.coords.height);
        }
      });
    });
  });

  describe('悬停状态', () => {
    it('应该正确设置和清除悬停状态', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      // 设置悬停
      act(() => {
        result.current.setHoveredBlockId('block_002');
      });
      expect(result.current.hoveredBlockId).toBe('block_002');

      // 移动到另一个 Block
      act(() => {
        result.current.setHoveredBlockId('block_003');
      });
      expect(result.current.hoveredBlockId).toBe('block_003');

      // 清除悬停
      act(() => {
        result.current.setHoveredBlockId(null);
      });
      expect(result.current.hoveredBlockId).toBeNull();
    });

    it('悬停状态应该独立于选中状态', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      // 选中一个 Block
      act(() => {
        result.current.setActiveBlockId('block_001');
      });

      // 悬停另一个 Block
      act(() => {
        result.current.setHoveredBlockId('block_002');
      });

      // 两个状态应该独立
      expect(result.current.activeBlockId).toBe('block_001');
      expect(result.current.hoveredBlockId).toBe('block_002');
    });
  });

  describe('边界情况', () => {
    it('应该处理空锚点列表', () => {
      const anchors: any[] = [];
      expect(getBlockIdAtPosition(anchors, 100)).toBeNull();
    });

    it('应该处理光标在第一个锚点之前的情况', () => {
      // 创建一个有前置内容的 markdown
      const markdownWithPrefix = `一些前置内容

<!-- @block:block_001 50,50,500,40 -->
# 文档标题`;
      const anchors = parseAnchors(markdownWithPrefix);
      
      // 第一个锚点位置不是 0，所以位置 0 应该返回 null
      if (anchors.length > 0 && anchors[0].position > 0) {
        expect(getBlockIdAtPosition(anchors, 0)).toBeNull();
      }
    });

    it('应该处理光标在最后一个锚点之后的情况', () => {
      const anchors = parseAnchors(mockMarkdown);
      // 光标在文档末尾
      expect(getBlockIdAtPosition(anchors, 10000)).toBe('block_005');
    });
  });
});
