/**
 * 端到端集成测试 - 完整工作流
 * 任务 19.1: 测试完整工作流：加载 -> 编辑 -> 保存
 * 
 * **Validates: Requirements 1.1, 1.2, 1.3**
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
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

describe('E2E: 完整工作流集成测试', () => {
  const mockJobId = 'test-job-123';
  
  const mockLayoutResponse = {
    success: true,
    data: {
      blocks: [
        {
          id: 'block_001',
          type: 'title',
          bbox: { x: 100, y: 50, width: 400, height: 30 },
          confidence: 0.95,
          pageNum: 1,
        },
        {
          id: 'block_002',
          type: 'text',
          bbox: { x: 100, y: 100, width: 400, height: 200 },
          confidence: 0.87,
          pageNum: 1,
        },
      ],
      imageWidth: 612,
      imageHeight: 792,
    },
  };

  const mockMarkdownResponse = {
    success: true,
    data: {
      markdown: `<div id="block_001" data-coords="100,50,400,30" style="display:none;"></div>
# 测试文档标题

<div id="block_002" data-coords="100,100,400,200" style="display:none;"></div>
这是测试正文内容，用于验证完整工作流。`,
      anchors: [
        { blockId: 'block_001', position: 0 },
        { blockId: 'block_002', position: 85 },
      ],
    },
  };

  const mockSaveResponse = {
    success: true,
    data: {
      savedAt: '2026-01-28T10:30:00Z',
      vectorUpdated: false,
    },
  };

  beforeEach(() => {
    // 重置 store
    useWorkbenchStore.getState().reset();
    
    // 设置默认 mock 返回值
    vi.mocked(api.getLayoutWithAnchors).mockResolvedValue(mockLayoutResponse);
    vi.mocked(api.getMarkdownWithAnchors).mockResolvedValue(mockMarkdownResponse);
    vi.mocked(api.saveMarkdown).mockResolvedValue(mockSaveResponse);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('阶段 1: 数据加载', () => {
    it('应该成功加载布局数据和 Markdown 内容', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      // 执行加载
      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      // 验证布局数据
      expect(result.current.layoutBlocks).toHaveLength(2);
      expect(result.current.layoutBlocks[0].id).toBe('block_001');
      expect(result.current.layoutBlocks[0].type).toBe('title');
      expect(result.current.layoutBlocks[1].id).toBe('block_002');
      expect(result.current.layoutBlocks[1].type).toBe('text');

      // 验证图像尺寸
      expect(result.current.imageWidth).toBe(612);
      expect(result.current.imageHeight).toBe(792);

      // 验证 Markdown 内容
      expect(result.current.markdownContent).toContain('# 测试文档标题');
      expect(result.current.markdownContent).toContain('测试正文内容');

      // 验证锚点
      expect(result.current.anchors).toHaveLength(2);

      // 验证状态
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.isDirty).toBe(false);
    });

    it('应该在加载失败时显示错误', async () => {
      vi.mocked(api.getLayoutWithAnchors).mockRejectedValue(new Error('网络错误'));

      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe('网络错误');
    });

    it('应该并行加载布局和 Markdown 数据', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      // 验证两个 API 都被调用
      expect(api.getLayoutWithAnchors).toHaveBeenCalledWith(mockJobId);
      expect(api.getMarkdownWithAnchors).toHaveBeenCalledWith(mockJobId);
    });
  });

  describe('阶段 2: 内容编辑', () => {
    it('应该在编辑后标记为 dirty', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      // 先加载数据
      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      expect(result.current.isDirty).toBe(false);

      // 编辑内容
      act(() => {
        result.current.setMarkdownContent('# 修改后的标题\n\n新的内容');
      });

      expect(result.current.isDirty).toBe(true);
    });

    it('应该在恢复原始内容后取消 dirty 标记', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        await result.current.loadData(mockJobId);
      });

      const originalContent = result.current.markdownContent;

      // 编辑内容
      act(() => {
        result.current.setMarkdownContent('修改后的内容');
      });
      expect(result.current.isDirty).toBe(true);

      // 恢复原始内容
      act(() => {
        result.current.setMarkdownContent(originalContent);
      });
      expect(result.current.isDirty).toBe(false);
    });
  });

  describe('阶段 3: 内容保存', () => {
    it('应该成功保存修改后的内容', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      // 加载数据
      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      // 编辑内容
      const newContent = '# 修改后的标题\n\n新的内容';
      act(() => {
        result.current.setMarkdownContent(newContent);
      });

      // 保存
      await act(async () => {
        await result.current.saveContent();
      });

      // 验证保存 API 被调用
      expect(api.saveMarkdown).toHaveBeenCalledWith(mockJobId, newContent);

      // 验证状态更新
      expect(result.current.isDirty).toBe(false);
      expect(result.current.isSaving).toBe(false);
      expect(result.current.lastSavedAt).toBeInstanceOf(Date);
      expect(result.current.saveError).toBeNull();
    });

    it('应该在保存失败时显示错误', async () => {
      vi.mocked(api.saveMarkdown).mockRejectedValue(new Error('保存失败'));

      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      act(() => {
        result.current.setMarkdownContent('修改后的内容');
      });

      await act(async () => {
        await result.current.saveContent();
      });

      expect(result.current.saveError).toBe('保存失败');
      expect(result.current.isDirty).toBe(true); // 保存失败，仍然是 dirty
    });

    it('应该在没有修改时跳过保存', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      // 不修改内容，直接保存
      await act(async () => {
        await result.current.saveContent();
      });

      // 验证保存 API 没有被调用
      expect(api.saveMarkdown).not.toHaveBeenCalled();
    });
  });

  describe('完整工作流: 加载 -> 编辑 -> 保存', () => {
    it('应该完成完整的编辑工作流', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      // 步骤 1: 设置 jobId 并加载数据
      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      expect(result.current.jobId).toBe(mockJobId);
      expect(result.current.layoutBlocks.length).toBeGreaterThan(0);
      expect(result.current.markdownContent).toBeTruthy();
      expect(result.current.isDirty).toBe(false);

      // 步骤 2: 选择一个 Block
      act(() => {
        result.current.setActiveBlockId('block_001');
      });
      expect(result.current.activeBlockId).toBe('block_001');

      // 步骤 3: 编辑内容
      const editedContent = '# 编辑后的标题\n\n这是编辑后的内容';
      act(() => {
        result.current.setMarkdownContent(editedContent);
      });
      expect(result.current.isDirty).toBe(true);

      // 步骤 4: 保存内容
      await act(async () => {
        await result.current.saveContent();
      });

      expect(result.current.isDirty).toBe(false);
      expect(result.current.lastSavedAt).not.toBeNull();
      expect(api.saveMarkdown).toHaveBeenCalledWith(mockJobId, editedContent);
    });

    it('应该支持多次编辑和保存', async () => {
      const { result } = renderHook(() => useWorkbenchStore());

      // 加载
      await act(async () => {
        result.current.setJobId(mockJobId);
        await result.current.loadData(mockJobId);
      });

      // 第一次编辑和保存
      act(() => {
        result.current.setMarkdownContent('第一次修改');
      });
      await act(async () => {
        await result.current.saveContent();
      });
      expect(api.saveMarkdown).toHaveBeenCalledTimes(1);

      // 第二次编辑和保存
      act(() => {
        result.current.setMarkdownContent('第二次修改');
      });
      await act(async () => {
        await result.current.saveContent();
      });
      expect(api.saveMarkdown).toHaveBeenCalledTimes(2);

      // 第三次编辑和保存
      act(() => {
        result.current.setMarkdownContent('第三次修改');
      });
      await act(async () => {
        await result.current.saveContent();
      });
      expect(api.saveMarkdown).toHaveBeenCalledTimes(3);
    });
  });
});
