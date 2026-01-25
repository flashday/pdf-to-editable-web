"""
PPStructureV3 结果解析模块

负责解析和转换 PPStructureV3 的输出格式：
- 将 PPStructureV3 结果转换为统一的内部格式
- 将 3.x 格式转换为 2.x 兼容格式
- 提取 OCR 文本行和置信度
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from backend.models.document import Region, BoundingBox, RegionType

logger = logging.getLogger(__name__)


class PPStructureParser:
    """PPStructureV3 结果解析器"""
    
    # PPStructureV3 类型到内部类型的映射
    # 注意：RegionType 只有 HEADER, PARAGRAPH, TABLE, IMAGE, LIST
    TYPE_MAPPING = {
        'title': RegionType.HEADER,  # 标题映射为 HEADER
        'doc_title': RegionType.HEADER,
        'text': RegionType.PARAGRAPH,
        'paragraph': RegionType.PARAGRAPH,
        'table': RegionType.TABLE,
        'figure': RegionType.IMAGE,
        'figure_caption': RegionType.PARAGRAPH,  # 图片说明映射为 PARAGRAPH
        'table_caption': RegionType.PARAGRAPH,  # 表格说明映射为 PARAGRAPH
        'header': RegionType.HEADER,
        'footer': RegionType.HEADER,  # 页脚映射为 HEADER
        'reference': RegionType.PARAGRAPH,
        'equation': RegionType.PARAGRAPH,
        'seal': RegionType.IMAGE,
        'chart': RegionType.IMAGE,
    }
    
    def __init__(self):
        pass
    
    def parse_to_regions(self, ppstructure_result: List[Dict[str, Any]]) -> List[Region]:
        """
        将 PPStructureV3 的布局分析结果转换为 Region 对象列表
        
        Args:
            ppstructure_result: PPStructureV3 处理后的结果列表
            
        Returns:
            Region 对象列表
        """
        regions = []
        
        for idx, item in enumerate(ppstructure_result):
            try:
                region = self._parse_single_item(item, idx)
                if region:
                    regions.append(region)
            except Exception as e:
                logger.warning(f"Failed to parse PPStructure item {idx}: {e}")
                continue
        
        logger.info(f"Parsed {len(regions)} regions from PPStructure result")
        return regions
    
    def _parse_single_item(self, item: Dict[str, Any], idx: int) -> Optional[Region]:
        """解析单个 PPStructure 项目"""
        item_type = item.get('type', 'unknown')
        bbox = item.get('bbox', [0, 0, 0, 0])
        res = item.get('res', {})
        confidence = item.get('confidence')
        
        # 转换 bbox 格式
        if len(bbox) == 4:
            bounding_box = BoundingBox(
                x=float(bbox[0]),
                y=float(bbox[1]),
                width=float(bbox[2] - bbox[0]),
                height=float(bbox[3] - bbox[1])
            )
        else:
            logger.warning(f"Invalid bbox format for item {idx}: {bbox}")
            return None
        
        # 确定区域类型
        region_type = self.TYPE_MAPPING.get(item_type, RegionType.PARAGRAPH)
        
        # 提取文本内容
        text_content = self._extract_text_content(res, item_type)
        
        # 提取表格 HTML（如果是表格类型）
        table_html = None
        if item_type == 'table' and isinstance(res, dict):
            table_html = res.get('html', '')
        
        return Region(
            id=f"region_{idx}",
            type=region_type,
            bounding_box=bounding_box,
            text=text_content,
            confidence=confidence,
            metadata={
                'original_type': item_type,
                'table_html': table_html,
                'index': idx
            }
        )
    
    def _extract_text_content(self, res: Any, item_type: str) -> str:
        """从 res 字段提取文本内容"""
        if item_type == 'table':
            # 表格类型不提取文本
            return ''
        
        if isinstance(res, str):
            return res.strip()
        
        if isinstance(res, list):
            texts = []
            for item in res:
                if isinstance(item, dict) and 'text' in item:
                    texts.append(item['text'])
                elif isinstance(item, str):
                    texts.append(item)
            return ' '.join(texts)
        
        if isinstance(res, dict) and 'text' in res:
            return res['text']
        
        return ''
    
    def convert_v3_to_legacy(self, v3_results: List) -> List:
        """
        将 PaddleOCR 3.x 的结果格式转换为 2.x 的旧格式
        
        支持两种输入格式：
        1. 普通 OCR 结果 (OCRResult): 包含 dt_polys, rec_texts, rec_scores
        2. PPStructure 结果 (LayoutParsingResultV2): 包含 overall_ocr_res 字段
        
        PaddleOCR 2.x 返回格式:
        - [[[bbox_points, (text, score)], ...]]
        - bbox_points: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        
        Args:
            v3_results: PaddleOCR 3.x predict 方法返回的结果列表
            
        Returns:
            转换为 2.x 格式的结果
        """
        legacy_results = []
        
        for result in v3_results:
            page_results = []
            
            # 获取检测框、文本和置信度
            dt_polys, rec_texts, rec_scores = self._extract_ocr_data(result)
            
            # 确保数据不为 None
            dt_polys = dt_polys or []
            rec_texts = rec_texts or []
            rec_scores = rec_scores or []
            
            # 转换 numpy array 为列表
            if hasattr(dt_polys, 'tolist'):
                dt_polys = dt_polys.tolist()
            if hasattr(rec_texts, 'tolist'):
                rec_texts = rec_texts.tolist()
            if hasattr(rec_scores, 'tolist'):
                rec_scores = rec_scores.tolist()
            
            logger.debug(f"Converting {len(dt_polys)} OCR items to legacy format")
            
            # 转换为旧格式
            for i, poly in enumerate(dt_polys):
                text = rec_texts[i] if i < len(rec_texts) else ''
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                
                # 将 numpy 数组转换为列表
                if hasattr(poly, 'tolist'):
                    poly_list = poly.tolist()
                else:
                    poly_list = list(poly)
                
                # 确保是正确的格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                if len(poly_list) == 4 and len(poly_list[0]) == 2:
                    bbox_points = poly_list
                else:
                    logger.warning(f"Unexpected poly format: {poly_list}")
                    continue
                
                # 旧格式: [bbox_points, (text, confidence)]
                page_results.append([bbox_points, (text, float(score))])
            
            legacy_results.append(page_results)
        
        logger.info(f"Converted to legacy format: {sum(len(p) for p in legacy_results)} total OCR items")
        return legacy_results
    
    def _extract_ocr_data(self, result: Any) -> tuple:
        """从结果中提取 OCR 数据"""
        dt_polys = None
        rec_texts = None
        rec_scores = None
        
        # 首先尝试从 overall_ocr_res 获取（PPStructure 结果）
        overall_ocr_res = self._get_overall_ocr_res(result)
        
        if overall_ocr_res is not None:
            logger.debug("Extracting OCR data from overall_ocr_res (PPStructure result)")
            dt_polys, rec_texts, rec_scores = self._extract_from_dict_or_obj(overall_ocr_res)
        else:
            # 直接从结果中获取（普通 OCR 结果）
            dt_polys, rec_texts, rec_scores = self._extract_from_dict_or_obj(result)
        
        return dt_polys, rec_texts, rec_scores
    
    def _get_overall_ocr_res(self, result: Any) -> Optional[Any]:
        """获取 overall_ocr_res 字段"""
        if isinstance(result, dict):
            return result.get('overall_ocr_res')
        elif hasattr(result, '__getitem__'):
            try:
                return result.get('overall_ocr_res') if hasattr(result, 'get') else result['overall_ocr_res']
            except (KeyError, TypeError):
                pass
        return getattr(result, 'overall_ocr_res', None)
    
    def _extract_from_dict_or_obj(self, data: Any) -> tuple:
        """从字典或对象中提取 OCR 数据"""
        dt_polys = None
        rec_texts = None
        rec_scores = None
        
        if isinstance(data, dict):
            dt_polys = data.get('dt_polys', [])
            rec_texts = data.get('rec_texts', [])
            rec_scores = data.get('rec_scores', [])
        elif hasattr(data, '__getitem__'):
            try:
                dt_polys = data.get('dt_polys', []) if hasattr(data, 'get') else data['dt_polys']
                rec_texts = data.get('rec_texts', []) if hasattr(data, 'get') else data['rec_texts']
                rec_scores = data.get('rec_scores', []) if hasattr(data, 'get') else data['rec_scores']
            except (KeyError, TypeError):
                pass
        
        if dt_polys is None:
            dt_polys = getattr(data, 'dt_polys', [])
        if rec_texts is None:
            rec_texts = getattr(data, 'rec_texts', [])
        if rec_scores is None:
            rec_scores = getattr(data, 'rec_scores', [])
        
        return dt_polys, rec_texts, rec_scores
    
    def extract_ocr_text_lines_with_confidence(self, overall_ocr_res: Any) -> List[Dict[str, Any]]:
        """
        从 overall_ocr_res 提取所有文本行的置信度和位置信息
        
        Args:
            overall_ocr_res: PPStructureV3 的 overall_ocr_res 字段
            
        Returns:
            文本行列表，每项包含 text, confidence, bbox
        """
        text_lines = []
        
        if overall_ocr_res is None:
            return text_lines
        
        # 提取数据
        dt_polys, rec_texts, rec_scores = self._extract_from_dict_or_obj(overall_ocr_res)
        
        # 转换为列表
        if hasattr(dt_polys, 'tolist'):
            dt_polys = dt_polys.tolist()
        if hasattr(rec_texts, 'tolist'):
            rec_texts = rec_texts.tolist()
        if hasattr(rec_scores, 'tolist'):
            rec_scores = rec_scores.tolist()
        
        for i, poly in enumerate(dt_polys or []):
            text = rec_texts[i] if i < len(rec_texts or []) else ''
            score = rec_scores[i] if i < len(rec_scores or []) else 0.0
            
            # 计算 bbox
            if hasattr(poly, 'tolist'):
                poly = poly.tolist()
            
            if len(poly) >= 4:
                x_coords = [p[0] for p in poly]
                y_coords = [p[1] for p in poly]
                bbox = {
                    'x': min(x_coords),
                    'y': min(y_coords),
                    'x2': max(x_coords),
                    'y2': max(y_coords)
                }
            else:
                bbox = {'x': 0, 'y': 0, 'x2': 0, 'y2': 0}
            
            text_lines.append({
                'text': text,
                'confidence': float(score) if score else 0.0,
                'bbox': bbox
            })
        
        return text_lines
    
    def match_block_confidence_from_ocr(self, block_bbox: List, ocr_text_lines: List[Dict[str, Any]]) -> Optional[float]:
        """
        根据布局区块的位置，从 OCR 文本行中匹配并计算平均置信度
        
        Args:
            block_bbox: 区块的 bbox [x1, y1, x2, y2]
            ocr_text_lines: OCR 文本行列表
            
        Returns:
            匹配到的平均置信度，如果没有匹配则返回 None
        """
        if not ocr_text_lines or not block_bbox or len(block_bbox) < 4:
            return None
        
        block_x1, block_y1, block_x2, block_y2 = block_bbox[:4]
        matched_confidences = []
        
        for line in ocr_text_lines:
            line_bbox = line.get('bbox', {})
            line_x1 = line_bbox.get('x', 0)
            line_y1 = line_bbox.get('y', 0)
            line_x2 = line_bbox.get('x2', 0)
            line_y2 = line_bbox.get('y2', 0)
            
            # 计算重叠区域
            overlap_x1 = max(block_x1, line_x1)
            overlap_y1 = max(block_y1, line_y1)
            overlap_x2 = min(block_x2, line_x2)
            overlap_y2 = min(block_y2, line_y2)
            
            if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
                # 有重叠
                overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                line_area = max((line_x2 - line_x1) * (line_y2 - line_y1), 1)
                overlap_ratio = overlap_area / line_area
                
                # 如果重叠超过 50%，认为匹配
                if overlap_ratio > 0.5:
                    conf = line.get('confidence', 0)
                    if conf and conf > 0:
                        matched_confidences.append(conf)
        
        if matched_confidences:
            return sum(matched_confidences) / len(matched_confidences)
        
        return None
