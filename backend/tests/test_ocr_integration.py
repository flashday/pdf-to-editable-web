"""
Integration tests for OCR service with the document processing pipeline
"""
import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch
from PIL import Image

from backend.services.ocr_service import PaddleOCRService, OCRProcessingError
from backend.models.document import Document, ProcessingStatus, LayoutResult, Region, BoundingBox, RegionType


class TestOCRIntegration:
    """Integration tests for OCR service"""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            # Create a simple test image
            img = Image.new('RGB', (800, 600), color='white')
            img.save(tmp.name)
            tmp_path = tmp.name
        
        yield tmp_path
        
        # Windows 文件清理：等待文件释放后再删除
        for _ in range(5):
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                break
            except PermissionError:
                time.sleep(0.1)
    
    def test_ocr_service_creation(self):
        """Test that OCR service can be created without PaddleOCR installed"""
        # This should work even without PaddleOCR since we handle ImportError
        try:
            service = PaddleOCRService(use_gpu=False)
            assert service.use_gpu is False
            assert service.lang == 'ch'  # default language
        except OCRProcessingError as e:
            # Expected if PaddleOCR is not installed
            assert "PaddleOCR not installed" in str(e)
    
    def test_image_preprocessing_without_ocr(self, sample_image):
        """Test image preprocessing works independently of OCR engines"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        service.use_gpu = False
        service.lang = 'en'
        service._ocr_engine = None
        service._structure_engine = None
        
        # Test preprocessing - now returns tuple (path, scale_info)
        preprocessed_path, scale_info = service.preprocess_image(sample_image)
        
        # Verify preprocessed image exists and is different
        assert os.path.exists(preprocessed_path)
        assert preprocessed_path != sample_image
        
        # Verify scale_info structure
        assert isinstance(scale_info, dict)
        assert 'original_width' in scale_info
        assert 'original_height' in scale_info
        assert 'scale_x' in scale_info
        assert 'scale_y' in scale_info
        
        # Verify it's a valid image
        with Image.open(preprocessed_path) as img:
            assert img.mode == 'RGB'
            assert img.size[0] <= 2048  # Should be within max dimension
            assert img.size[1] <= 2048
        
        # Clean up
        os.unlink(preprocessed_path)
    
    def test_region_classification_logic(self):
        """Test region classification logic works correctly"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        service.use_gpu = False
        service.lang = 'en'
        
        # Test various text patterns
        test_cases = [
            ("CHAPTER 1: INTRODUCTION", BoundingBox(100, 50, 300, 30), RegionType.HEADER),
            ("This is a regular paragraph of text.", BoundingBox(100, 200, 400, 60), RegionType.PARAGRAPH),
            ("• First item\n• Second item", BoundingBox(100, 300, 300, 80), RegionType.LIST),
            ("1. First point\n2. Second point", BoundingBox(100, 400, 300, 80), RegionType.LIST),
            ("", BoundingBox(100, 500, 200, 100), RegionType.IMAGE),  # Empty content
        ]
        
        for text, bbox, expected_type in test_cases:
            result = service._classify_region(text, bbox)
            assert result == expected_type, f"Failed for text: '{text}'"
    
    def test_confidence_metrics_calculation(self):
        """Test confidence metrics calculation with various scenarios"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        
        # Test with empty regions
        empty_metrics = service._calculate_confidence_metrics([])
        assert empty_metrics['overall'] == 0.0
        assert empty_metrics['region_count'] == 0
        
        # Test with mixed confidence regions
        regions = [
            Region(BoundingBox(0, 0, 100, 50), RegionType.HEADER, 0.95, "Header"),
            Region(BoundingBox(0, 50, 100, 50), RegionType.PARAGRAPH, 0.85, "Paragraph"),
            Region(BoundingBox(0, 100, 100, 50), RegionType.LIST, 0.75, "List item"),
            Region(BoundingBox(0, 150, 100, 50), RegionType.TABLE, 0.65, "Table cell")
        ]
        
        metrics = service._calculate_confidence_metrics(regions)
        
        assert metrics['region_count'] == 4
        assert 0 <= metrics['overall'] <= 1
        assert 0 <= metrics['text_confidence'] <= 1
        assert 0 <= metrics['layout_confidence'] <= 1
        
        # Text confidence should be average of individual confidences
        expected_text_confidence = (0.95 + 0.85 + 0.75 + 0.65) / 4
        assert abs(metrics['text_confidence'] - expected_text_confidence) < 0.01
    
    def test_reading_order_sorting(self):
        """Test that regions are sorted in correct reading order"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        
        # Create regions in random order
        regions = [
            Region(BoundingBox(200, 100, 100, 50), RegionType.PARAGRAPH, 0.8, "Middle Right"),
            Region(BoundingBox(50, 50, 100, 50), RegionType.HEADER, 0.9, "Top Left"),
            Region(BoundingBox(50, 100, 100, 50), RegionType.PARAGRAPH, 0.8, "Middle Left"),
            Region(BoundingBox(200, 50, 100, 50), RegionType.HEADER, 0.9, "Top Right"),
            Region(BoundingBox(50, 150, 100, 50), RegionType.PARAGRAPH, 0.8, "Bottom Left")
        ]
        
        sorted_regions = service._sort_regions_by_reading_order(regions)
        
        # Verify reading order: top row (left to right), then middle row, then bottom
        expected_order = ["Top Left", "Top Right", "Middle Left", "Middle Right", "Bottom Left"]
        actual_order = [region.content for region in sorted_regions]
        
        assert actual_order == expected_order
    
    def test_layout_confidence_calculation(self):
        """Test layout confidence calculation with different region distributions"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        
        # Test with diverse region types (should have higher confidence)
        diverse_regions = [
            Region(BoundingBox(0, 0, 200, 50), RegionType.HEADER, 0.9, "Good header content"),
            Region(BoundingBox(0, 50, 400, 100), RegionType.PARAGRAPH, 0.8, "Good paragraph content"),
            Region(BoundingBox(0, 150, 300, 80), RegionType.LIST, 0.85, "Good list content"),
            Region(BoundingBox(0, 230, 350, 120), RegionType.TABLE, 0.75, "Good table content")
        ]
        
        diverse_confidence = service._calculate_layout_confidence(diverse_regions)
        
        # Test with only one type of region (should have lower confidence)
        uniform_regions = [
            Region(BoundingBox(0, 0, 400, 50), RegionType.PARAGRAPH, 0.8, "Para 1"),
            Region(BoundingBox(0, 50, 400, 50), RegionType.PARAGRAPH, 0.8, "Para 2"),
            Region(BoundingBox(0, 100, 400, 50), RegionType.PARAGRAPH, 0.8, "Para 3")
        ]
        
        uniform_confidence = service._calculate_layout_confidence(uniform_regions)
        
        # Diverse layout should have higher confidence than uniform
        assert diverse_confidence > uniform_confidence
        assert 0 <= diverse_confidence <= 1
        assert 0 <= uniform_confidence <= 1
    
    def test_error_handling_without_engines(self):
        """Test error handling when OCR engines are not available"""
        service = PaddleOCRService.__new__(PaddleOCRService)
        service._ocr_engine = None
        service._structure_engine = None
        
        # Should raise appropriate errors
        with pytest.raises(OCRProcessingError, match="Structure engine not initialized"):
            service.analyze_layout("dummy_path.jpg")
        
        with pytest.raises(OCRProcessingError, match="OCR engine not initialized"):
            service.extract_text("dummy_path.jpg", [])
        
        with pytest.raises(OCRProcessingError, match="Structure engine not initialized"):
            service.extract_tables("dummy_path.jpg", [])
    
    def test_document_integration_readiness(self):
        """Test that OCR service integrates properly with Document model"""
        from backend.models.document import Document, ProcessingStatus
        
        # Create a document
        doc = Document(
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            processing_status=ProcessingStatus.PENDING
        )
        
        # Verify document can be created and has expected fields
        assert doc.id is not None
        assert doc.processing_status == ProcessingStatus.PENDING
        assert doc.conversion_result is None
        assert doc.confidence_metrics is None
        
        # Test that LayoutResult can be created with OCR service output format
        regions = [
            Region(BoundingBox(0, 0, 100, 50), RegionType.HEADER, 0.9, "Test Header")
        ]
        
        layout_result = LayoutResult(
            regions=regions,
            tables=[],
            confidence_score=0.9,
            processing_time=1.5
        )
        
        assert len(layout_result.regions) == 1
        assert layout_result.confidence_score == 0.9
        assert layout_result.processing_time == 1.5