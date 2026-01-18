"""
File validation service for document uploads
"""
import os
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import magic
from pathlib import Path
from backend.services.error_handler import error_handler, ErrorCategory

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class FileValidator:
    """File validation service for uploads"""
    
    # Supported file types with their MIME types
    SUPPORTED_TYPES = {
        'pdf': ['application/pdf'],
        'jpg': ['image/jpeg'],
        'jpeg': ['image/jpeg'], 
        'png': ['image/png']
    }
    
    # Maximum file size (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    @classmethod
    def validate_file(cls, file: FileStorage) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file for type, size, and format
        
        Args:
            file: Uploaded file from Flask request
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not file or not file.filename:
                raise ValidationError("No file provided")
            
            # Validate filename
            # Keep original filename for display, use secure_filename for storage
            original_filename = file.filename
            filename = secure_filename(file.filename)
            
            # If secure_filename returns empty (e.g., all Chinese characters),
            # use a fallback based on file extension
            if not filename:
                file_ext = cls._get_file_extension(original_filename)
                if file_ext:
                    filename = f"document.{file_ext}"
                else:
                    raise ValidationError("Invalid filename")
            
            # Check file extension
            file_ext = cls._get_file_extension(filename)
            if file_ext not in cls.SUPPORTED_TYPES:
                supported_formats = ', '.join(cls.SUPPORTED_TYPES.keys()).upper()
                raise ValidationError(f"Unsupported file type. Supported formats: {supported_formats}")
            
            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            if file_size > cls.MAX_FILE_SIZE:
                size_mb = cls.MAX_FILE_SIZE / (1024 * 1024)
                raise ValidationError(f"File size exceeds {size_mb}MB limit")
            
            if file_size == 0:
                raise ValidationError("File is empty")
            
            # Validate MIME type
            file_content = file.read(1024)  # Read first 1KB for MIME detection
            file.seek(0)  # Reset file pointer
            
            try:
                mime_type = magic.from_buffer(file_content, mime=True)
                if mime_type not in cls.SUPPORTED_TYPES[file_ext]:
                    raise ValidationError(f"File content does not match extension. Expected {file_ext.upper()} format")
            except Exception:
                # If magic fails, continue with extension-based validation
                pass
            
            return True, None
            
        except ValidationError as e:
            # Log validation error with context
            context = {
                'filename': file.filename if file else None,
                'file_size': file_size if 'file_size' in locals() else None,
                'operation': 'file_validation'
            }
            error_handler.log_error(e, ErrorCategory.VALIDATION_ERROR, 
                                  error_handler.get_error_severity(e, ErrorCategory.VALIDATION_ERROR),
                                  context)
            return False, str(e)
        except Exception as e:
            # Log unexpected errors
            context = {
                'filename': file.filename if file else None,
                'operation': 'file_validation'
            }
            error_handler.log_error(e, ErrorCategory.SYSTEM_ERROR,
                                  error_handler.get_error_severity(e, ErrorCategory.SYSTEM_ERROR),
                                  context)
            return False, f"Validation error: {str(e)}"
    
    @classmethod
    def _get_file_extension(cls, filename: str) -> str:
        """Extract file extension from filename"""
        if not filename:
            return ''
        # Handle both secure and original filenames
        ext = Path(filename).suffix.lower().lstrip('.')
        return ext
    
    @classmethod
    def get_file_info(cls, file: FileStorage) -> dict:
        """Get file information for processing"""
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        filename = secure_filename(file.filename)
        file_ext = cls._get_file_extension(filename)
        
        return {
            'filename': filename,
            'original_filename': file.filename,
            'file_type': file_ext,
            'file_size': file_size,
            'mime_type': file.content_type
        }