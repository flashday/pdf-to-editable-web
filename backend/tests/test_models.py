"""
Unit tests for data models
"""
import pytest
from datetime import datetime
from backend.models.document import (
    Document, ProcessingStatus, RegionType, BoundingBox, 
    Region, TableStructure, LayoutResult, ConfidenceMetrics,
    EditorJSBlock, EditorJSData
)

class TestDocument:
    """Test Document model"""
    
    def test_document_creation(self):
        """Test document creation with defaults"""
        doc = Document()
        
        assert doc.id is not None
        assert len(doc.id) > 0
        assert doc.processing_status == ProcessingStatus.PENDING
        assert isinstance(doc.upload_timestamp, datetime)
        assert doc.conversion_result is None
        assert doc.error_message is None

    def test_document_with_values(self):
        """Test document creation with specific values"""
        doc = Document(
            original_filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            processing_status=ProcessingStatus.COMPLETED
        )
        
        assert doc.original_filename == "test.pdf"
        assert doc.file_type == "pdf"
        assert doc.file_size == 1024
        assert doc.processing_status == ProcessingStatus.COMPLETED

class TestBoundingBox:
    """Test BoundingBox model"""
    
    def test_bounding_box_creation(self):
        """Test bounding box creation"""
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        
        assert bbox.x == 10.0
        assert bbox.y == 20.0
        assert bbox.width == 100.0
        assert bbox.height == 50.0

class TestRegion:
    """Test Region model"""
    
    def test_region_creation(self):
        """Test region creation"""
        bbox = BoundingBox(x=0, y=0, width=100, height=50)
        region = Region(
            coordinates=bbox,
            classification=RegionType.PARAGRAPH,
            confidence=0.95,
            content="Sample text"
        )
        
        assert region.coordinates == bbox
        assert region.classification == RegionType.PARAGRAPH
        assert region.confidence == 0.95
        assert region.content == "Sample text"
        assert region.metadata == {}

class TestEditorJSData:
    """Test Editor.js data structures"""
    
    def test_editor_block_creation(self):
        """Test Editor.js block creation"""
        block = EditorJSBlock(
            id="block-1",
            type="paragraph",
            data={"text": "Sample paragraph"}
        )
        
        assert block.id == "block-1"
        assert block.type == "paragraph"
        assert block.data["text"] == "Sample paragraph"
        assert block.metadata is None

    def test_editor_data_creation(self):
        """Test Editor.js data structure creation"""
        block = EditorJSBlock(
            id="block-1",
            type="paragraph",
            data={"text": "Sample paragraph"}
        )
        
        editor_data = EditorJSData(
            time=1234567890,
            blocks=[block]
        )
        
        assert editor_data.time == 1234567890
        assert len(editor_data.blocks) == 1
        assert editor_data.blocks[0] == block
        assert editor_data.version == "2.28.2"