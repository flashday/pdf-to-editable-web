"""
Integration tests for complete OCR to Editor.js conversion workflow
"""
import pytest
import json
from backend.services.data_normalizer import DataNormalizer
from backend.services.schema_validator import EditorJSSchemaValidator
from backend.models.document import (
    LayoutResult, Region, TableStructure, RegionType, BoundingBox
)

class TestDataConversionIntegration:
    """Integration tests for complete data conversion workflow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.normalizer = DataNormalizer()
        self.validator = EditorJSSchemaValidator()
    
    def test_complete_document_conversion(self):
        """Test complete document conversion from OCR to Editor.js"""
        # Create a complex layout result simulating real OCR output
        regions = [
            # Document title
            Region(
                coordinates=BoundingBox(x=50, y=20, width=400, height=40),
                classification=RegionType.HEADER,
                confidence=0.95,
                content="Document Processing System"
            ),
            # Introduction paragraph
            Region(
                coordinates=BoundingBox(x=50, y=80, width=500, height=60),
                classification=RegionType.PARAGRAPH,
                confidence=0.88,
                content="This document describes the implementation of a PDF to editable web layout system using OCR technology."
            ),
            # Section header
            Region(
                coordinates=BoundingBox(x=50, y=160, width=300, height=25),
                classification=RegionType.HEADER,
                confidence=0.92,
                content="System Architecture"
            ),
            # List of components
            Region(
                coordinates=BoundingBox(x=70, y=200, width=450, height=80),
                classification=RegionType.LIST,
                confidence=0.85,
                content="• OCR Processing Engine\n• Data Normalization Service\n• Editor.js Frontend\n• Schema Validation"
            ),
            # Another paragraph
            Region(
                coordinates=BoundingBox(x=50, y=300, width=480, height=40),
                classification=RegionType.PARAGRAPH,
                confidence=0.87,
                content="The system processes documents through multiple stages to ensure accuracy and compatibility."
            )
        ]
        
        # Add a table structure
        table = TableStructure(
            rows=3,
            columns=2,
            cells=[
                ["Component", "Technology"],
                ["Backend", "Python + PaddleOCR"],
                ["Frontend", "JavaScript + Editor.js"]
            ],
            coordinates=BoundingBox(x=50, y=360, width=300, height=90),
            has_headers=True
        )
        
        layout_result = LayoutResult(
            regions=regions,
            tables=[table],
            confidence_score=0.89,
            processing_time=3.2
        )
        
        # Convert to Editor.js format
        editor_data = self.normalizer.normalize_ocr_result(layout_result)
        
        # Verify conversion results
        assert len(editor_data.blocks) == 6  # 5 regions + 1 table
        
        # Verify block types and order
        expected_types = ["header", "paragraph", "header", "list", "paragraph", "table"]
        actual_types = [block.type for block in editor_data.blocks]
        assert actual_types == expected_types
        
        # Verify specific content
        title_block = editor_data.blocks[0]
        assert title_block.data["text"] == "Document Processing System"
        assert title_block.data["level"] == 1  # Should be detected as main title
        
        list_block = editor_data.blocks[3]
        assert list_block.data["style"] == "unordered"
        assert len(list_block.data["items"]) == 4
        assert "OCR Processing Engine" in list_block.data["items"]
        
        table_block = editor_data.blocks[5]
        assert table_block.data["withHeadings"] == True
        assert len(table_block.data["content"]) == 3
        assert table_block.data["content"][0] == ["Component", "Technology"]
        
        # Validate schema compliance
        validation_result = self.normalizer.validate_editor_schema(editor_data)
        assert validation_result["is_valid"] == True
        assert len(validation_result["errors"]) == 0
        
        # Test JSON serialization
        self._test_json_serialization(editor_data)
    
    def test_edge_cases_handling(self):
        """Test handling of edge cases in conversion"""
        # Test with empty content
        empty_regions = [
            Region(
                coordinates=BoundingBox(x=0, y=0, width=100, height=20),
                classification=RegionType.PARAGRAPH,
                confidence=0.5,
                content=""  # Empty content
            ),
            Region(
                coordinates=BoundingBox(x=0, y=30, width=100, height=20),
                classification=RegionType.PARAGRAPH,
                confidence=0.7,
                content="   "  # Whitespace only
            )
        ]
        
        layout_result = LayoutResult(
            regions=empty_regions,
            tables=[],
            confidence_score=0.6,
            processing_time=1.0
        )
        
        editor_data = self.normalizer.normalize_ocr_result(layout_result)
        
        # Should filter out empty content
        assert len(editor_data.blocks) == 0
        
        # Test with malformed table
        malformed_table = TableStructure(
            rows=2,
            columns=2,
            cells=[
                ["A", "B"],
                ["C"]  # Missing cell
            ],
            coordinates=BoundingBox(x=0, y=0, width=100, height=50),
            has_headers=False
        )
        
        layout_result = LayoutResult(
            regions=[],
            tables=[malformed_table],
            confidence_score=0.5,
            processing_time=1.0
        )
        
        editor_data = self.normalizer.normalize_ocr_result(layout_result)
        
        # Should normalize table structure
        assert len(editor_data.blocks) == 1
        table_block = editor_data.blocks[0]
        assert len(table_block.data["content"][1]) == 2  # Should pad missing cell
        assert table_block.data["content"][1][1] == ""  # Empty cell
    
    def test_confidence_metadata_preservation(self):
        """Test that confidence scores and metadata are preserved"""
        region = Region(
            coordinates=BoundingBox(x=10, y=10, width=200, height=30),
            classification=RegionType.HEADER,
            confidence=0.75,
            content="Low Confidence Header"
        )
        
        layout_result = LayoutResult(
            regions=[region],
            tables=[],
            confidence_score=0.75,
            processing_time=1.5
        )
        
        editor_data = self.normalizer.normalize_ocr_result(layout_result)
        
        # Verify metadata preservation
        block = editor_data.blocks[0]
        assert block.metadata is not None
        assert block.metadata["confidence"] == 0.75
        assert "originalCoordinates" in block.metadata
        assert block.metadata["originalCoordinates"]["x"] == 10
        assert block.metadata["originalCoordinates"]["y"] == 10
        assert block.metadata["originalClassification"] == "header"
    
    def test_validation_error_reporting(self):
        """Test comprehensive validation error reporting"""
        # Create data with multiple validation errors
        from backend.models.document import EditorJSBlock, EditorJSData
        import time
        
        invalid_blocks = [
            EditorJSBlock(
                id="",  # Empty ID
                type="header",
                data={"text": "Header", "level": 7}  # Invalid level
            ),
            EditorJSBlock(
                id="test-2",
                type="table",
                data={
                    "content": [["A"], ["B", "C"]],  # Inconsistent columns
                    "withHeadings": "yes"  # Wrong type
                }
            )
        ]
        
        editor_data = EditorJSData(
            time=int(time.time() * 1000),
            blocks=invalid_blocks,
            version="2.28.2"
        )
        
        validation_result = self.normalizer.validate_editor_schema(editor_data)
        
        assert validation_result["is_valid"] == False
        assert len(validation_result["errors"]) >= 3  # Multiple errors expected
        
        # Generate and verify report
        report = self.normalizer.generate_validation_report(editor_data)
        assert "FAILED" in report
        assert "ERRORS:" in report
        assert "Block 0" in report  # Should reference specific blocks
    
    def _test_json_serialization(self, editor_data):
        """Helper method to test JSON serialization"""
        # Convert to dictionary for JSON serialization
        data_dict = {
            "time": editor_data.time,
            "blocks": [],
            "version": editor_data.version
        }
        
        for block in editor_data.blocks:
            block_dict = {
                "id": block.id,
                "type": block.type,
                "data": block.data
            }
            
            if hasattr(block, 'metadata') and block.metadata:
                block_dict["metadata"] = block.metadata
            
            data_dict["blocks"].append(block_dict)
        
        # Test serialization and deserialization
        json_str = json.dumps(data_dict, ensure_ascii=False, indent=2)
        parsed_data = json.loads(json_str)
        
        # Verify structure is preserved
        assert parsed_data["time"] == editor_data.time
        assert len(parsed_data["blocks"]) == len(editor_data.blocks)
        assert parsed_data["version"] == editor_data.version
        
        # Verify first block content
        if parsed_data["blocks"]:
            first_block = parsed_data["blocks"][0]
            original_first = editor_data.blocks[0]
            assert first_block["type"] == original_first.type
            assert first_block["data"] == original_first.data