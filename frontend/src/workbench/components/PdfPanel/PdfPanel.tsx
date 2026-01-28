import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { useWorkbenchStore } from '../../stores/workbenchStore';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import ZoomControls from './ZoomControls';
import styles from './PdfPanel.module.css';

// 设置 PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

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
    isLoading,
    imageWidth: ocrImageWidth,  // OCR 坐标基于的 PNG 图像尺寸
    imageHeight: ocrImageHeight
  } = useWorkbenchStore();

  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [pageDimensions, setPageDimensions] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [scrollPosition, setScrollPosition] = useState({ x: 0, y: 0 });
  const [scrollState, setScrollState] = useState({ top: 0, left: 0 });
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [fileType, setFileType] = useState<'pdf' | 'image' | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);

  // 检测文件类型并设置 URL
  useEffect(() => {
    if (!jobId) return;
    
    const checkFileType = async () => {
      try {
        // 先尝试获取原始文件信息
        const response = await fetch(`/api/convert/${jobId}/original-file`, {
          method: 'HEAD'
        });
        
        const contentType = response.headers.get('Content-Type') || '';
        console.log('PdfPanel: 文件类型检测', contentType);
        
        if (contentType.includes('pdf')) {
          setFileType('pdf');
          setPdfUrl(`/api/convert/${jobId}/original-file`);
          console.log('PdfPanel: 使用 PDF 渲染模式');
        } else {
          // 如果不是 PDF，回退到图片模式
          setFileType('image');
          setImageUrl(`/api/convert/${jobId}/image?t=${Date.now()}`);
          console.log('PdfPanel: 使用图片渲染模式');
        }
      } catch (error) {
        console.error('PdfPanel: 文件类型检测失败，回退到图片模式', error);
        setFileType('image');
        setImageUrl(`/api/convert/${jobId}/image?t=${Date.now()}`);
      }
    };
    
    checkFileType();
    
    return () => {
      setPdfUrl(null);
      setImageUrl(null);
      setPdfLoaded(false);
      setPdfError(null);
    };
  }, [jobId]);

  // PDF 加载成功回调
  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    console.log('PdfPanel: PDF 加载成功，共', numPages, '页');
    setNumPages(numPages);
    setPdfLoaded(true);
    setPdfError(null);
  }, []);

  // PDF 加载失败回调
  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('PdfPanel: PDF 加载失败', error);
    setPdfError(`PDF 加载失败: ${error.message}`);
    // 回退到图片模式
    setFileType('image');
    setImageUrl(`/api/convert/${jobId}/image?t=${Date.now()}`);
  }, [jobId]);

  // PDF 页面渲染成功回调
  const onPageLoadSuccess = useCallback((page: any) => {
    const { width, height } = page;
    console.log('PdfPanel: PDF 页面渲染成功', width, 'x', height);
    setPageDimensions({ width, height });
  }, []);

  // 图片加载成功回调（回退模式）
  const handleImageLoad = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    console.log('PdfPanel: 图片加载成功', img.naturalWidth, 'x', img.naturalHeight);
    setPageDimensions({ width: img.naturalWidth, height: img.naturalHeight });
    setPdfLoaded(true);
  }, []);

  // 图片加载失败回调
  const handleImageError = useCallback(() => {
    console.error('PdfPanel: 图片加载失败');
    setPdfError('无法加载文档预览');
  }, []);

  // 重试加载
  const handleRetry = useCallback(() => {
    setPdfError(null);
    setPdfLoaded(false);
    
    if (jobId) {
      // 重新检测文件类型
      setFileType(null);
      setPdfUrl(null);
      setImageUrl(null);
      
      // 触发重新加载
      setTimeout(() => {
        setFileType('pdf');
        setPdfUrl(`/api/convert/${jobId}/original-file?t=${Date.now()}`);
      }, 100);
    }
  }, [jobId]);

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
  const scaledWidth = pageDimensions.width * scale;
  const scaledHeight = pageDimensions.height * scale;

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
          {numPages > 1 && ` · 第 ${pageNumber}/${numPages} 页`}
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
        {pdfError ? (
          <div className={styles.error}>
            <span className={styles.errorIcon}>⚠</span>
            <p>{pdfError}</p>
            <button onClick={handleRetry}>重试</button>
          </div>
        ) : fileType === 'pdf' && pdfUrl ? (
          <div 
            ref={pageRef}
            className={styles.imageWrapper}
            style={{
              width: pdfLoaded ? scaledWidth : 'auto',
              height: pdfLoaded ? scaledHeight : 'auto',
            }}
          >
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={
                <div className={styles.imagePlaceholder}>
                  <div className={styles.spinner}></div>
                  <p>正在加载 PDF...</p>
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                onLoadSuccess={onPageLoadSuccess}
                renderTextLayer={false}
                renderAnnotationLayer={false}
              />
            </Document>
            
            {pdfLoaded && pageDimensions.width > 0 && (
              <BoundingBoxOverlay
                blocks={layoutBlocks}
                activeBlockId={activeBlockId}
                hoveredBlockId={hoveredBlockId}
                imageWidth={pageDimensions.width}
                imageHeight={pageDimensions.height}
                zoomLevel={zoomLevel}
                onBlockClick={handleBlockClick}
                onBlockHover={handleBlockHover}
                scrollTop={scrollState.top}
                scrollLeft={scrollState.left}
                containerWidth={containerSize.width}
                containerHeight={containerSize.height}
                ocrImageWidth={ocrImageWidth}
                ocrImageHeight={ocrImageHeight}
              />
            )}
          </div>
        ) : fileType === 'image' && imageUrl ? (
          <div 
            className={styles.imageWrapper}
            style={{
              width: pdfLoaded ? scaledWidth : 'auto',
              height: pdfLoaded ? scaledHeight : 'auto',
            }}
          >
            <img
              src={imageUrl}
              alt="文档预览"
              className={styles.image}
              onLoad={handleImageLoad}
              onError={handleImageError}
              style={{
                width: pdfLoaded ? scaledWidth : 'auto',
                height: pdfLoaded ? scaledHeight : 'auto',
                display: pdfLoaded ? 'block' : 'none',
              }}
            />
            
            {!pdfLoaded && (
              <div className={styles.imagePlaceholder}>
                <div className={styles.spinner}></div>
                <p>正在加载图片...</p>
              </div>
            )}
            
            {pdfLoaded && pageDimensions.width > 0 && (
              <BoundingBoxOverlay
                blocks={layoutBlocks}
                activeBlockId={activeBlockId}
                hoveredBlockId={hoveredBlockId}
                imageWidth={pageDimensions.width}
                imageHeight={pageDimensions.height}
                zoomLevel={zoomLevel}
                onBlockClick={handleBlockClick}
                onBlockHover={handleBlockHover}
                scrollTop={scrollState.top}
                scrollLeft={scrollState.left}
                containerWidth={containerSize.width}
                containerHeight={containerSize.height}
                ocrImageWidth={ocrImageWidth}
                ocrImageHeight={ocrImageHeight}
              />
            )}
          </div>
        ) : (
          <div className={styles.imagePlaceholder}>
            <div className={styles.spinner}></div>
            <p>正在检测文件类型...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PdfPanel;
