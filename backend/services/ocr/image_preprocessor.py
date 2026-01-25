"""
图像预处理模块

负责 OCR 前的图像预处理：
- 图像质量增强（对比度、锐度）
- 图像尺寸归一化
- 坐标缩放信息管理
"""
import logging
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """图像预处理器"""
    
    def __init__(self, max_dimension: int = 1280):
        """
        初始化预处理器
        
        Args:
            max_dimension: 图像最大边长，超过此值会缩放
        """
        self.max_dimension = max_dimension
    
    def preprocess(self, image_path: str, output_path: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        预处理图像以获得最佳 OCR 结果
        
        Args:
            image_path: 输入图像路径
            output_path: 预处理后图像保存路径（可选）
            
        Returns:
            Tuple of (预处理后图像路径, 缩放信息字典)
        """
        try:
            # 加载图像
            image = Image.open(image_path)
            original_width, original_height = image.size
            
            # 转换为 RGB（如果需要）
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 应用预处理步骤
            image = self._enhance_quality(image)
            image, scale_info = self._normalize_size(image)
            
            # 记录原始尺寸用于坐标映射
            scale_info['original_width'] = original_width
            scale_info['original_height'] = original_height
            
            # 保存预处理后的图像
            if output_path is None:
                base_path = Path(image_path)
                output_path = str(base_path.parent / f"{base_path.stem}_preprocessed{base_path.suffix}")
            
            image.save(output_path, quality=95, optimize=True)
            
            logger.info(f"Image preprocessed: {output_path}, scale_info: {scale_info}")
            return output_path, scale_info
            
        except Exception as e:
            raise ImagePreprocessingError(f"Image preprocessing failed: {e}")
    
    def _enhance_quality(self, image: Image.Image) -> Image.Image:
        """
        增强图像质量以获得更好的 OCR 结果
        
        Args:
            image: PIL Image 对象
            
        Returns:
            增强后的 PIL Image 对象
        """
        # 增强对比度
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # 增强锐度
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        # 轻微去噪
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        return image
    
    def _normalize_size(self, image: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        归一化图像尺寸并返回缩放信息
        
        Args:
            image: PIL Image 对象
            
        Returns:
            Tuple of (缩放后的 PIL Image 对象, 缩放信息字典)
        """
        width, height = image.size
        scale_info = {
            'preprocessed_width': width,
            'preprocessed_height': height,
            'scale_x': 1.0,
            'scale_y': 1.0,
            'was_resized': False
        }
        
        # 仅当图像过大时才缩放
        if max(width, height) > self.max_dimension:
            if width > height:
                new_width = self.max_dimension
                new_height = int(height * (self.max_dimension / width))
            else:
                new_height = self.max_dimension
                new_width = int(width * (self.max_dimension / height))
            
            # 计算缩放因子（从预处理后到原始）
            scale_info['scale_x'] = width / new_width
            scale_info['scale_y'] = height / new_height
            scale_info['preprocessed_width'] = new_width
            scale_info['preprocessed_height'] = new_height
            scale_info['was_resized'] = True
            
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"Image resized: {width}x{height} -> {new_width}x{new_height}, "
                       f"scale: {scale_info['scale_x']:.3f}x{scale_info['scale_y']:.3f}")
        
        return image, scale_info


class ImagePreprocessingError(Exception):
    """图像预处理错误"""
    pass
