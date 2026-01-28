import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import { api } from '../../services/api';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import ZoomControls from './ZoomControls';
import styles from './PdfPanel.module.css';

const PdfPanel: React.FC = () => {
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

  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [scrollPosition, setScrollPosition] = useState({ x: 0, y: 0 });
  // 虚拟渲染所需的滚动和容器状态
  const [scrollState, setScrollState] = useState({ top: 0, left: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const imageUrl = jobId ? api.getImageUrl(jobId) : '';

  // 图像加载成功
  const handleImageLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    setImageLoaded(true);
    setImageError(null);
  }, []);

  // 图像加载失败
  const handleImageError = useCallback(() => {
    setImageLoaded(false);
    setImageError('无法加载 PDF 预览图像');
  }, []);

  // 拖拽开始
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return; // 只响应左键
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
  }, [setActiveBlockId]);

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

  // 监听滚动事件以更新虚拟渲染视口
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

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>
          <div className={styles.spinner}></div>
          <p>加载 PDF 预览...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>PDF 预览</span>
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
            <button onClick={() => setImageError(null)}>重试</button>
          </div>
        ) : (
          <div 
            className={styles.imageWrapper}
            style={{
              width: imageDimensions.width * (zoomLevel / 100),
              height: imageDimensions.height * (zoomLevel / 100),
            }}
          >
            <img
              ref={imageRef}
              src={imageUrl}
              alt="PDF Preview"
              className={styles.image}
              style={{
                width: imageDimensions.width * (zoomLevel / 100),
                height: imageDimensions.height * (zoomLevel / 100),
              }}
              onLoad={handleImageLoad}
              onError={handleImageError}
              draggable={false}
            />
            
            {imageLoaded && (
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
        )}
        
        {!imageLoaded && !imageError && imageUrl && (
          <div className={styles.imagePlaceholder}>
            <div className={styles.spinner}></div>
            <p>加载图像中...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PdfPanel;
