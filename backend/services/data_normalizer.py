"""
Data normalization service for converting OCR results to Editor.js format
"""
import logging
import uuid
import time
from typing import List, Dict, Any, Optional
from backend.models.document import (
    LayoutResult, Region, TableStructure, RegionType, 
    EditorJSData, EditorJSBlock, BoundingBox, ConfidenceMetrics
)
from backend.services.interfaces import DataNormalizerInterface
from backend.services.schema_validator import EditorJSSchemaValidator
from backend.services.confidence_monitor import confidence_monitor

logger = logging.getLogger(__name__)

class DataNormalizer(DataNormalizerInterface):
    """
    Service for normalizing OCR results into Editor.js compatible format
    """
    
    def __init__(self):
        """Initialize the data normalizer"""
        self.editor_version = "2.28.2"
        self.schema_validator = EditorJSSchemaValidator()
        
        # Mapping configuration for region types to Editor.js block types
        self.region_to_block_mapping = {
            RegionType.HEADER: "header",
            RegionType.PARAGRAPH: "paragraph", 
            RegionType.TABLE: "table",
            RegionType.LIST: "list",
            RegionType.IMAGE: "image"
        }
        
        # Header level detection patterns
        self.header_patterns = {
            1: ["title", "主题", "标题", "chapter", "章节"],
            2: ["section", "部分", "节", "subtitle", "副标题"],
            3: ["subsection", "小节", "子部分"],
            4: ["subsubsection", "子小节"],
            5: ["paragraph", "段落标题"],
            6: ["subparagraph", "子段落"]
        }
    
    def normalize_ocr_result(self, layout_result: LayoutResult) -> EditorJSData:
        """
        Convert OCR layout result to Editor.js format with confidence monitoring
        
        Args:
            layout_result: OCR analysis result containing regions and tables
            
        Returns:
            EditorJSData object compatible with Editor.js
        """
        try:
            logger.info(f"Normalizing OCR result with {len(layout_result.regions)} regions")
            
            blocks = []
            
            # Process text regions first
            for region in layout_result.regions:
                block = self._convert_region_to_block(region)
                if block:
                    blocks.append(block)
            
            # Process tables separately to ensure proper structure
            for table in layout_result.tables:
                table_block = self._convert_table_to_block(table)
                if table_block:
                    blocks.append(table_block)
            
            # Sort blocks by their original position (reading order)
            blocks = self._sort_blocks_by_position(blocks)
            
            # Calculate confidence metrics for the conversion
            confidence_metrics = self._calculate_conversion_confidence(layout_result, blocks)
            
            # Create Editor.js data structure
            editor_data = EditorJSData(
                time=int(time.time() * 1000),  # Current timestamp in milliseconds
                blocks=blocks,
                version=self.editor_version
            )
            
            # Validate schema compliance before returning
            validation_result = self.validate_editor_schema(editor_data)
            if not validation_result["is_valid"]:
                logger.warning(f"Schema validation failed: {len(validation_result['errors'])} errors")
                # Log first few errors for debugging
                for error in validation_result["errors"][:3]:
                    logger.warning(f"Schema error: {error}")
            
            # Generate confidence report and warnings
            confidence_report = confidence_monitor.generate_confidence_report(confidence_metrics)
            
            # Log confidence analysis
            confidence_monitor.log_confidence_analysis(
                confidence_metrics, 
                confidence_report.get('warnings', []),
                'normalization_process'
            )
            
            # Add confidence information to editor data metadata
            if hasattr(editor_data, 'metadata'):
                editor_data.metadata = confidence_report
            else:
                # Store confidence report for later use
                setattr(editor_data, 'confidence_report', confidence_report)
            
            logger.info(f"Successfully normalized to {len(blocks)} Editor.js blocks with confidence: {confidence_metrics.overall_confidence:.3f}")
            return editor_data
            
        except Exception as e:
            logger.error(f"OCR result normalization failed: {e}")
            raise ValueError(f"Failed to normalize OCR result: {e}")
    
    def _calculate_conversion_confidence(self, layout_result: LayoutResult, blocks: List[EditorJSBlock]) -> ConfidenceMetrics:
        """
        Calculate confidence metrics for the conversion process
        
        Args:
            layout_result: Original OCR layout result
            blocks: Converted Editor.js blocks
            
        Returns:
            ConfidenceMetrics object
        """
        # Calculate text confidence from regions
        text_confidences = [region.confidence for region in layout_result.regions 
                          if region.classification in [RegionType.PARAGRAPH, RegionType.HEADER]]
        text_confidence = sum(text_confidences) / len(text_confidences) if text_confidences else 0.5
        
        # Calculate layout confidence from overall structure
        layout_confidence = layout_result.confidence_score if hasattr(layout_result, 'confidence_score') else 0.7
        
        # Calculate table confidence from table structures
        table_confidences = []
        for block in blocks:
            if block.type == "table" and block.metadata and "confidence" in block.metadata:
                table_confidences.append(block.metadata["confidence"])
        table_confidence = sum(table_confidences) / len(table_confidences) if table_confidences else 0.6
        
        # Calculate overall confidence as weighted average
        weights = {
            'text': 0.4,
            'layout': 0.3,
            'table': 0.2,
            'conversion': 0.1
        }
        
        # Conversion confidence based on successful block creation
        expected_blocks = len(layout_result.regions) + len(layout_result.tables)
        actual_blocks = len(blocks)
        conversion_confidence = min(actual_blocks / expected_blocks, 1.0) if expected_blocks > 0 else 1.0
        
        overall_confidence = (
            text_confidence * weights['text'] +
            layout_confidence * weights['layout'] +
            table_confidence * weights['table'] +
            conversion_confidence * weights['conversion']
        )
        
        return ConfidenceMetrics(
            overall_confidence=overall_confidence,
            text_confidence=text_confidence,
            layout_confidence=layout_confidence,
            table_confidence=table_confidence
        )
    
    def _convert_region_to_block(self, region: Region) -> Optional[EditorJSBlock]:
        """
        Convert a single OCR region to Editor.js block
        
        Args:
            region: OCR region to convert
            
        Returns:
            EditorJSBlock object or None if conversion fails
        """
        try:
            if not region.content or not region.content.strip():
                return None
            
            block_type = self.region_to_block_mapping.get(region.classification, "paragraph")
            block_id = str(uuid.uuid4())
            
            # Create block data based on type
            if region.classification == RegionType.HEADER:
                block_data = self._create_header_block_data(region)
            elif region.classification == RegionType.PARAGRAPH:
                block_data = self._create_paragraph_block_data(region)
            elif region.classification == RegionType.LIST:
                block_data = self._create_list_block_data(region)
            elif region.classification == RegionType.IMAGE:
                block_data = self._create_image_block_data(region)
            else:
                # Default to paragraph for unknown types
                block_data = self._create_paragraph_block_data(region)
            
            # Add metadata for traceability
            metadata = {
                "confidence": region.confidence,
                "originalCoordinates": {
                    "x": region.coordinates.x,
                    "y": region.coordinates.y,
                    "width": region.coordinates.width,
                    "height": region.coordinates.height
                },
                "originalClassification": region.classification.value,
                "processingNotes": []
            }
            
            return EditorJSBlock(
                id=block_id,
                type=block_type,
                data=block_data,
                metadata=metadata
            )
            
        except Exception as e:
            logger.warning(f"Failed to convert region to block: {e}")
            return None
    
    def _create_header_block_data(self, region: Region) -> Dict[str, Any]:
        """
        Create header block data with level detection
        
        Args:
            region: Header region
            
        Returns:
            Dictionary containing header block data
        """
        text = region.content.strip()
        level = self._detect_header_level(text, region.coordinates)
        
        return {
            "text": text,
            "level": level
        }
    
    def _detect_header_level(self, text: str, coordinates: BoundingBox) -> int:
        """
        Detect header level based on content and position
        
        Args:
            text: Header text content
            coordinates: Position and size information
            
        Returns:
            Header level (1-6)
        """
        text_lower = text.lower()
        
        # Check for explicit level indicators in text
        for level, patterns in self.header_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return level
        
        # Use position and size heuristics
        # Headers near top of page are likely higher level
        if coordinates.y < 100:  # Top 100px
            if len(text) < 30:
                return 1  # Short text at top = main title
            else:
                return 2  # Longer text at top = subtitle
        
        # Use text length as indicator
        if len(text) < 20:
            return 3  # Short text = subsection
        elif len(text) < 40:
            return 4  # Medium text = sub-subsection
        else:
            return 5  # Longer text = paragraph header
    
    def _create_paragraph_block_data(self, region: Region) -> Dict[str, Any]:
        """
        Create paragraph block data with text preservation
        
        Args:
            region: Paragraph region
            
        Returns:
            Dictionary containing paragraph block data
        """
        text = region.content.strip()
        
        # Preserve basic formatting by converting to HTML-like format
        # Editor.js paragraph tool supports basic HTML tags
        formatted_text = self._preserve_text_formatting(text)
        
        return {
            "text": formatted_text
        }
    
    def _preserve_text_formatting(self, text: str) -> str:
        """
        Preserve basic text formatting for Editor.js
        
        Args:
            text: Raw text content
            
        Returns:
            Text with preserved formatting
        """
        # Basic formatting preservation
        # This can be enhanced with more sophisticated formatting detection
        
        # Preserve line breaks as <br> tags for Editor.js
        formatted_text = text.replace('\n', '<br>')
        
        # Detect and preserve bold text (simple heuristic)
        # Look for text in ALL CAPS (likely bold/emphasized)
        words = formatted_text.split()
        for i, word in enumerate(words):
            if (len(word) > 3 and word.isupper() and 
                not any(char.isdigit() for char in word)):
                words[i] = f"<b>{word}</b>"
        
        return ' '.join(words)
    
    def _create_list_block_data(self, region: Region) -> Dict[str, Any]:
        """
        Create list block data from list region
        
        Args:
            region: List region
            
        Returns:
            Dictionary containing list block data
        """
        text = region.content.strip()
        
        # Parse list items
        list_items = self._parse_list_items(text)
        
        # Detect list style (ordered vs unordered)
        style = self._detect_list_style(text)
        
        return {
            "style": style,
            "items": list_items
        }
    
    def _parse_list_items(self, text: str) -> List[str]:
        """
        Parse individual list items from text
        
        Args:
            text: Raw list text
            
        Returns:
            List of individual items
        """
        items = []
        
        # Split by common list indicators
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove list indicators
            list_indicators = ['•', '-', '*', '○', '▪', '▫']
            for indicator in list_indicators:
                if line.startswith(indicator):
                    line = line[1:].strip()
                    break
            
            # Remove numbered indicators (1., 2., etc.)
            if line and line[0].isdigit():
                dot_index = line.find('.')
                if dot_index > 0 and dot_index < 5:  # Reasonable number length
                    line = line[dot_index + 1:].strip()
            
            if line:
                items.append(line)
        
        return items if items else [text]  # Fallback to original text
    
    def _detect_list_style(self, text: str) -> str:
        """
        Detect whether list is ordered or unordered
        
        Args:
            text: List text content
            
        Returns:
            "ordered" or "unordered"
        """
        # Check for numbered patterns
        lines = text.split('\n')
        numbered_count = 0
        
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and line[0].isdigit():
                dot_index = line.find('.')
                if 0 < dot_index < 5:
                    numbered_count += 1
        
        # If more than half start with numbers, it's ordered
        return "ordered" if numbered_count > len(lines) / 2 else "unordered"
    
    def _create_image_block_data(self, region: Region) -> Dict[str, Any]:
        """
        Create image block data (placeholder for non-text regions)
        
        Args:
            region: Image region
            
        Returns:
            Dictionary containing image block data
        """
        return {
            "file": {
                "url": "",  # Will be populated when image processing is implemented
                "width": int(region.coordinates.width),
                "height": int(region.coordinates.height)
            },
            "caption": region.content or "Image content detected",
            "withBorder": False,
            "withBackground": False,
            "stretched": False
        }
    
    def _convert_table_to_block(self, table: TableStructure) -> Optional[EditorJSBlock]:
        """
        Convert table structure to Editor.js table block with enhanced processing
        
        Args:
            table: Table structure from OCR
            
        Returns:
            EditorJSBlock for table or None if conversion fails
        """
        try:
            if not table.cells or not table.cells[0]:
                return None
            
            block_id = str(uuid.uuid4())
            
            # Process and validate table content
            processed_content = self._process_table_content(table.cells)
            validated_content = self._validate_table_content(processed_content)
            
            # Detect and preserve table metadata
            table_metadata = self._extract_table_metadata(table, validated_content)
            
            # Create table block data with Editor.js format
            block_data = {
                "withHeadings": table.has_headers,
                "content": validated_content,
                "stretched": False  # Don't stretch table by default
            }
            
            # Add comprehensive metadata
            metadata = {
                "confidence": self._calculate_table_confidence(table, validated_content),
                "originalCoordinates": {
                    "x": table.coordinates.x,
                    "y": table.coordinates.y,
                    "width": table.coordinates.width,
                    "height": table.coordinates.height
                },
                "tableStructure": {
                    "rows": len(validated_content),
                    "columns": len(validated_content[0]) if validated_content else 0,
                    "hasHeaders": table.has_headers,
                    "originalRows": table.rows,
                    "originalColumns": table.columns
                },
                "tableMetadata": table_metadata,
                "processingNotes": ["Converted from OCR table detection", "Content validated and normalized"]
            }
            
            return EditorJSBlock(
                id=block_id,
                type="table",
                data=block_data,
                metadata=metadata
            )
            
        except Exception as e:
            logger.warning(f"Failed to convert table to block: {e}")
            return None
    
    def _process_table_content(self, raw_cells: List[List[str]]) -> List[List[str]]:
        """
        Process raw table cells to clean and normalize content
        
        Args:
            raw_cells: Raw table cell content from OCR
            
        Returns:
            Processed table content
        """
        processed_content = []
        
        for row in raw_cells:
            processed_row = []
            for cell in row:
                # Clean cell content
                cleaned_cell = self._clean_table_cell(cell)
                processed_row.append(cleaned_cell)
            processed_content.append(processed_row)
        
        return processed_content
    
    def _clean_table_cell(self, cell_content: str) -> str:
        """
        Clean individual table cell content
        
        Args:
            cell_content: Raw cell content
            
        Returns:
            Cleaned cell content
        """
        if not cell_content:
            return ""
        
        # Remove excessive whitespace
        cleaned = ' '.join(cell_content.split())
        
        # Remove common OCR artifacts
        artifacts = ['|', '│', '─', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼']
        for artifact in artifacts:
            cleaned = cleaned.replace(artifact, '')
        
        # Trim and return
        return cleaned.strip()
    
    def _validate_table_content(self, content: List[List[str]]) -> List[List[str]]:
        """
        Validate and normalize table content structure
        
        Args:
            content: Processed table content
            
        Returns:
            Validated table content with consistent structure
        """
        if not content:
            return []
        
        # Find maximum column count
        max_cols = max(len(row) for row in content)
        
        # Normalize all rows to have same column count
        normalized_content = []
        for row in content:
            normalized_row = row.copy()
            
            # Pad short rows with empty cells
            while len(normalized_row) < max_cols:
                normalized_row.append("")
            
            # Truncate overly long rows
            if len(normalized_row) > max_cols:
                normalized_row = normalized_row[:max_cols]
            
            normalized_content.append(normalized_row)
        
        # Remove completely empty rows
        normalized_content = [row for row in normalized_content if any(cell.strip() for cell in row)]
        
        # Ensure minimum table size (at least 1x1)
        if not normalized_content:
            normalized_content = [[""]]
        
        return normalized_content
    
    def _extract_table_metadata(self, table: TableStructure, content: List[List[str]]) -> Dict[str, Any]:
        """
        Extract metadata about table structure and content
        
        Args:
            table: Original table structure
            content: Processed table content
            
        Returns:
            Dictionary containing table metadata
        """
        metadata = {
            "cellCount": sum(len(row) for row in content),
            "nonEmptyCells": sum(1 for row in content for cell in row if cell.strip()),
            "averageCellLength": 0,
            "hasNumericData": False,
            "hasTextData": False,
            "columnTypes": []
        }
        
        # Calculate average cell length
        all_cells = [cell for row in content for cell in row if cell.strip()]
        if all_cells:
            metadata["averageCellLength"] = sum(len(cell) for cell in all_cells) / len(all_cells)
        
        # Analyze data types
        for row in content:
            for cell in row:
                if cell.strip():
                    if any(char.isdigit() for char in cell):
                        metadata["hasNumericData"] = True
                    if any(char.isalpha() for char in cell):
                        metadata["hasTextData"] = True
        
        # Analyze column types
        if content and content[0]:
            for col_idx in range(len(content[0])):
                column_cells = [row[col_idx] for row in content if col_idx < len(row) and row[col_idx].strip()]
                
                if not column_cells:
                    metadata["columnTypes"].append("empty")
                    continue
                
                # Determine column type
                numeric_count = sum(1 for cell in column_cells if self._is_numeric(cell))
                text_count = len(column_cells) - numeric_count
                
                if numeric_count > text_count:
                    metadata["columnTypes"].append("numeric")
                elif text_count > 0:
                    metadata["columnTypes"].append("text")
                else:
                    metadata["columnTypes"].append("mixed")
        
        return metadata
    
    def _is_numeric(self, text: str) -> bool:
        """
        Check if text represents numeric data
        
        Args:
            text: Text to check
            
        Returns:
            True if text is numeric
        """
        try:
            # Remove common formatting characters
            cleaned = text.replace(',', '').replace('$', '').replace('%', '').strip()
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _calculate_table_confidence(self, table: TableStructure, content: List[List[str]]) -> float:
        """
        Calculate confidence score for table conversion
        
        Args:
            table: Original table structure
            content: Processed table content
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence_factors = []
        
        # Factor 1: Content completeness
        total_cells = len(content) * len(content[0]) if content and content[0] else 0
        non_empty_cells = sum(1 for row in content for cell in row if cell.strip())
        
        if total_cells > 0:
            completeness = non_empty_cells / total_cells
            confidence_factors.append(completeness)
        
        # Factor 2: Structure consistency
        if content:
            expected_cols = len(content[0])
            consistent_rows = sum(1 for row in content if len(row) == expected_cols)
            structure_consistency = consistent_rows / len(content)
            confidence_factors.append(structure_consistency)
        
        # Factor 3: Content quality (reasonable cell lengths)
        reasonable_cells = 0
        total_content_cells = 0
        
        for row in content:
            for cell in row:
                if cell.strip():
                    total_content_cells += 1
                    if 1 <= len(cell.strip()) <= 100:  # Reasonable length
                        reasonable_cells += 1
        
        if total_content_cells > 0:
            content_quality = reasonable_cells / total_content_cells
            confidence_factors.append(content_quality)
        
        # Factor 4: Original table structure confidence
        if hasattr(table, 'confidence'):
            confidence_factors.append(table.confidence)
        else:
            confidence_factors.append(0.7)  # Default confidence
        
        # Return weighted average
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    def _sort_blocks_by_position(self, blocks: List[EditorJSBlock]) -> List[EditorJSBlock]:
        """
        Sort blocks by their original position (reading order)
        
        Args:
            blocks: List of Editor.js blocks
            
        Returns:
            Sorted list of blocks
        """
        def position_key(block: EditorJSBlock) -> tuple:
            if not block.metadata or "originalCoordinates" not in block.metadata:
                return (0, 0)  # Default position
            
            coords = block.metadata["originalCoordinates"]
            # Sort by Y position first (top to bottom), then X position (left to right)
            return (coords["y"], coords["x"])
        
        return sorted(blocks, key=position_key)
    
    def validate_editor_schema(self, editor_data: EditorJSData) -> Dict[str, Any]:
        """
        Validate Editor.js schema compliance using comprehensive validator
        
        Args:
            editor_data: Editor.js data to validate
            
        Returns:
            Dictionary containing validation results
        """
        try:
            return self.schema_validator.validate_editor_data(editor_data)
        except Exception as e:
            logger.error(f"Schema validation failed with exception: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation exception: {str(e)}"],
                "warnings": [],
                "block_count": 0,
                "validation_details": {
                    "structure_valid": False,
                    "blocks_valid": False,
                    "schema_compliant": False
                }
            }
    
    def generate_validation_report(self, editor_data: EditorJSData) -> str:
        """
        Generate comprehensive validation report for Editor.js data
        
        Args:
            editor_data: Editor.js data to validate and report on
            
        Returns:
            Human-readable validation report
        """
        validation_result = self.validate_editor_schema(editor_data)
        return self.schema_validator.generate_validation_report(validation_result)