"""
Document processing pipeline service
Orchestrates the complete document conversion workflow from upload to Editor.js output
"""
import os
import logging
import time
import threading
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from backend.models.document import (
    Document, ProcessingStatus, LayoutResult, EditorJSData
)
from backend.services.interfaces import DocumentProcessorInterface
from backend.services.ocr_service import PaddleOCRService, OCRProcessingError
from backend.services.data_normalizer import DataNormalizer
from backend.services.pdf_processor import PDFProcessor, PDFProcessingError
from backend.services.status_tracker import status_tracker, ProcessingStage
from backend.services.performance_monitor import performance_monitor
from backend.services.error_handler import error_handler
from backend.services.job_cache import get_job_cache
from backend.config import ChatOCRConfig

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of document processing"""
    success: bool
    document_id: str
    editor_data: Optional[EditorJSData] = None
    confidence_report: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_time: float = 0.0


class DocumentProcessor(DocumentProcessorInterface):
    """
    Main document processing pipeline that orchestrates:
    1. File validation and preparation
    2. PDF page extraction (if needed)
    3. OCR layout analysis
    4. Table structure recognition
    5. Data normalization to Editor.js format
    6. Schema validation
    """
    
    def __init__(self, upload_folder: Path, temp_folder: Path, use_gpu: bool = False):
        """
        Initialize document processor
        
        Args:
            upload_folder: Path to uploaded files
            temp_folder: Path for temporary files
            use_gpu: Whether to use GPU for OCR (default: False)
        """
        self.upload_folder = upload_folder
        self.temp_folder = temp_folder
        self.use_gpu = use_gpu
        
        # Initialize services lazily
        self._ocr_service = None
        self._data_normalizer = None
        self._rag_service = None
        
        # Processing results storage (in-memory for now)
        self._results: Dict[str, ProcessingResult] = {}
        self._lock = threading.Lock()
        
        # Ensure folders exist
        self.upload_folder.mkdir(exist_ok=True)
        self.temp_folder.mkdir(exist_ok=True)
    
    @property
    def ocr_service(self) -> PaddleOCRService:
        """Lazy initialization of OCR service"""
        if self._ocr_service is None:
            try:
                self._ocr_service = PaddleOCRService(use_gpu=self.use_gpu, lang='ch')
                logger.info("OCR service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OCR service: {e}")
                raise OCRProcessingError(f"OCR service initialization failed: {e}")
        return self._ocr_service
    
    @property
    def data_normalizer(self) -> DataNormalizer:
        """Lazy initialization of data normalizer"""
        if self._data_normalizer is None:
            self._data_normalizer = DataNormalizer()
            logger.info("Data normalizer initialized")
        return self._data_normalizer
    
    @property
    def rag_service(self):
        """Lazy initialization of RAG service"""
        if self._rag_service is None and ChatOCRConfig.ENABLE_RAG:
            try:
                from backend.services.rag_service import get_rag_service
                self._rag_service = get_rag_service()
                logger.info("RAG service initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG service: {e}")
                self._rag_service = None
        return self._rag_service
    
    def process_document(self, document: Document) -> Document:
        """
        Process document through complete pipeline
        
        Args:
            document: Document to process
            
        Returns:
            Updated document with processing results
        """
        start_time = time.time()
        operation_id = performance_monitor.start_operation(f'process_document_{document.id}')
        
        try:
            logger.info(f"Starting document processing: {document.id}")
            
            # Update status to processing
            document.processing_status = ProcessingStatus.PROCESSING
            status_tracker.update_status(
                document.id, 
                ProcessingStage.OCR_PROCESSING, 
                0.0, 
                'Starting OCR processing'
            )
            
            # Get file path
            file_path = self._get_file_path(document)
            if not file_path.exists():
                raise FileNotFoundError(f"Document file not found: {file_path}")
            
            # Prepare image for OCR
            image_path = self._prepare_image_for_ocr(document, file_path)
            
            # Perform OCR layout analysis
            status_tracker.update_status(
                document.id,
                ProcessingStage.LAYOUT_ANALYSIS,
                0.0,
                'Analyzing document layout'
            )
            
            layout_result = self._perform_ocr_analysis(image_path)
            
            status_tracker.update_status(
                document.id,
                ProcessingStage.LAYOUT_ANALYSIS,
                0.5,
                f'Detected {len(layout_result.regions)} regions'
            )
            
            # Always try to extract tables using PPStructure
            # This provides better table detection than simple heuristics
            try:
                tables = self.ocr_service.extract_tables(str(image_path), layout_result.regions)
                if tables:
                    layout_result.tables = tables
                    logger.info(f"Extracted {len(tables)} tables using PPStructure")
            except Exception as e:
                logger.warning(f"Table extraction failed: {e}")
            
            status_tracker.update_status(
                document.id,
                ProcessingStage.LAYOUT_ANALYSIS,
                1.0,
                'Layout analysis complete'
            )
            
            # Normalize to Editor.js format
            status_tracker.update_status(
                document.id,
                ProcessingStage.DATA_NORMALIZATION,
                0.0,
                'Converting to Editor.js format'
            )
            
            editor_data = self.data_normalizer.normalize_ocr_result(layout_result)
            
            status_tracker.update_status(
                document.id,
                ProcessingStage.DATA_NORMALIZATION,
                0.5,
                f'Created {len(editor_data.blocks)} blocks'
            )
            
            # Validate schema
            status_tracker.update_status(
                document.id,
                ProcessingStage.SCHEMA_VALIDATION,
                0.0,
                'Validating Editor.js schema'
            )
            
            validation_result = self.data_normalizer.validate_editor_schema(editor_data)
            
            if not validation_result.get('is_valid', False):
                logger.warning(f"Schema validation warnings: {validation_result.get('errors', [])}")
            
            status_tracker.update_status(
                document.id,
                ProcessingStage.SCHEMA_VALIDATION,
                1.0,
                'Schema validation complete'
            )
            
            # Store result
            processing_time = time.time() - start_time
            confidence_report = getattr(editor_data, 'confidence_report', None)
            
            result = ProcessingResult(
                success=True,
                document_id=document.id,
                editor_data=editor_data,
                confidence_report=confidence_report,
                processing_time=processing_time
            )
            
            with self._lock:
                self._results[document.id] = result
            
            # Update document status
            document.processing_status = ProcessingStatus.COMPLETED
            document.conversion_result = editor_data
            
            # Mark job as completed
            status_tracker.mark_completed(document.id, {
                'blocks_count': len(editor_data.blocks),
                'processing_time': processing_time
            })
            
            # 保存到任务缓存
            try:
                cache = get_job_cache()
                if cache:
                    # 提取置信度分数
                    conf_score = None
                    if confidence_report and 'confidence_breakdown' in confidence_report:
                        overall = confidence_report['confidence_breakdown'].get('overall', {})
                        conf_score = overall.get('score')
                    
                    # 检查是否有表格
                    has_tables = any(b.type == 'table' for b in editor_data.blocks)
                    
                    cache.save_job(
                        job_id=document.id,
                        filename=document.original_filename,
                        processing_time=processing_time,
                        confidence_score=conf_score,
                        block_count=len(editor_data.blocks),
                        has_tables=has_tables,
                        status='completed',
                        document_type_id=document.document_type_id
                    )
            except Exception as cache_error:
                logger.warning(f"Failed to save job to cache: {cache_error}")
            
            # 构建 RAG 向量索引（异步，不阻塞主流程）
            self._build_rag_index_async(document.id, editor_data)
            
            # Clean up temporary files
            self._cleanup_temp_files(document.id)
            
            performance_monitor.end_operation(operation_id, success=True)
            logger.info(f"Document processing completed: {document.id} in {processing_time:.2f}s")
            
            return document
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            
            logger.error(f"Document processing failed: {document.id} - {error_message}")
            
            # Store error result
            result = ProcessingResult(
                success=False,
                document_id=document.id,
                error=error_message,
                processing_time=processing_time
            )
            
            with self._lock:
                self._results[document.id] = result
            
            # Update document status
            document.processing_status = ProcessingStatus.FAILED
            document.error_message = error_message
            
            # Mark job as failed
            status_tracker.mark_failed(document.id, error_message)
            
            # Clean up temporary files
            self._cleanup_temp_files(document.id)
            
            performance_monitor.end_operation(operation_id, success=False, error_message=error_message)
            
            return document
    
    def process_document_async(self, document: Document) -> None:
        """
        Process document asynchronously in a background thread
        
        Args:
            document: Document to process
        """
        thread = threading.Thread(
            target=self.process_document,
            args=(document,),
            daemon=True
        )
        thread.start()
        logger.info(f"Started async processing for document: {document.id}")
    
    def get_processing_status(self, document_id: str) -> Optional[Document]:
        """
        Get current processing status
        
        Args:
            document_id: Document identifier
            
        Returns:
            Document with current status or None
        """
        job_status = status_tracker.get_job_status(document_id)
        if not job_status:
            return None
        
        # Create document object from status
        document = Document(
            id=document_id,
            original_filename=job_status.get('metadata', {}).get('filename', 'unknown'),
            file_type='unknown',
            file_size=0,
            processing_status=self._map_stage_to_status(job_status['status'])
        )
        
        if job_status.get('error'):
            document.error_message = job_status['error']
        
        return document
    
    def get_processing_result(self, document_id: str) -> Optional[ProcessingResult]:
        """
        Get processing result for a document
        
        Args:
            document_id: Document identifier
            
        Returns:
            ProcessingResult or None if not found
        """
        with self._lock:
            return self._results.get(document_id)
    
    def _get_file_path(self, document: Document) -> Path:
        """Get file path for document"""
        file_extension = document.file_type
        return self.upload_folder / f"{document.id}.{file_extension}"
    
    def _prepare_image_for_ocr(self, document: Document, file_path: Path) -> Path:
        """
        Prepare image for OCR processing
        
        Args:
            document: Document being processed
            file_path: Path to original file
            
        Returns:
            Path to image ready for OCR
        """
        if document.file_type == 'pdf':
            # 检测 PDF 类型（仅记录日志，为后续优化做准备）
            # TODO: 后续可根据类型分流处理，文本型 PDF 直接提取文本
            pdf_type = PDFProcessor.detect_pdf_type(file_path)
            
            # Extract first page as image
            image_path = self.temp_folder / f"{document.id}_page1.png"
            
            if not image_path.exists():
                success, error = PDFProcessor.extract_first_page_as_image(file_path, image_path)
                if not success:
                    raise PDFProcessingError(f"Failed to extract PDF page: {error}")
            
            performance_monitor.register_temp_file(str(image_path))
            return image_path
        else:
            # Image file - use directly
            return file_path
    
    def _perform_ocr_analysis(self, image_path: Path) -> LayoutResult:
        """
        Perform OCR layout analysis
        
        Args:
            image_path: Path to image file
            
        Returns:
            LayoutResult with detected regions
        """
        try:
            layout_result = self.ocr_service.analyze_layout(str(image_path))
            logger.info(f"OCR analysis complete: {len(layout_result.regions)} regions, "
                       f"confidence: {layout_result.confidence_score:.2f}")
            return layout_result
        except OCRProcessingError:
            raise
        except Exception as e:
            raise OCRProcessingError(f"OCR analysis failed: {e}")
    
    def _cleanup_temp_files(self, document_id: str) -> None:
        """Clean up temporary files for a document
        
        注意：为了支持缓存功能，保留以下文件：
        - {document_id}_page1.png - 页面图片（用于显示）
        - {document_id}_ppstructure.json - 布局结果
        - {document_id}_raw_ocr.json - OCR原始结果
        - {document_id}_raw_ocr.html - HTML格式
        - {document_id}_confidence_log.md - 置信度日志
        
        只清理预处理图片等临时文件
        """
        try:
            # 只清理预处理图片，保留其他文件用于缓存
            for pattern in [f"{document_id}_preprocessed*", f"{document_id}_page[2-9]*.png"]:
                for temp_file in self.temp_folder.glob(pattern):
                    try:
                        temp_file.unlink()
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                    except OSError as e:
                        logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
        except Exception as e:
            logger.warning(f"Temp file cleanup error: {e}")
    
    def _map_stage_to_status(self, stage: ProcessingStage) -> ProcessingStatus:
        """Map processing stage to document status"""
        if stage == ProcessingStage.COMPLETED:
            return ProcessingStatus.COMPLETED
        elif stage == ProcessingStage.FAILED:
            return ProcessingStatus.FAILED
        else:
            return ProcessingStatus.PROCESSING
    
    def _build_rag_index_async(self, document_id: str, editor_data: EditorJSData) -> None:
        """
        异步构建 RAG 向量索引
        
        在后台线程中执行，不阻塞主处理流程
        索引失败不影响 OCR 结果的返回
        
        Args:
            document_id: 文档 ID
            editor_data: Editor.js 格式的数据
        """
        if not ChatOCRConfig.ENABLE_RAG:
            logger.debug("RAG indexing disabled")
            return
        
        def build_index():
            try:
                rag = self.rag_service
                if rag is None:
                    logger.warning("RAG service not available, skipping indexing")
                    return
                
                # 从 editor_data 提取文本
                text = self._extract_text_from_editor_data(editor_data)
                
                if not text or len(text.strip()) < 50:
                    logger.info(f"Document {document_id} has insufficient text for indexing")
                    return
                
                # 构建索引
                status = rag.index_document(document_id, text)
                
                if status.indexed:
                    logger.info(f"RAG index built for {document_id}: {status.chunk_count} chunks in {status.index_time:.2f}s")
                else:
                    logger.warning(f"RAG indexing failed for {document_id}: {status.error}")
                    
            except Exception as e:
                logger.error(f"RAG indexing error for {document_id}: {e}")
        
        # 在后台线程中执行
        thread = threading.Thread(target=build_index, daemon=True)
        thread.start()
    
    def _extract_text_from_editor_data(self, editor_data: EditorJSData) -> str:
        """
        从 Editor.js 数据中提取纯文本
        
        Args:
            editor_data: Editor.js 格式的数据
            
        Returns:
            str: 提取的文本内容
        """
        text_parts = []
        
        for block in editor_data.blocks:
            if block.type == 'paragraph':
                text = block.data.get('text', '')
                if text:
                    text_parts.append(text)
            elif block.type == 'header':
                text = block.data.get('text', '')
                if text:
                    text_parts.append(text)
            elif block.type == 'table':
                # 从表格 HTML 中提取文本
                html = block.data.get('tableHtml', '')
                if html:
                    text = self._extract_text_from_html(html)
                    if text:
                        text_parts.append(text)
            elif block.type == 'list':
                items = block.data.get('items', [])
                for item in items:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict):
                        text_parts.append(item.get('content', ''))
        
        return '\n\n'.join(text_parts)
    
    def _extract_text_from_html(self, html: str) -> str:
        """
        从 HTML 中提取纯文本
        
        Args:
            html: HTML 字符串
            
        Returns:
            str: 提取的文本
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception:
            # 简单的正则提取
            import re
            text = re.sub(r'<[^>]+>', ' ', html)
            return ' '.join(text.split())
    
    def get_rag_index_status(self, document_id: str) -> Optional[dict]:
        """
        获取文档的 RAG 索引状态
        
        Args:
            document_id: 文档 ID
            
        Returns:
            dict: 索引状态信息，如果 RAG 未启用则返回 None
        """
        if not ChatOCRConfig.ENABLE_RAG:
            return None
        
        rag = self.rag_service
        if rag is None:
            return None
        
        status = rag.get_index_status(document_id)
        return status.to_dict()


# Global document processor instance (will be initialized with app config)
document_processor: Optional[DocumentProcessor] = None


def init_document_processor(upload_folder: Path, temp_folder: Path, use_gpu: bool = False) -> DocumentProcessor:
    """
    Initialize global document processor
    
    Args:
        upload_folder: Path to uploaded files
        temp_folder: Path for temporary files
        use_gpu: Whether to use GPU for OCR
        
    Returns:
        Initialized DocumentProcessor instance
    """
    global document_processor
    document_processor = DocumentProcessor(upload_folder, temp_folder, use_gpu)
    return document_processor


def get_document_processor() -> Optional[DocumentProcessor]:
    """Get global document processor instance"""
    return document_processor
