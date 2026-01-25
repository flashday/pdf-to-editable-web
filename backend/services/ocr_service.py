"""
PaddleOCR PP-Structure integration service with error handling and preprocessing

PaddleOCR 版本兼容性：
- 支持 PaddleOCR 3.x (推荐 3.3.3)
- 支持 PaddlePaddle 3.x (推荐 3.2.2，注意 3.3.0 有 oneDNN 兼容性问题)
- 向后兼容 PaddleOCR 2.x

主要 API 变化（3.x vs 2.x）：
- PaddleOCR 类：基本兼容，use_structure 参数已废弃
- PPStructure 类：layout_score_threshold/layout_nms_threshold 参数已移除
- 结果格式：基本兼容

模型缓存策略：
- PPStructureV3 实例在模块级别缓存，避免重复加载
- 支持启动时预加载模型

CPU 性能优化：
- 线程数配置：根据 Intel CPU 特性优化
- 参考：MDFiles/implementation/PADDLEOCR_CPU_PERFORMANCE_OPTIMIZATION.md
"""
import os
import logging
import threading

# ============================================================================
# CPU 性能优化 - 线程配置（必须在导入 paddle 之前设置）
# 针对 Intel Core Ultra 7 / i7 优化
# 注意：某些 Intel CPU 上单线程可能更快，建议进行基准测试
# ============================================================================
# CPU 线程设置：默认 8 线程（适合 Intel i7/Ultra 7）
# 如需调整，可设置环境变量 PADDLEOCR_CPU_THREADS
_CPU_THREADS = os.environ.get('PADDLEOCR_CPU_THREADS', '8')
os.environ.setdefault('OMP_NUM_THREADS', _CPU_THREADS)
os.environ.setdefault('MKL_NUM_THREADS', _CPU_THREADS)
# OpenBLAS 线程设置
os.environ.setdefault('OPENBLAS_NUM_THREADS', _CPU_THREADS)
# 禁用 oneDNN 详细日志
os.environ.setdefault('DNNL_VERBOSE', '0')
os.environ.setdefault('MKLDNN_VERBOSE', '0')
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

# ============================================================================
# 模型缓存 - 单例模式，避免重复加载模型
# ============================================================================
_ppstructure_v3_instance = None
_ppstructure_v3_lock = threading.Lock()
_models_loaded = False
_models_loading = False


def get_ppstructure_v3_instance():
    """
    获取 PPStructureV3 的单例实例
    
    使用双重检查锁定模式确保线程安全
    模型只会在第一次调用时加载，后续调用直接返回缓存的实例
    
    Returns:
        PPStructureV3 实例，如果不可用则返回 None
    """
    global _ppstructure_v3_instance
    
    if _ppstructure_v3_instance is not None:
        return _ppstructure_v3_instance
    
    with _ppstructure_v3_lock:
        # 双重检查
        if _ppstructure_v3_instance is not None:
            return _ppstructure_v3_instance
        
        try:
            from paddleocr import PPStructureV3
            logger.info("正在加载 PPStructureV3 模型（首次加载，请耐心等待）...")
            import time
            start_time = time.time()
            _ppstructure_v3_instance = PPStructureV3()
            elapsed = time.time() - start_time
            logger.info(f"PPStructureV3 模型加载完成，耗时 {elapsed:.1f} 秒")
            return _ppstructure_v3_instance
        except ImportError as e:
            logger.warning(f"PPStructureV3 不可用: {e}")
            return None
        except Exception as e:
            logger.error(f"PPStructureV3 加载失败: {e}")
            return None


def preload_models():
    """
    预加载所有 OCR 模型
    
    在后端启动时调用此函数，确保模型在接收请求前已加载完成
    这样用户上传 PDF 时不需要等待模型加载
    
    重要：PPStructureV3 内部的模型是懒加载的，仅创建实例不会加载模型
    必须调用 predict() 方法才能触发内部模型的加载
    
    注意：PPStructureV3 已经包含了完整的 OCR 功能，不需要单独加载 PaddleOCR
    
    Returns:
        bool: 模型是否加载成功
    """
    global _models_loaded, _models_loading
    
    if _models_loaded:
        logger.info("模型已加载，跳过预加载")
        return True
    
    if _models_loading:
        logger.info("模型正在加载中...")
        return False
    
    _models_loading = True
    logger.info("=" * 60)
    logger.info("开始预加载 OCR 模型...")
    logger.info("=" * 60)
    
    import time
    total_start = time.time()
    
    try:
        # 预加载 PPStructureV3（包含布局分析、表格识别、OCR 等多个模型）
        # PPStructureV3 已经包含了完整的 OCR 功能，不需要单独加载 PaddleOCR
        logger.info("加载 PPStructureV3 模型（包含 OCR 功能）...")
        ppstructure = get_ppstructure_v3_instance()
        if ppstructure is None:
            logger.warning("PPStructureV3 加载失败，将使用回退方案")
        else:
            # 重要：PPStructureV3 内部模型是懒加载的
            # 必须调用 predict() 才能触发内部模型（PP-LCNet, PP-OCRv5 等）的加载
            # 创建一个小的测试图像来触发模型加载
            logger.info("触发 PPStructureV3 内部模型加载（首次 predict 调用）...")
            try:
                # 创建一个 100x100 的白色测试图像
                test_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
                # 添加一些文字区域（黑色矩形）以触发 OCR 模型
                test_image[20:40, 20:80] = 0
                
                # 保存临时测试图像
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                    Image.fromarray(test_image).save(tmp_path)
                
                # 调用 predict 触发内部模型加载
                warmup_start = time.time()
                # 使用与实际处理相同的参数，禁用不必要的功能
                _ = list(ppstructure.predict(
                    tmp_path,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_seal_recognition=False,
                    use_formula_recognition=False,
                    use_chart_recognition=False
                ))
                warmup_elapsed = time.time() - warmup_start
                logger.info(f"PPStructureV3 内部模型加载完成，耗时 {warmup_elapsed:.1f} 秒")
                
                # 删除临时文件
                try:
                    os.remove(tmp_path)
                except:
                    pass
                    
            except Exception as e:
                logger.warning(f"PPStructureV3 预热失败: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        
        total_elapsed = time.time() - total_start
        logger.info("=" * 60)
        logger.info(f"所有模型预加载完成！总耗时: {total_elapsed:.1f} 秒")
        logger.info("=" * 60)
        
        _models_loaded = True
        _models_loading = False
        return True
        
    except Exception as e:
        logger.error(f"模型预加载失败: {e}")
        _models_loading = False
        return False


def is_models_loaded() -> bool:
    """检查模型是否已加载完成"""
    return _models_loaded


def is_models_loading() -> bool:
    """检查模型是否正在加载中"""
    return _models_loading


# ============================================================================
# PaddleOCR 基础引擎缓存
# ============================================================================
_paddleocr_instance = None
_paddleocr_lock = threading.Lock()


def get_paddleocr_instance(lang: str = 'ch'):
    """
    获取 PaddleOCR 基础引擎的单例实例
    
    Args:
        lang: 语言设置
        
    Returns:
        PaddleOCR 实例
    """
    global _paddleocr_instance
    
    if _paddleocr_instance is not None:
        return _paddleocr_instance
    
    with _paddleocr_lock:
        if _paddleocr_instance is not None:
            return _paddleocr_instance
        
        try:
            from paddleocr import PaddleOCR
            import paddleocr
            
            version = getattr(paddleocr, '__version__', '2.0.0')
            is_v3 = version.startswith('3.')
            
            logger.info(f"正在加载 PaddleOCR 基础引擎 (版本: {version})...")
            import time
            start_time = time.time()
            
            if is_v3:
                # 关闭方向分类器（不需要处理旋转文档），显式设置 det_limit_side_len=960
                _paddleocr_instance = PaddleOCR(
                    use_textline_orientation=False,  # 关闭方向分类，提速 10-20%
                    lang=lang,
                    det_limit_side_len=960  # 显式设置检测图像最大边长
                )
            else:
                # 关闭方向分类器，显式设置 det_limit_side_len=960
                _paddleocr_instance = PaddleOCR(
                    use_angle_cls=False,  # 关闭方向分类，提速 10-20%
                    lang=lang,
                    use_gpu=False,
                    show_log=False,
                    det_limit_side_len=960  # 显式设置检测图像最大边长
                )
            
            elapsed = time.time() - start_time
            logger.info(f"PaddleOCR 基础引擎加载完成，耗时 {elapsed:.1f} 秒")
            return _paddleocr_instance
            
        except Exception as e:
            logger.error(f"PaddleOCR 基础引擎加载失败: {e}")
            return None

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
        
        # 缓存 PPStructure 的结果，避免重复处理
        # key: image_path, value: processed_result
        self._ppstructure_result_cache = {}
        
        # Initialize engines lazily to avoid import errors during testing
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize PaddleOCR engines with error handling
        
        使用缓存的单例实例，避免重复加载模型
        PaddleOCR 3.x 中，PPStructureV3 已经包含了完整的 OCR 功能，
        不需要单独创建 PaddleOCR 实例
        """
        try:
            import paddleocr
            version = getattr(paddleocr, '__version__', '2.0.0')
            is_v3 = version.startswith('3.')
            
            if is_v3:
                # PaddleOCR 3.x: 使用缓存的 PPStructureV3 实例
                # PPStructureV3 已经包含了 OCR 功能，不需要单独的 PaddleOCR 实例
                ppstructure = get_ppstructure_v3_instance()
                if ppstructure is not None:
                    # 使用 PPStructureV3 作为主引擎
                    self._ocr_engine = ppstructure
                    self._structure_engine = ppstructure
                    logger.info("使用缓存的 PPStructureV3 作为 OCR 引擎")
                    return
                
                # 如果 PPStructureV3 不可用，回退到 PaddleOCR
                cached_ocr = get_paddleocr_instance(self.lang)
                if cached_ocr is not None:
                    self._ocr_engine = cached_ocr
                    self._structure_engine = cached_ocr
                    logger.info("使用缓存的 PaddleOCR 引擎实例")
                    return
            
            # PaddleOCR 2.x 或缓存不可用时，创建新实例
            logger.warning("缓存实例不可用，创建新的 PaddleOCR 实例...")
            from paddleocr import PaddleOCR
            
            if is_v3:
                # 关闭方向分类器（不需要处理旋转文档），显式设置 det_limit_side_len=960
                self._ocr_engine = PaddleOCR(
                    use_textline_orientation=False,  # 关闭方向分类，提速 10-20%
                    lang=self.lang,
                    det_limit_side_len=960  # 显式设置检测图像最大边长
                )
            else:
                # 关闭方向分类器，显式设置 det_limit_side_len=960
                self._ocr_engine = PaddleOCR(
                    use_angle_cls=False,  # 关闭方向分类，提速 10-20%
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False,
                    det_limit_side_len=960  # 显式设置检测图像最大边长
                )
            
            self._structure_engine = self._ocr_engine
            logger.info(f"PaddleOCR engines initialized (version: {version})")
            
        except Exception as e:
            raise OCRProcessingError(f"Engine initialization failed: {e}")
    
    def _convert_v3_result_to_legacy(self, v3_results: List) -> List:
        """
        将 PaddleOCR 3.x 的 OCRResult 格式转换为 2.x 的旧格式
        
        PaddleOCR 3.x 返回格式:
        - OCRResult 对象，包含 dt_polys, rec_texts, rec_scores 等属性
        - dt_polys: numpy array, shape (N, 4, 2) - N个检测框，每个框4个点，每个点2个坐标
        
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
            if isinstance(result, dict):
                dt_polys = result.get('dt_polys', [])
                rec_texts = result.get('rec_texts', [])
                rec_scores = result.get('rec_scores', [])
            else:
                dt_polys = getattr(result, 'dt_polys', [])
                rec_texts = getattr(result, 'rec_texts', [])
                rec_scores = getattr(result, 'rec_scores', [])
            
            # 转换为旧格式
            for i, poly in enumerate(dt_polys):
                text = rec_texts[i] if i < len(rec_texts) else ''
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                
                # 将 numpy 数组转换为列表
                # poly 的形状是 (4, 2)，即 4 个点，每个点 2 个坐标
                if hasattr(poly, 'tolist'):
                    poly_list = poly.tolist()
                else:
                    poly_list = list(poly)
                
                # 确保是正确的格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                if len(poly_list) == 4 and len(poly_list[0]) == 2:
                    bbox_points = poly_list
                else:
                    # 尝试其他格式转换
                    logger.warning(f"Unexpected poly format: {poly_list}")
                    continue
                
                # 旧格式: [bbox_points, (text, confidence)]
                page_results.append([bbox_points, (text, float(score))])
            
            legacy_results.append(page_results)
        
        return legacy_results
    
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
    
    def _normalize_image_size_with_scale(self, image: Image.Image, max_dimension: int = 1280) -> Tuple[Image.Image, Dict[str, Any]]:
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
    
    def _normalize_image_size(self, image: Image.Image, max_dimension: int = 1280) -> Image.Image:
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
        
        PaddleOCR 3.x API 适配：
        - 使用 predict 方法替代 ocr 方法
        - 处理新的 OCRResult 返回格式
        
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
                import paddleocr
                start_time = time.time()
                
                # Preprocess image for better results and get scale info
                preprocessed_path, scale_info = self.preprocess_image(image_path)
                
                # 检测 PaddleOCR 版本并使用相应的 API
                version = getattr(paddleocr, '__version__', '2.0.0')
                is_v3 = version.startswith('3.')
                
                if is_v3:
                    # PaddleOCR 3.x: 使用 predict 方法
                    # 禁用不必要的功能以加速处理：
                    # - use_doc_orientation_classify=False: 禁用文档方向分类
                    # - use_doc_unwarping=False: 禁用文档去畸变
                    # - use_seal_recognition=False: 禁用印章识别
                    # - use_formula_recognition=False: 禁用公式识别
                    # - use_chart_recognition=False: 禁用图表识别
                    raw_result = list(self._structure_engine.predict(
                        preprocessed_path,
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_seal_recognition=False,
                        use_formula_recognition=False,
                        use_chart_recognition=False
                    ))
                    
                    # 处理 PPStructureV3 的返回格式并缓存
                    # 这样 extract_tables 可以直接使用缓存的结果，避免重复调用 predict()
                    processed_ppstructure_result = self._process_ppstructure_v3_result(raw_result, preprocessed_path)
                    self._ppstructure_result_cache[preprocessed_path] = processed_ppstructure_result
                    # 同时缓存原始图像路径的结果
                    self._ppstructure_result_cache[image_path] = processed_ppstructure_result
                    
                    # 保存 PPStructure HTML 输出（传入开始时间和 scale_info）
                    self._save_ppstructure_html(image_path, processed_ppstructure_result, start_time, scale_info)
                    
                    # 【修复】使用 PPStructureV3 的布局分析结果创建 regions
                    # 而不是使用 OCR 文本行结果
                    regions = self._parse_ppstructure_v3_to_regions(processed_ppstructure_result)
                    
                    # 同时保存 OCR 文本行结果用于下载
                    structure_result = self._convert_v3_result_to_legacy(raw_result)
                    self._save_raw_ocr_output(image_path, structure_result, scale_info)
                else:
                    # PaddleOCR 2.x: 使用 ocr 方法
                    structure_result = self._structure_engine.ocr(preprocessed_path, cls=True)
                    
                    # Save raw OCR output for download
                    self._save_raw_ocr_output(image_path, structure_result, scale_info)
                    
                    # Parse structure results with enhanced classification
                    regions = self._parse_structure_result(structure_result)
                
                # Convert coordinates back to original image scale
                regions = self._scale_regions_to_original(regions, scale_info)
                
                # 【重要】只在 PaddleOCR 2.x 时进行启发式布局分类增强
                # PaddleOCR 3.x (PPStructureV3) 已经内置了深度学习布局分析，
                # 不需要也不应该用启发式规则覆盖其分类结果
                if not is_v3:
                    regions = self._enhance_layout_classification(regions, image_path)
                
                # Sort regions by reading order (top to bottom, left to right)
                regions = self._sort_regions_by_reading_order(regions)
                
                # Calculate confidence metrics
                confidence_metrics = self._calculate_confidence_metrics(regions)
                
                # 计算处理时间
                end_time = time.time()
                processing_time = end_time - start_time
                
                # 生成置信度计算日志（包含时间信息）
                try:
                    output_folder = str(Path(image_path).parent)
                    # 从 image_path 提取 job_id
                    image_name = Path(image_path).stem
                    if '_page' in image_name:
                        job_id = image_name.split('_page')[0]
                    else:
                        job_id = image_name
                    self.generate_confidence_log(regions, job_id, output_folder, start_time, end_time, processing_time)
                except Exception as e:
                    logger.warning(f"生成置信度日志失败: {e}")
                
                # 保留预处理后的图像用于调试（不再删除）
                # 文件名格式: {job_id}_page1_preprocessed.png
                if preprocessed_path != image_path:
                    logger.info(f"保留预处理图像用于调试: {preprocessed_path}")
                
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
    
    def _save_ppstructure_html(self, image_path: str, ppstructure_result: List, start_time: float = None, scale_info: Dict[str, Any] = None) -> None:
        """
        Save PPStructure raw HTML output for download - 包含所有内容（文本+表格）
        同时读取普通 OCR 结果，将未被 PPStructure 识别的文本也添加到 HTML 中
        
        Args:
            image_path: Path to the original image
            ppstructure_result: Raw result from PPStructure
            start_time: OCR 处理开始时间戳
            scale_info: 图像缩放信息
        """
        from pathlib import Path
        import json
        import time
        from datetime import datetime
        
        try:
            # Extract job_id from image path
            image_name = Path(image_path).stem
            if '_page' in image_name:
                job_id = image_name.split('_page')[0]
            else:
                job_id = image_name
            
            output_folder = Path(image_path).parent
            
            # 计算时间信息
            current_time = time.time()
            start_datetime = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S') if start_time else None
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elapsed_time = f"{current_time - start_time:.2f}s" if start_time else None
            
            # 保存 PPStructure 原始结果到 JSON 文件
            ppstructure_json_path = output_folder / f"{job_id}_ppstructure.json"
            
            # 使用传入的 scale_info
            scale_info_for_save = scale_info if scale_info else {}
            
            ppstructure_json_data = {
                'job_id': job_id,
                'image_path': str(image_path),
                'processing_info': {
                    'start_time': start_datetime,
                    'save_time': current_datetime,
                    'elapsed_at_save': elapsed_time
                },
                'scale_info': scale_info_for_save,  # 添加缩放信息用于调试
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
                    # 表格无 OCR 置信度（SLANet 模型不输出置信度）
                    item_data['res'] = {
                        'html': res.get('html', ''),
                        'cell_bbox': res.get('cell_bbox', []),
                        'confidence': res.get('confidence', None)  # 表格置信度为 None
                    }
                elif isinstance(res, list):
                    # 文本类型，包含文本行列表
                    item_data['res'] = []
                    for text_item in res:
                        if isinstance(text_item, dict):
                            # 保留真实的置信度，None 表示无置信度
                            conf = text_item.get('confidence')
                            item_data['res'].append({
                                'text': text_item.get('text', ''),
                                'confidence': conf,  # 保留 None 或真实值
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
    
    def generate_markdown_output(self, image_path: str, ppstructure_result: List) -> str:
        """
        Generate Markdown output from PPStructure result
        
        PaddleOCR 3.x 新功能：支持 Markdown 格式输出
        
        Args:
            image_path: Path to the original image
            ppstructure_result: Raw result from PPStructure
            
        Returns:
            Markdown formatted string
        """
        from pathlib import Path
        
        # Extract job_id from image path
        image_name = Path(image_path).stem
        if '_page' in image_name:
            job_id = image_name.split('_page')[0]
        else:
            job_id = image_name
        
        # Sort results by y-coordinate (top to bottom reading order)
        sorted_results = sorted(ppstructure_result, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1])
        
        markdown_parts = []
        
        for item in sorted_results:
            item_type = item.get('type', 'unknown')
            res = item.get('res', {})
            
            if item_type == 'title':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    # 使用 # 作为标题
                    markdown_parts.append(f"# {text_content}")
                    markdown_parts.append("")
                    
            elif item_type == 'text':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    markdown_parts.append(text_content)
                    markdown_parts.append("")
                    
            elif item_type == 'header':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    # 页眉使用斜体
                    markdown_parts.append(f"*{text_content}*")
                    markdown_parts.append("")
                    
            elif item_type == 'footer':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    # 页脚使用斜体
                    markdown_parts.append(f"*{text_content}*")
                    markdown_parts.append("")
                    
            elif item_type == 'table':
                table_md = self._convert_table_to_markdown(res)
                if table_md:
                    markdown_parts.append(table_md)
                    markdown_parts.append("")
                    
            elif item_type == 'figure':
                markdown_parts.append("![图像]()")
                markdown_parts.append("")
                
            elif item_type == 'figure_caption':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    markdown_parts.append(f"*图: {text_content}*")
                    markdown_parts.append("")
                    
            elif item_type == 'table_caption':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    markdown_parts.append(f"*表: {text_content}*")
                    markdown_parts.append("")
                    
            elif item_type == 'reference':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    markdown_parts.append(f"> {text_content}")
                    markdown_parts.append("")
                    
            elif item_type == 'equation':
                text_content = self._extract_text_from_res(res)
                if text_content:
                    # 公式使用 LaTeX 格式
                    markdown_parts.append(f"$${text_content}$$")
                    markdown_parts.append("")
                    
            else:
                text_content = self._extract_text_from_res(res)
                if text_content:
                    markdown_parts.append(text_content)
                    markdown_parts.append("")
        
        markdown_content = '\n'.join(markdown_parts)
        
        # 保存 Markdown 文件
        output_folder = Path(image_path).parent
        md_path = output_folder / f"{job_id}_raw_ocr.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logger.info(f"Saved Markdown to: {md_path}")
        
        return markdown_content
    
    def _convert_table_to_markdown(self, table_res) -> str:
        """
        Convert table result to Markdown table format
        
        Args:
            table_res: Table result from PPStructure (dict with 'html' or list)
            
        Returns:
            Markdown table string
        """
        try:
            # 如果有 HTML，从 HTML 解析
            if isinstance(table_res, dict) and 'html' in table_res:
                return self._html_table_to_markdown(table_res['html'])
            
            # 如果是列表格式
            if isinstance(table_res, list):
                return self._list_to_markdown_table(table_res)
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to convert table to Markdown: {e}")
            return ""
    
    def _html_table_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML table to Markdown format
        
        Args:
            html_content: HTML table string
            
        Returns:
            Markdown table string
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return ""
            
            rows = table.find_all('tr')
            if not rows:
                return ""
            
            markdown_rows = []
            max_cols = 0
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                max_cols = max(max_cols, len(cell_texts))
                
                # 转义 Markdown 特殊字符
                cell_texts = [text.replace('|', '\\|') for text in cell_texts]
                
                markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
                
                # 在第一行后添加分隔符
                if row_idx == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cell_texts)) + ' |'
                    markdown_rows.append(separator)
            
            return '\n'.join(markdown_rows)
            
        except ImportError:
            logger.warning("BeautifulSoup not available for HTML table parsing")
            return ""
        except Exception as e:
            logger.warning(f"HTML table to Markdown conversion failed: {e}")
            return ""
    
    def _list_to_markdown_table(self, table_data: List) -> str:
        """
        Convert list-based table data to Markdown format
        
        Args:
            table_data: List of rows, each row is a list of cells
            
        Returns:
            Markdown table string
        """
        if not table_data:
            return ""
        
        markdown_rows = []
        
        for row_idx, row in enumerate(table_data):
            if isinstance(row, list):
                cell_texts = [str(cell).replace('|', '\\|') for cell in row]
                markdown_rows.append('| ' + ' | '.join(cell_texts) + ' |')
                
                # 在第一行后添加分隔符
                if row_idx == 0:
                    separator = '| ' + ' | '.join(['---'] * len(cell_texts)) + ' |'
                    markdown_rows.append(separator)
        
        return '\n'.join(markdown_rows)
    
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
        
        注意：此函数仅在 PaddleOCR 2.x 时使用
        PaddleOCR 3.x (PPStructureV3) 已经内置了深度学习布局分析，不需要此函数
        
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
        
        【改进】添加更详细的置信度统计信息，包括：
        - 有置信度的区域数量
        - 无置信度的区域数量
        - 置信度覆盖率
        
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
                'region_count': 0,
                'regions_with_confidence': 0,
                'regions_without_confidence': 0,
                'confidence_coverage': 0.0
            }
        
        # 分别统计有置信度和无置信度的区域
        regions_with_conf = [r for r in regions if r.confidence is not None and r.confidence > 0]
        regions_without_conf = [r for r in regions if r.confidence is None or r.confidence <= 0]
        
        # Calculate text confidence (average of all text confidences)
        text_confidences = [r.confidence for r in regions_with_conf]
        text_confidence = sum(text_confidences) / len(text_confidences) if text_confidences else 0.0
        
        # Calculate layout confidence based on region distribution and classification
        layout_confidence = self._calculate_layout_confidence(regions)
        
        # 计算置信度覆盖率
        confidence_coverage = len(regions_with_conf) / len(regions) if regions else 0.0
        
        # Overall confidence is weighted average
        # 【改进】考虑置信度覆盖率对整体置信度的影响
        # 如果覆盖率低，整体置信度也应该降低
        base_confidence = (text_confidence * 0.7 + layout_confidence * 0.3)
        # 覆盖率惩罚：覆盖率低于 50% 时开始惩罚
        coverage_penalty = min(1.0, confidence_coverage / 0.5) if confidence_coverage < 0.5 else 1.0
        overall_confidence = base_confidence * (0.5 + 0.5 * coverage_penalty)
        
        # 记录日志
        logger.info(f"Confidence metrics: {len(regions_with_conf)}/{len(regions)} regions have confidence "
                   f"(coverage: {confidence_coverage:.1%}), avg: {text_confidence:.4f}")
        
        # 保留完整精度，不做round处理
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
        Calculate confidence score for layout analysis quality
        
        【修复】调整置信度计算逻辑：
        - 降低类型多样性的权重（文档可能只有表格也是正常的）
        - 增加内容质量的权重
        - 使用加权平均而非简单平均
        
        Args:
            regions: List of analyzed regions
            
        Returns:
            Layout confidence score (0.0 to 1.0)
        """
        if not regions:
            return 0.0
        
        # Factor 1: Region diversity (降低权重，因为文档可能只有特定类型)
        # 只要有 1 种以上类型就给较高分数
        region_types = set(r.classification for r in regions)
        num_types = len(region_types)
        if num_types >= 3:
            type_diversity = 1.0
        elif num_types == 2:
            type_diversity = 0.9
        else:
            type_diversity = 0.7  # 即使只有一种类型也给 0.7
        
        # Factor 2: Reasonable region sizes (not too small or too large)
        reasonable_sizes = 0
        for region in regions:
            area = region.coordinates.width * region.coordinates.height
            # 放宽面积范围，PPStructureV3 的区域通常较大
            if 50 < area < 10000000:  # 更宽松的面积范围
                reasonable_sizes += 1
        size_factor = reasonable_sizes / len(regions) if regions else 0.5
        
        # Factor 3: Text content quality (regions should have meaningful content)
        meaningful_content = 0
        for region in regions:
            if region.content and len(region.content.strip()) > 3:
                meaningful_content += 1
        content_factor = meaningful_content / len(regions) if regions else 0.5
        
        # 加权平均：内容质量权重最高，类型多样性权重最低
        # 权重：内容质量 0.5, 尺寸合理性 0.3, 类型多样性 0.2
        layout_confidence = (
            content_factor * 0.5 +
            size_factor * 0.3 +
            type_diversity * 0.2
        )
        
        return layout_confidence
    
    def generate_confidence_log(self, regions: List[Region], job_id: str, output_folder: str, 
                                start_time: float = None, end_time: float = None, processing_time: float = None) -> str:
        """
        生成详细的置信度计算日志（Markdown 格式）
        
        此方法生成一个详细的 MD 文件，展示置信度计算的完整过程，包括：
        1. 处理时间信息
        2. 每个区域的置信度详情
        3. 文本置信度计算过程
        4. 布局置信度计算过程
        5. 总体置信度计算过程
        
        Args:
            regions: 识别的区域列表
            job_id: 任务 ID
            output_folder: 输出文件夹路径
            start_time: OCR 处理开始时间戳
            end_time: OCR 处理结束时间戳
            processing_time: 处理耗时（秒）
            
        Returns:
            生成的日志文件路径
        """
        from datetime import datetime
        
        lines = []
        lines.append("# 置信度计算详细日志")
        lines.append("")
        lines.append(f"**任务 ID**: `{job_id}`")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # ========== 处理时间信息 ==========
        lines.append("---")
        lines.append("## 处理时间信息")
        lines.append("")
        if start_time:
            lines.append(f"- **开始时间**: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if end_time:
            lines.append(f"- **结束时间**: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        if processing_time is not None:
            lines.append(f"- **处理耗时**: {processing_time:.2f}s")
        lines.append("")
        
        # ========== 1. 区域概览 ==========
        lines.append("---")
        lines.append("## 1. 区域概览")
        lines.append("")
        lines.append(f"- **总区域数**: {len(regions)}")
        
        # 分类统计
        regions_with_conf = [r for r in regions if r.confidence is not None and r.confidence > 0]
        regions_without_conf = [r for r in regions if r.confidence is None or r.confidence <= 0]
        
        lines.append(f"- **有置信度的区域**: {len(regions_with_conf)}")
        lines.append(f"- **无置信度的区域**: {len(regions_without_conf)}")
        lines.append(f"- **置信度覆盖率**: {len(regions_with_conf) / len(regions) * 100:.1f}%" if regions else "- **置信度覆盖率**: 0%")
        lines.append("")
        
        # ========== 2. 每个区域的详细信息 ==========
        lines.append("---")
        lines.append("## 2. 各区域置信度详情")
        lines.append("")
        
        if not regions:
            lines.append("*无识别区域*")
        else:
            lines.append("| 序号 | 类型 | 位置 (x,y) | 尺寸 (w×h) | 置信度 | 内容预览 |")
            lines.append("|------|------|------------|------------|--------|----------|")
            
            for i, region in enumerate(regions):
                conf_str = f"{region.confidence}" if region.confidence is not None else "无"
                content_preview = (region.content[:30] + "...") if region.content and len(region.content) > 30 else (region.content or "")
                content_preview = content_preview.replace("|", "\\|").replace("\n", " ")
                
                lines.append(f"| {i+1} | {region.classification.value} | ({region.coordinates.x:.0f}, {region.coordinates.y:.0f}) | {region.coordinates.width:.0f}×{region.coordinates.height:.0f} | {conf_str} | {content_preview} |")
        
        lines.append("")
        
        # ========== 3. 文本置信度计算 ==========
        lines.append("---")
        lines.append("## 3. 文本置信度计算")
        lines.append("")
        
        text_confidences = [r.confidence for r in regions_with_conf]
        
        if text_confidences:
            lines.append("### 3.1 有效置信度值列表")
            lines.append("")
            lines.append("```")
            for i, conf in enumerate(text_confidences):
                lines.append(f"  区域 {i+1}: {conf}")
            lines.append("```")
            lines.append("")
            
            text_confidence = sum(text_confidences) / len(text_confidences)
            lines.append("### 3.2 计算过程")
            lines.append("")
            lines.append("```")
            lines.append(f"文本置信度 = 所有有效置信度的平均值")
            lines.append(f"           = ({' + '.join([f'{c}' for c in text_confidences])}) / {len(text_confidences)}")
            lines.append(f"           = {sum(text_confidences)} / {len(text_confidences)}")
            lines.append(f"           = {text_confidence}")
            lines.append("```")
        else:
            text_confidence = 0.0
            lines.append("*无有效置信度数据，文本置信度 = 0.0*")
        
        lines.append("")
        
        # ========== 4. 布局置信度计算 ==========
        lines.append("---")
        lines.append("## 4. 布局置信度计算")
        lines.append("")
        
        if not regions:
            layout_confidence = 0.0
            lines.append("*无区域数据，布局置信度 = 0.0*")
        else:
            # Factor 1: 类型多样性
            region_types = set(r.classification for r in regions)
            num_types = len(region_types)
            if num_types >= 3:
                type_diversity = 1.0
            elif num_types == 2:
                type_diversity = 0.9
            else:
                type_diversity = 0.7
            
            lines.append("### 4.1 类型多样性因子")
            lines.append("")
            lines.append(f"- 检测到的区域类型: {', '.join([t.value for t in region_types])}")
            lines.append(f"- 类型数量: {num_types}")
            lines.append(f"- 多样性评分规则: ≥3种类型=1.0, 2种类型=0.9, 1种类型=0.7")
            lines.append(f"- **类型多样性因子**: {type_diversity:.2f}")
            lines.append("")
            
            # Factor 2: 尺寸合理性
            reasonable_sizes = 0
            size_details = []
            for region in regions:
                area = region.coordinates.width * region.coordinates.height
                is_reasonable = 50 < area < 10000000
                if is_reasonable:
                    reasonable_sizes += 1
                size_details.append((area, is_reasonable))
            size_factor = reasonable_sizes / len(regions)
            
            lines.append("### 4.2 尺寸合理性因子")
            lines.append("")
            lines.append(f"- 合理尺寸范围: 50 < 面积 < 10,000,000 像素")
            lines.append(f"- 合理尺寸区域数: {reasonable_sizes} / {len(regions)}")
            lines.append(f"- **尺寸合理性因子**: {size_factor}")
            lines.append("")
            
            # Factor 3: 内容质量
            meaningful_content = 0
            for region in regions:
                if region.content and len(region.content.strip()) > 3:
                    meaningful_content += 1
            content_factor = meaningful_content / len(regions)
            
            lines.append("### 4.3 内容质量因子")
            lines.append("")
            lines.append(f"- 有效内容标准: 内容长度 > 3 字符")
            lines.append(f"- 有效内容区域数: {meaningful_content} / {len(regions)}")
            lines.append(f"- **内容质量因子**: {content_factor}")
            lines.append("")
            
            # 计算布局置信度
            layout_confidence = content_factor * 0.5 + size_factor * 0.3 + type_diversity * 0.2
            
            lines.append("### 4.4 布局置信度计算")
            lines.append("")
            lines.append("```")
            lines.append("布局置信度 = 内容质量因子 × 0.5 + 尺寸合理性因子 × 0.3 + 类型多样性因子 × 0.2")
            lines.append(f"           = {content_factor} × 0.5 + {size_factor} × 0.3 + {type_diversity} × 0.2")
            lines.append(f"           = {content_factor * 0.5} + {size_factor * 0.3} + {type_diversity * 0.2}")
            lines.append(f"           = {layout_confidence}")
            lines.append("```")
        
        lines.append("")
        
        # ========== 5. 总体置信度计算 ==========
        lines.append("---")
        lines.append("## 5. 总体置信度计算")
        lines.append("")
        
        if not regions:
            overall_confidence = 0.0
            lines.append("*无区域数据，总体置信度 = 0.0*")
        else:
            confidence_coverage = len(regions_with_conf) / len(regions)
            base_confidence = text_confidence * 0.7 + layout_confidence * 0.3
            coverage_penalty = min(1.0, confidence_coverage / 0.5) if confidence_coverage < 0.5 else 1.0
            overall_confidence = base_confidence * (0.5 + 0.5 * coverage_penalty)
            
            lines.append("### 5.1 基础置信度")
            lines.append("")
            lines.append("```")
            lines.append("基础置信度 = 文本置信度 × 0.7 + 布局置信度 × 0.3")
            lines.append(f"           = {text_confidence} × 0.7 + {layout_confidence} × 0.3")
            lines.append(f"           = {text_confidence * 0.7} + {layout_confidence * 0.3}")
            lines.append(f"           = {base_confidence}")
            lines.append("```")
            lines.append("")
            
            lines.append("### 5.2 覆盖率惩罚")
            lines.append("")
            lines.append(f"- 置信度覆盖率: {confidence_coverage} ({confidence_coverage * 100:.1f}%)")
            lines.append(f"- 惩罚规则: 覆盖率 < 50% 时开始惩罚")
            if confidence_coverage < 0.5:
                lines.append(f"- 惩罚因子 = min(1.0, {confidence_coverage} / 0.5) = {coverage_penalty}")
            else:
                lines.append(f"- 覆盖率 ≥ 50%，无惩罚，惩罚因子 = 1.0")
            lines.append("")
            
            lines.append("### 5.3 最终计算")
            lines.append("")
            lines.append("```")
            lines.append("总体置信度 = 基础置信度 × (0.5 + 0.5 × 惩罚因子)")
            lines.append(f"           = {base_confidence} × (0.5 + 0.5 × {coverage_penalty})")
            lines.append(f"           = {base_confidence} × {0.5 + 0.5 * coverage_penalty}")
            lines.append(f"           = {overall_confidence}")
            lines.append("```")
        
        lines.append("")
        
        # ========== 6. 结果汇总 ==========
        lines.append("---")
        lines.append("## 6. 结果汇总")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 总区域数 | {len(regions)} |")
        lines.append(f"| 有置信度区域 | {len(regions_with_conf)} |")
        lines.append(f"| 无置信度区域 | {len(regions_without_conf)} |")
        lines.append(f"| 置信度覆盖率 | {len(regions_with_conf) / len(regions) * 100:.1f}% |" if regions else "| 置信度覆盖率 | 0% |")
        lines.append(f"| 文本置信度 | {text_confidence} |")
        lines.append(f"| 布局置信度 | {layout_confidence} |")
        lines.append(f"| **总体置信度** | **{overall_confidence}** |")
        lines.append("")
        
        # 写入文件
        log_content = "\n".join(lines)
        log_path = os.path.join(output_folder, f"{job_id}_confidence_log.md")
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        logger.info(f"置信度计算日志已保存: {log_path}")
        return log_path
    
    def _parse_ppstructure_v3_to_regions(self, ppstructure_result: List[Dict[str, Any]]) -> List[Region]:
        """
        将 PPStructureV3 的布局分析结果转换为 Region 对象列表
        
        PPStructureV3 返回的每个 item 包含：
        - type: 区域类型（table, text, figure, figure_caption, header, footer, reference 等）
        - bbox: 边界框 [x1, y1, x2, y2]
        - res: 内容（表格为 HTML 字典，文本为文本行列表）
        
        【重要修复说明】：
        - PPStructure 的 'figure' 类型可能包含文本内容，需要根据 res 内容判断
        - 如果 'figure' 的 res 是文本列表，应该作为 PARAGRAPH 处理
        - 只有当 res 为空或不包含文本时，才作为 IMAGE 处理
        
        Args:
            ppstructure_result: _process_ppstructure_v3_result 处理后的结果列表
            
        Returns:
            Region 对象列表
        """
        regions = []
        
        if not ppstructure_result:
            logger.warning("Empty PPStructureV3 result")
            return regions
        
        # PPStructureV3 类型到 RegionType 的基础映射
        # 注意：figure 类型需要根据内容动态判断
        type_mapping = {
            'table': RegionType.TABLE,
            'text': RegionType.PARAGRAPH,
            'title': RegionType.HEADER,
            'header': RegionType.HEADER,
            'footer': RegionType.PARAGRAPH,
            'figure': RegionType.IMAGE,  # 默认值，会根据内容动态调整
            'figure_caption': RegionType.PARAGRAPH,
            'table_caption': RegionType.PARAGRAPH,
            'reference': RegionType.PARAGRAPH,
            'equation': RegionType.PARAGRAPH,
            'chart': RegionType.IMAGE,
            'seal': RegionType.IMAGE,
        }
        
        for item in ppstructure_result:
            try:
                item_type = item.get('type', 'text')
                bbox = item.get('bbox', [0, 0, 0, 0])
                res = item.get('res', [])
                # 【新增】获取原始 PPStructureV3 类型和编辑类型
                original_struct_type = item.get('original_struct_type', item_type)
                edit_type = item.get('edit_type', 'table' if item_type == 'table' else 'text')
                
                # 计算边界框
                if len(bbox) == 4:
                    x1, y1, x2, y2 = bbox
                    bounding_box = BoundingBox(
                        x=float(x1),
                        y=float(y1),
                        width=float(x2 - x1),
                        height=float(y2 - y1)
                    )
                else:
                    continue
                
                # 提取文本内容和置信度
                content = ""
                confidence = None  # 默认无置信度
                has_text_content = False  # 标记是否有文本内容
                
                if item_type == 'table':
                    # 表格类型：res 是包含 html 的字典
                    if isinstance(res, dict):
                        content = res.get('html', '')
                        # 表格的置信度：SLANet 模型不输出置信度，设为 None
                        confidence = res.get('confidence', None)
                else:
                    # 其他类型：res 是文本行列表
                    if isinstance(res, list):
                        text_parts = []
                        confidences = []
                        for text_item in res:
                            if isinstance(text_item, dict):
                                text = text_item.get('text', '')
                                conf = text_item.get('confidence')  # 可能为 None
                                if text:
                                    text_parts.append(text)
                                    if conf is not None:
                                        confidences.append(conf)
                        content = '\n'.join(text_parts)
                        # 只有当有真实置信度时才计算平均值
                        if confidences:
                            confidence = sum(confidences) / len(confidences)
                        else:
                            confidence = None  # 无置信度
                        has_text_content = len(text_parts) > 0
                    elif isinstance(res, str):
                        content = res
                        has_text_content = bool(res.strip())
                        confidence = None  # 纯字符串无置信度
                
                # 【关键修复】动态判断 figure 类型的实际分类
                # PPStructure 的 'figure' 类型可能包含文本内容或 HTML 表格
                if item_type == 'figure' and has_text_content:
                    # 检查内容是否是 HTML 表格
                    content_lower = content.lower().strip()
                    if content_lower.startswith('<html') or content_lower.startswith('<table') or '<table>' in content_lower:
                        # 内容是 HTML 表格，作为 TABLE 处理
                        region_type = RegionType.TABLE
                        logger.debug(f"Figure with HTML table content treated as TABLE")
                    else:
                        # 普通文本内容，作为 PARAGRAPH 处理
                        region_type = RegionType.PARAGRAPH
                        logger.debug(f"Figure with text content treated as PARAGRAPH: {content[:50]}...")
                else:
                    # 使用默认映射
                    region_type = type_mapping.get(item_type, RegionType.PARAGRAPH)
                
                # 跳过空内容的区域（除了表格）
                if not content and item_type != 'table':
                    logger.debug(f"Skipping empty {item_type} region")
                    continue
                
                # 【新增】构建 metadata，包含原始类型信息
                region_metadata = {
                    'originalStructType': original_struct_type,  # PPStructureV3 原始类型
                    'editType': edit_type,  # 编辑类型: text 或 table
                }
                
                region = Region(
                    coordinates=bounding_box,
                    classification=region_type,
                    confidence=confidence,
                    content=content,
                    metadata=region_metadata
                )
                
                regions.append(region)
                logger.debug(f"Created region: type={region_type.value}, struct_type={original_struct_type}, content_len={len(content)}")
                
            except Exception as e:
                logger.warning(f"Failed to parse PPStructureV3 item: {e}")
                continue
        
        logger.info(f"Parsed {len(regions)} regions from PPStructureV3 result")
        return regions

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
        
        PaddleOCR 3.x API 适配：
        - 使用 predict 方法替代 ocr 方法
        - 处理新的返回格式
        
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
                import paddleocr
                version = getattr(paddleocr, '__version__', '2.0.0')
                is_v3 = version.startswith('3.')
                
                # If no specific regions provided, use full image OCR
                if not regions:
                    if is_v3:
                        result = list(self._ocr_engine.predict(image_path))
                        result = self._convert_v3_result_to_legacy(result)
                    else:
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
                        if is_v3:
                            ocr_result = list(self._ocr_engine.predict(temp_path))
                            ocr_result = self._convert_v3_result_to_legacy(ocr_result)
                        else:
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
        
        PaddleOCR 3.x API 适配：
        - 使用 PPStructureV3 替代 PPStructure
        - 使用缓存的单例实例，避免重复加载模型
        - 优先使用缓存的 PPStructure 结果，避免重复处理
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of detected TableStructure objects
        """
        try:
            # 首先检查是否有缓存的 PPStructure 结果
            # 这样可以避免重复调用 predict()
            if image_path in self._ppstructure_result_cache:
                logger.info(f"Using cached PPStructure result for {image_path}")
                processed_result = self._ppstructure_result_cache[image_path]
            else:
                # 没有缓存，需要调用 PPStructure
                # 使用缓存的 PPStructureV3 实例（避免重复加载模型）
                table_engine = get_ppstructure_v3_instance()
                
                if table_engine is not None:
                    logger.info("Using cached PPStructureV3 instance (PaddleOCR 3.x)")
                else:
                    # 回退到旧版 PPStructure (PaddleOCR 2.x)
                    try:
                        from paddleocr import PPStructure
                        table_engine = PPStructure(
                            use_gpu=self.use_gpu,
                            show_log=False,
                            lang=self.lang,
                            layout=True,
                            table=True,
                            ocr=True,
                            recovery=True,
                        )
                        logger.info("Using PPStructure (PaddleOCR 2.x fallback)")
                    except ImportError:
                        logger.warning("PPStructure not available, using fallback")
                        return self._fallback_table_detection(image_path)
                
                # Perform table detection
                # 禁用不必要的功能以加速处理
                result = table_engine.predict(
                    image_path,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_seal_recognition=False,
                    use_formula_recognition=False,
                    use_chart_recognition=False
                )
                
                # PPStructureV3 返回格式不同，需要适配
                if hasattr(result, '__iter__') and not isinstance(result, (str, dict)):
                    result_list = list(result)
                else:
                    result_list = [result] if result else []
                
                logger.info(f"PPStructure returned {len(result_list)} items")
                
                # 处理 PPStructureV3 的返回格式
                processed_result = self._process_ppstructure_v3_result(result_list, image_path)
                
                # 缓存结果
                self._ppstructure_result_cache[image_path] = processed_result
            
            # Save raw PPStructure HTML output
            self._save_ppstructure_html(image_path, processed_result)
            
            tables = []
            for idx, item in enumerate(processed_result):
                item_type = item.get('type', 'unknown')
                logger.info(f"Item {idx}: type={item_type}, keys={list(item.keys())}")
                
                if item_type == 'table':
                    table_structure = self._parse_table_result(item)
                    if table_structure:
                        if table_structure.rows > 20:
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
            
        except ImportError as e:
            logger.warning(f"PPStructure not available: {e}, using fallback table detection")
            return self._fallback_table_detection(image_path)
        except Exception as e:
            logger.warning(f"Table detection failed: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return []
    
    def _process_ppstructure_v3_result(self, result_list: List, image_path: str) -> List[Dict[str, Any]]:
        """
        处理 PPStructureV3 的返回结果，转换为统一格式
        
        PPStructureV3 返回 LayoutParsingResultV2 对象（dict-like），包含：
        - parsing_res_list: LayoutBlock 对象列表，每个对象有 block_label, block_bbox, block_content 属性
        - layout_det_res: 布局检测结果
        - table_res_list: 表格识别结果（包含 OCR 置信度）
        - overall_ocr_res: 整体 OCR 结果（包含所有文本行的置信度）
        
        【重要】PPStructureV3 结果对象是 dict-like，必须使用 result['key'] 访问，
        而不是 getattr(result, 'key')
        
        置信度获取策略（PaddleOCR 3.x 改进版）：
        - 表格区块：从 table_res_list[x].table_ocr_pred.rec_scores 获取平均置信度
        - 非表格区块：从 overall_ocr_res 获取文本行置信度，通过位置匹配关联到区块
        
        Args:
            result_list: PPStructureV3 返回的结果列表（通常只有一个页面结果）
            image_path: 图像路径
            
        Returns:
            统一格式的结果列表，兼容旧版 PPStructure 格式
        """
        processed = []
        
        for result in result_list:
            # PPStructureV3 返回 LayoutParsingResultV2 对象（dict-like）
            # 【重要】必须使用 [] 访问，不能用 hasattr/getattr
            parsing_res_list = None
            table_res_list = None
            overall_ocr_res = None
            
            # 尝试 dict-like 访问（PPStructureV3 的正确方式）
            try:
                if hasattr(result, '__getitem__') and hasattr(result, 'keys'):
                    # dict-like 对象，使用 [] 访问
                    parsing_res_list = result.get('parsing_res_list') if hasattr(result, 'get') else result['parsing_res_list']
                    table_res_list = result.get('table_res_list', []) if hasattr(result, 'get') else result.get('table_res_list', [])
                    overall_ocr_res = result.get('overall_ocr_res') if hasattr(result, 'get') else result.get('overall_ocr_res')
                    logger.debug(f"PPStructureV3 result keys: {list(result.keys())}")
                elif isinstance(result, dict):
                    parsing_res_list = result.get('parsing_res_list')
                    table_res_list = result.get('table_res_list', [])
                    overall_ocr_res = result.get('overall_ocr_res')
                else:
                    # 回退到属性访问
                    parsing_res_list = getattr(result, 'parsing_res_list', None)
                    table_res_list = getattr(result, 'table_res_list', [])
                    overall_ocr_res = getattr(result, 'overall_ocr_res', None)
            except (KeyError, TypeError) as e:
                logger.warning(f"Failed to access PPStructureV3 result: {e}")
                # 回退到属性访问
                parsing_res_list = getattr(result, 'parsing_res_list', None)
                table_res_list = getattr(result, 'table_res_list', [])
                overall_ocr_res = getattr(result, 'overall_ocr_res', None)
            
            # 【新增】从 overall_ocr_res 提取文本行置信度和位置信息
            # overall_ocr_res 包含 dt_polys (检测框), rec_texts (识别文本), rec_scores (识别置信度)
            ocr_text_lines = self._extract_ocr_text_lines_with_confidence(overall_ocr_res)
            if ocr_text_lines:
                logger.info(f"Extracted {len(ocr_text_lines)} text lines with confidence from overall_ocr_res")
            
            # 构建表格区域到置信度的映射
            # 从 table_res_list[x].table_ocr_pred.rec_scores 获取
            table_confidence_map = {}
            if table_res_list:
                for table_idx, table_res in enumerate(table_res_list):
                    try:
                        # table_res 也是 dict-like 对象
                        table_ocr_pred = None
                        if hasattr(table_res, '__getitem__'):
                            table_ocr_pred = table_res.get('table_ocr_pred') if hasattr(table_res, 'get') else None
                        if table_ocr_pred is None:
                            table_ocr_pred = getattr(table_res, 'table_ocr_pred', None)
                        
                        if table_ocr_pred:
                            # table_ocr_pred 也是 dict-like，rec_scores 是 numpy array
                            rec_scores = None
                            if hasattr(table_ocr_pred, '__getitem__'):
                                rec_scores = table_ocr_pred.get('rec_scores') if hasattr(table_ocr_pred, 'get') else None
                            if rec_scores is None:
                                rec_scores = getattr(table_ocr_pred, 'rec_scores', None)
                            
                            if rec_scores is not None and len(rec_scores) > 0:
                                # rec_scores 可能是 numpy array，需要转换
                                if hasattr(rec_scores, 'tolist'):
                                    rec_scores = rec_scores.tolist()
                                avg_confidence = sum(rec_scores) / len(rec_scores)
                                table_confidence_map[table_idx] = avg_confidence
                                logger.info(f"Table {table_idx} average OCR confidence: {avg_confidence:.4f} (from {len(rec_scores)} cells)")
                    except Exception as e:
                        logger.warning(f"Failed to extract confidence for table {table_idx}: {e}")
            
            if parsing_res_list:
                logger.info(f"Processing {len(parsing_res_list)} layout blocks from parsing_res_list")
                # 处理 LayoutBlock 对象列表
                table_block_idx = 0  # 用于匹配 table_res_list
                for block_idx, block in enumerate(parsing_res_list):
                    # 【重要】block 对象使用 block_label, block_content, block_bbox 属性
                    # 可能是 dict-like 或普通对象
                    label = None
                    block_bbox = None
                    try:
                        if hasattr(block, '__getitem__'):
                            label = block.get('block_label') if hasattr(block, 'get') else block['block_label']
                            block_bbox = block.get('block_bbox') if hasattr(block, 'get') else block.get('block_bbox')
                        if label is None:
                            label = getattr(block, 'block_label', None) or getattr(block, 'label', None)
                        if block_bbox is None:
                            block_bbox = getattr(block, 'block_bbox', None) or getattr(block, 'bbox', None)
                    except (KeyError, TypeError):
                        label = getattr(block, 'block_label', None) or getattr(block, 'label', None)
                        block_bbox = getattr(block, 'block_bbox', None) or getattr(block, 'bbox', None)
                    
                    # 获取置信度
                    block_confidence = None
                    if label == 'table' and table_block_idx in table_confidence_map:
                        block_confidence = table_confidence_map[table_block_idx]
                        table_block_idx += 1
                    elif label == 'table':
                        table_block_idx += 1
                    else:
                        # 【新增】非表格区块：从 overall_ocr_res 匹配置信度
                        if ocr_text_lines and block_bbox is not None:
                            block_confidence = self._match_block_confidence_from_ocr(block_bbox, ocr_text_lines)
                    
                    item_dict = self._convert_layout_block_to_dict(block, block_confidence)
                    if item_dict:
                        processed.append(item_dict)
                        logger.debug(f"Block {block_idx}: type={item_dict.get('type')}, confidence={block_confidence}")
            else:
                logger.warning("parsing_res_list is None or empty, trying fallback processing")
                # 回退：尝试旧格式处理
                if isinstance(result, dict):
                    if 'type' in result:
                        processed.append(result)
                    else:
                        for key, value in result.items():
                            if isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict) and 'type' in item:
                                        processed.append(item)
                elif hasattr(result, '__dict__'):
                    item_dict = {}
                    if hasattr(result, 'type'):
                        item_dict['type'] = result.type
                    if hasattr(result, 'bbox'):
                        item_dict['bbox'] = result.bbox
                    if hasattr(result, 'res'):
                        item_dict['res'] = result.res
                    if hasattr(result, 'html'):
                        item_dict['res'] = {'html': result.html}
                    if item_dict:
                        processed.append(item_dict)
        
        if not processed and result_list:
            logger.warning(f"Could not process PPStructureV3 result, result_list has {len(result_list)} items")
        else:
            logger.info(f"Processed {len(processed)} items from PPStructureV3 result")
        
        return processed
    
    def _extract_ocr_text_lines_with_confidence(self, overall_ocr_res) -> List[Dict[str, Any]]:
        """
        从 overall_ocr_res 提取所有文本行的置信度和位置信息
        
        overall_ocr_res 是 PPStructureV3 的整体 OCR 结果，包含：
        - dt_polys: 检测框坐标 (N, 4, 2) - N个检测框，每个框4个点
        - rec_texts: 识别的文本列表
        - rec_scores: 识别置信度列表
        
        Args:
            overall_ocr_res: PPStructureV3 的 overall_ocr_res 字段
            
        Returns:
            文本行列表，每个元素包含 bbox, text, confidence
        """
        text_lines = []
        
        if overall_ocr_res is None:
            return text_lines
        
        try:
            # 获取检测框、文本和置信度
            dt_polys = None
            rec_texts = None
            rec_scores = None
            
            # 尝试 dict-like 访问
            if hasattr(overall_ocr_res, '__getitem__'):
                try:
                    dt_polys = overall_ocr_res.get('dt_polys') if hasattr(overall_ocr_res, 'get') else overall_ocr_res['dt_polys']
                    rec_texts = overall_ocr_res.get('rec_texts') if hasattr(overall_ocr_res, 'get') else overall_ocr_res['rec_texts']
                    rec_scores = overall_ocr_res.get('rec_scores') if hasattr(overall_ocr_res, 'get') else overall_ocr_res['rec_scores']
                except (KeyError, TypeError):
                    pass
            
            # 回退到属性访问
            if dt_polys is None:
                dt_polys = getattr(overall_ocr_res, 'dt_polys', None)
            if rec_texts is None:
                rec_texts = getattr(overall_ocr_res, 'rec_texts', None)
            if rec_scores is None:
                rec_scores = getattr(overall_ocr_res, 'rec_scores', None)
            
            if dt_polys is None or rec_scores is None:
                logger.debug("overall_ocr_res missing dt_polys or rec_scores")
                return text_lines
            
            # 转换 numpy array 为列表
            if hasattr(dt_polys, 'tolist'):
                dt_polys = dt_polys.tolist()
            if hasattr(rec_scores, 'tolist'):
                rec_scores = rec_scores.tolist()
            if rec_texts is not None and hasattr(rec_texts, 'tolist'):
                rec_texts = rec_texts.tolist()
            
            # 构建文本行列表
            for i, poly in enumerate(dt_polys):
                if i >= len(rec_scores):
                    break
                
                # 计算边界框 [x1, y1, x2, y2]
                if len(poly) >= 4:
                    x_coords = [p[0] for p in poly]
                    y_coords = [p[1] for p in poly]
                    bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                else:
                    continue
                
                text = rec_texts[i] if rec_texts and i < len(rec_texts) else ''
                confidence = float(rec_scores[i])
                
                text_lines.append({
                    'bbox': bbox,
                    'text': text,
                    'confidence': confidence,
                    'poly': poly
                })
            
            logger.debug(f"Extracted {len(text_lines)} text lines from overall_ocr_res")
            
        except Exception as e:
            logger.warning(f"Failed to extract text lines from overall_ocr_res: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return text_lines
    
    def _match_block_confidence_from_ocr(self, block_bbox, ocr_text_lines: List[Dict[str, Any]]) -> Optional[float]:
        """
        根据布局区块的位置，从 OCR 文本行中匹配并计算平均置信度
        
        匹配策略：
        1. 计算每个 OCR 文本行与布局区块的 IoU (Intersection over Union)
        2. 如果 IoU > 0.3 或文本行中心点在区块内，则认为该文本行属于该区块
        3. 计算所有匹配文本行的平均置信度
        
        Args:
            block_bbox: 布局区块的边界框 [x1, y1, x2, y2] 或 numpy array
            ocr_text_lines: OCR 文本行列表
            
        Returns:
            平均置信度，如果没有匹配的文本行则返回 None
        """
        if not ocr_text_lines or block_bbox is None:
            return None
        
        try:
            # 转换 block_bbox 为列表
            if hasattr(block_bbox, 'tolist'):
                block_bbox = block_bbox.tolist()
            block_bbox = list(block_bbox)
            
            if len(block_bbox) != 4:
                return None
            
            bx1, by1, bx2, by2 = block_bbox
            block_area = (bx2 - bx1) * (by2 - by1)
            
            if block_area <= 0:
                return None
            
            matched_confidences = []
            
            for text_line in ocr_text_lines:
                line_bbox = text_line.get('bbox', [])
                if len(line_bbox) != 4:
                    continue
                
                lx1, ly1, lx2, ly2 = line_bbox
                
                # 计算文本行中心点
                center_x = (lx1 + lx2) / 2
                center_y = (ly1 + ly2) / 2
                
                # 检查中心点是否在区块内
                center_in_block = (bx1 <= center_x <= bx2) and (by1 <= center_y <= by2)
                
                # 计算 IoU
                inter_x1 = max(bx1, lx1)
                inter_y1 = max(by1, ly1)
                inter_x2 = min(bx2, lx2)
                inter_y2 = min(by2, ly2)
                
                if inter_x2 > inter_x1 and inter_y2 > inter_y1:
                    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
                    line_area = (lx2 - lx1) * (ly2 - ly1)
                    union_area = block_area + line_area - inter_area
                    iou = inter_area / union_area if union_area > 0 else 0
                else:
                    iou = 0
                
                # 如果 IoU > 0.3 或中心点在区块内，则匹配
                if iou > 0.3 or center_in_block:
                    confidence = text_line.get('confidence')
                    if confidence is not None:
                        matched_confidences.append(confidence)
            
            if matched_confidences:
                avg_confidence = sum(matched_confidences) / len(matched_confidences)
                logger.debug(f"Block matched {len(matched_confidences)} text lines, avg confidence: {avg_confidence:.4f}")
                return avg_confidence
            
        except Exception as e:
            logger.warning(f"Failed to match block confidence: {e}")
        
        return None
    
    def _convert_layout_block_to_dict(self, block, block_confidence: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        将 PPStructureV3 的 LayoutBlock 对象转换为统一的字典格式
        
        【重要】PPStructureV3 的 LayoutBlock 属性名称：
        - block_label: 区域类型（table, text, figure, figure_title, header, footer 等）
        - block_bbox: 边界框 [x1, y1, x2, y2]
        - block_content: 内容（表格为 HTML，文本为纯文本）
        - block_id: 区块 ID
        - block_order: 区块顺序
        
        注意：旧版使用 label, bbox, content，新版使用 block_label, block_bbox, block_content
        
        置信度说明（PaddleOCR 3.x 改进版）：
        - 表格区块：从 table_res_list 获取平均 OCR 置信度
        - 非表格区块：从 overall_ocr_res 匹配获取平均 OCR 置信度
        
        Args:
            block: LayoutBlock 对象（dict-like 或普通对象）
            block_confidence: 区块的平均 OCR 置信度（表格或文本区块）
            
        Returns:
            统一格式的字典，兼容旧版 PPStructure 格式
        """
        try:
            # 获取基本属性 - 支持 dict-like 和普通对象两种访问方式
            # PPStructureV3 使用 block_label, block_bbox, block_content
            label = None
            bbox = None
            content = None
            
            # 尝试 dict-like 访问（优先）
            if hasattr(block, '__getitem__'):
                try:
                    label = block.get('block_label') if hasattr(block, 'get') else block['block_label']
                except (KeyError, TypeError):
                    pass
                try:
                    bbox = block.get('block_bbox') if hasattr(block, 'get') else block['block_bbox']
                except (KeyError, TypeError):
                    pass
                try:
                    content = block.get('block_content') if hasattr(block, 'get') else block['block_content']
                except (KeyError, TypeError):
                    pass
            
            # 回退到属性访问（兼容旧版）
            if label is None:
                label = getattr(block, 'block_label', None) or getattr(block, 'label', None)
            if bbox is None:
                bbox = getattr(block, 'block_bbox', None) or getattr(block, 'bbox', None)
            if content is None:
                content = getattr(block, 'block_content', None) or getattr(block, 'content', None)
            
            if not label:
                logger.warning(f"Block has no label, skipping. Block type: {type(block)}")
                return None
            
            # 映射 label 到旧版 type
            type_mapping = {
                'table': 'table',
                'figure': 'figure',
                'figure_title': 'figure_caption',
                'text': 'text',
                'title': 'title',
                'header': 'header',
                'footer': 'footer',
                'reference': 'reference',
                'equation': 'equation',
                'table_title': 'table_caption',
                'chart': 'figure',
                'seal': 'figure',
                'doc_title': 'doc_title',
                'paragraph_title': 'title',  # 段落标题映射为标题
            }
            
            item_type = type_mapping.get(label, label)
            
            # 处理 bbox - 可能是 numpy array
            if bbox is not None:
                if hasattr(bbox, 'tolist'):
                    bbox = bbox.tolist()
                bbox = list(bbox)
            else:
                bbox = [0, 0, 0, 0]
            
            # 构建结果字典
            # 【新增】保存原始 PPStructureV3 类型 (original_struct_type) 和编辑类型 (edit_type)
            edit_type = 'table' if item_type == 'table' else 'text'
            item_dict = {
                'type': item_type,
                'bbox': bbox,
                'original_struct_type': label,  # PPStructureV3 原始类型
                'edit_type': edit_type,  # 编辑类型: text 或 table
            }
            
            # 处理内容
            if item_type == 'table':
                # 表格内容是 HTML
                # 使用从 table_res_list 获取的平均置信度
                if content and str(content).strip():
                    item_dict['res'] = {
                        'html': str(content),
                        'confidence': block_confidence  # 表格平均 OCR 置信度
                    }
                else:
                    item_dict['res'] = {
                        'html': '',
                        'confidence': block_confidence
                    }
                logger.debug(f"Table block: confidence={block_confidence}")
            else:
                # 其他类型，内容是文本
                if content and str(content).strip():
                    content_str = str(content)
                    # 【修复】检查内容是否是 HTML 表格
                    # 如果是 HTML 表格，应该作为 table 类型处理
                    content_lower = content_str.lower().strip()
                    if content_lower.startswith('<html') or content_lower.startswith('<table') or '<table>' in content_lower:
                        # 内容是 HTML 表格，修改类型为 table
                        item_dict['type'] = 'table'
                        item_dict['res'] = {
                            'html': content_str,
                            'confidence': block_confidence  # 使用区块置信度
                        }
                        logger.debug(f"Non-table block with HTML table content converted to table type")
                    else:
                        # 转换为旧版格式：res 是文本行列表
                        # 【改进】使用从 overall_ocr_res 匹配的置信度
                        item_dict['res'] = [{
                            'text': content_str.strip(),
                            'confidence': block_confidence,  # 使用从 overall_ocr_res 匹配的置信度
                            'text_region': []
                        }]
                else:
                    item_dict['res'] = []
            
            return item_dict
            
        except Exception as e:
            logger.warning(f"Failed to convert LayoutBlock to dict: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return None
    
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