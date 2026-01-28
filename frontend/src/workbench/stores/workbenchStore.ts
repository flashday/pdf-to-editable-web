import { create } from 'zustand';
import { LayoutBlock, AnchorInfo } from './types';
import { api } from '../services/api';

interface WorkbenchState {
  // 数据
  jobId: string | null;
  layoutBlocks: LayoutBlock[];
  markdownContent: string;
  originalMarkdown: string;
  anchors: AnchorInfo[];
  imageWidth: number;
  imageHeight: number;
  
  // UI 状态
  activeBlockId: string | null;
  hoveredBlockId: string | null;
  zoomLevel: number;
  syncScrollEnabled: boolean;
  isLoading: boolean;
  error: string | null;
  
  // 保存状态
  isDirty: boolean;
  isSaving: boolean;
  lastSavedAt: Date | null;
  saveError: string | null;
  
  // Actions
  setJobId: (jobId: string) => void;
  setLayoutBlocks: (blocks: LayoutBlock[]) => void;
  setMarkdownContent: (content: string) => void;
  setActiveBlockId: (id: string | null) => void;
  setHoveredBlockId: (id: string | null) => void;
  setZoomLevel: (level: number) => void;
  toggleSyncScroll: () => void;
  loadData: (jobId: string) => Promise<void>;
  saveContent: () => Promise<void>;
  reset: () => void;
}

const initialState = {
  jobId: null,
  layoutBlocks: [],
  markdownContent: '',
  originalMarkdown: '',
  anchors: [],
  imageWidth: 0,
  imageHeight: 0,
  activeBlockId: null,
  hoveredBlockId: null,
  zoomLevel: 100,
  syncScrollEnabled: false,
  isLoading: false,
  error: null,
  isDirty: false,
  isSaving: false,
  lastSavedAt: null,
  saveError: null,
};

export const useWorkbenchStore = create<WorkbenchState>((set, get) => ({
  ...initialState,

  setJobId: (jobId: string) => {
    set({ jobId });
  },

  setLayoutBlocks: (blocks: LayoutBlock[]) => {
    set({ layoutBlocks: blocks });
  },

  setMarkdownContent: (content: string) => {
    const { originalMarkdown } = get();
    set({ 
      markdownContent: content,
      isDirty: content !== originalMarkdown
    });
  },

  setActiveBlockId: (id: string | null) => {
    set({ activeBlockId: id });
  },

  setHoveredBlockId: (id: string | null) => {
    set({ hoveredBlockId: id });
  },

  setZoomLevel: (level: number) => {
    // 限制缩放范围 50% - 200%
    const clampedLevel = Math.max(50, Math.min(200, level));
    set({ zoomLevel: clampedLevel });
  },

  toggleSyncScroll: () => {
    set((state) => ({ syncScrollEnabled: !state.syncScrollEnabled }));
  },

  loadData: async (jobId: string) => {
    set({ isLoading: true, error: null });
    
    try {
      // 并行加载布局数据和 Markdown 内容
      const [layoutResult, markdownResult] = await Promise.all([
        api.getLayoutWithAnchors(jobId),
        api.getMarkdownWithAnchors(jobId)
      ]);

      if (!layoutResult.success) {
        throw new Error('加载布局数据失败');
      }

      if (!markdownResult.success) {
        throw new Error('加载 Markdown 内容失败');
      }

      set({
        layoutBlocks: layoutResult.data.blocks,
        imageWidth: layoutResult.data.imageWidth,
        imageHeight: layoutResult.data.imageHeight,
        markdownContent: markdownResult.data.markdown,
        originalMarkdown: markdownResult.data.markdown,
        anchors: markdownResult.data.anchors,
        isLoading: false,
        isDirty: false
      });
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error instanceof Error ? error.message : '加载失败'
      });
    }
  },

  saveContent: async () => {
    const { jobId, markdownContent, isDirty } = get();
    
    if (!jobId || !isDirty) return;

    set({ isSaving: true, saveError: null });

    try {
      const result = await api.saveMarkdown(jobId, markdownContent);
      
      if (!result.success) {
        throw new Error('保存失败');
      }

      set({
        isSaving: false,
        isDirty: false,
        originalMarkdown: markdownContent,
        lastSavedAt: new Date(result.data.savedAt)
      });
    } catch (error) {
      set({
        isSaving: false,
        saveError: error instanceof Error ? error.message : '保存失败'
      });
    }
  },

  reset: () => {
    set(initialState);
  }
}));
