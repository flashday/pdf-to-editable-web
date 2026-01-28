import React, { useState, useEffect } from 'react';
import { LayoutBlock } from '../../stores/types';
import { useVirtualizedBlocks } from '../../hooks/useVirtualizedBlocks';
import styles from './BoundingBoxOverlay.module.css';

interface BoundingBoxOverlayProps {
  blocks: LayoutBlock[];
  activeBlockId: string | null;
  hoveredBlockId: string | null;
  imageWidth: number;      // 现在等于 OCR 图像宽度
  imageHeight: number;     // 现在等于 OCR 图像高度
  zoomLevel: number;
  onBlockClick: (blockId: string) => void;
  onBlockHover: (blockId: string | null) => void;
  /** 父容器滚动位置（用于虚拟渲染） */
  scrollTop?: number;
  scrollLeft?: number;
  /** 父容器尺寸（用于虚拟渲染） */
  containerWidth?: number;
  containerHeight?: number;
  // 移除: ocrImageWidth, ocrImageHeight - 不再需要坐标转换
}

// 置信度颜色映射
const getConfidenceColor = (confidence: number): string => {
  if (confidence >= 0.9) return 'rgba(40, 167, 69, 0.25)';  // 绿色
  if (confidence >= 0.8) return 'rgba(255, 193, 7, 0.25)';  // 黄色
  return 'rgba(220, 53, 69, 0.25)';  // 红色
};

// 置信度边框颜色
const getConfidenceBorderColor = (confidence: number): string => {
  if (confidence >= 0.9) return '#28a745';  // 绿色
  if (confidence >= 0.8) return '#ffc107';  // 黄色
  return '#dc3545';  // 红色
};

// Block 类型图标
const getBlockTypeIcon = (type: string): string => {
  const icons: Record<string, string> = {
    'title': '📑',
    'text': '📝',
    'table': '📊',
    'figure': '🖼️',
    'list': '📋',
    'reference': '📚'
  };
  return icons[type] || '📄';
};

// Block 类型中文名
const getBlockTypeName = (type: string): string => {
  const names: Record<string, string> = {
    'title': '标题',
    'text': '文本',
    'table': '表格',
    'figure': '图片',
    'list': '列表',
    'reference': '引用'
  };
  return names[type] || type;
};

const BoundingBoxOverlay: React.FC<BoundingBoxOverlayProps> = ({
  blocks,
  activeBlockId,
  hoveredBlockId,
  imageWidth,
  imageHeight,
  zoomLevel,
  onBlockClick,
  onBlockHover,
  scrollTop = 0,
  scrollLeft = 0,
  containerWidth = 0,
  containerHeight = 0,
}) => {
  const [tooltipBlock, setTooltipBlock] = useState<LayoutBlock | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  // 简化后的缩放计算：仅应用 zoomLevel 缩放因子
  const scale = zoomLevel / 100;

  // 使用虚拟渲染 Hook
  const { visibleBlocks, updateViewport, isVirtualized, totalCount, visibleCount } = useVirtualizedBlocks({
    blocks,
    zoomLevel,
    overscan: 200,
  });

  // 更新视口边界
  useEffect(() => {
    if (containerWidth > 0 && containerHeight > 0) {
      updateViewport({
        top: scrollTop,
        bottom: scrollTop + containerHeight,
        left: scrollLeft,
        right: scrollLeft + containerWidth,
      });
    }
  }, [scrollTop, scrollLeft, containerWidth, containerHeight, updateViewport]);

  const handleMouseEnter = (block: LayoutBlock, e: React.MouseEvent) => {
    onBlockHover(block.id);
    setTooltipBlock(block);
    setTooltipPosition({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (tooltipBlock) {
      setTooltipPosition({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseLeave = () => {
    onBlockHover(null);
    setTooltipBlock(null);
  };

  const handleClick = (block: LayoutBlock, e: React.MouseEvent) => {
    e.stopPropagation();
    onBlockClick(block.id);
  };

  return (
    <div 
      className={styles.overlay}
      style={{
        width: imageWidth * scale,
        height: imageHeight * scale,
      }}
    >
      {/* 虚拟渲染状态指示器（仅在开发模式显示） */}
      {isVirtualized && process.env.NODE_ENV === 'development' && (
        <div className={styles.virtualizedIndicator}>
          渲染: {visibleCount}/{totalCount}
        </div>
      )}
      
      {visibleBlocks.map((block) => {
        const isActive = block.id === activeBlockId;
        const isHovered = block.id === hoveredBlockId;
        const isLowConfidence = block.confidence < 0.8;

        // 简化后的坐标计算：直接使用 OCR 坐标 * scale
        // 不再需要 coordScaleX/coordScaleY 转换

        return (
          <div
            key={block.id}
            className={`
              ${styles.box}
              ${isActive ? styles.active : ''}
              ${isHovered ? styles.hovered : ''}
              ${isLowConfidence ? styles.lowConfidence : ''}
            `}
            style={{
              left: block.bbox.x * scale,
              top: block.bbox.y * scale,
              width: block.bbox.width * scale,
              height: block.bbox.height * scale,
              backgroundColor: getConfidenceColor(block.confidence),
              borderColor: isActive 
                ? '#007bff' 
                : isHovered 
                  ? '#17a2b8' 
                  : getConfidenceBorderColor(block.confidence),
            }}
            onMouseEnter={(e) => handleMouseEnter(block, e)}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={(e) => handleClick(block, e)}
          >
            <span className={styles.blockLabel}>
              {getBlockTypeIcon(block.type)}
            </span>
          </div>
        );
      })}

      {/* Tooltip */}
      {tooltipBlock && (
        <div 
          className={styles.tooltip}
          style={{
            left: tooltipPosition.x + 10,
            top: tooltipPosition.y + 10,
          }}
        >
          <div className={styles.tooltipHeader}>
            <span className={styles.tooltipIcon}>
              {getBlockTypeIcon(tooltipBlock.type)}
            </span>
            <span className={styles.tooltipType}>
              {getBlockTypeName(tooltipBlock.type)}
            </span>
          </div>
          <div className={styles.tooltipContent}>
            <div className={styles.tooltipRow}>
              <span>ID:</span>
              <span>{tooltipBlock.id}</span>
            </div>
            <div className={styles.tooltipRow}>
              <span>置信度:</span>
              <span 
                className={styles.confidence}
                style={{ color: getConfidenceBorderColor(tooltipBlock.confidence) }}
              >
                {(tooltipBlock.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <div className={styles.tooltipRow}>
              <span>位置:</span>
              <span>
                ({Math.round(tooltipBlock.bbox.x)}, {Math.round(tooltipBlock.bbox.y)})
              </span>
            </div>
            <div className={styles.tooltipRow}>
              <span>尺寸:</span>
              <span>
                {Math.round(tooltipBlock.bbox.width)} × {Math.round(tooltipBlock.bbox.height)}
              </span>
            </div>
          </div>
          {tooltipBlock.confidence < 0.8 && (
            <div className={styles.tooltipWarning}>
              ⚠ 低置信度，建议人工校验
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default BoundingBoxOverlay;

// 导出工具函数供测试使用
export { getConfidenceColor, getConfidenceBorderColor };
