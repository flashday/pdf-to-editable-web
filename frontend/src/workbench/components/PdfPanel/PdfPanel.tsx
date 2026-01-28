import React, { useState, useRef, useCallback, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import ZoomControls from './ZoomControls';
import styles from './PdfPanel.module.css';

// V2 优化：移除 react-pdf 依赖，直接使用 OCR 生成的 PNG 图片
// 这消除了 PDF.js worker 加载延迟和坐标转换复杂性

export interface PdfPanelRef {
  /** 获取滚动容器元素 */
  getScrollContainer: () => HTMLDivElement | null;
}

export interface PdfPanelProps {
  /** Block 点击回调 */
  onBlockClick?: (blockId: string) => void;
}

const PdfPanel = forwardRef<PdfPanelRef, PdfPanelProps>(({ onBlockClick }, ref) => {
  const { 
    jobId, 
    layoutBlocks, 
    zoomLevel, 
    setZoomLevel,
    activeBlockId,
    hoveredBlockId,
    setActiveBlockId,
    setHoveredBlockId,
    isLoading
  } = useWorkbenchStore();

  // V2 优化：移除 numPages, pageNumber, pdfUrl, fileType 状态
  // 统一使用图片模式，简化状态管理
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [scrollPosition, setScrollPosition] = useState({ x: 0, y: 0 });
  const [scrollState, setScrollState] = useState({ top: 0, left: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  
  const containerRef = useRef<HTMLDivElement>(null);

  // 暴露滚动容器给父组件（用于同步滚动）
  useImperativeHandle(ref, () => ({
    getScrollContainer: () => containerRef.current
  }), []);

  // V2 优化：直接构建图片 URL，无需文件类型检测
  const imageUrl = jobId ? `/api/convert/${jobId}/image?t=${Date.now()}` : null;

  // 重置状态当 jobId 变化
  useEffect(() => {
    setImageLoaded(false);
    setImageError(null);
    setImageDimensions({ width: 0, height: 0 });
  }, [jobId]);

  // 图片加载成功回调
  const handleImageLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    console.log('PdfPanel: 图片加载成功', img.naturalWidth, 'x', img.naturalHeight);
    setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    setImageLoaded(true);
    setImageError(null);
  }, []);

  // 图片加载失败回调
  const handleImageError = useCallback(() => {
    console.error('PdfPanel: 图片加载失败');
    setImageError('无法加载文档预览');
    setImageLoaded(false);
  }, []);

  // 重试加载
  const handleRetry = useCallback(() => {
    setImageError(null);
    setImageLoaded(false);
    // 通过更新 key 强制重新加载图片
    setImageDimensions({ width: 0, height: 0 });
  }, []);

  // 拖拽开始
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    if (containerRef.current) {
      setScrollPosition({
        x: containerRef.current.scrollLeft,
        y: containerRef.current.scrollTop
      });
    }
  }, []);

  // 拖拽移动
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !containerRef.current) return;
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    containerRef.current.scrollLeft = scrollPosition.x - dx;
    containerRef.current.scrollTop = scrollPosition.y - dy;
  }, [isDragging, dragStart, scrollPosition]);

  // 拖拽结束
  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 鼠标离开
  const handleMouseLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  // 滚轮缩放
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -10 : 10;
      setZoomLevel(zoomLevel + delta);
    }
  }, [zoomLevel, setZoomLevel]);

  // Block 点击
  const handleBlockClick = useCallback((blockId: string) => {
    setActiveBlockId(blockId);
    // 通知父组件（用于同步滚动）
    if (onBlockClick) {
      onBlockClick(blockId);
    }
  }, [setActiveBlockId, onBlockClick]);

  // Block 悬停
  const handleBlockHover = useCallback((blockId: string | null) => {
    setHoveredBlockId(blockId);
  }, [setHoveredBlockId]);

  // 滚动到激活的 Block
  useEffect(() => {
    if (!activeBlockId || !containerRef.current) return;
    const block = layoutBlocks.find(b => b.id === activeBlockId);
    if (!block) return;
    const scale = zoomLevel / 100;
    const targetX = block.bbox.x * scale;
    const targetY = block.bbox.y * scale;
    containerRef.current.scrollTo({
      left: targetX - containerRef.current.clientWidth / 2 + (block.bbox.width * scale) / 2,
      top: targetY - containerRef.current.clientHeight / 2 + (block.bbox.height * scale) / 2,
      behavior: 'smooth'
    });
  }, [activeBlockId, layoutBlocks, zoomLevel]);

  // 监听滚动事件
  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollState({
        top: containerRef.current.scrollTop,
        left: containerRef.current.scrollLeft,
      });
    }
  }, []);

  // 监听容器尺寸变化
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const updateSize = () => {
      setContainerSize({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    };
    updateSize();
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(container);
    container.addEventListener('scroll', handleScroll);
    return () => {
      resizeObserver.disconnect();
      container.removeEventListener('scroll', handleScroll);
    };
  }, [handleScroll]);

  // 计算缩放后的尺寸
  const scale = zoomLevel / 100;
  const scaledWidth = imageDimensions.width * scale;
  const scaledHeight = imageDimensions.height * scale;

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>加载预览...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>文档预览</span>
        <span className={styles.blockCount}>
          {layoutBlocks.length} 个区块
        </span>
        <ZoomControls 
          zoomLevel={zoomLevel} 
          onZoomChange={setZoomLevel}
        />
      </div>
      
      <div 
        ref={containerRef}
        className={`${styles.content} ${isDragging ? styles.dragging : ''}`}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
        onWheel={handleWheel}
      >
        {imageError ? (
          <div className={styles.error}>
            <span className={styles.errorIcon}>⚠</span>
            <p>{imageError}</p>
            <button onClick={handleRetry}>重试</button>
          </div>
        ) : imageUrl ? (
          <div 
            className={styles.imageWrapper}
            style={{
              width: imageLoaded ? scaledWidth : 'auto',
              height: imageLoaded ? scaledHeight : 'auto',
            }}
          >
            <img
              key={jobId} // 强制在 jobId 变化时重新加载
              src={imageUrl}
              alt="文档预览"
              className={styles.image}
              onLoad={handleImageLoad}
              onError={handleImageError}
              style={{
                width: imageLoaded ? scaledWidth : 'auto',
                height: imageLoaded ? scaledHeight : 'auto',
                display: imageLoaded ? 'block' : 'none',
              }}
            />
            
            {!imageLoaded && (
              <div className={styles.imagePlaceholder}>
                <div className={styles.spinner}></div>
                <p>正在加载图片...</p>
              </div>
            )}
            
            {/* V2 优化：BoundingBoxOverlay 直接使用图片尺寸，无需 ocrImageWidth/ocrImageHeight */}
            {imageLoaded && imageDimensions.width > 0 && (
              <BoundingBoxOverlay
                blocks={layoutBlocks}
                activeBlockId={activeBlockId}
                hoveredBlockId={hoveredBlockId}
                imageWidth={imageDimensions.width}
                imageHeight={imageDimensions.height}
                zoomLevel={zoomLevel}
                onBlockClick={handleBlockClick}
                onBlockHover={handleBlockHover}
                scrollTop={scrollState.top}
                scrollLeft={scrollState.left}
                containerWidth={containerSize.width}
                containerHeight={containerSize.height}
              />
            )}
          </div>
        ) : (
          <div className={styles.imagePlaceholder}>
            <p>请选择一个任务以预览文档</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PdfPanel;

export type { PdfPanelRef, PdfPanelProps };
