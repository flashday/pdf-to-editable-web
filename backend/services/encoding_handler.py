"""
Character encoding handling service for text processing
Implements Unicode and special character processing with encoding detection and conversion
"""
import logging
import unicodedata
import chardet
from typing import Optional, Dict, Any, List, Tuple
import re

logger = logging.getLogger(__name__)

class EncodingError(Exception):
    """Custom exception for encoding-related errors"""
    pass

class CharacterEncodingHandler:
    """
    Service for handling character encoding, Unicode processing, and special character management
    """
    
    def __init__(self):
        """Initialize the encoding handler with configuration"""
        # Common encoding fallbacks in order of preference
        self.encoding_fallbacks = [
            'utf-8',
            'utf-16',
            'latin-1',
            'cp1252',  # Windows-1252
            'iso-8859-1',
            'ascii'
        ]
        
        # Characters that commonly cause issues in OCR
        self.problematic_chars = {
            # Common OCR misreads
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
            '\u00a0': ' ',  # Non-breaking space
            '\u00ad': '',   # Soft hyphen (remove)
            '\ufeff': '',   # Byte order mark (remove)
        }
        
        # Unicode categories to preserve
        self.preserve_categories = {
            'Lu', 'Ll', 'Lt', 'Lm', 'Lo',  # Letters
            'Nd', 'Nl', 'No',               # Numbers
            'Pc', 'Pd', 'Ps', 'Pe', 'Pi', 'Pf', 'Po',  # Punctuation
            'Sm', 'Sc', 'Sk', 'So',         # Symbols
            'Zs', 'Zl', 'Zp'               # Separators
        }
    
    def detect_encoding(self, text_bytes: bytes) -> Dict[str, Any]:
        """
        Detect character encoding of byte data
        
        Args:
            text_bytes: Raw byte data to analyze
            
        Returns:
            Dictionary containing encoding information
        """
        try:
            # Use chardet for encoding detection
            detection_result = chardet.detect(text_bytes)
            
            if not detection_result or not detection_result.get('encoding'):
                logger.warning("Encoding detection failed, using UTF-8 as fallback")
                return {
                    'encoding': 'utf-8',
                    'confidence': 0.5,
                    'language': None,
                    'detection_method': 'fallback'
                }
            
            encoding = detection_result['encoding'].lower()
            confidence = detection_result.get('confidence', 0.0)
            
            # Validate detected encoding by attempting decode
            try:
                text_bytes.decode(encoding)
                detection_method = 'chardet'
            except (UnicodeDecodeError, LookupError):
                # Try fallback encodings
                encoding, confidence = self._try_fallback_encodings(text_bytes)
                detection_method = 'fallback'
            
            return {
                'encoding': encoding,
                'confidence': confidence,
                'language': detection_result.get('language'),
                'detection_method': detection_method
            }
            
        except Exception as e:
            logger.error(f"Encoding detection failed: {e}")
            return {
                'encoding': 'utf-8',
                'confidence': 0.3,
                'language': None,
                'detection_method': 'error_fallback',
                'error': str(e)
            }
    
    def _try_fallback_encodings(self, text_bytes: bytes) -> Tuple[str, float]:
        """
        Try fallback encodings when primary detection fails
        
        Args:
            text_bytes: Raw byte data
            
        Returns:
            Tuple of (encoding, confidence)
        """
        for encoding in self.encoding_fallbacks:
            try:
                text_bytes.decode(encoding)
                logger.info(f"Successfully decoded with fallback encoding: {encoding}")
                return encoding, 0.7
            except (UnicodeDecodeError, LookupError):
                continue
        
        # Last resort - use utf-8 with error handling
        logger.warning("All encoding attempts failed, using UTF-8 with error replacement")
        return 'utf-8', 0.3
    
    def convert_to_utf8(self, text_data: bytes, source_encoding: Optional[str] = None) -> str:
        """
        Convert text data to UTF-8 string with encoding detection and error handling
        
        Args:
            text_data: Raw byte data to convert
            source_encoding: Known source encoding (optional)
            
        Returns:
            UTF-8 decoded string
            
        Raises:
            EncodingError: If conversion fails completely
        """
        try:
            # If source encoding is provided, try it first
            if source_encoding:
                try:
                    decoded_text = text_data.decode(source_encoding)
                    logger.debug(f"Successfully decoded with provided encoding: {source_encoding}")
                    return self.normalize_unicode(decoded_text)
                except (UnicodeDecodeError, LookupError) as e:
                    logger.warning(f"Provided encoding {source_encoding} failed: {e}")
            
            # Detect encoding automatically
            encoding_info = self.detect_encoding(text_data)
            detected_encoding = encoding_info['encoding']
            
            try:
                # Attempt decode with detected encoding
                decoded_text = text_data.decode(detected_encoding)
                logger.info(f"Successfully decoded with detected encoding: {detected_encoding}")
                return self.normalize_unicode(decoded_text)
                
            except UnicodeDecodeError as e:
                logger.warning(f"Detected encoding {detected_encoding} failed: {e}")
                
                # Try decode with error handling
                decoded_text = text_data.decode(detected_encoding, errors='replace')
                logger.warning("Used error replacement during decoding")
                return self.normalize_unicode(decoded_text)
            
        except Exception as e:
            logger.error(f"Text conversion to UTF-8 failed: {e}")
            raise EncodingError(f"Failed to convert text to UTF-8: {e}")
    
    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode text for consistent processing
        
        Args:
            text: Input text to normalize
            
        Returns:
            Normalized Unicode text
        """
        try:
            # Apply Unicode normalization (NFC - Canonical Decomposition followed by Canonical Composition)
            normalized_text = unicodedata.normalize('NFC', text)
            
            # Handle problematic characters
            cleaned_text = self._clean_problematic_characters(normalized_text)
            
            # Remove or replace control characters
            processed_text = self._process_control_characters(cleaned_text)
            
            # Validate final result
            validated_text = self._validate_unicode_text(processed_text)
            
            return validated_text
            
        except Exception as e:
            logger.error(f"Unicode normalization failed: {e}")
            # Return original text if normalization fails
            return text
    
    def _clean_problematic_characters(self, text: str) -> str:
        """
        Clean and replace problematic characters commonly found in OCR results
        
        Args:
            text: Input text with potential problematic characters
            
        Returns:
            Text with problematic characters cleaned
        """
        cleaned_text = text
        
        # Replace known problematic characters
        for problematic_char, replacement in self.problematic_chars.items():
            if problematic_char in cleaned_text:
                cleaned_text = cleaned_text.replace(problematic_char, replacement)
                logger.debug(f"Replaced problematic character: {repr(problematic_char)} -> {repr(replacement)}")
        
        return cleaned_text
    
    def _process_control_characters(self, text: str) -> str:
        """
        Process control characters and whitespace
        
        Args:
            text: Input text to process
            
        Returns:
            Text with control characters processed
        """
        # Remove most control characters but preserve important ones
        processed_chars = []
        
        for char in text:
            category = unicodedata.category(char)
            
            # Preserve characters in allowed categories
            if category in self.preserve_categories:
                processed_chars.append(char)
            # Preserve important control characters
            elif char in ['\n', '\r', '\t']:
                processed_chars.append(char)
            # Remove other control characters
            elif category.startswith('C'):
                logger.debug(f"Removed control character: {repr(char)} (category: {category})")
                continue
            else:
                # Keep other characters
                processed_chars.append(char)
        
        return ''.join(processed_chars)
    
    def _validate_unicode_text(self, text: str) -> str:
        """
        Validate Unicode text and handle any remaining issues
        
        Args:
            text: Text to validate
            
        Returns:
            Validated text
        """
        try:
            # Test encoding/decoding roundtrip
            encoded = text.encode('utf-8')
            decoded = encoded.decode('utf-8')
            
            if decoded != text:
                logger.warning("Unicode validation detected encoding issues")
            
            return decoded
            
        except UnicodeError as e:
            logger.error(f"Unicode validation failed: {e}")
            # Try to fix by re-encoding with error handling
            try:
                fixed_text = text.encode('utf-8', errors='replace').decode('utf-8')
                logger.warning("Applied error replacement during Unicode validation")
                return fixed_text
            except Exception:
                logger.error("Unicode validation completely failed, returning original text")
                return text
    
    def detect_corruption(self, text: str) -> Dict[str, Any]:
        """
        Detect potential character corruption in text
        
        Args:
            text: Text to analyze for corruption
            
        Returns:
            Dictionary containing corruption analysis
        """
        corruption_indicators = {
            'replacement_chars': 0,
            'invalid_sequences': 0,
            'suspicious_patterns': [],
            'encoding_issues': [],
            'is_corrupted': False,
            'confidence': 1.0
        }
        
        try:
            # Count replacement characters
            replacement_chars = text.count('\ufffd')  # Unicode replacement character
            corruption_indicators['replacement_chars'] = replacement_chars
            
            # Look for suspicious character patterns
            suspicious_patterns = [
                r'[^\x00-\x7F]{3,}',  # Long sequences of non-ASCII
                r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]',  # Control characters
                r'�+',  # Replacement character sequences
            ]
            
            for pattern in suspicious_patterns:
                matches = re.findall(pattern, text)
                if matches:
                    corruption_indicators['suspicious_patterns'].extend(matches)
            
            # Check for encoding issues
            try:
                # Test various encoding roundtrips
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        encoded = text.encode(encoding)
                        decoded = encoded.decode(encoding)
                        if decoded != text:
                            corruption_indicators['encoding_issues'].append(f"Roundtrip failed for {encoding}")
                    except UnicodeError:
                        corruption_indicators['encoding_issues'].append(f"Cannot encode/decode with {encoding}")
            except Exception as e:
                corruption_indicators['encoding_issues'].append(f"Encoding test failed: {e}")
            
            # Calculate corruption confidence
            total_issues = (
                replacement_chars +
                len(corruption_indicators['suspicious_patterns']) +
                len(corruption_indicators['encoding_issues'])
            )
            
            if total_issues > 0:
                corruption_indicators['is_corrupted'] = True
                # Reduce confidence based on number of issues
                corruption_indicators['confidence'] = max(0.1, 1.0 - (total_issues * 0.1))
            
            return corruption_indicators
            
        except Exception as e:
            logger.error(f"Corruption detection failed: {e}")
            return {
                'replacement_chars': 0,
                'invalid_sequences': 0,
                'suspicious_patterns': [],
                'encoding_issues': [f"Detection failed: {e}"],
                'is_corrupted': True,
                'confidence': 0.1
            }
    
    def fix_common_ocr_errors(self, text: str) -> str:
        """
        Fix common OCR character recognition errors
        
        Args:
            text: Text with potential OCR errors
            
        Returns:
            Text with common OCR errors corrected
        """
        try:
            fixed_text = text
            
            # Common OCR character substitutions
            ocr_fixes = {
                # Number/letter confusion
                r'\b0(?=[a-zA-Z])': 'O',  # 0 -> O at word boundaries
                r'\b1(?=[a-zA-Z])': 'I',  # 1 -> I at word boundaries
                r'(?<=[a-zA-Z])0\b': 'O',  # 0 -> O at word endings
                r'(?<=[a-zA-Z])1\b': 'l',  # 1 -> l at word endings
                
                # Common character misreads
                r'rn': 'm',  # rn -> m (common OCR error)
                r'cl': 'd',  # cl -> d in some contexts
                r'vv': 'w',  # vv -> w
                
                # Punctuation fixes
                r',,': ',',   # Double commas
                r'\.\.': '.', # Double periods (not ellipsis)
                r'\s+': ' ',  # Multiple spaces to single space
            }
            
            for pattern, replacement in ocr_fixes.items():
                fixed_text = re.sub(pattern, replacement, fixed_text)
            
            # Clean up whitespace
            fixed_text = re.sub(r'\s+', ' ', fixed_text).strip()
            
            return fixed_text
            
        except Exception as e:
            logger.error(f"OCR error fixing failed: {e}")
            return text
    
    def validate_text_integrity(self, original_text: str, processed_text: str) -> Dict[str, Any]:
        """
        Validate that text processing preserved content integrity
        
        Args:
            original_text: Original text before processing
            processed_text: Text after processing
            
        Returns:
            Dictionary containing integrity validation results
        """
        integrity_report = {
            'length_change': 0,
            'character_changes': 0,
            'content_preserved': True,
            'significant_changes': [],
            'integrity_score': 1.0
        }
        
        try:
            # Calculate length change
            original_len = len(original_text)
            processed_len = len(processed_text)
            integrity_report['length_change'] = processed_len - original_len
            
            # Count character differences
            min_len = min(original_len, processed_len)
            char_changes = 0
            
            for i in range(min_len):
                if original_text[i] != processed_text[i]:
                    char_changes += 1
            
            # Add length difference to character changes
            char_changes += abs(original_len - processed_len)
            integrity_report['character_changes'] = char_changes
            
            # Detect significant changes
            if abs(integrity_report['length_change']) > original_len * 0.1:  # More than 10% length change
                integrity_report['significant_changes'].append(f"Large length change: {integrity_report['length_change']}")
            
            if char_changes > original_len * 0.05:  # More than 5% character changes
                integrity_report['significant_changes'].append(f"High character change rate: {char_changes}/{original_len}")
            
            # Calculate integrity score
            if original_len > 0:
                change_ratio = char_changes / original_len
                integrity_report['integrity_score'] = max(0.0, 1.0 - change_ratio)
            
            # Determine if content is preserved
            if integrity_report['integrity_score'] < 0.9:
                integrity_report['content_preserved'] = False
            
            return integrity_report
            
        except Exception as e:
            logger.error(f"Text integrity validation failed: {e}")
            return {
                'length_change': 0,
                'character_changes': 0,
                'content_preserved': False,
                'significant_changes': [f"Validation failed: {e}"],
                'integrity_score': 0.0
            }

# Global instance for easy access
encoding_handler = CharacterEncodingHandler()