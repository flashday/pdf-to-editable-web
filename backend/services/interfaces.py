"""
Core interfaces for document processing pipeline
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.models.document import Document, LayoutResult, EditorJSData

class FileValidatorInterface(ABC):
    """Interface for file validation services"""
    
    @abstractmethod
    def validate_file_type(self, filename: str) -> bool:
        """Validate if file type is supported"""
        pass
    
    @abstractmethod
    def validate_file_size(self, file_size: int) -> bool:
        """Validate if file size is within limits"""
        pass
    
    @abstractmethod
    def validate_file_content(self, file_path: str) -> bool:
        """Validate file content integrity"""
        pass

class OCRServiceInterface(ABC):
    """Interface for OCR processing services"""
    
    @abstractmethod
    def analyze_layout(self, image_path: str) -> LayoutResult:
        """Perform layout analysis on image"""
        pass
    
    @abstractmethod
    def extract_text(self, image_path: str, regions: List) -> List:
        """Extract text from specified regions"""
        pass
    
    @abstractmethod
    def extract_tables(self, image_path: str, regions: List) -> List:
        """Extract table structures from regions"""
        pass

class DataNormalizerInterface(ABC):
    """Interface for data normalization services"""
    
    @abstractmethod
    def normalize_ocr_result(self, layout_result: LayoutResult) -> EditorJSData:
        """Convert OCR results to Editor.js format"""
        pass
    
    @abstractmethod
    def validate_editor_schema(self, editor_data: EditorJSData) -> bool:
        """Validate Editor.js schema compliance"""
        pass

class DocumentProcessorInterface(ABC):
    """Interface for document processing pipeline"""
    
    @abstractmethod
    def process_document(self, document: Document) -> Document:
        """Process document through complete pipeline"""
        pass
    
    @abstractmethod
    def get_processing_status(self, document_id: str) -> Optional[Document]:
        """Get current processing status"""
        pass