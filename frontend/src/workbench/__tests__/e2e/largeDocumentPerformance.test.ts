/**
 * 端到端集成测试 - 大文档性能测试
 * 任务 19.4: 测试大文档性能（50+ Block）
 * 
 * **Validates: Requirements 4.1, 4.2**
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

// 生成大量 Block 的辅助函数
function generateLargeBlockSet(count: number) {
  const blocks = [];
  const types = ['title', 'text', 'table', 'figure', 'list'];
  
  for (let i = 0; i < count; i++) {
    blocks.push({
      id: `block_${String(i + 1).padStart(3, '0')}`,
      type: types[i % types.length],
      bbox: {
        x: 50,
        y: 50 + i * 100,
        width: 500,
        height: 80,
      },
      confidence: 0.7 + Math.random() * 0.3,
      pageNum: Math.floor(i / 10) + 1,
    });
  }
  
  return blocks;
}

// 生成大量锚点的 Markdown
function generateLargeMarkdown(count: number) {
  let markdown = '';
  
  for (let i = 0; i < count; i++) {
    const blockId = `block_${String(i + 1).padStart(3, '0')}`;
    const y = 50 + i * 100;
    markdown += `<div id="${blockId}" data-coords="50,${y},500,80" style="display:none;"></div>\n`;
    
    if (i % 5 === 0) {
      markdown += `# 标题 ${i + 1}\n\n`;
    } else if (i % 5 === 2) {
      markdown += `| 列1 | 列2 |\n|-----|-----|\n| A | B |\n\n`;
    } else {
      markdown += `这是第 ${i + 1} 段内容。Lorem ipsum dolor sit amet.\n\n`;
    }
  }
  
  return markdown;
}

// 生成锚点数组
function generateAnchors(count: number) {
  const anchors = [];
  let position = 0;
  
  for (let i = 0; i < count; i++) {
    anchors.push({
      blockId: `block_${String(i + 1).padStart(3, '0')}`,
      position: position,
    });
    position += 100 + Math.floor(Math.random() * 50);
  }
  
  return anchors;
}

describe('E2E: 大文档性能测试', () => {
  const mockJobId = 'test-job-large-doc';
  const BLOCK_COUNT = 100; // 测试 100 个 Block

  beforeEach(() => {
    useWorkbenchStore.getState().reset();
    
    const largeBlocks = generateLargeBlockSet(BLOCK_COUNT);
    const largeMarkdown = generateLargeMarkdown(BLOCK_COUNT);
    const largeAnchors = generateAnchors(BLOCK_COUNT);
    
    vi.mocked(api.getLayoutWithAnchors).mockResolvedValue({
      success: true,
      data: { blocks: largeBlocks, imageWidth: 612, imageHeight: BLOCK_COUNT * 100 },
    });
    
    vi.mocked(api.getMarkdownWithAnchors).mockResolvedValue({
      success: true,
      data: { markdown: largeMarkdown, anchors: largeAnchors },
    });
    
    vi.mocked(api.saveMarkdown).mockResolvedValue({
      success: true,
      data: { savedAt: new Date().toISOString(), vectorUpdated: false },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('大文档加载性能', () => {
    it('应该能够加载 100+ Block 的文档', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      const startTime = performance.now();
      
      await act(async () => {
        await result.current.loadData(mockJobId);
      });
      
      const loadTime = performance.now() - startTime;

      expect(result.current.layoutBlocks).toHaveLength(BLOCK_COUNT);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      
      // 加载时间应该在合理范围内（< 1000ms）
      console.log(`加载 ${BLOCK_COUNT} 个 Block 耗时: ${loadTime.toFixed(2)}ms`);
      expect(loadTime).toBeLessThan(1000);
    });

    it('应该正确解析大量锚点', () => {
      const largeMarkdown = generateLargeMarkdown(BLOCK_COUNT);
      
      const startTime = performance.now();
      const anchors = parseAnchors(largeMarkdown);
      const parseTime = performance.now() - startTime;

      expect(anchors).toHaveLength(BLOCK_COUNT);
      
      // 解析时间应该在合理范围内（< 100ms）
      console.log(`解析 ${BLOCK_COUNT} 个锚点耗时: ${parseTime.toFixed(2)}ms`);
      expect(parseTime).toBeLessThan(100);
    });
  });

  describe('大文档交互性能', () => {
    it('应该快速响应 Block 选择', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      // 测试快速连续选择多个 Block
      const startTime = performance.now();
      
      for (let i = 0; i < 50; i++) {
        const blockId = `block_${String(i + 1).padStart(3, '0')}`;
        act(() => {
          result.current.setActiveBlockId(blockId);
        });
      }
      
      const selectTime = performance.now() - startTime;

      console.log(`连续选择 50 个 Block 耗时: ${selectTime.toFixed(2)}ms`);
      expect(selectTime).toBeLessThan(100);
    });

    it('应该快速响应悬停状态变化', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      const startTime = performance.now();
      
      // 模拟快速悬停多个 Block
      for (let i = 0; i < 100; i++) {
        const blockId = `block_${String(i + 1).padStart(3, '0')}`;
        act(() => {
          result.current.setHoveredBlockId(blockId);
        });
      }
      
      const hoverTime = performance.now() - startTime;

      console.log(`连续悬停 100 个 Block 耗时: ${hoverTime.toFixed(2)}ms`);
      expect(hoverTime).toBeLessThan(100);
    });
  });

  describe('大文档定位性能', () => {
    it('应该快速定位到任意 Block', () => {
      const largeMarkdown = generateLargeMarkdown(BLOCK_COUNT);
      const anchors = parseAnchors(largeMarkdown);

      const startTime = performance.now();
      
      // 测试定位到不同位置
      const positions = [100, 5000, 10000, 50000, 100000];
      positions.forEach(pos => {
        getBlockIdAtPosition(anchors, pos);
      });
      
      const locateTime = performance.now() - startTime;

      console.log(`定位 5 个不同位置耗时: ${locateTime.toFixed(2)}ms`);
      expect(locateTime).toBeLessThan(10);
    });

    it('应该正确定位到最后一个 Block', () => {
      const largeMarkdown = generateLargeMarkdown(BLOCK_COUNT);
      const anchors = parseAnchors(largeMarkdown);

      const lastBlockId = getBlockIdAtPosition(anchors, 1000000);
      // blockId 不包含 block_ 前缀
      expect(lastBlockId).toBe(`${String(BLOCK_COUNT).padStart(3, '0')}`);
    });
  });

  describe('大文档保存性能', () => {
    it('应该能够保存大文档', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      // 修改内容
      const largeContent = generateLargeMarkdown(BLOCK_COUNT) + '\n\n# 新增内容';
      act(() => {
        result.current.setMarkdownContent(largeContent);
      });

      const startTime = performance.now();
      
      await act(async () => {
        await result.current.saveContent();
      });
      
      const saveTime = performance.now() - startTime;

      expect(result.current.isDirty).toBe(false);
      expect(result.current.saveError).toBeNull();
      
      console.log(`保存大文档耗时: ${saveTime.toFixed(2)}ms`);
    });
  });

  describe('内存使用', () => {
    it('应该在重置后释放数据', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      expect(result.current.layoutBlocks).toHaveLength(BLOCK_COUNT);

      // 重置 store
      act(() => {
        result.current.reset();
      });

      expect(result.current.layoutBlocks).toHaveLength(0);
      expect(result.current.markdownContent).toBe('');
      expect(result.current.anchors).toHaveLength(0);
    });
  });

  describe('极端情况测试', () => {
    it('应该处理 500 个 Block 的文档', async () => {
      const extremeCount = 500;
      const extremeBlocks = generateLargeBlockSet(extremeCount);
      const extremeMarkdown = generateLargeMarkdown(extremeCount);
      const extremeAnchors = generateAnchors(extremeCount);

      vi.mocked(api.getLayoutWithAnchors).mockResolvedValue({
        success: true,
        data: { blocks: extremeBlocks, imageWidth: 612, imageHeight: extremeCount * 100 },
      });
      
      vi.mocked(api.getMarkdownWithAnchors).mockResolvedValue({
        success: true,
        data: { markdown: extremeMarkdown, anchors: extremeAnchors },
      });

      const { result } = renderHook(() => useWorkbenchStore());

      const startTime = performance.now();
      
      await act(async () => {
        await result.current.loadData(mockJobId);
      });
      
      const loadTime = performance.now() - startTime;

      expect(result.current.layoutBlocks).toHaveLength(extremeCount);
      console.log(`加载 ${extremeCount} 个 Block 耗时: ${loadTime.toFixed(2)}ms`);
      
      // 即使是 500 个 Block，加载时间也应该在 2 秒内
      expect(loadTime).toBeLessThan(2000);
    });

    it('应该处理空文档', async () => {
      vi.mocked(api.getLayoutWithAnchors).mockResolvedValue({
        success: true,
        data: { blocks: [], imageWidth: 612, imageHeight: 792 },
      });
      
      vi.mocked(api.getMarkdownWithAnchors).mockResolvedValue({
        success: true,
        data: { markdown: '', anchors: [] },
      });

      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      expect(result.current.layoutBlocks).toHaveLength(0);
      expect(result.current.markdownContent).toBe('');
      expect(result.current.error).toBeNull();
    });
  });
});
