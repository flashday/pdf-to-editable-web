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
        # 【修复】过滤掉 None 值，因为某些区域（如表格）没有置信度
        text_confidences = [region.confidence for region in layout_result.regions 
                          if region.classification in [RegionType.PARAGRAPH, RegionType.HEADER]
                          and region.confidence is not None]
        text_confidence = sum(text_confidences) / len(text_confidences) if text_confidences else 0.5
        
        # Calculate layout confidence from overall structure
        layout_confidence = layout_result.confidence_score if hasattr(layout_result, 'confidence_score') else 0.7
        
        # Calculate table confidence from table structures
        # 【修复】过滤掉 None 值
        table_confidences = []
        for block in blocks:
            if block.type == "table" and block.metadata and "confidence" in block.metadata:
                conf = block.metadata["confidence"]
                if conf is not None:
                    table_confidences.append(conf)
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
            elif region.classification == RegionType.TABLE:
                # 【修复】处理表格类型的 region
                # 表格的 content 是 HTML 字符串
                block_data = self._create_table_block_data_from_html(region)
            else:
                # Default to paragraph for unknown types
                block_data = self._create_paragraph_block_data(region)
            
            # Estimate font size based on bounding box height
            estimated_font_size = self._estimate_font_size(region)
            
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
                "estimatedFontSize": estimated_font_size,
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
    
    def _estimate_font_size(self, region: Region) -> int:
        """
        Estimate font size based on bounding box height and text content
        
        Args:
            region: OCR region with coordinates and content
            
        Returns:
            Estimated font size in pixels
        """
        if not region.content or not region.coordinates:
            return 14  # Default font size
        
        # Get bounding box height
        bbox_height = region.coordinates.height
        
        # Count number of lines in the text
        text = region.content.strip()
        line_count = max(1, text.count('\n') + 1)
        
        # Estimate line height (bbox height / number of lines)
        line_height = bbox_height / line_count
        
        # Font size is typically about 70-80% of line height
        # We use 0.75 as a reasonable factor
        estimated_size = int(line_height * 0.75)
        
        # Clamp to reasonable range (8px - 72px)
        estimated_size = max(8, min(72, estimated_size))
        
        # Round to common font sizes for cleaner display
        common_sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]
        closest_size = min(common_sizes, key=lambda x: abs(x - estimated_size))
        
        return closest_size
    
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
        # 注意：不再自动将全大写单词转换为 <b> 标签
        # 因为前端可能不会正确渲染这些 HTML 标签
        
        # Preserve line breaks as <br> tags for Editor.js
        formatted_text = text.replace('\n', '<br>')
        
        return formatted_text
    
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
    
    def _create_table_block_data_from_html(self, region: Region) -> Dict[str, Any]:
        """
        从 HTML 字符串创建表格 block 数据
        
        PPStructureV3 返回的表格内容是 HTML 格式，需要解析为 Editor.js 表格格式
        
        Args:
            region: 包含 HTML 表格内容的 Region
            
        Returns:
            Dictionary containing table block data
        """
        import re
        
        html_content = region.content or ""
        
        # 解析 HTML 表格为二维数组
        content = []
        has_headers = False
        
        try:
            # 提取所有行
            row_pattern = r'<tr[^>]*>(.*?)</tr>'
            rows = re.findall(row_pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            for row_idx, row_html in enumerate(rows):
                row_cells = []
                
                # 提取表头单元格
                th_pattern = r'<th[^>]*>(.*?)</th>'
                th_cells = re.findall(th_pattern, row_html, re.DOTALL | re.IGNORECASE)
                
                if th_cells:
                    has_headers = True
                    for cell in th_cells:
                        # 清理 HTML 标签
                        cell_text = re.sub(r'<[^>]+>', '', cell).strip()
                        row_cells.append(cell_text)
                
                # 提取普通单元格
                td_pattern = r'<td[^>]*>(.*?)</td>'
                td_cells = re.findall(td_pattern, row_html, re.DOTALL | re.IGNORECASE)
                
                for cell in td_cells:
                    # 清理 HTML 标签
                    cell_text = re.sub(r'<[^>]+>', '', cell).strip()
                    row_cells.append(cell_text)
                
                if row_cells:
                    content.append(row_cells)
            
            # 确保所有行有相同的列数
            if content:
                max_cols = max(len(row) for row in content)
                for row in content:
                    while len(row) < max_cols:
                        row.append("")
        
        except Exception as e:
            logger.warning(f"Failed to parse table HTML: {e}")
            # 如果解析失败，创建一个包含原始 HTML 的单元格表格
            content = [[html_content]]
        
        # 如果解析结果为空，使用原始 HTML
        if not content:
            content = [[html_content]]
        
        return {
            "withHeadings": has_headers,
            "content": content,
            "stretched": False,
            "tableHtml": html_content  # 保留原始 HTML 用于渲染
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
                "stretched": False,  # Don't stretch table by default
                "tableHtml": self._generate_table_html(validated_content, table.has_headers)
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
    
    def _generate_table_html(self, content: List[List[str]], has_headers: bool = False) -> str:
        """
        Generate HTML table from content
        
        Args:
            content: Table content as 2D list
            has_headers: Whether first row is header
            
        Returns:
            HTML table string
        """
        if not content:
            return "<table><tr><td>Empty table</td></tr></table>"
        
        html_parts = ["<table>"]
        
        for row_idx, row in enumerate(content):
            html_parts.append("<tr>")
            for cell in row:
                if row_idx == 0 and has_headers:
                    html_parts.append(f"<th>{cell}</th>")
                else:
                    html_parts.append(f"<td>{cell}</td>")
            html_parts.append("</tr>")
        
        html_parts.append("</table>")
        return "".join(html_parts)
    
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
    
    def normalize_markdown_to_blocks(self, markdown_content: str) -> EditorJSData:
        """
        Convert Markdown content to Editor.js blocks
        
        PaddleOCR 3.x 新功能：支持从 Markdown 格式转换为 Editor.js blocks
        
        Args:
            markdown_content: Markdown formatted string
            
        Returns:
            EditorJSData object compatible with Editor.js
        """
        try:
            logger.info("Converting Markdown to Editor.js blocks")
            
            blocks = []
            lines = markdown_content.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    i += 1
                    continue
                
                block = None
                
                # 检测标题 (# ## ### 等)
                if line.startswith('#'):
                    block = self._parse_markdown_header(line)
                
                # 检测表格 (| ... |)
                elif line.startswith('|'):
                    table_lines = [line]
                    i += 1
                    while i < len(lines) and lines[i].strip().startswith('|'):
                        table_lines.append(lines[i].strip())
                        i += 1
                    block = self._parse_markdown_table(table_lines)
                    i -= 1  # 回退一行，因为外层循环会 +1
                
                # 检测引用 (> ...)
                elif line.startswith('>'):
                    block = self._parse_markdown_quote(line)
                
                # 检测列表 (- 或 * 或 数字.)
                elif line.startswith('-') or line.startswith('*') or (line[0].isdigit() and '.' in line[:3]):
                    list_lines = [line]
                    i += 1
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if next_line.startswith('-') or next_line.startswith('*') or (next_line and next_line[0].isdigit() and '.' in next_line[:3]):
                            list_lines.append(next_line)
                            i += 1
                        else:
                            break
                    block = self._parse_markdown_list(list_lines)
                    i -= 1
                
                # 检测公式 ($$...$$)
                elif line.startswith('$$'):
                    formula_content = line[2:]
                    if line.endswith('$$') and len(line) > 4:
                        formula_content = line[2:-2]
                    block = self._create_formula_block(formula_content)
                
                # 检测图片 (![alt](url))
                elif line.startswith('!['):
                    block = self._parse_markdown_image(line)
                
                # 检测斜体文本 (*text*)
                elif line.startswith('*') and line.endswith('*') and not line.startswith('**'):
                    text = line[1:-1]
                    block = self._create_paragraph_block_from_text(text, italic=True)
                
                # 普通段落
                else:
                    block = self._create_paragraph_block_from_text(line)
                
                if block:
                    blocks.append(block)
                
                i += 1
            
            # Create Editor.js data structure
            editor_data = EditorJSData(
                time=int(time.time() * 1000),
                blocks=blocks,
                version=self.editor_version
            )
            
            logger.info(f"Successfully converted Markdown to {len(blocks)} Editor.js blocks")
            return editor_data
            
        except Exception as e:
            logger.error(f"Markdown to Editor.js conversion failed: {e}")
            raise ValueError(f"Failed to convert Markdown: {e}")
    
    def _parse_markdown_header(self, line: str) -> EditorJSBlock:
        """Parse Markdown header line to Editor.js header block"""
        level = 0
        for char in line:
            if char == '#':
                level += 1
            else:
                break
        
        text = line[level:].strip()
        level = min(level, 6)  # Max header level is 6
        
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="header",
            data={"text": text, "level": level},
            metadata={"source": "markdown"}
        )
    
    def _parse_markdown_table(self, table_lines: List[str]) -> EditorJSBlock:
        """Parse Markdown table lines to Editor.js table block"""
        content = []
        has_headers = False
        
        for idx, line in enumerate(table_lines):
            # 跳过分隔符行 (| --- | --- |)
            if '---' in line:
                has_headers = True
                continue
            
            # 解析单元格
            cells = [cell.strip() for cell in line.split('|')]
            # 移除首尾空元素
            cells = [c for c in cells if c]
            
            if cells:
                content.append(cells)
        
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="table",
            data={
                "withHeadings": has_headers,
                "content": content,
                "tableHtml": self._generate_table_html(content, has_headers)
            },
            metadata={"source": "markdown"}
        )
    
    def _parse_markdown_quote(self, line: str) -> EditorJSBlock:
        """Parse Markdown quote to Editor.js paragraph block"""
        text = line[1:].strip()  # Remove '>'
        
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="paragraph",
            data={"text": f"<blockquote>{text}</blockquote>"},
            metadata={"source": "markdown", "type": "quote"}
        )
    
    def _parse_markdown_list(self, list_lines: List[str]) -> EditorJSBlock:
        """Parse Markdown list to Editor.js list block"""
        items = []
        style = "unordered"
        
        for line in list_lines:
            line = line.strip()
            
            # 检测有序列表
            if line[0].isdigit() and '.' in line[:3]:
                style = "ordered"
                dot_idx = line.find('.')
                item_text = line[dot_idx + 1:].strip()
            else:
                # 无序列表
                item_text = line[1:].strip()  # Remove - or *
            
            if item_text:
                items.append(item_text)
        
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="list",
            data={"style": style, "items": items},
            metadata={"source": "markdown"}
        )
    
    def _create_formula_block(self, formula: str) -> EditorJSBlock:
        """Create Editor.js block for formula"""
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="paragraph",
            data={"text": f"<em>公式: {formula}</em>"},
            metadata={"source": "markdown", "type": "formula"}
        )
    
    def _parse_markdown_image(self, line: str) -> EditorJSBlock:
        """Parse Markdown image to Editor.js image block"""
        # Format: ![alt](url)
        alt_start = line.find('[') + 1
        alt_end = line.find(']')
        url_start = line.find('(') + 1
        url_end = line.find(')')
        
        alt_text = line[alt_start:alt_end] if alt_start > 0 and alt_end > alt_start else ""
        url = line[url_start:url_end] if url_start > 0 and url_end > url_start else ""
        
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="image",
            data={
                "file": {"url": url},
                "caption": alt_text,
                "withBorder": False,
                "withBackground": False,
                "stretched": False
            },
            metadata={"source": "markdown"}
        )
    
    def _create_paragraph_block_from_text(self, text: str, italic: bool = False) -> EditorJSBlock:
        """Create paragraph block from text"""
        if italic:
            text = f"<em>{text}</em>"
        
        return EditorJSBlock(
            id=str(uuid.uuid4()),
            type="paragraph",
            data={"text": text},
            metadata={"source": "markdown"}
        )