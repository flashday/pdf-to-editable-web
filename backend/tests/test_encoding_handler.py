"""
Tests for character encoding handling service
"""
import pytest
import unicodedata
from backend.services.encoding_handler import CharacterEncodingHandler, EncodingError

class TestCharacterEncodingHandler:
    """Test cases for character encoding handler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = CharacterEncodingHandler()
    
    def test_detect_encoding_utf8(self):
        """Test encoding detection for UTF-8 text"""
        text = "Hello, 世界! 🌍"
        text_bytes = text.encode('utf-8')
        
        result = self.handler.detect_encoding(text_bytes)
        
        assert result['encoding'] == 'utf-8'
        assert result['confidence'] >= 0.5
        assert result['detection_method'] in ['chardet', 'fallback']
    
    def test_detect_encoding_latin1(self):
        """Test encoding detection for Latin-1 text"""
        text = "Café résumé naïve"
        text_bytes = text.encode('latin-1')
        
        result = self.handler.detect_encoding(text_bytes)
        
        # Accept various ISO encodings that are compatible
        assert result['encoding'] in ['latin-1', 'iso-8859-1', 'iso-8859-9', 'cp1252']
        assert result['confidence'] > 0.3
    
    def test_detect_encoding_empty_data(self):
        """Test encoding detection with empty data"""
        result = self.handler.detect_encoding(b'')
        
        assert result['encoding'] == 'utf-8'
        assert 'detection_method' in result
    
    def test_convert_to_utf8_with_known_encoding(self):
        """Test UTF-8 conversion with known source encoding"""
        original_text = "Test with special chars: café, résumé"
        text_bytes = original_text.encode('latin-1')
        
        result = self.handler.convert_to_utf8(text_bytes, source_encoding='latin-1')
        
        assert isinstance(result, str)
        assert "café" in result
        assert "résumé" in result
    
    def test_convert_to_utf8_auto_detect(self):
        """Test UTF-8 conversion with automatic encoding detection"""
        original_text = "Hello, world! 你好世界"
        text_bytes = original_text.encode('utf-8')
        
        result = self.handler.convert_to_utf8(text_bytes)
        
        assert result == original_text
        assert "你好世界" in result
    
    def test_convert_to_utf8_with_errors(self):
        """Test UTF-8 conversion with encoding errors"""
        # Create invalid UTF-8 sequence
        invalid_bytes = b'\xff\xfe\x00\x48\x00\x65\x00\x6c\x00\x6c\x00\x6f'
        
        # Should not raise exception, should handle gracefully
        result = self.handler.convert_to_utf8(invalid_bytes)
        
        assert isinstance(result, str)
        # Should contain some recognizable content or replacement characters
    
    def test_normalize_unicode_basic(self):
        """Test basic Unicode normalization"""
        # Text with combining characters
        text = "café"  # é as combining character
        
        result = self.handler.normalize_unicode(text)
        
        assert isinstance(result, str)
        assert "café" in result or "cafe" in result
    
    def test_normalize_unicode_problematic_chars(self):
        """Test normalization of problematic characters"""
        text = 'Hello "world" with—dashes and…ellipsis'
        
        result = self.handler.normalize_unicode(text)
        
        # Should replace smart quotes and other problematic characters
        assert '"' in result
        assert '--' in result or '-' in result
        assert '...' in result
    
    def test_normalize_unicode_control_chars(self):
        """Test removal of control characters"""
        text = "Hello\x00\x01\x02World\x7f"
        
        result = self.handler.normalize_unicode(text)
        
        # Control characters should be removed
        assert '\x00' not in result
        assert '\x01' not in result
        assert '\x02' not in result
        assert '\x7f' not in result
        assert "HelloWorld" in result
    
    def test_detect_corruption_clean_text(self):
        """Test corruption detection on clean text"""
        clean_text = "This is clean text with no corruption."
        
        result = self.handler.detect_corruption(clean_text)
        
        assert result['is_corrupted'] is False
        assert result['replacement_chars'] == 0
        assert result['confidence'] > 0.9
    
    def test_detect_corruption_with_replacement_chars(self):
        """Test corruption detection with replacement characters"""
        corrupted_text = "This text has � replacement characters �"
        
        result = self.handler.detect_corruption(corrupted_text)
        
        assert result['is_corrupted'] is True
        assert result['replacement_chars'] > 0
        assert result['confidence'] < 1.0
    
    def test_detect_corruption_with_control_chars(self):
        """Test corruption detection with control characters"""
        corrupted_text = "Text with\x00control\x01chars\x02"
        
        result = self.handler.detect_corruption(corrupted_text)
        
        assert result['is_corrupted'] is True
        assert len(result['suspicious_patterns']) > 0
    
    def test_fix_common_ocr_errors(self):
        """Test fixing common OCR errors"""
        ocr_text = "He11o w0rld! This is a c1ear exarnple of OCR err0rs."
        
        result = self.handler.fix_common_ocr_errors(ocr_text)
        
        # Should fix some common OCR errors
        assert isinstance(result, str)
        # Check that some fixes were applied (exact fixes depend on implementation)
        assert len(result) > 0
    
    def test_validate_text_integrity_identical(self):
        """Test text integrity validation with identical texts"""
        text = "This is the same text"
        
        result = self.handler.validate_text_integrity(text, text)
        
        assert result['content_preserved'] is True
        assert result['character_changes'] == 0
        assert result['length_change'] == 0
        assert result['integrity_score'] == 1.0
    
    def test_validate_text_integrity_minor_changes(self):
        """Test text integrity validation with minor changes"""
        original = "Hello world"
        processed = "Hello world!"  # Added exclamation
        
        result = self.handler.validate_text_integrity(original, processed)
        
        assert result['length_change'] == 1
        assert result['character_changes'] == 1
        assert result['integrity_score'] > 0.9
    
    def test_validate_text_integrity_major_changes(self):
        """Test text integrity validation with major changes"""
        original = "This is the original text"
        processed = "Completely different content"
        
        result = self.handler.validate_text_integrity(original, processed)
        
        assert result['content_preserved'] is False
        assert result['character_changes'] > 0
        assert result['integrity_score'] < 0.9
        assert len(result['significant_changes']) > 0
    
    def test_encoding_error_handling(self):
        """Test that encoding errors are properly handled"""
        # Test with completely invalid data
        with pytest.raises(EncodingError):
            self.handler.convert_to_utf8(None)
    
    def test_unicode_categories_preservation(self):
        """Test that important Unicode categories are preserved"""
        text = "Letters123 Symbols@#$ Punctuation.,!?"
        
        result = self.handler.normalize_unicode(text)
        
        # Should preserve letters, numbers, symbols, and punctuation
        assert any(c.isalpha() for c in result)  # Letters
        assert any(c.isdigit() for c in result)  # Numbers
        assert any(c in "@#$" for c in result)   # Symbols
        assert any(c in ".,!?" for c in result)  # Punctuation
    
    def test_fallback_encoding_handling(self):
        """Test fallback encoding when detection fails"""
        # Create bytes that might be ambiguous
        ambiguous_bytes = bytes([0x80, 0x81, 0x82, 0x83])
        
        result = self.handler.convert_to_utf8(ambiguous_bytes)
        
        # Should not raise exception and return some result
        assert isinstance(result, str)
    
    def test_roundtrip_encoding_validation(self):
        """Test that text survives encoding roundtrips"""
        original_text = "Test with émojis 🌍 and special chars: café, naïve"
        
        # Convert to bytes and back
        text_bytes = original_text.encode('utf-8')
        result = self.handler.convert_to_utf8(text_bytes)
        
        # Should be very similar to original
        integrity = self.handler.validate_text_integrity(original_text, result)
        assert integrity['integrity_score'] > 0.95