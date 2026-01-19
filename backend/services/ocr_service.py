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
    
    def preprocess_image(self, image_path: str, output_path: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Preprocess image for optimal OCR results
        
        Args:
            image_path: Path to input image
            output_path: Path for preprocessed image (optional)
            
        Returns:
            Tuple of (path to preprocessed image, scale info dict)
        """
        try:
            # Load image
            image = Image.open(image_path)
            original_width, original_height = image.size
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Apply preprocessing steps
            image = self._enhance_image_quality(image)
            image, scale_info = self._normalize_image_size_with_scale(image)
            
            # Record original dimensions for coordinate mapping
            scale_info['original_width'] = original_width
            scale_info['original_height'] = original_height
            
            # Save preprocessed image
            if output_path is None:
                base_path = Path(image_path)
                output_path = str(base_path.parent / f"{base_path.stem}_preprocessed{base_path.suffix}")
            
            image.save(output_path, quality=95, optimize=True)
            
            logger.info(f"Image preprocessed and saved to: {output_path}, scale_info: {scale_info}")
            return output_path, scale_info
            
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
    
    def _normalize_image_size_with_scale(self, image: Image.Image, max_dimension: int = 2048) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Normalize image size to optimal dimensions for OCR and return scale info
        
        Args:
            image: PIL Image object
            max_dimension: Maximum dimension for resizing
            
        Returns:
            Tuple of (Resized PIL Image object, scale info dict)
        """
        width, height = image.size
        scale_info = {
            'preprocessed_width': width,
            'preprocessed_height': height,
            'scale_x': 1.0,
            'scale_y': 1.0,
            'was_resized': False
        }
        
        # Only resize if image is too large
        if max(width, height) > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            # Calculate scale factors (from preprocessed back to original)
            scale_info['scale_x'] = width / new_width
            scale_info['scale_y'] = height / new_height
            scale_info['preprocessed_width'] = new_width
            scale_info['preprocessed_height'] = new_height
            scale_info['was_resized'] = True
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Image resized from {width}x{height} to {new_width}x{new_height}, scale: {scale_info['scale_x']:.3f}x{scale_info['scale_y']:.3f}")
        
        return image, scale_info
    
    def _normalize_image_size(self, image: Image.Image, max_dimension: int = 2048) -> Image.Image:
        """
        Normalize image size to optimal dimensions for OCR (legacy method)
        
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
        
        # Store raw output path for later saving
        self._current_image_path = image_path
        
        @retry_handler.retry(RetryConfig(max_retries=3, base_delay=1.5))
        def perform_layout_analysis():
            try:
                import time
                import json
                start_time = time.time()
                
                # Preprocess image for better results and get scale info
                preprocessed_path, scale_info = self.preprocess_image(image_path)
                
                # Perform structure analysis with retry for network issues
                structure_result = self._structure_engine.ocr(preprocessed_path, cls=True)
                
                # Save raw OCR output for download
                self._save_raw_ocr_output(image_path, structure_result, scale_info)
                
                # Parse structure results with enhanced classification
                regions = self._parse_structure_result(structure_result)
                
                # Convert coordinates back to original image scale
                regions = self._scale_regions_to_original(regions, scale_info)
                
                # Perform advanced layout analysis (use original image path for correct dimensions)
                regions = self._enhance_layout_classification(regions, image_path)
                
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
    
    def _save_raw_ocr_output(self, image_path: str, structure_result: List, scale_info: Dict[str, Any]) -> None:
        """
        Save raw PaddleOCR output for download
        
        Args:
            image_path: Path to the original image
            structure_result: Raw OCR result from PaddleOCR
            scale_info: Scale information from preprocessing
        """
        import json
        from pathlib import Path
        
        try:
            # Extract job_id from image path (format: {job_id}_page1.png)
            image_name = Path(image_path).stem
            if '_page' in image_name:
                job_id = image_name.split('_page')[0]
            else:
                job_id = image_name
            
            # Determine output folder
            output_folder = Path(image_path).parent
            
            # Prepare raw JSON output
            raw_json_data = {
                'job_id': job_id,
                'image_path': str(image_path),
                'scale_info': scale_info,
                'ocr_result': []
            }
            
            # Process OCR results
            if structure_result and len(structure_result) > 0:
                actual_results = structure_result[0] if structure_result else []
                
                for idx, item in enumerate(actual_results):
                    if not item or len(item) < 2:
                        continue
                    
                    try:
                        bbox_coords = item[0]
                        text_info = item[1]
                        
                        # Extract text and confidence
                        if isinstance(text_info, tuple) and len(text_info) >= 2:
                            text_content = text_info[0]
                            confidence = float(text_info[1])
                        else:
                            text_content = str(text_info)
                            confidence = 0.0
                        
                        # Calculate bounding box
                        x_coords = [point[0] for point in bbox_coords]
                        y_coords = [point[1] for point in bbox_coords]
                        bbox = {
                            'x': min(x_coords),
                            'y': min(y_coords),
                            'width': max(x_coords) - min(x_coords),
                            'height': max(y_coords) - min(y_coords),
                            'points': [[float(p[0]), float(p[1])] for p in bbox_coords]
                        }
                        
                        # Add to JSON
                        raw_json_data['ocr_result'].append({
                            'index': idx,
                            'text': text_content,
                            'confidence': confidence,
                            'bbox': bbox
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to process OCR item {idx}: {e}")
            
            # Save JSON file
            json_path = output_folder / f"{job_id}_raw_ocr.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(raw_json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved raw OCR JSON to: {json_path}")
            
            # Note: HTML will be saved separately when PPStructure table detection runs
            # The HTML contains the actual table structure from PPStructure
            
        except Exception as e:
            logger.warning(f"Failed to save raw OCR output: {e}")
    
    def _save_ppstructure_html(self, image_path: str, ppstructure_result: List) -> None:
        """
        Save PPStructure raw HTML output for download - 包含所有内容（文本+表格）
        同时读取普通 OCR 结果，将未被 PPStructure 识别的文本也添加到 HTML 中
        
        Args:
            image_path: Path to the original image
            ppstructure_result: Raw result from PPStructure
        """
        from pathlib import Path
        import json
        
        try:
            # Extract job_id from image path
            image_name = Path(image_path).stem
            if '_page' in image_name:
                job_id = image_name.split('_page')[0]
            else:
                job_id = image_name
            
            output_folder = Path(image_path).parent
            
            # 保存 PPStructure 原始结果到 JSON 文件
            ppstructure_json_path = output_folder / f"{job_id}_ppstructure.json"
            ppstructure_json_data = {
                'job_id': job_id,
                'image_path': str(image_path),
                'total_items': len(ppstructure_result),
                'items': []
            }
            
            for idx, item in enumerate(ppstructure_result):
                item_data = {
                    'index': idx,
                    'type': item.get('type', 'unknown'),
                    'bbox': item.get('bbox', []),
                    'res': None
                }
                
                # 处理 res 字段
                res = item.get('res', {})
                if isinstance(res, dict):
                    # 表格类型，包含 html 和 cell_bbox
                    item_data['res'] = {
                        'html': res.get('html', ''),
                        'cell_bbox': res.get('cell_bbox', [])
                    }
                elif isinstance(res, list):
                    # 文本类型，包含文本行列表
                    item_data['res'] = []
                    for text_item in res:
                        if isinstance(text_item, dict):
                            item_data['res'].append({
                                'text': text_item.get('text', ''),
                                'confidence': text_item.get('confidence', 0),
                                'text_region': text_item.get('text_region', [])
                            })
                elif isinstance(res, str):
                    item_data['res'] = res
                
                ppstructure_json_data['items'].append(item_data)
            
            with open(ppstructure_json_path, 'w', encoding='utf-8') as f:
                json.dump(ppstructure_json_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved PPStructure JSON to: {ppstructure_json_path}")
            
            # 读取普通 OCR 结果（包含所有文本行）
            ocr_json_path = output_folder / f"{job_id}_raw_ocr.json"
            ocr_text_items = []
            scale_info = {}
            if ocr_json_path.exists():
                with open(ocr_json_path, 'r', encoding='utf-8') as f:
                    ocr_data = json.load(f)
                    ocr_text_items = ocr_data.get('ocr_result', [])
                    scale_info = ocr_data.get('scale_info', {})
                logger.info(f"Loaded {len(ocr_text_items)} text items from OCR JSON")
            
            # 按 y 坐标排序所有 PPStructure 区域
            sorted_items = sorted(ppstructure_result, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1])
            
            # 去重：过滤掉重叠且内容相同的区域（保留第一个）
            def boxes_overlap(bbox1, bbox2, threshold=0.7):
                """检查两个边界框是否重叠超过阈值"""
                x1 = max(bbox1[0], bbox2[0])
                y1 = max(bbox1[1], bbox2[1])
                x2 = min(bbox1[2], bbox2[2])
                y2 = min(bbox1[3], bbox2[3])
                
                if x1 >= x2 or y1 >= y2:
                    return False
                
                intersection = (x2 - x1) * (y2 - y1)
                area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
                area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
                min_area = min(area1, area2)
                
                return intersection / min_area > threshold if min_area > 0 else False
            
            # 过滤重叠且内容相同的区域
            filtered_items = []
            for item in sorted_items:
                bbox = item.get('bbox', [0, 0, 0, 0])
                item_text = self._extract_text_from_res(item.get('res', {}))
                is_duplicate = False
                for existing in filtered_items:
                    existing_bbox = existing.get('bbox', [0, 0, 0, 0])
                    if boxes_overlap(bbox, existing_bbox):
                        # 只有当文本内容也相同时才认为是重复
                        existing_text = self._extract_text_from_res(existing.get('res', {}))
                        if item_text == existing_text or not item_text:
                            is_duplicate = True
                            logger.info(f"Filtered duplicate region: {item.get('type')} overlaps with {existing.get('type')}, same content")
                            break
                if not is_duplicate:
                    filtered_items.append(item)
            
            sorted_items = filtered_items
            
            # 统计各类型数量
            type_counts = {}
            for item in sorted_items:
                item_type = item.get('type', 'unknown')
                type_counts[item_type] = type_counts.get(item_type, 0) + 1
            logger.info(f"PPStructure result types (after dedup): {type_counts}")
            
            # 获取所有 PPStructure 区域的边界框（用于过滤重复文本）
            ppstructure_bboxes = []
            for item in sorted_items:
                bbox = item.get('bbox', [0, 0, 0, 0])
                ppstructure_bboxes.append({
                    'x1': bbox[0], 'y1': bbox[1], 'x2': bbox[2], 'y2': bbox[3],
                    'type': item.get('type', 'unknown')
                })
            
            # 过滤出不在 PPStructure 区域内的文本（避免重复）
            # 坐标需要根据 scale_info 转换
            scale_x = scale_info.get('scale_x', 1.0)
            scale_y = scale_info.get('scale_y', 1.0)
            
            standalone_texts = []
            for text_item in ocr_text_items:
                bbox = text_item.get('bbox', {})
                # 转换坐标到原始图像尺寸
                text_x = bbox.get('x', 0) * scale_x
                text_y = bbox.get('y', 0) * scale_y
                text_x2 = text_x + bbox.get('width', 0) * scale_x
                text_y2 = text_y + bbox.get('height', 0) * scale_y
                text_center_x = (text_x + text_x2) / 2
                text_center_y = (text_y + text_y2) / 2
                
                # 检查文本是否在任何 PPStructure 区域内
                is_inside_ppstructure = False
                for pp_bbox in ppstructure_bboxes:
                    # 如果文本中心点在 PPStructure 区域内，则认为是重复的
                    if (pp_bbox['x1'] <= text_center_x <= pp_bbox['x2'] and
                        pp_bbox['y1'] <= text_center_y <= pp_bbox['y2']):
                        is_inside_ppstructure = True
                        break
                
                if not is_inside_ppstructure:
                    standalone_texts.append({
                        'text': text_item.get('text', ''),
                        'confidence': text_item.get('confidence', 0),
                        'bbox': {
                            'x': text_x, 'y': text_y,
                            'x2': text_x2, 'y2': text_y2
                        },
                        'original_bbox': bbox
                    })
            
            logger.info(f"Found {len(standalone_texts)} standalone text items not in PPStructure regions")
            
            # 调试：检查特定文本
            for text_item in ocr_text_items:
                if 'DOMESTIC' in text_item.get('text', ''):
                    bbox = text_item.get('bbox', {})
                    text_x = bbox.get('x', 0) * scale_x
                    text_y = bbox.get('y', 0) * scale_y
                    text_x2 = text_x + bbox.get('width', 0) * scale_x
                    text_y2 = text_y + bbox.get('height', 0) * scale_y
                    text_center_x = (text_x + text_x2) / 2
                    text_center_y = (text_y + text_y2) / 2
                    logger.info(f"DEBUG DOMESTIC: text='{text_item.get('text')}', center=({text_center_x:.1f}, {text_center_y:.1f})")
                    for pp_bbox in ppstructure_bboxes:
                        if (pp_bbox['x1'] <= text_center_x <= pp_bbox['x2'] and
                            pp_bbox['y1'] <= text_center_y <= pp_bbox['y2']):
                            logger.info(f"DEBUG DOMESTIC: INSIDE {pp_bbox['type']} region ({pp_bbox['x1']:.0f},{pp_bbox['y1']:.0f})-({pp_bbox['x2']:.0f},{pp_bbox['y2']:.0f})")
            
            # 合并 PPStructure 区域和独立文本，按 y 坐标排序
            all_items = []
            
            # 添加 PPStructure 区域
            for idx, item in enumerate(sorted_items):
                bbox = item.get('bbox', [0, 0, 0, 0])
                all_items.append({
                    'source': 'ppstructure',
                    'type': item.get('type', 'unknown'),
                    'data': item,
                    'y': bbox[1],
                    'idx': idx
                })
            
            # 添加独立文本
            for idx, text_item in enumerate(standalone_texts):
                all_items.append({
                    'source': 'ocr',
                    'type': 'text',
                    'data': text_item,
                    'y': text_item['bbox']['y'],
                    'idx': len(sorted_items) + idx
                })
            
            logger.info(f"all_items count: {len(all_items)} (PPStructure: {len(sorted_items)}, standalone: {len(standalone_texts)})")
            
            # 按 y 坐标排序
            all_items.sort(key=lambda x: x['y'])
            
            # Build HTML document with all content
            html_parts = []
            html_parts.append('<!DOCTYPE html>')
            html_parts.append('<html lang="zh-CN">')
            html_parts.append('<head>')
            html_parts.append('<meta charset="UTF-8">')
            html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
            html_parts.append(f'<title>OCR识别结果 - {job_id}</title>')
            html_parts.append('<style>')
            html_parts.append('''
body { 
    font-family: "Microsoft YaHei", "SimSun", Arial, sans-serif; 
    max-width: 900px; 
    margin: 0 auto; 
    padding: 20px;
    line-height: 1.6;
    color: #333;
}
.ocr-region {
    cursor: pointer;
    transition: all 0.2s ease;
    border-radius: 3px;
    position: relative;
    padding: 8px;
    margin: 10px 0;
}
.ocr-region:hover {
    background-color: rgba(66, 133, 244, 0.1);
    outline: 2px solid rgba(66, 133, 244, 0.3);
}
.ocr-region.title {
    font-size: 1.4em;
    font-weight: bold;
    color: #1a1a1a;
    margin: 20px 0 10px 0;
}
.ocr-region.text-block {
    line-height: 1.8;
}
.ocr-region.header, .ocr-region.footer {
    font-size: 0.9em;
    color: #666;
}
.ocr-region.figure-caption, .ocr-region.table-caption {
    font-size: 0.9em;
    color: #666;
    text-align: center;
    font-style: italic;
}
.ocr-region.reference {
    font-size: 0.85em;
    color: #555;
}
.ocr-region.figure-placeholder {
    background: #f5f5f5;
    border: 1px dashed #ccc;
    text-align: center;
    color: #888;
    padding: 30px;
    margin: 15px 0;
}
.table-wrapper {
    margin: 15px 0;
    overflow-x: auto;
}
table { 
    border-collapse: collapse; 
    width: 100%; 
    font-size: 0.95em;
}
table td, table th { 
    border: 1px solid #ccc; 
    padding: 8px 12px; 
    text-align: left;
    vertical-align: top;
}
table th { 
    background: #f5f5f5; 
    font-weight: bold;
}
table tr:nth-child(even) {
    background: #fafafa;
}
.no-content {
    text-align: center;
    color: #888;
    padding: 40px;
    font-size: 1.1em;
}
.editable-content {
    display: block;
}
''')
            html_parts.append('</style>')
            html_parts.append('</head>')
            html_parts.append('<body>')
            
            if not all_items:
                html_parts.append('<div class="no-content">📋 未检测到内容</div>')
            else:
                # Process all items in reading order
                for item_wrapper in all_items:
                    idx = item_wrapper['idx']
                    source = item_wrapper['source']
                    item_type = item_wrapper['type']
                    
                    if source == 'ocr':
                        # 来自普通 OCR 的独立文本
                        text_data = item_wrapper['data']
                        text_content = text_data.get('text', '')
                        confidence = text_data.get('confidence', 0)
                        bbox = text_data.get('bbox', {})
                        bbox_data = json.dumps({'x': float(bbox.get('x', 0)), 'y': float(bbox.get('y', 0)), 'x2': float(bbox.get('x2', 0)), 'y2': float(bbox.get('y2', 0))})
                        
                        if text_content:
                            html_parts.append(f'<div class="ocr-region text-block" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\' data-confidence="{confidence:.2f}">')
                            html_parts.append(f'<span class="editable-content">{text_content}</span>')
                            html_parts.append('</div>')
                    else:
                        # 来自 PPStructure 的区域
                        item = item_wrapper['data']
                        res = item.get('res', {})
                        bbox = item.get('bbox', [0, 0, 0, 0])
                        bbox_data = json.dumps({'x': float(bbox[0]), 'y': float(bbox[1]), 'x2': float(bbox[2]), 'y2': float(bbox[3])})
                        
                        if item_type == 'table':
                            # 表格：使用 PPStructure 返回的 HTML
                            if isinstance(res, dict) and 'html' in res:
                                table_html = res['html']
                                table_html = table_html.replace('<html>', '').replace('</html>', '')
                                table_html = table_html.replace('<body>', '').replace('</body>', '')
                                html_parts.append(f'<div class="ocr-region table-wrapper" data-region-id="{idx}" data-region-type="table" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(table_html.strip())
                                html_parts.append('</div>')
                            elif isinstance(res, str):
                                html_parts.append(f'<div class="ocr-region table-wrapper" data-region-id="{idx}" data-region-type="table" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(res)
                                html_parts.append('</div>')
                        
                        elif item_type == 'title':
                            # 标题
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region title" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'text':
                            # 普通文本
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region text-block" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'figure':
                            # 图像区域：尝试从普通 OCR 结果中提取该区域内的文本
                            figure_bbox = item.get('bbox', [0, 0, 0, 0])
                            figure_texts = []
                            for text_item in ocr_text_items:
                                t_bbox = text_item.get('bbox', {})
                                # 转换坐标到原始图像尺寸
                                t_x = t_bbox.get('x', 0) * scale_x
                                t_y = t_bbox.get('y', 0) * scale_y
                                t_x2 = t_x + t_bbox.get('width', 0) * scale_x
                                t_y2 = t_y + t_bbox.get('height', 0) * scale_y
                                t_center_x = (t_x + t_x2) / 2
                                t_center_y = (t_y + t_y2) / 2
                                
                                # 检查文本是否在 figure 区域内
                                if (figure_bbox[0] <= t_center_x <= figure_bbox[2] and
                                    figure_bbox[1] <= t_center_y <= figure_bbox[3]):
                                    figure_texts.append({
                                        'text': text_item.get('text', ''),
                                        'y': t_y,
                                        'x': t_x
                                    })
                            
                            if figure_texts:
                                # 按 y 坐标排序，然后按 x 坐标
                                figure_texts.sort(key=lambda x: (x['y'], x['x']))
                                combined_text = ' '.join([t['text'] for t in figure_texts])
                                html_parts.append(f'<div class="ocr-region text-block" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{combined_text}</span>')
                                html_parts.append('</div>')
                            else:
                                # 没有文本，显示图像占位符
                                html_parts.append(f'<div class="ocr-region figure-placeholder" data-region-id="{idx}" data-region-type="figure" data-bbox=\'{bbox_data}\'>[图像区域]</div>')
                        
                        elif item_type == 'figure_caption':
                            # 图像说明
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region figure-caption" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'table_caption':
                            # 表格说明
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region table-caption" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'header':
                            # 页眉
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region header" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'footer':
                            # 页脚
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region footer" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'reference':
                            # 参考文献
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region reference" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
                        
                        elif item_type == 'equation':
                            # 公式
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region equation" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content"><em>{text_content}</em></span>')
                                html_parts.append('</div>')
                        
                        else:
                            # 其他类型，尝试提取文本
                            text_content = self._extract_text_from_res(res)
                            if text_content:
                                html_parts.append(f'<div class="ocr-region text-block" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                                html_parts.append(f'<span class="editable-content">{text_content}</span>')
                                html_parts.append('</div>')
            
            html_parts.append('</body>')
            html_parts.append('</html>')
            
            # Save HTML file
            html_content = '\n'.join(html_parts)
            html_path = output_folder / f"{job_id}_raw_ocr.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"Saved full HTML to: {html_path} with {len(all_items)} items (PPStructure: {len(sorted_items)}, standalone OCR text: {len(standalone_texts)})")
            
        except Exception as e:
            logger.warning(f"Failed to save PPStructure HTML output: {e}")
            import traceback
            logger.warning(traceback.format_exc())
    
    def _extract_text_from_res(self, res) -> str:
        """
        Extract text content from PPStructure result 'res' field
        
        Args:
            res: The 'res' field from PPStructure result item
            
        Returns:
            Extracted text as a string
        """
        if isinstance(res, str):
            return res
        
        if isinstance(res, list):
            text_lines = []
            for item in res:
                if isinstance(item, dict):
                    # Format: {'text': ..., 'confidence': ..., 'text_region': ...}
                    if 'text' in item:
                        text_lines.append(str(item['text']))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    # Format: [bbox, (text, confidence)] or [bbox, text]
                    text_info = item[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                        text_lines.append(str(text_info[0]))
                    else:
                        text_lines.append(str(text_info))
                elif isinstance(item, str):
                    text_lines.append(item)
            return ' '.join(text_lines)
        
        if isinstance(res, dict):
            # Try common keys
            if 'text' in res:
                return str(res['text'])
            if 'html' in res:
                # Strip HTML tags for plain text
                import re
                return re.sub(r'<[^>]+>', '', res['html'])
        
        return str(res) if res else ''
    
    def generate_editable_html(self, image_path: str, ppstructure_result: List) -> str:
        """
        Generate editable HTML content for frontend rendering
        
        This method generates HTML with data attributes for inline editing.
        Each region has data-region-id, data-region-type, and data-bbox attributes.
        
        Args:
            image_path: Path to the original image
            ppstructure_result: Raw result from PPStructure
            
        Returns:
            HTML string for frontend rendering
        """
        import json
        from pathlib import Path
        
        # Extract job_id from image path
        image_name = Path(image_path).stem
        if '_page' in image_name:
            job_id = image_name.split('_page')[0]
        else:
            job_id = image_name
        
        # Sort results by y-coordinate (top to bottom reading order)
        sorted_results = sorted(ppstructure_result, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1])
        
        html_parts = []
        
        # Process each item from PPStructure result (sorted by position)
        for idx, item in enumerate(sorted_results):
            item_type = item.get('type', 'unknown')
            res = item.get('res', {})
            bbox = item.get('bbox', [0, 0, 0, 0])
            
            # Create bbox JSON for data attribute
            bbox_data = json.dumps({'x': float(bbox[0]), 'y': float(bbox[1]), 'x2': float(bbox[2]), 'y2': float(bbox[3])})
            
            # Handle different content types
            if item_type == 'table':
                if isinstance(res, dict) and 'html' in res:
                    table_html = res['html']
                    table_html = table_html.replace('<html>', '').replace('</html>', '')
                    table_html = table_html.replace('<body>', '').replace('</body>', '')
                    html_parts.append(f'<div class="ocr-region table-wrapper" data-region-id="{idx}" data-region-type="table" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(table_html.strip())
                    html_parts.append('</div>')
                elif isinstance(res, str):
                    html_parts.append(f'<div class="ocr-region table-wrapper" data-region-id="{idx}" data-region-type="table" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(res)
                    html_parts.append('</div>')
                    
            elif item_type == 'title':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region title" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'text':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region text-block" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'header':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region header" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'footer':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region footer" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'figure':
                html_parts.append(f'<div class="ocr-region figure-placeholder" data-region-id="{idx}" data-region-type="figure" data-bbox=\'{bbox_data}\'>[图像]</div>')
                
            elif item_type == 'figure_caption':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region figure-caption" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'table_caption':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region table-caption" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'reference':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region reference" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
                    
            elif item_type == 'equation':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region equation" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content"><em>{text_content}</em></span>')
                    html_parts.append('</div>')
                    
            else:
                text_content = self._extract_text_from_res(res)
                if text_content:
                    html_parts.append(f'<div class="ocr-region text-block" data-region-id="{idx}" data-region-type="text" data-bbox=\'{bbox_data}\'>')
                    html_parts.append(f'<span class="editable-content">{text_content}</span>')
                    html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    def _scale_regions_to_original(self, regions: List[Region], scale_info: Dict[str, Any]) -> List[Region]:
        """
        Scale region coordinates from preprocessed image back to original image dimensions
        
        Args:
            regions: List of regions with coordinates from preprocessed image
            scale_info: Dictionary containing scale factors and dimensions
            
        Returns:
            List of regions with coordinates scaled to original image
        """
        if not scale_info.get('was_resized', False):
            # No scaling needed if image wasn't resized
            logger.info("No coordinate scaling needed - image was not resized")
            return regions
        
        scale_x = scale_info.get('scale_x', 1.0)
        scale_y = scale_info.get('scale_y', 1.0)
        
        logger.info(f"Scaling coordinates by {scale_x:.3f}x{scale_y:.3f} to match original image")
        
        scaled_regions = []
        for region in regions:
            # Scale the bounding box coordinates
            scaled_bbox = BoundingBox(
                x=region.coordinates.x * scale_x,
                y=region.coordinates.y * scale_y,
                width=region.coordinates.width * scale_x,
                height=region.coordinates.height * scale_y
            )
            
            # Create new region with scaled coordinates
            scaled_region = Region(
                coordinates=scaled_bbox,
                classification=region.classification,
                confidence=region.confidence,
                content=region.content,
                metadata=region.metadata.copy() if region.metadata else {}
            )
            
            # Add scale info to metadata for debugging
            scaled_region.metadata['coordinate_scaling'] = {
                'scale_x': scale_x,
                'scale_y': scale_y,
                'original_image_width': scale_info.get('original_width'),
                'original_image_height': scale_info.get('original_height')
            }
            
            scaled_regions.append(scaled_region)
        
        return scaled_regions
    
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
        
        # PaddleOCR returns results in format: [[[bbox, text_info], ...]]
        # We need to unwrap the outer list first
        if not structure_result or len(structure_result) == 0:
            logger.warning("Empty structure result from PaddleOCR")
            return regions
        
        # Get the actual results from the first element
        actual_results = structure_result[0] if structure_result else []
        
        for item in actual_results:
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
            
            # Initialize table structure engine with optimized settings
            # recovery=True enables HTML output for tables
            table_engine = PPStructure(
                use_gpu=self.use_gpu,
                show_log=False,
                lang=self.lang,
                layout=True,
                table=True,
                ocr=True,
                recovery=True,  # Enable recovery mode for HTML table output
                layout_score_threshold=0.3,  # Lower threshold to detect more regions
                layout_nms_threshold=0.3     # Lower NMS threshold to keep more separate boxes
            )
            
            # Perform table detection
            result = table_engine(image_path)
            
            logger.info(f"PPStructure returned {len(result)} items")
            
            # Save raw PPStructure HTML output (includes tables with HTML structure)
            self._save_ppstructure_html(image_path, result)
            
            tables = []
            for idx, item in enumerate(result):
                item_type = item.get('type', 'unknown')
                logger.info(f"Item {idx}: type={item_type}, keys={list(item.keys())}")
                
                if item_type == 'table':
                    table_structure = self._parse_table_result(item)
                    if table_structure:
                        # Check if this is a large table that might need splitting
                        if table_structure.rows > 20:
                            # Try to split large tables by empty rows
                            split_tables = self._split_large_table(table_structure)
                            tables.extend(split_tables)
                            logger.info(f"Split large table into {len(split_tables)} tables")
                        else:
                            tables.append(table_structure)
                            logger.info(f"Successfully parsed table {idx}")
                    else:
                        logger.warning(f"Failed to parse table {idx}")
            
            logger.info(f"Total tables extracted: {len(tables)}")
            return tables
            
        except ImportError:
            logger.warning("PPStructure not available, using fallback table detection")
            return self._fallback_table_detection(image_path)
        except Exception as e:
            logger.warning(f"Table detection failed: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return []
    
    def _split_large_table(self, table: TableStructure) -> List[TableStructure]:
        """
        Split a large table into smaller tables based on empty rows
        
        Args:
            table: Large table structure to split
            
        Returns:
            List of smaller table structures
        """
        if not table.cells or len(table.cells) <= 5:
            return [table]
        
        tables = []
        current_rows = []
        empty_row_count = 0
        
        for row_idx, row in enumerate(table.cells):
            # Check if row is mostly empty (separator row)
            non_empty_cells = sum(1 for cell in row if cell and cell.strip())
            is_empty_row = non_empty_cells <= 1  # Allow 1 non-empty cell for row numbers
            
            if is_empty_row:
                empty_row_count += 1
                # If we have 2+ consecutive empty rows, it might be a table separator
                if empty_row_count >= 2 and current_rows:
                    # Save current table
                    if len(current_rows) >= 2:  # At least 2 rows to be a table
                        new_table = TableStructure(
                            rows=len(current_rows),
                            columns=table.columns,
                            cells=current_rows,
                            coordinates=table.coordinates,  # Approximate
                            has_headers=True
                        )
                        tables.append(new_table)
                    current_rows = []
                    empty_row_count = 0
            else:
                empty_row_count = 0
                current_rows.append(row)
        
        # Don't forget the last table
        if current_rows and len(current_rows) >= 2:
            new_table = TableStructure(
                rows=len(current_rows),
                columns=table.columns,
                cells=current_rows,
                coordinates=table.coordinates,
                has_headers=True
            )
            tables.append(new_table)
        
        # If no split happened, return original
        if not tables:
            return [table]
        
        logger.info(f"Split table with {table.rows} rows into {len(tables)} tables")
        return tables
    
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
            logger.info(f"Parsing table item with keys: {list(table_item.keys())}")
            
            # Get bounding box if available
            bbox = BoundingBox(0, 0, 0, 0)
            if 'bbox' in table_item:
                box = table_item['bbox']
                if len(box) >= 4:
                    bbox = BoundingBox(
                        x=float(box[0]),
                        y=float(box[1]),
                        width=float(box[2] - box[0]),
                        height=float(box[3] - box[1])
                    )
                    logger.info(f"Table bbox: x={bbox.x}, y={bbox.y}, w={bbox.width}, h={bbox.height}")
            
            # Extract table data from PP-Structure result
            if 'res' not in table_item:
                logger.warning("No 'res' key in table item")
                return None
            
            table_data = table_item['res']
            logger.info(f"Table res type: {type(table_data)}")
            
            table_structure = None
            
            # Parse table structure based on data format
            if isinstance(table_data, dict):
                logger.info(f"Table data dict keys: {list(table_data.keys())}")
                if 'html' in table_data:
                    # Parse HTML table structure (if available)
                    table_structure = self._parse_html_table(table_data['html'])
                elif 'cell_bbox' in table_data:
                    # Parse cell-based table data
                    table_structure = self._parse_cell_bbox_table(table_data)
            elif isinstance(table_data, list):
                # Parse list-based table data
                table_structure = self._parse_list_table(table_data)
            elif isinstance(table_data, str):
                # HTML string directly
                table_structure = self._parse_html_table(table_data)
            
            # Update coordinates if we have them
            if table_structure and bbox.width > 0:
                table_structure.coordinates = bbox
            
            return table_structure
            
        except Exception as e:
            logger.warning(f"Failed to parse table result: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return None
    
    def _parse_cell_bbox_table(self, table_data: Dict) -> Optional[TableStructure]:
        """
        Parse table from cell bounding box data
        
        Args:
            table_data: Dictionary with cell_bbox and other table info
            
        Returns:
            TableStructure object or None
        """
        try:
            cell_bboxes = table_data.get('cell_bbox', [])
            if not cell_bboxes:
                return None
            
            # Group cells by row (based on y-coordinate)
            rows_dict = {}
            for cell_info in cell_bboxes:
                if len(cell_info) >= 5:
                    # Format: [x1, y1, x2, y2, text] or similar
                    y_center = (cell_info[1] + cell_info[3]) / 2
                    row_key = int(y_center / 20)  # Group by ~20px rows
                    
                    if row_key not in rows_dict:
                        rows_dict[row_key] = []
                    
                    text = str(cell_info[4]) if len(cell_info) > 4 else ''
                    rows_dict[row_key].append((cell_info[0], text))  # (x, text)
            
            # Sort rows and cells
            sorted_rows = sorted(rows_dict.keys())
            table_grid = []
            max_cols = 0
            
            for row_key in sorted_rows:
                cells = sorted(rows_dict[row_key], key=lambda x: x[0])
                row_data = [cell[1] for cell in cells]
                table_grid.append(row_data)
                max_cols = max(max_cols, len(row_data))
            
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
                coordinates=BoundingBox(0, 0, 0, 0),
                has_headers=True  # Assume first row is header
            )
            
        except Exception as e:
            logger.warning(f"Cell bbox table parsing failed: {e}")
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