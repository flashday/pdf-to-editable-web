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
            
            # Extract tables
            if any(r.classification.value == 'table' for r in layout_result.regions):
                tables = self.ocr_service.extract_tables(str(image_path), layout_result.regions)
                layout_result.tables = tables
                logger.info(f"Extracted {len(tables)} tables")
            
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
        """Clean up temporary files for a document"""
        try:
            # Clean up extracted page images
            for pattern in [f"{document_id}_page*.png", f"{document_id}_preprocessed*"]:
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
