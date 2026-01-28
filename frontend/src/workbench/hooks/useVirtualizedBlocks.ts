/**
 * 虚拟渲染 Hook - 仅渲染可视区域内的 Bounding Box
 * 任务 20.1: 实现 Bounding Box 虚拟渲染（仅渲染可视区域）
 */
import { useMemo, useState, useCallback, useEffect } from 'react';
import { LayoutBlock } from '../stores/types';

interface ViewportBounds {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

interface UseVirtualizedBlocksOptions {
  /** 所有 Block 数据 */
  blocks: LayoutBlock[];
  /** 缩放级别 (100 = 100%) */
  zoomLevel: number;
  /** 视口边界扩展（像素），用于预渲染 */
  overscan?: number;
}

interface UseVirtualizedBlocksResult {
  /** 可见的 Block 列表 */
  visibleBlocks: LayoutBlock[];
  /** 更新视口边界 */
  updateViewport: (bounds: ViewportBounds) => void;
  /** 当前视口边界 */
  viewportBounds: ViewportBounds | null;
  /** 是否启用虚拟渲染 */
  isVirtualized: boolean;
  /** 总 Block 数量 */
  totalCount: number;
  /** 可见 Block 数量 */
  visibleCount: number;
}

/** 启用虚拟渲染的 Block 数量阈值 */
const VIRTUALIZATION_THRESHOLD = 50;

/** 默认预渲染边距（像素） */
const DEFAULT_OVERSCAN = 200;

/**
 * 虚拟渲染 Hook
 * 当 Block 数量超过阈值时，仅渲染可视区域内的 Block
 */
export function useVirtualizedBlocks({
  blocks,
  zoomLevel,
  overscan = DEFAULT_OVERSCAN,
}: UseVirtualizedBlocksOptions): UseVirtualizedBlocksResult {
  const [viewportBounds, setViewportBounds] = useState<ViewportBounds | null>(null);
  
  const scale = zoomLevel / 100;
  
  // 是否启用虚拟渲染
  const isVirtualized = blocks.length > VIRTUALIZATION_THRESHOLD;

  // 更新视口边界
  const updateViewport = useCallback((bounds: ViewportBounds) => {
    setViewportBounds(bounds);
  }, []);

  // 计算可见的 Block
  const visibleBlocks = useMemo(() => {
    // 如果 Block 数量少于阈值，直接返回所有 Block
    if (!isVirtualized) {
      return blocks;
    }

    // 如果没有视口信息，返回所有 Block（初始状态）
    if (!viewportBounds) {
      return blocks;
    }

    // 计算扩展后的视口边界（考虑预渲染）
    const expandedBounds = {
      top: viewportBounds.top - overscan,
      bottom: viewportBounds.bottom + overscan,
      left: viewportBounds.left - overscan,
      right: viewportBounds.right + overscan,
    };

    // 过滤出在视口内的 Block
    return blocks.filter(block => {
      // 计算 Block 的缩放后边界
      const blockLeft = block.bbox.x * scale;
      const blockTop = block.bbox.y * scale;
      const blockRight = (block.bbox.x + block.bbox.width) * scale;
      const blockBottom = (block.bbox.y + block.bbox.height) * scale;

      // 检查是否与视口相交
      const isVisible = !(
        blockRight < expandedBounds.left ||
        blockLeft > expandedBounds.right ||
        blockBottom < expandedBounds.top ||
        blockTop > expandedBounds.bottom
      );

      return isVisible;
    });
  }, [blocks, viewportBounds, scale, isVirtualized, overscan]);

  return {
    visibleBlocks,
    updateViewport,
    viewportBounds,
    isVirtualized,
    totalCount: blocks.length,
    visibleCount: visibleBlocks.length,
  };
}

export default useVirtualizedBlocks;
