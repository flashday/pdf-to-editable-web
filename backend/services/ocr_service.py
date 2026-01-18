"""
PaddleOCR PP-Structure integration service with error handling and preprocessing
"""
import os
import logging
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2

from backend.models.document import LayoutResult, Region, TableStructure, BoundingBox, RegionType
from backend.services.interfaces import OCRServiceInterface
from backend.services.retry_handler import retry_handler, RetryConfig, NetworkRetryError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessingError(Exception):
    """Custom exception for OCR processing errors"""
    pass

class PaddleOCRService(OCRServiceInterface):
    """
    PaddleOCR PP-Structure service wrapper with error handling and preprocessing
    """
    
    def __init__(self, use_gpu: bool = False, lang: str = 'ch'):
        """
        Initialize PaddleOCR service
        
        Args:
            use_gpu: Whether to use GPU acceleration (default: False for CPU-only)
            lang: Language for OCR recognition (default: 'ch' for Chinese/English)
        """
        self.use_gpu = use_gpu
        self.lang = lang
        self._ocr_engine = None
        self._structure_engine = None
        
        # Initialize engines lazily to avoid import errors during testing
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize PaddleOCR engines with error handling and retry mechanism"""
        @retry_handler.retry(RetryConfig(max_retries=2, base_delay=2.0))
        def initialize_with_retry():
            try:
                from paddleocr import PaddleOCR
                
                # Initialize OCR engine for text recognition
                self._ocr_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
                
                # Initialize PP-Structure engine for layout analysis
                self._structure_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False,
                    use_structure=True  # Enable structure analysis
                )
                
                logger.info(f"PaddleOCR engines initialized successfully (GPU: {self.use_gpu})")
                
            except ImportError as e:
                raise OCRProcessingError(f"PaddleOCR not installed: {e}")
            except Exception as e:
                # Convert to retryable error for network-related issues
                if any(keyword in str(e).lower() for keyword in ['network', 'connection', 'download', 'model']):
                    raise NetworkRetryError(f"Failed to initialize PaddleOCR engines (network issue): {e}")
                else:
                    raise OCRProcessingError(f"Failed to initialize PaddleOCR engines: {e}")
        
        try:
            initialize_with_retry()
        except NetworkRetryError as e:
            raise OCRProcessingError(f"Failed to initialize after retries: {e}")
        except Exception as e:
            raise OCRProcessingError(f"Engine initialization failed: {e}")
    
    def preprocess_image(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Preprocess image for optimal OCR results
        
        Args:
            image_path: Path to input image
            output_path: Path for preprocessed image (optional)
            
        Returns:
            Path to preprocessed image
        """
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply preprocessing steps
            image = self._enhance_image_quality(image)
            image = self._normalize_image_size(image)
            
            # Save preprocessed image
            if output_path is None:
                base_path = Path(image_path)
                output_path = str(base_path.parent / f"{base_path.stem}_preprocessed{base_path.suffix}")
            
            image.save(output_path, quality=95, optimize=True)
            
            logger.info(f"Image preprocessed and saved to: {output_path}")
            return output_path
            
        except Exception as e:
            raise OCRProcessingError(f"Image preprocessing failed: {e}")
    
    def _enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """
        Enhance image quality for better OCR results
        
        Args:
            image: PIL Image object
            
        Returns:
            Enhanced PIL Image object
        """
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        # Apply slight denoising
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def _normalize_image_size(self, image: Image.Image, max_dimension: int = 2048) -> Image.Image:
        """
        Normalize image size to optimal dimensions for OCR
        
        Args:
            image: PIL Image object
            max_dimension: Maximum dimension for resizing
            
        Returns:
            Resized PIL Image object
        """
        width, height = image.size
        
        # Only resize if image is too large
        if max(width, height) > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Image resized from {width}x{height} to {new_width}x{new_height}")
        
        return image
    
    def analyze_layout(self, image_path: str) -> LayoutResult:
        """
        Perform comprehensive layout analysis on image using PP-Structure with retry mechanism
        
        Args:
            image_path: Path to image file
            
        Returns:
            LayoutResult containing detected regions and metadata
        """
        if not self._structure_engine:
            raise OCRProcessingError("Structure engine not initialized")
        
        @retry_handler.retry(RetryConfig(max_retries=3, base_delay=1.5))
        def perform_layout_analysis():
            try:
                import time
                start_time = time.time()
                
                # Preprocess image for better results
                preprocessed_path = self.preprocess_image(image_path)
                
                # Perform structure analysis with retry for network issues
                structure_result = self._structure_engine.ocr(preprocessed_path, cls=True)
                
                # Parse structure results with enhanced classification
                regions = self._parse_structure_result(structure_result)
                
                # Perform advanced layout analysis
                regions = self._enhance_layout_classification(regions, preprocessed_path)
                
                # Sort regions by reading order (top to bottom, left to right)
                regions = self._sort_regions_by_reading_order(regions)
                
                # Calculate confidence metrics
                confidence_metrics = self._calculate_confidence_metrics(regions)
                
                processing_time = time.time() - start_time
                
                # Clean up preprocessed image
                if preprocessed_path != image_path:
                    try:
                        os.remove(preprocessed_path)
                    except OSError:
                        pass
                
                return LayoutResult(
                    regions=regions,
                    tables=[],  # Tables will be populated in extract_tables method
                    confidence_score=confidence_metrics['overall'],
                    processing_time=processing_time
                )
                
            except Exception as e:
                # Convert certain errors to retryable network errors
                if any(keyword in str(e).lower() for keyword in ['network', 'connection', 'timeout', 'model']):
                    raise NetworkRetryError(f"Layout analysis network error: {e}")
                else:
                    raise OCRProcessingError(f"Layout analysis failed: {e}")
        
        try:
            return perform_layout_analysis()
        except NetworkRetryError as e:
            raise OCRProcessingError(f"Layout analysis failed after retries: {e}")
        except Exception as e:
            raise OCRProcessingError(f"Layout analysis error: {e}")
    
    def _enhance_layout_classification(self, regions: List[Region], image_path: str) -> List[Region]:
        """
        Enhance layout classification with advanced heuristics
        
        Args:
            regions: Initial regions from structure analysis
            image_path: Path to preprocessed image
            
        Returns:
            Enhanced regions with better classification
        """
        try:
            # Load image for additional analysis
            image = cv2.imread(image_path)
            if image is None:
                return regions
            
            image_height, image_width = image.shape[:2]
            
            enhanced_regions = []
            
            for region in regions:
                # Create enhanced region copy
                enhanced_region = Region(
                    coordinates=region.coordinates,
                    classification=region.classification,
                    confidence=region.confidence,
                    content=region.content,
                    metadata=region.metadata.copy()
                )
                
                # Add position-based metadata
                enhanced_region.metadata.update({
                    'relative_position': {
                        'x_ratio': region.coordinates.x / image_width,
                        'y_ratio': region.coordinates.y / image_height,
                        'width_ratio': region.coordinates.width / image_width,
                        'height_ratio': region.coordinates.height / image_height
                    },
                    'area': region.coordinates.width * region.coordinates.height
                })
                
                # Refine classification based on enhanced analysis
                enhanced_region.classification = self._refine_region_classification(
                    enhanced_region, image_height, image_width
                )
                
                enhanced_regions.append(enhanced_region)
            
            return enhanced_regions
            
        except Exception as e:
            logger.warning(f"Layout enhancement failed: {e}")
            return regions
    
    def _refine_region_classification(self, region: Region, image_height: int, image_width: int) -> RegionType:
        """
        Refine region classification using advanced heuristics
        
        Args:
            region: Region to classify
            image_height: Total image height
            image_width: Total image width
            
        Returns:
            Refined RegionType
        """
        if not region.content:
            return RegionType.IMAGE
        
        text = region.content.strip()
        bbox = region.coordinates
        
        # Position-based classification
        y_ratio = bbox.y / image_height
        width_ratio = bbox.width / image_width
        height_ratio = bbox.height / image_height
        
        # List detection (enhanced) - check this first before header detection
        list_indicators = ['•', '-', '*', '○', '▪', '▫']
        numbered_pattern = any(text.startswith(f'{i}.') for i in range(1, 20))
        
        if (any(text.startswith(indicator) for indicator in list_indicators) or
            numbered_pattern or
            any(f'\n{indicator}' in text for indicator in list_indicators) or
            any(f'\n{i}.' in text for i in range(1, 20))):
            return RegionType.LIST
        
        # Header detection (enhanced)
        if (y_ratio < 0.2 or  # Top 20% of image
            (len(text) < 80 and 
             (text.isupper() or 
              any(keyword in text.lower() for keyword in ['title', 'chapter', 'section']) or
              width_ratio > 0.6))):  # Wide text likely to be header
            return RegionType.HEADER
        
        # Table detection (basic - will be enhanced in subtask 3.4)
        if (('\t' in text or '|' in text or 
             text.count(' ') > len(text) * 0.3) and  # Lots of spaces
            height_ratio > 0.1):  # Reasonable height
            return RegionType.TABLE
        
        # Default to paragraph
        return RegionType.PARAGRAPH
    
    def _sort_regions_by_reading_order(self, regions: List[Region]) -> List[Region]:
        """
        Sort regions by natural reading order (top to bottom, left to right)
        
        Args:
            regions: List of regions to sort
            
        Returns:
            Sorted list of regions
        """
        def reading_order_key(region: Region) -> Tuple[int, int]:
            # Group by approximate rows (with tolerance for slight misalignment)
            row_group = int(region.coordinates.y // 50)  # 50px tolerance
            return (row_group, int(region.coordinates.x))
        
        return sorted(regions, key=reading_order_key)
    
    def _calculate_confidence_metrics(self, regions: List[Region]) -> Dict[str, float]:
        """
        Calculate detailed confidence metrics for layout analysis
        
        Args:
            regions: List of analyzed regions
            
        Returns:
            Dictionary containing confidence metrics
        """
        if not regions:
            return {
                'overall': 0.0,
                'text_confidence': 0.0,
                'layout_confidence': 0.0,
                'region_count': 0
            }
        
        # Calculate text confidence (average of all text confidences)
        text_confidences = [r.confidence for r in regions if r.confidence > 0]
        text_confidence = sum(text_confidences) / len(text_confidences) if text_confidences else 0.0
        
        # Calculate layout confidence based on region distribution and classification
        layout_confidence = self._calculate_layout_confidence(regions)
        
        # Overall confidence is weighted average
        overall_confidence = (text_confidence * 0.7 + layout_confidence * 0.3)
        
        return {
            'overall': round(overall_confidence, 3),
            'text_confidence': round(text_confidence, 3),
            'layout_confidence': round(layout_confidence, 3),
            'region_count': len(regions)
        }
    
    def _calculate_layout_confidence(self, regions: List[Region]) -> float:
        """
        Calculate confidence score for layout analysis quality
        
        Args:
            regions: List of analyzed regions
            
        Returns:
            Layout confidence score (0.0 to 1.0)
        """
        if not regions:
            return 0.0
        
        confidence_factors = []
        
        # Factor 1: Region diversity (good layout should have different types)
        region_types = set(r.classification for r in regions)
        type_diversity = len(region_types) / len(RegionType)
        confidence_factors.append(type_diversity)
        
        # Factor 2: Reasonable region sizes (not too small or too large)
        reasonable_sizes = 0
        for region in regions:
            area = region.coordinates.width * region.coordinates.height
            if 100 < area < 500000:  # Reasonable area range
                reasonable_sizes += 1
        size_factor = reasonable_sizes / len(regions)
        confidence_factors.append(size_factor)
        
        # Factor 3: Text content quality (regions should have meaningful content)
        meaningful_content = 0
        for region in regions:
            if region.content and len(region.content.strip()) > 3:
                meaningful_content += 1
        content_factor = meaningful_content / len(regions)
        confidence_factors.append(content_factor)
        
        # Return average of all factors
        return sum(confidence_factors) / len(confidence_factors)
    
    def _parse_structure_result(self, structure_result: List) -> List[Region]:
        """
        Parse PaddleOCR structure result into Region objects
        
        Args:
            structure_result: Raw PaddleOCR structure result
            
        Returns:
            List of Region objects
        """
        regions = []
        
        for item in structure_result:
            if not item or len(item) < 2:
                continue
            
            try:
                # Extract bounding box coordinates
                bbox_coords = item[0]
                if len(bbox_coords) != 4 or len(bbox_coords[0]) != 2:
                    continue
                
                # Calculate bounding box
                x_coords = [point[0] for point in bbox_coords]
                y_coords = [point[1] for point in bbox_coords]
                
                bbox = BoundingBox(
                    x=min(x_coords),
                    y=min(y_coords),
                    width=max(x_coords) - min(x_coords),
                    height=max(y_coords) - min(y_coords)
                )
                
                # Extract text and confidence
                text_info = item[1]
                if isinstance(text_info, tuple) and len(text_info) >= 2:
                    text_content = text_info[0]
                    confidence = float(text_info[1])
                else:
                    text_content = str(text_info)
                    confidence = 0.8  # Default confidence
                
                # Classify region type based on content and position
                region_type = self._classify_region(text_content, bbox)
                
                region = Region(
                    coordinates=bbox,
                    classification=region_type,
                    confidence=confidence,
                    content=text_content
                )
                
                regions.append(region)
                
            except Exception as e:
                logger.warning(f"Failed to parse structure item: {e}")
                continue
        
        return regions
    
    def _classify_region(self, text_content: str, bbox: BoundingBox) -> RegionType:
        """
        Classify region type based on content and position
        
        Args:
            text_content: Extracted text content
            bbox: Bounding box of the region
            
        Returns:
            RegionType classification
        """
        if not text_content or not text_content.strip():
            return RegionType.IMAGE
        
        text = text_content.strip()
        
        # Simple heuristics for classification
        # This can be enhanced with more sophisticated ML models
        
        # Check for list patterns first (before header detection)
        list_indicators = ['•', '-', '*', '○', '▪', '▫']
        numbered_pattern = any(text.startswith(f'{i}.') for i in range(1, 20))
        
        if (any(text.startswith(indicator) for indicator in list_indicators) or
            numbered_pattern or
            any(f'\n{indicator}' in text for indicator in list_indicators) or
            any(f'\n{i}.' in text for i in range(1, 20))):
            return RegionType.LIST
        
        # Check for header patterns
        if (len(text) < 100 and 
            (text.isupper() or 
             any(char.isdigit() for char in text[:10]) or
             bbox.y < 100)):  # Likely header if near top
            return RegionType.HEADER
        
        # Default to paragraph for regular text
        return RegionType.PARAGRAPH
    
    def extract_text(self, image_path: str, regions: List[Region]) -> List[Region]:
        """
        Extract text from specified regions using OCR with retry mechanism
        
        Args:
            image_path: Path to image file
            regions: List of regions to extract text from
            
        Returns:
            List of regions with updated text content
        """
        if not self._ocr_engine:
            raise OCRProcessingError("OCR engine not initialized")
        
        @retry_handler.retry(RetryConfig(max_retries=3, base_delay=1.0))
        def perform_text_extraction():
            try:
                # If no specific regions provided, use full image OCR
                if not regions:
                    result = self._ocr_engine.ocr(image_path, cls=True)
                    return self._parse_ocr_result(result)
                
                # Extract text from specific regions
                updated_regions = []
                image = cv2.imread(image_path)
                
                for region in regions:
                    try:
                        # Crop region from image
                        x = int(region.coordinates.x)
                        y = int(region.coordinates.y)
                        w = int(region.coordinates.width)
                        h = int(region.coordinates.height)
                        
                        cropped = image[y:y+h, x:x+w]
                        
                        # Save cropped region temporarily
                        temp_path = f"/tmp/region_{hash(str(region.coordinates))}.jpg"
                        cv2.imwrite(temp_path, cropped)
                        
                        # Perform OCR on cropped region with retry
                        ocr_result = self._ocr_engine.ocr(temp_path, cls=True)
                        
                        # Update region with OCR result
                        if ocr_result and ocr_result[0]:
                            text_parts = []
                            confidences = []
                            
                            for line in ocr_result[0]:
                                if len(line) >= 2:
                                    text_parts.append(line[1][0])
                                    confidences.append(line[1][1])
                            
                            region.content = ' '.join(text_parts)
                            region.confidence = sum(confidences) / len(confidences) if confidences else 0.0
                        
                        updated_regions.append(region)
                        
                        # Clean up temporary file
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass
                            
                    except Exception as e:
                        logger.warning(f"Failed to extract text from region: {e}")
                        updated_regions.append(region)
                
                return updated_regions
                
            except Exception as e:
                # Convert certain errors to retryable network errors
                if any(keyword in str(e).lower() for keyword in ['network', 'connection', 'timeout', 'model']):
                    raise NetworkRetryError(f"Text extraction network error: {e}")
                else:
                    raise OCRProcessingError(f"Text extraction failed: {e}")
        
        try:
            return perform_text_extraction()
        except NetworkRetryError as e:
            raise OCRProcessingError(f"Text extraction failed after retries: {e}")
        except Exception as e:
            raise OCRProcessingError(f"Text extraction error: {e}")
    
    def _parse_ocr_result(self, ocr_result: List) -> List[Region]:
        """
        Parse standard OCR result into Region objects
        
        Args:
            ocr_result: Raw PaddleOCR result
            
        Returns:
            List of Region objects
        """
        regions = []
        
        if not ocr_result or not ocr_result[0]:
            return regions
        
        for line in ocr_result[0]:
            if len(line) < 2:
                continue
            
            try:
                # Extract coordinates
                bbox_coords = line[0]
                x_coords = [point[0] for point in bbox_coords]
                y_coords = [point[1] for point in bbox_coords]
                
                bbox = BoundingBox(
                    x=min(x_coords),
                    y=min(y_coords),
                    width=max(x_coords) - min(x_coords),
                    height=max(y_coords) - min(y_coords)
                )
                
                # Extract text and confidence
                text_content = line[1][0]
                confidence = line[1][1]
                
                # Classify region
                region_type = self._classify_region(text_content, bbox)
                
                region = Region(
                    coordinates=bbox,
                    classification=region_type,
                    confidence=confidence,
                    content=text_content
                )
                
                regions.append(region)
                
            except Exception as e:
                logger.warning(f"Failed to parse OCR line: {e}")
                continue
        
        return regions
    
    def extract_tables(self, image_path: str, regions: List[Region]) -> List[TableStructure]:
        """
        Extract table structures from regions using PP-Structure table recognition
        
        Args:
            image_path: Path to image file
            regions: List of regions that might contain tables
            
        Returns:
            List of TableStructure objects
        """
        if not self._structure_engine:
            raise OCRProcessingError("Structure engine not initialized")
        
        try:
            tables = []
            image = cv2.imread(image_path)
            
            if image is None:
                raise OCRProcessingError(f"Could not load image: {image_path}")
            
            # Filter regions that are likely to be tables
            table_regions = [r for r in regions if r.classification == RegionType.TABLE]
            
            # If no table regions identified, try to detect tables in the full image
            if not table_regions:
                tables.extend(self._detect_tables_in_full_image(image_path))
            else:
                # Process each table region
                for region in table_regions:
                    table_structure = self._extract_table_from_region(image, region)
                    if table_structure:
                        tables.append(table_structure)
            
            logger.info(f"Extracted {len(tables)} table structures")
            return tables
            
        except Exception as e:
            raise OCRProcessingError(f"Table extraction failed: {e}")
    
    def _detect_tables_in_full_image(self, image_path: str) -> List[TableStructure]:
        """
        Detect tables in the full image using PP-Structure
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of detected TableStructure objects
        """
        try:
            # Use PaddleOCR's table recognition capability
            from paddleocr import PPStructure
            
            # Initialize table structure engine
            table_engine = PPStructure(
                use_gpu=self.use_gpu,
                show_log=False,
                lang=self.lang
            )
            
            # Perform table detection
            result = table_engine(image_path)
            
            tables = []
            for item in result:
                if item.get('type') == 'table':
                    table_structure = self._parse_table_result(item)
                    if table_structure:
                        tables.append(table_structure)
            
            return tables
            
        except ImportError:
            logger.warning("PPStructure not available, using fallback table detection")
            return self._fallback_table_detection(image_path)
        except Exception as e:
            logger.warning(f"Table detection failed: {e}")
            return []
    
    def _extract_table_from_region(self, image: np.ndarray, region: Region) -> Optional[TableStructure]:
        """
        Extract table structure from a specific region
        
        Args:
            image: OpenCV image array
            region: Region containing table
            
        Returns:
            TableStructure object or None if extraction fails
        """
        try:
            # Crop table region
            x = int(region.coordinates.x)
            y = int(region.coordinates.y)
            w = int(region.coordinates.width)
            h = int(region.coordinates.height)
            
            # Add padding to ensure complete table capture
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(image.shape[1] - x, w + 2 * padding)
            h = min(image.shape[0] - y, h + 2 * padding)
            
            cropped_table = image[y:y+h, x:x+w]
            
            # Save cropped table temporarily
            temp_path = f"/tmp/table_{hash(str(region.coordinates))}.jpg"
            cv2.imwrite(temp_path, cropped_table)
            
            # Extract table structure
            table_structure = self._analyze_table_structure(temp_path, region.coordinates)
            
            # Clean up temporary file
            try:
                os.remove(temp_path)
            except OSError:
                pass
            
            return table_structure
            
        except Exception as e:
            logger.warning(f"Failed to extract table from region: {e}")
            return None
    
    def _analyze_table_structure(self, table_image_path: str, original_coords: BoundingBox) -> Optional[TableStructure]:
        """
        Analyze table structure using OCR and layout analysis
        
        Args:
            table_image_path: Path to cropped table image
            original_coords: Original coordinates of the table
            
        Returns:
            TableStructure object or None if analysis fails
        """
        try:
            # Perform OCR on table image
            ocr_result = self._ocr_engine.ocr(table_image_path, cls=True)
            
            if not ocr_result or not ocr_result[0]:
                return None
            
            # Parse table cells from OCR result
            cells_data = self._parse_table_cells(ocr_result[0])
            
            if not cells_data:
                return None
            
            # Organize cells into grid structure
            table_grid = self._organize_cells_into_grid(cells_data)
            
            if not table_grid:
                return None
            
            # Detect if table has headers
            has_headers = self._detect_table_headers(table_grid)
            
            return TableStructure(
                rows=len(table_grid),
                columns=len(table_grid[0]) if table_grid else 0,
                cells=table_grid,
                coordinates=original_coords,
                has_headers=has_headers
            )
            
        except Exception as e:
            logger.warning(f"Table structure analysis failed: {e}")
            return None
    
    def _parse_table_cells(self, ocr_result: List) -> List[Dict[str, Any]]:
        """
        Parse OCR result to extract table cell information
        
        Args:
            ocr_result: OCR result from table image
            
        Returns:
            List of cell data dictionaries
        """
        cells = []
        
        for line in ocr_result:
            if len(line) < 2:
                continue
            
            try:
                # Extract cell coordinates
                bbox_coords = line[0]
                x_coords = [point[0] for point in bbox_coords]
                y_coords = [point[1] for point in bbox_coords]
                
                cell_bbox = BoundingBox(
                    x=min(x_coords),
                    y=min(y_coords),
                    width=max(x_coords) - min(x_coords),
                    height=max(y_coords) - min(y_coords)
                )
                
                # Extract cell content
                text_content = line[1][0]
                confidence = line[1][1]
                
                cells.append({
                    'bbox': cell_bbox,
                    'content': text_content.strip(),
                    'confidence': confidence,
                    'center_x': cell_bbox.x + cell_bbox.width / 2,
                    'center_y': cell_bbox.y + cell_bbox.height / 2
                })
                
            except Exception as e:
                logger.warning(f"Failed to parse table cell: {e}")
                continue
        
        return cells
    
    def _organize_cells_into_grid(self, cells_data: List[Dict[str, Any]]) -> List[List[str]]:
        """
        Organize cell data into a 2D grid structure
        
        Args:
            cells_data: List of cell data dictionaries
            
        Returns:
            2D list representing table grid
        """
        if not cells_data:
            return []
        
        try:
            # Sort cells by position (top to bottom, left to right)
            cells_data.sort(key=lambda cell: (cell['center_y'], cell['center_x']))
            
            # Group cells into rows based on Y coordinates
            rows = []
            current_row = []
            current_y = cells_data[0]['center_y']
            y_tolerance = 20  # Pixels tolerance for same row
            
            for cell in cells_data:
                if abs(cell['center_y'] - current_y) <= y_tolerance:
                    current_row.append(cell)
                else:
                    if current_row:
                        # Sort current row by X coordinate
                        current_row.sort(key=lambda c: c['center_x'])
                        rows.append(current_row)
                    current_row = [cell]
                    current_y = cell['center_y']
            
            # Add the last row
            if current_row:
                current_row.sort(key=lambda c: c['center_x'])
                rows.append(current_row)
            
            # Convert to string grid
            max_cols = max(len(row) for row in rows) if rows else 0
            table_grid = []
            
            for row in rows:
                row_data = []
                for i in range(max_cols):
                    if i < len(row):
                        row_data.append(row[i]['content'])
                    else:
                        row_data.append('')  # Empty cell
                table_grid.append(row_data)
            
            return table_grid
            
        except Exception as e:
            logger.warning(f"Failed to organize cells into grid: {e}")
            return []
    
    def _detect_table_headers(self, table_grid: List[List[str]]) -> bool:
        """
        Detect if table has header row based on content analysis
        
        Args:
            table_grid: 2D table grid
            
        Returns:
            True if table likely has headers
        """
        if not table_grid or len(table_grid) < 2:
            return False
        
        try:
            first_row = table_grid[0]
            second_row = table_grid[1] if len(table_grid) > 1 else []
            
            # Heuristics for header detection
            header_indicators = 0
            
            # Check if first row has different formatting patterns
            for i, cell in enumerate(first_row):
                if not cell:
                    continue
                
                # Headers often shorter and more descriptive
                if len(cell) < 50 and any(char.isalpha() for char in cell):
                    header_indicators += 1
                
                # Compare with second row if available
                if i < len(second_row) and second_row[i]:
                    # If first row is text and second row has numbers/data
                    if (cell.replace(' ', '').isalpha() and 
                        any(char.isdigit() for char in second_row[i])):
                        header_indicators += 1
            
            # Consider it a header if more than half the cells show header patterns
            return header_indicators > len(first_row) / 2
            
        except Exception as e:
            logger.warning(f"Header detection failed: {e}")
            return False
    
    def _fallback_table_detection(self, image_path: str) -> List[TableStructure]:
        """
        Fallback table detection using basic OCR and heuristics
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of detected tables using fallback method
        """
        try:
            # Perform regular OCR
            ocr_result = self._ocr_engine.ocr(image_path, cls=True)
            
            if not ocr_result or not ocr_result[0]:
                return []
            
            # Look for table-like patterns in OCR result
            table_candidates = []
            
            for line in ocr_result[0]:
                if len(line) < 2:
                    continue
                
                text_content = line[1][0]
                
                # Simple heuristics for table detection
                if (('\t' in text_content or '|' in text_content or 
                     text_content.count(' ') > len(text_content) * 0.3) and
                    len(text_content.strip()) > 10):
                    
                    # Extract coordinates
                    bbox_coords = line[0]
                    x_coords = [point[0] for point in bbox_coords]
                    y_coords = [point[1] for point in bbox_coords]
                    
                    bbox = BoundingBox(
                        x=min(x_coords),
                        y=min(y_coords),
                        width=max(x_coords) - min(x_coords),
                        height=max(y_coords) - min(y_coords)
                    )
                    
                    # Create simple table structure
                    cells = [cell.strip() for cell in text_content.split() if cell.strip()]
                    if len(cells) >= 2:  # At least 2 columns
                        table_structure = TableStructure(
                            rows=1,
                            columns=len(cells),
                            cells=[cells],
                            coordinates=bbox,
                            has_headers=False
                        )
                        table_candidates.append(table_structure)
            
            return table_candidates
            
        except Exception as e:
            logger.warning(f"Fallback table detection failed: {e}")
            return []
    
    def _parse_table_result(self, table_item: Dict[str, Any]) -> Optional[TableStructure]:
        """
        Parse table result from PP-Structure
        
        Args:
            table_item: Table item from PP-Structure result
            
        Returns:
            TableStructure object or None
        """
        try:
            # Extract table data from PP-Structure result
            if 'res' not in table_item:
                return None
            
            table_data = table_item['res']
            
            # Parse table structure
            if isinstance(table_data, dict) and 'html' in table_data:
                # Parse HTML table structure (if available)
                return self._parse_html_table(table_data['html'])
            elif isinstance(table_data, list):
                # Parse list-based table data
                return self._parse_list_table(table_data)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse table result: {e}")
            return None
    
    def _parse_html_table(self, html_content: str) -> Optional[TableStructure]:
        """
        Parse HTML table content to extract structure
        
        Args:
            html_content: HTML table content
            
        Returns:
            TableStructure object or None
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return None
            
            rows = table.find_all('tr')
            if not rows:
                return None
            
            table_grid = []
            max_cols = 0
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                table_grid.append(row_data)
                max_cols = max(max_cols, len(row_data))
            
            # Normalize row lengths
            for row in table_grid:
                while len(row) < max_cols:
                    row.append('')
            
            # Detect headers (first row with th tags)
            has_headers = bool(rows[0].find_all('th')) if rows else False
            
            return TableStructure(
                rows=len(table_grid),
                columns=max_cols,
                cells=table_grid,
                coordinates=BoundingBox(0, 0, 0, 0),  # Will be updated with actual coordinates
                has_headers=has_headers
            )
            
        except ImportError:
            logger.warning("BeautifulSoup not available for HTML table parsing")
            return None
        except Exception as e:
            logger.warning(f"HTML table parsing failed: {e}")
            return None
    
    def _parse_list_table(self, table_data: List) -> Optional[TableStructure]:
        """
        Parse list-based table data
        
        Args:
            table_data: List-based table data
            
        Returns:
            TableStructure object or None
        """
        try:
            if not table_data:
                return None
            
            # Convert list data to grid format
            table_grid = []
            max_cols = 0
            
            for row_data in table_data:
                if isinstance(row_data, list):
                    row = [str(cell) for cell in row_data]
                    table_grid.append(row)
                    max_cols = max(max_cols, len(row))
                elif isinstance(row_data, str):
                    # Split string into cells
                    row = [cell.strip() for cell in row_data.split('\t') if cell.strip()]
                    if not row:
                        row = [cell.strip() for cell in row_data.split() if cell.strip()]
                    table_grid.append(row)
                    max_cols = max(max_cols, len(row))
            
            # Normalize row lengths
            for row in table_grid:
                while len(row) < max_cols:
                    row.append('')
            
            if not table_grid:
                return None
            
            return TableStructure(
                rows=len(table_grid),
                columns=max_cols,
                cells=table_grid,
                coordinates=BoundingBox(0, 0, 0, 0),  # Will be updated with actual coordinates
                has_headers=self._detect_table_headers(table_grid)
            )
            
        except Exception as e:
            logger.warning(f"List table parsing failed: {e}")
            return None