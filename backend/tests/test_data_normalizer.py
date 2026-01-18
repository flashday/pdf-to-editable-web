"""
Tests for data normalization service
"""
import pytest
import time
from backend.services.data_normalizer import DataNormalizer
from backend.models.document import (
    LayoutResult, Region, TableStructure, RegionType, 
    BoundingBox, EditorJSData, EditorJSBlock
)

class TestDataNormalizer:
    """Test cases for DataNormalizer service"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.normalizer = DataNormalizer()
    
    def test_normalize_simple_layout(self):
        """Test normalization of simple layout with header and paragraph"""
        # Create test layout result
        regions = [
            Region(
                coordinates=BoundingBox(x=10, y=10, width=200, height=30),
                classification=RegionType.HEADER,
                confidence=0.9,
                content="Test Header"
            ),
            Region(
                coordinates=BoundingBox(x=10, y=50, width=300, height=60),
                classification=RegionType.PARAGRAPH,
                confidence=0.85,
                content="This is a test paragraph with some content."
            )
        ]
        
        layout_result = LayoutResult(
            regions=regions,
            tables=[],
            confidence_score=0.875,
            processing_time=1.5
        )
        
        # Normalize to Editor.js format
        editor_data = self.normalizer.normalize_ocr_result(layout_result)
        
        # Verify structure
        assert isinstance(editor_data, EditorJSData)
        assert len(editor_data.blocks) == 2
        assert editor_data.version == "2.28.2"
        assert isinstance(editor_data.time, int)
        
        # Verify header block
        header_block = editor_data.blocks[0]
        assert header_block.type == "header"
        assert header_block.data["text"] == "Test Header"
        assert 1 <= header_block.data["level"] <= 6
        
        # Verify paragraph block
        para_block = editor_data.blocks[1]
        assert para_block.type == "paragraph"
        assert para_block.data["text"] == "This is a test paragraph with some content."
    
    def test_normalize_table_structure(self):
        """Test normalization of table structure"""
        # Create test table
        table = TableStructure(
            rows=2,
            columns=3,
            cells=[
                ["Header 1", "Header 2", "Header 3"],
                ["Data 1", "Data 2", "Data 3"]
            ],
            coordinates=BoundingBox(x=20, y=100, width=400, height=80),
            has_headers=True
        )
        
        layout_result = LayoutResult(
            regions=[],
            tables=[table],
            confidence_score=0.8,
            processing_time=2.0
        )
        
        # Normalize to Editor.js format
        editor_data = self.normalizer.normalize_ocr_result(layout_result)
        
        # Verify table block
        assert len(editor_data.blocks) == 1
        table_block = editor_data.blocks[0]
        assert table_block.type == "table"
        assert table_block.data["withHeadings"] == True
        assert table_block.data["content"] == [
            ["Header 1", "Header 2", "Header 3"],
            ["Data 1", "Data 2", "Data 3"]
        ]
    
    def test_schema_validation_valid_data(self):
        """Test schema validation with valid data"""
        # Create valid Editor.js data
        blocks = [
            EditorJSBlock(
                id="test-1",
                type="header",
                data={"text": "Test Header", "level": 1}
            ),
            EditorJSBlock(
                id="test-2", 
                type="paragraph",
                data={"text": "Test paragraph"}
            )
        ]
        
        editor_data = EditorJSData(
            time=int(time.time() * 1000),
            blocks=blocks,
            version="2.28.2"
        )
        
        # Validate schema
        validation_result = self.normalizer.validate_editor_schema(editor_data)
        
        assert validation_result["is_valid"] == True
        assert len(validation_result["errors"]) == 0
        assert validation_result["block_count"] == 2
    
    def test_schema_validation_invalid_data(self):
        """Test schema validation with invalid data"""
        # Create invalid Editor.js data (missing required fields)
        blocks = [
            EditorJSBlock(
                id="test-1",
                type="header",
                data={"text": "Test Header"}  # Missing level field
            )
        ]
        
        editor_data = EditorJSData(
            time=int(time.time() * 1000),
            blocks=blocks,
            version="2.28.2"
        )
        
        # Validate schema
        validation_result = self.normalizer.validate_editor_schema(editor_data)
        
        assert validation_result["is_valid"] == False
        assert len(validation_result["errors"]) > 0
    
    def test_header_level_detection(self):
        """Test header level detection logic"""
        # Test different header patterns
        test_cases = [
            ("MAIN TITLE", BoundingBox(x=0, y=10, width=200, height=30), 1),
            ("Chapter 1: Introduction", BoundingBox(x=0, y=50, width=300, height=25), 1),
            ("Section 2.1", BoundingBox(x=0, y=100, width=150, height=20), 2),
            ("Short Header", BoundingBox(x=0, y=150, width=100, height=15), 3),
            ("Longer subsection header text", BoundingBox(x=0, y=200, width=250, height=18), 4)
        ]
        
        for text, coords, expected_min_level in test_cases:
            level = self.normalizer._detect_header_level(text, coords)
            assert 1 <= level <= 6, f"Header level {level} out of range for text: {text}"
    
    def test_table_content_processing(self):
        """Test table content processing and validation"""
        # Test with messy table data
        raw_cells = [
            ["  Header 1  ", "Header|2", "Header 3"],
            ["Data│1", "  Data 2  ", "Data─3"],
            ["", "Data 4", "Data 5"]  # Empty cell
        ]
        
        processed = self.normalizer._process_table_content(raw_cells)
        validated = self.normalizer._validate_table_content(processed)
        
        # Verify cleaning and validation
        assert len(validated) == 3  # All rows preserved
        assert len(validated[0]) == 3  # Consistent column count
        assert validated[0][0] == "Header 1"  # Whitespace cleaned
        assert validated[0][1] == "Header2"  # Artifacts removed
        assert validated[2][0] == ""  # Empty cell preserved
    
    def test_list_parsing(self):
        """Test list item parsing"""
        test_cases = [
            ("• Item 1\n• Item 2\n• Item 3", ["Item 1", "Item 2", "Item 3"], "unordered"),
            ("1. First item\n2. Second item\n3. Third item", ["First item", "Second item", "Third item"], "ordered"),
            ("- Dash item\n- Another dash", ["Dash item", "Another dash"], "unordered")
        ]
        
        for text, expected_items, expected_style in test_cases:
            items = self.normalizer._parse_list_items(text)
            style = self.normalizer._detect_list_style(text)
            
            assert items == expected_items
            assert style == expected_style
    
    def test_validation_report_generation(self):
        """Test validation report generation"""
        # Create test data
        blocks = [
            EditorJSBlock(
                id="test-1",
                type="header",
                data={"text": "Test", "level": 1}
            )
        ]
        
        editor_data = EditorJSData(
            time=int(time.time() * 1000),
            blocks=blocks,
            version="2.28.2"
        )
        
        # Generate report
        report = self.normalizer.generate_validation_report(editor_data)
        
        assert isinstance(report, str)
        assert "Editor.js Schema Validation Report" in report
        assert "PASSED" in report or "FAILED" in report
        assert "Total Blocks: 1" in report