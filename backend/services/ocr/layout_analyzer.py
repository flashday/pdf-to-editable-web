"""
布局分析模块

负责布局分析相关功能：
- 区域分类和排序
- 置信度计算
- 布局增强
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
import cv2

from backend.models.document import Region, BoundingBox, RegionType

logger = logging.getLogger(__name__)


class LayoutAnalyzer:
    """布局分析器"""
    
    def __init__(self):
        pass
    
    def sort_regions_by_reading_order(self, regions: List[Region]) -> List[Region]:
        """
        按自然阅读顺序排序区域（从上到下，从左到右）
        
        Args:
            regions: 待排序的区域列表
            
        Returns:
            排序后的区域列表
        """
        def reading_order_key(region: Region) -> Tuple[int, int]:
            # 按大约行分组（允许轻微的对齐偏差）
            row_group = int(region.coordinates.y // 50)  # 50px 容差
            return (row_group, int(region.coordinates.x))
        
        return sorted(regions, key=reading_order_key)
    
    def scale_regions_to_original(self, regions: List[Region], scale_info: Dict[str, Any]) -> List[Region]:
        """
        将区域坐标从预处理图像缩放回原始图像尺寸
        
        Args:
            regions: 预处理图像坐标的区域列表
            scale_info: 包含缩放因子和尺寸的字典
            
        Returns:
            缩放到原始图像坐标的区域列表
        """
        if not scale_info.get('was_resized', False):
            logger.info("无需坐标缩放 - 图像未被调整大小")
            return regions
        
        scale_x = scale_info.get('scale_x', 1.0)
        scale_y = scale_info.get('scale_y', 1.0)
        
        logger.info(f"按 {scale_x:.3f}x{scale_y:.3f} 缩放坐标以匹配原始图像")
        
        scaled_regions = []
        for region in regions:
            scaled_bbox = BoundingBox(
                x=region.coordinates.x * scale_x,
                y=region.coordinates.y * scale_y,
                width=region.coordinates.width * scale_x,
                height=region.coordinates.height * scale_y
            )
            
            scaled_region = Region(
                coordinates=scaled_bbox,
                classification=region.classification,
                confidence=region.confidence,
                content=region.content,
                metadata=region.metadata.copy() if region.metadata else {}
            )
            
            scaled_region.metadata['coordinate_scaling'] = {
                'scale_x': scale_x,
                'scale_y': scale_y,
                'original_image_width': scale_info.get('original_width'),
                'original_image_height': scale_info.get('original_height')
            }
            
            scaled_regions.append(scaled_region)
        
        return scaled_regions
    
    def enhance_layout_classification(self, regions: List[Region], image_path: str) -> List[Region]:
        """
        使用高级启发式方法增强布局分类
        
        注意：此方法仅在 PaddleOCR 2.x 时使用
        PaddleOCR 3.x (PPStructureV3) 已经内置了深度学习布局分析
        
        Args:
            regions: 初始区域列表
            image_path: 预处理图像路径
            
        Returns:
            增强分类后的区域列表
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return regions
            
            image_height, image_width = image.shape[:2]
            
            enhanced_regions = []
            
            for region in regions:
                enhanced_region = Region(
                    coordinates=region.coordinates,
                    classification=region.classification,
                    confidence=region.confidence,
                    content=region.content,
                    metadata=region.metadata.copy() if region.metadata else {}
                )
                
                enhanced_region.metadata.update({
                    'relative_position': {
                        'x_ratio': region.coordinates.x / image_width,
                        'y_ratio': region.coordinates.y / image_height,
                        'width_ratio': region.coordinates.width / image_width,
                        'height_ratio': region.coordinates.height / image_height
                    },
                    'area': region.coordinates.width * region.coordinates.height
                })
                
                enhanced_region.classification = self._refine_region_classification(
                    enhanced_region, image_height, image_width
                )
                
                enhanced_regions.append(enhanced_region)
            
            return enhanced_regions
            
        except Exception as e:
            logger.warning(f"布局增强失败: {e}")
            return regions
    
    def _refine_region_classification(self, region: Region, image_height: int, image_width: int) -> RegionType:
        """
        使用高级启发式方法细化区域分类
        
        注意：此函数仅在 PaddleOCR 2.x 时使用
        
        Args:
            region: 待分类的区域
            image_height: 图像总高度
            image_width: 图像总宽度
            
        Returns:
            细化后的 RegionType
        """
        if not region.content:
            return RegionType.IMAGE
        
        text = region.content.strip()
        bbox = region.coordinates
        
        y_ratio = bbox.y / image_height
        width_ratio = bbox.width / image_width
        height_ratio = bbox.height / image_height
        
        # 列表检测
        list_indicators = ['•', '-', '*', '○', '▪', '▫']
        numbered_pattern = any(text.startswith(f'{i}.') for i in range(1, 20))
        
        if (any(text.startswith(indicator) for indicator in list_indicators) or
            numbered_pattern or
            any(f'\n{indicator}' in text for indicator in list_indicators) or
            any(f'\n{i}.' in text for i in range(1, 20))):
            return RegionType.LIST
        
        # 标题检测
        if (y_ratio < 0.2 or
            (len(text) < 80 and 
             (text.isupper() or 
              any(keyword in text.lower() for keyword in ['title', 'chapter', 'section']) or
              width_ratio > 0.6))):
            return RegionType.HEADER
        
        # 表格检测
        if (('\t' in text or '|' in text or 
             text.count(' ') > len(text) * 0.3) and
            height_ratio > 0.1):
            return RegionType.TABLE
        
        return RegionType.PARAGRAPH
    
    def classify_region(self, text_content: str, bbox: BoundingBox) -> RegionType:
        """
        基于内容和位置分类区域类型
        
        Args:
            text_content: 提取的文本内容
            bbox: 区域边界框
            
        Returns:
            RegionType 分类
        """
        if not text_content or not text_content.strip():
            return RegionType.IMAGE
        
        text = text_content.strip()
        
        # 列表检测
        list_indicators = ['•', '-', '*', '○', '▪', '▫']
        numbered_pattern = any(text.startswith(f'{i}.') for i in range(1, 20))
        
        if (any(text.startswith(indicator) for indicator in list_indicators) or
            numbered_pattern or
            any(f'\n{indicator}' in text for indicator in list_indicators) or
            any(f'\n{i}.' in text for i in range(1, 20))):
            return RegionType.LIST
        
        # 标题检测
        if (len(text) < 100 and 
            (text.isupper() or 
             any(char.isdigit() for char in text[:10]) or
             bbox.y < 100)):
            return RegionType.HEADER
        
        return RegionType.PARAGRAPH


class ConfidenceCalculator:
    """置信度计算器"""
    
    def __init__(self):
        pass
    
    def calculate_confidence_metrics(self, regions: List[Region]) -> Dict[str, float]:
        """
        计算布局分析的详细置信度指标
        
        Args:
            regions: 分析的区域列表
            
        Returns:
            包含置信度指标的字典
        """
        if not regions:
            return {
                'overall': 0.0,
                'text_confidence': 0.0,
                'layout_confidence': 0.0,
                'region_count': 0,
                'regions_with_confidence': 0,
                'regions_without_confidence': 0,
                'confidence_coverage': 0.0
            }
        
        regions_with_conf = [r for r in regions if r.confidence is not None and r.confidence > 0]
        regions_without_conf = [r for r in regions if r.confidence is None or r.confidence <= 0]
        
        text_confidences = [r.confidence for r in regions_with_conf]
        text_confidence = sum(text_confidences) / len(text_confidences) if text_confidences else 0.0
        
        layout_confidence = self._calculate_layout_confidence(regions)
        
        confidence_coverage = len(regions_with_conf) / len(regions) if regions else 0.0
        
        base_confidence = (text_confidence * 0.7 + layout_confidence * 0.3)
        coverage_penalty = min(1.0, confidence_coverage / 0.5) if confidence_coverage < 0.5 else 1.0
        overall_confidence = base_confidence * (0.5 + 0.5 * coverage_penalty)
        
        logger.info(f"置信度指标: {len(regions_with_conf)}/{len(regions)} 区域有置信度 "
                   f"(覆盖率: {confidence_coverage:.1%}), 平均: {text_confidence:.4f}")
        
        return {
            'overall': overall_confidence,
            'text_confidence': text_confidence,
            'layout_confidence': layout_confidence,
            'region_count': len(regions),
            'regions_with_confidence': len(regions_with_conf),
            'regions_without_confidence': len(regions_without_conf),
            'confidence_coverage': confidence_coverage
        }
    
    def _calculate_layout_confidence(self, regions: List[Region]) -> float:
        """
        计算布局分析质量的置信度分数
        
        Args:
            regions: 分析的区域列表
            
        Returns:
            布局置信度分数 (0.0 到 1.0)
        """
        if not regions:
            return 0.0
        
        # 因子 1: 区域多样性
        region_types = set(r.classification for r in regions)
        num_types = len(region_types)
        if num_types >= 3:
            type_diversity = 1.0
        elif num_types == 2:
            type_diversity = 0.9
        else:
            type_diversity = 0.7
        
        # 因子 2: 合理的区域尺寸
        reasonable_sizes = 0
        for region in regions:
            area = region.coordinates.width * region.coordinates.height
            if 50 < area < 10000000:
                reasonable_sizes += 1
        size_factor = reasonable_sizes / len(regions) if regions else 0.5
        
        # 因子 3: 文本内容质量
        meaningful_content = 0
        for region in regions:
            if region.content and len(region.content.strip()) > 3:
                meaningful_content += 1
        content_factor = meaningful_content / len(regions) if regions else 0.5
        
        # 加权平均
        layout_confidence = (
            content_factor * 0.5 +
            size_factor * 0.3 +
            type_diversity * 0.2
        )
        
        return layout_confidence
