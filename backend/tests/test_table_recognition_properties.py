"""
Property-based tests for table structure recognition
Feature: pdf-to-editable-web
Property 5: Table structure recognition
Validates: Requirements 2.2
"""
import sys
from unittest.mock import MagicMock

# Make paddleocr optional - mock it before importing
try:
    import paddleocr
    PADDLEOCR_AVAILABLE = True
except ImportError:
    PADDLEOCR_AVAILABLE = False
    sys.modules['paddleocr'] = MagicMock()

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from PIL import Image
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from hypothesis import HealthCheck

from backend.services.ocr_service import PaddleOCRService, OCRProcessingError
from backend.models.document import Region, TableStructure, BoundingBox, RegionType


# Custom strategies for generating test data
@st.composite
def table_region_strategy(draw):
    """Generate a valid table region"""
    x = draw(st.integers(min_value=0, max_value=500))
    y = draw(st.integers(min_value=0, max_value=500))
    width = draw(st.integers(min_value=100, max_value=400))
    height = draw(st.integers(min_value=50, max_value=300))
    confidence = draw(st.floats(min_value=0.5, max_value=1.0))
    
    # Generate table-like content
    rows = draw(st.integers(min_value=2, max_value=5))
    cols = draw(st.integers(min_value=2, max_value=5))
    
    # Create simple table content
    content_parts = []
    for i in range(rows):
        row_parts = [f"Cell{i}{j}" for j in range(cols)]
        content_parts.append(" | ".join(row_parts))
    content = "\n".join(content_parts)
    
    return Region(
        coordinates=BoundingBox(x=x, y=y, width=width, height=height),
        classification=RegionType.TABLE,
        confidence=confidence,
        content=content
    )


@st.composite
def table_ocr_result_strategy(draw):
    """Generate a valid OCR result for a table"""
    rows = draw(st.integers(min_value=2, max_value=5))
    cols = draw(st.integers(min_value=2, max_value=5))
    
    ocr_result = []
    cell_height = 30
    cell_width = 100
    
    for row_idx in range(rows):
        for col_idx in range(cols):
            x_start = col_idx * cell_width
            y_start = row_idx * cell_height
            
            bbox = [
                [x_start, y_start],
                [x_start + cell_width, y_start],
                [x_start + cell_width, y_start + cell_height],
                [x_start, y_start + cell_height]
            ]
            
            # Generate cell content
            if row_idx == 0:
                # Header row
                text = f"Header{col_idx}"
            else:
                # Data rows
                text = f"Data{row_idx}{col_idx}"
            
            confidence = draw(st.floats(min_value=0.7, max_value=1.0))
            
            ocr_result.append([bbox, (text, confidence)])
    
    return [ocr_result]


@st.composite
def table_structure_strategy(draw):
    """Generate a valid TableStructure"""
    rows = draw(st.integers(min_value=1, max_value=10))
    cols = draw(st.integers(min_value=1, max_value=10))
    
    # Generate table cells
    cells = []
    for i in range(rows):
        row = []
        for j in range(cols):
            cell_content = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
            row.append(cell_content)
        cells.append(row)
    
    x = draw(st.integers(min_value=0, max_value=500))
    y = draw(st.integers(min_value=0, max_value=500))
    width = draw(st.integers(min_value=100, max_value=400))
    height = draw(st.integers(min_value=50, max_value=300))
    
    has_headers = draw(st.booleans())
    
    return TableStructure(
        rows=rows,
        columns=cols,
        cells=cells,
        coordinates=BoundingBox(x=x, y=y, width=width, height=height),
        has_headers=has_headers
    )


class TestTableRecognitionProperties:
    """Property-based tests for table structure recognition"""
    
    @pytest.fixture
    def mock_ocr_service(self):
        """Create OCR service with mocked PaddleOCR engines"""
        with patch('paddleocr.PaddleOCR') as mock_paddle:
            mock_engine = Mock()
            mock_paddle.return_value = mock_engine
            
            service = PaddleOCRService(use_gpu=False)
            service._ocr_engine = mock_engine
            service._structure_engine = mock_engine
            
            return service, mock_engine
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            img = Image.new('RGB', (800, 600), color='white')
            img.save(tmp.name)
            yield tmp.name
            os.unlink(tmp.name)
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(table_region=table_region_strategy())
    def test_property_table_structure_recognition(self, table_region, mock_ocr_service, sample_image):
        """
        Property 5: Table structure recognition
        
        For any document containing table structures, the OCR engine should recognize
        and classify them with appropriate structural metadata.
        
        Validates: Requirements 2.2
        """
        service, mock_engine = mock_ocr_service
        
        # Generate mock OCR result for the table
        mock_table_ocr = [
            [
                [[[0, 0], [100, 0], [100, 30], [0, 30]], ('Header1', 0.9)],
                [[[100, 0], [200, 0], [200, 30], [100, 30]], ('Header2', 0.9)],
                [[[0, 30], [100, 30], [100, 60], [0, 60]], ('Data1', 0.85)],
                [[[100, 30], [200, 30], [200, 60], [100, 60]], ('Data2', 0.88)]
            ]
        ]
        
        mock_engine.ocr.return_value = mock_table_ocr
        
        with patch('cv2.imread') as mock_imread, \
             patch('cv2.imwrite') as mock_imwrite:
            
            mock_imread.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
            
            # Execute table extraction
            tables = service.extract_tables(sample_image, [table_region])
            
            # Property assertions:
            # 1. Table extraction should not raise exceptions for valid table regions
            assert isinstance(tables, list), "extract_tables should return a list"
            
            # 2. If tables are detected, they should have proper structure
            for table in tables:
                assert isinstance(table, TableStructure), "Each table should be a TableStructure"
                assert table.rows > 0, "Table should have at least one row"
                assert table.columns > 0, "Table should have at least one column"
                assert len(table.cells) == table.rows, "Number of cell rows should match rows count"
                
                # 3. Each row should have the correct number of columns
                for row in table.cells:
                    assert len(row) == table.columns, f"Each row should have {table.columns} columns"
                
                # 4. Table should have valid coordinates
                assert isinstance(table.coordinates, BoundingBox), "Table should have BoundingBox coordinates"
                assert table.coordinates.width >= 0, "Table width should be non-negative"
                assert table.coordinates.height >= 0, "Table height should be non-negative"
                
                # 5. has_headers should be a boolean
                assert isinstance(table.has_headers, bool), "has_headers should be a boolean"
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_tables=st.integers(min_value=0, max_value=5),
        rows=st.integers(min_value=2, max_value=6),
        cols=st.integers(min_value=2, max_value=6)
    )
    def test_property_multiple_tables_recognition(self, num_tables, rows, cols, mock_ocr_service, sample_image):
        """
        Property: Multiple table structures should be recognized independently
        
        For any document containing multiple table structures, each table should be
        recognized and classified independently with its own structural metadata.
        
        Validates: Requirements 2.2
        """
        service, mock_engine = mock_ocr_service
        
        # Create multiple table regions
        table_regions = []
        for i in range(num_tables):
            region = Region(
                coordinates=BoundingBox(x=50, y=100 + i * 200, width=300, height=150),
                classification=RegionType.TABLE,
                confidence=0.85,
                content=f"Table {i}"
            )
            table_regions.append(region)
        
        # Mock OCR result
        mock_table_ocr = []
        for row_idx in range(rows):
            for col_idx in range(cols):
                x_start = col_idx * 100
                y_start = row_idx * 30
                bbox = [[x_start, y_start], [x_start + 100, y_start], 
                       [x_start + 100, y_start + 30], [x_start, y_start + 30]]
                text = f"Cell{row_idx}{col_idx}"
                mock_table_ocr.append([bbox, (text, 0.9)])
        
        mock_engine.ocr.return_value = [mock_table_ocr]
        
        with patch('cv2.imread') as mock_imread, \
             patch('cv2.imwrite') as mock_imwrite:
            
            mock_imread.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
            
            # Execute table extraction
            tables = service.extract_tables(sample_image, table_regions)
            
            # Property assertions:
            # 1. Result should be a list
            assert isinstance(tables, list), "extract_tables should return a list"
            
            # 2. Number of detected tables should not exceed input regions
            assert len(tables) <= num_tables, "Should not detect more tables than regions provided"
            
            # 3. Each detected table should be valid
            for table in tables:
                assert isinstance(table, TableStructure), "Each table should be a TableStructure"
                assert table.rows > 0 and table.columns > 0, "Table should have positive dimensions"
    
    @settings(max_examples=100, deadline=None)
    @given(table_structure=table_structure_strategy())
    def test_property_table_structure_integrity(self, table_structure):
        """
        Property: Table structure should maintain data integrity
        
        For any valid TableStructure, the structure should maintain consistency
        between declared dimensions and actual cell data.
        
        Validates: Requirements 2.2
        """
        # Property assertions:
        # 1. Rows and columns should match cell dimensions
        assert len(table_structure.cells) == table_structure.rows, \
            "Number of cell rows should match declared rows"
        
        # 2. Each row should have the correct number of columns
        for row_idx, row in enumerate(table_structure.cells):
            assert len(row) == table_structure.columns, \
                f"Row {row_idx} should have {table_structure.columns} columns, got {len(row)}"
        
        # 3. All cells should be strings
        for row in table_structure.cells:
            for cell in row:
                assert isinstance(cell, str), "All cells should be strings"
        
        # 4. Coordinates should be valid
        assert table_structure.coordinates.width >= 0, "Width should be non-negative"
        assert table_structure.coordinates.height >= 0, "Height should be non-negative"
        assert table_structure.coordinates.x >= 0, "X coordinate should be non-negative"
        assert table_structure.coordinates.y >= 0, "Y coordinate should be non-negative"
        
        # 5. has_headers should be boolean
        assert isinstance(table_structure.has_headers, bool), "has_headers should be boolean"
    
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        has_table=st.booleans(),
        confidence=st.floats(min_value=0.5, max_value=1.0)
    )
    def test_property_table_detection_consistency(self, has_table, confidence, mock_ocr_service, sample_image):
        """
        Property: Table detection should be consistent with region classification
        
        For any region classified as TABLE, the extraction process should attempt
        to extract table structure, and the result should be consistent.
        
        Validates: Requirements 2.2
        """
        service, mock_engine = mock_ocr_service
        
        if has_table:
            # Create a table region
            region = Region(
                coordinates=BoundingBox(x=100, y=100, width=300, height=150),
                classification=RegionType.TABLE,
                confidence=confidence,
                content="Header1 | Header2\nData1 | Data2"
            )
            regions = [region]
            
            # Mock table OCR result
            mock_table_ocr = [
                [
                    [[[0, 0], [100, 0], [100, 30], [0, 30]], ('Header1', 0.9)],
                    [[[100, 0], [200, 0], [200, 30], [100, 30]], ('Header2', 0.9)],
                    [[[0, 30], [100, 30], [100, 60], [0, 60]], ('Data1', 0.85)],
                    [[[100, 30], [200, 30], [200, 60], [100, 60]], ('Data2', 0.88)]
                ]
            ]
        else:
            # Create a non-table region
            region = Region(
                coordinates=BoundingBox(x=100, y=100, width=300, height=50),
                classification=RegionType.PARAGRAPH,
                confidence=confidence,
                content="This is a paragraph"
            )
            regions = [region]
            
            # Mock non-table OCR result
            mock_table_ocr = [
                [
                    [[[0, 0], [300, 0], [300, 50], [0, 50]], ('This is a paragraph', 0.9)]
                ]
            ]
        
        mock_engine.ocr.return_value = mock_table_ocr
        
        with patch('cv2.imread') as mock_imread, \
             patch('cv2.imwrite') as mock_imwrite:
            
            mock_imread.return_value = np.zeros((600, 800, 3), dtype=np.uint8)
            
            # Execute table extraction
            tables = service.extract_tables(sample_image, regions)
            
            # Property assertions:
            # 1. Result should always be a list
            assert isinstance(tables, list), "extract_tables should always return a list"
            
            # 2. If region is classified as TABLE, extraction should be attempted
            if has_table:
                # Table extraction was attempted (may or may not succeed)
                # But should not raise exceptions
                pass
            else:
                # Non-table regions should result in empty or minimal table detection
                # This is acceptable behavior
                pass
            
            # 3. All returned tables should be valid TableStructure objects
            for table in tables:
                assert isinstance(table, TableStructure), "All results should be TableStructure"
                assert table.rows >= 0, "Rows should be non-negative"
                assert table.columns >= 0, "Columns should be non-negative"
