"""
OCR Service Package

将原 ocr_service.py (3843行) 拆分为多个模块：
- image_preprocessor.py: 图像预处理（增强、缩放、归一化）
- layout_analyzer.py: 布局分析、区域分类、排序、置信度计算
- table_processor.py: 表格检测、结构解析、单元格提取
- output_generator.py: HTML/Markdown 生成
- ppstructure_parser.py: PPStructureV3 结果解析、格式转换
- confidence_logger.py: 置信度日志生成

核心服务类和引擎管理保留在原 ocr_service.py 中，
此包提供模块化的辅助功能。
"""

# 导出图像预处理模块
from backend.services.ocr.image_preprocessor import (
    ImagePreprocessor,
    ImagePreprocessingError,
)

# 导出布局分析模块
from backend.services.ocr.layout_analyzer import (
    LayoutAnalyzer,
    ConfidenceCalculator,
)

# 导出表格处理模块
from backend.services.ocr.table_processor import (
    TableProcessor,
)

# 导出输出生成模块
from backend.services.ocr.output_generator import (
    OutputGenerator,
)

# 导出 PPStructure 解析模块
from backend.services.ocr.ppstructure_parser import (
    PPStructureParser,
)

# 导出置信度日志模块
from backend.services.ocr.confidence_logger import (
    ConfidenceLogger,
)

__all__ = [
    # 图像预处理
    'ImagePreprocessor',
    'ImagePreprocessingError',
    # 布局分析
    'LayoutAnalyzer',
    'ConfidenceCalculator',
    # 表格处理
    'TableProcessor',
    # 输出生成
    'OutputGenerator',
    # PPStructure 解析
    'PPStructureParser',
    # 置信度日志
    'ConfidenceLogger',
]
