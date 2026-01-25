"""
PDF processing service for multi-page handling and page extraction
"""
import io
import logging
from typing import Tuple, Optional, Dict, Any
from pathlib import Path
import PyPDF2
from PIL import Image
import fitz  # PyMuPDF for better PDF to image conversion
from backend.services.error_handler import error_handler, ErrorCategory

# Configure logging
logger = logging.getLogger(__name__)

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
            
            # 获取页面尺寸（以点为单位，72点=1英寸）
            page_rect = first_page.rect
            page_width_inches = page_rect.width / 72
            page_height_inches = page_rect.height / 72
            
            # 计算在指定 DPI 下的图像尺寸
            target_width = int(page_width_inches * dpi)
            target_height = int(page_height_inches * dpi)
            
            # 限制最大图像尺寸为 2048 像素（性能优化）
            # 降低此值可以显著减少 OCR 处理时间，同时保持足够的识别精度
            max_dimension = 2048
            if max(target_width, target_height) > max_dimension:
                # 计算缩放比例
                scale = max_dimension / max(target_width, target_height)
                effective_dpi = int(dpi * scale)
                logger.info(f"PDF page is large ({target_width}x{target_height} at {dpi} DPI), "
                           f"reducing to {effective_dpi} DPI to fit within {max_dimension}px limit")
            else:
                effective_dpi = dpi
            
            # Convert to image with effective DPI
            mat = fitz.Matrix(effective_dpi/72, effective_dpi/72)  # 72 is default DPI
            pix = first_page.get_pixmap(matrix=mat)
            
            # Save as PNG
            pix.save(str(output_path))
            
            logger.info(f"Extracted PDF page as image: {pix.width}x{pix.height} pixels")
            
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
    def detect_pdf_type(cls, file_path: Path, min_text_length: int = 50) -> str:
        """
        检测 PDF 类型（文本型/图像型/混合型）
        
        目前仅做日志记录，为后续优化做准备。
        TODO: 后续可根据类型分流处理，文本型 PDF 直接提取文本，跳过 OCR
        
        Args:
            file_path: PDF 文件路径
            min_text_length: 判断为文本型的最小文本长度阈值
            
        Returns:
            'text': 文本型 PDF - 包含可提取的文本层，可直接提取
            'image': 图像型 PDF - 扫描文档，需要 OCR
            'mixed': 混合型 PDF - 部分页面有文本，部分是图像
        """
        try:
            doc = fitz.open(str(file_path))
            text_pages = 0
            image_pages = 0
            page_details = []
            
            # 只检查前 5 页或全部页面（取较小值）
            pages_to_check = min(5, len(doc))
            
            for page_num in range(pages_to_check):
                page = doc[page_num]
                text = page.get_text().strip()
                text_len = len(text)
                
                if text_len >= min_text_length:
                    text_pages += 1
                    page_details.append(f"P{page_num+1}:text({text_len}字符)")
                else:
                    image_pages += 1
                    page_details.append(f"P{page_num+1}:image({text_len}字符)")
            
            doc.close()
            
            # 判断类型
            if text_pages == pages_to_check:
                pdf_type = 'text'
            elif image_pages == pages_to_check:
                pdf_type = 'image'
            else:
                pdf_type = 'mixed'
            
            # 记录日志
            logger.info(f"PDF 类型检测: {pdf_type} | "
                       f"检查页数: {pages_to_check} | "
                       f"文本页: {text_pages}, 图像页: {image_pages} | "
                       f"详情: {', '.join(page_details)}")
            
            # TODO: 后续优化 - 根据类型分流处理
            # if pdf_type == 'text':
            #     # 文本型 PDF 可直接提取文本，跳过 OCR，处理时间 <1 秒
            #     pass
            # else:
            #     # 图像型/混合型 PDF 需要 OCR 处理
            #     pass
            
            return pdf_type
            
        except Exception as e:
            logger.warning(f"PDF 类型检测失败: {e}，默认按图像型处理")
            return 'image'
    
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