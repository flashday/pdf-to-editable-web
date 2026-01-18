"""
PDF processing service for multi-page handling and page extraction
"""
import io
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import PyPDF2
from PIL import Image
import fitz  # PyMuPDF for better PDF to image conversion
from backend.services.error_handler import error_handler, ErrorCategory

class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors"""
    pass

class PDFProcessor:
    """Service for handling PDF documents and page extraction"""
    
    @classmethod
    def analyze_pdf(cls, file_path: Path) -> Dict[str, Any]:
        """
        Analyze PDF document to get page count and metadata
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF analysis results
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                page_count = len(pdf_reader.pages)
                
                # Get metadata if available
                metadata = pdf_reader.metadata or {}
                
                return {
                    'page_count': page_count,
                    'is_multi_page': page_count > 1,
                    'metadata': {
                        'title': metadata.get('/Title', ''),
                        'author': metadata.get('/Author', ''),
                        'creator': metadata.get('/Creator', ''),
                        'producer': metadata.get('/Producer', ''),
                        'creation_date': str(metadata.get('/CreationDate', '')),
                        'modification_date': str(metadata.get('/ModDate', ''))
                    }
                }
                
        except Exception as e:
            # Log PDF analysis error with context
            context = {
                'file_path': str(file_path),
                'operation': 'pdf_analysis'
            }
            error_handler.log_error(e, ErrorCategory.PROCESSING_ERROR,
                                  error_handler.get_error_severity(e, ErrorCategory.PROCESSING_ERROR),
                                  context)
            raise PDFProcessingError(f"Failed to analyze PDF: {str(e)}")
    
    @classmethod
    def extract_first_page_as_image(cls, file_path: Path, output_path: Path, dpi: int = 300) -> Tuple[bool, Optional[str]]:
        """
        Extract the first page of PDF as an image for OCR processing
        
        Args:
            file_path: Path to the PDF file
            output_path: Path where the image should be saved
            dpi: Resolution for image extraction
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Use PyMuPDF for better image quality
            pdf_document = fitz.open(str(file_path))
            
            if len(pdf_document) == 0:
                return False, "PDF contains no pages"
            
            # Get the first page
            first_page = pdf_document[0]
            
            # Convert to image with specified DPI
            mat = fitz.Matrix(dpi/72, dpi/72)  # 72 is default DPI
            pix = first_page.get_pixmap(matrix=mat)
            
            # Save as PNG
            pix.save(str(output_path))
            
            pdf_document.close()
            
            return True, None
            
        except Exception as e:
            # Log PDF extraction error with context
            context = {
                'file_path': str(file_path),
                'output_path': str(output_path),
                'dpi': dpi,
                'operation': 'pdf_page_extraction'
            }
            error_handler.log_error(e, ErrorCategory.PROCESSING_ERROR,
                                  error_handler.get_error_severity(e, ErrorCategory.PROCESSING_ERROR),
                                  context)
            return False, f"Failed to extract first page: {str(e)}"
    
    @classmethod
    def get_processing_notification(cls, page_count: int) -> Optional[str]:
        """
        Generate user notification message for multi-page PDFs
        
        Args:
            page_count: Number of pages in the PDF
            
        Returns:
            Notification message if multi-page, None otherwise
        """
        if page_count > 1:
            return (
                f"This PDF contains {page_count} pages. "
                f"Only the first page will be processed and converted to editable format. "
                f"To process additional pages, please upload them as separate files."
            )
        return None
    
    @classmethod
    def validate_pdf_structure(cls, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF file structure and readability
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    return False, "Encrypted PDFs are not supported. Please provide an unencrypted PDF."
                
                # Check if PDF has pages
                if len(pdf_reader.pages) == 0:
                    return False, "PDF contains no pages"
                
                # Try to access the first page to ensure it's readable
                first_page = pdf_reader.pages[0]
                _ = first_page.extract_text()  # This will fail if page is corrupted
                
                return True, None
                
        except PyPDF2.errors.PdfReadError as e:
            # Log PDF read error with context
            context = {
                'file_path': str(file_path),
                'operation': 'pdf_validation',
                'error_type': 'pdf_read_error'
            }
            error_handler.log_error(e, ErrorCategory.PROCESSING_ERROR,
                                  error_handler.get_error_severity(e, ErrorCategory.PROCESSING_ERROR),
                                  context)
            return False, f"PDF file is corrupted or invalid: {str(e)}"
        except Exception as e:
            # Log general PDF validation error
            context = {
                'file_path': str(file_path),
                'operation': 'pdf_validation'
            }
            error_handler.log_error(e, ErrorCategory.PROCESSING_ERROR,
                                  error_handler.get_error_severity(e, ErrorCategory.PROCESSING_ERROR),
                                  context)
            return False, f"Failed to validate PDF: {str(e)}"