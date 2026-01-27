"""
Job Cache Service - 基于文件系统的任务缓存

功能：
1. 保存任务元数据到 JSON 文件
2. 服务重启后可恢复历史任务
3. 前端可直接加载缓存的识别结果

存储结构：
- temp/job_cache.json - 任务索引文件
- temp/{job_id}_*.* - 各种中间结果文件（已有）
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

@dataclass
class CachedJob:
    """缓存的任务信息"""
    job_id: str
    filename: str
    created_at: float  # timestamp
    processing_time: float  # 处理耗时（秒）
    status: str  # completed, failed
    confidence_score: Optional[float] = None
    block_count: int = 0
    has_tables: bool = False
    document_type_id: Optional[str] = None  # 单据类型ID
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedJob':
        # 兼容旧数据，添加默认值
        if 'document_type_id' not in data:
            data['document_type_id'] = None
        return cls(**data)


class JobCacheService:
    """任务缓存服务"""
    
    def __init__(self, temp_folder: Path):
        self.temp_folder = Path(temp_folder)
        self.cache_file = self.temp_folder / 'job_cache.json'
        self._cache: Dict[str, CachedJob] = {}
        self._lock = threading.Lock()
        self._load_cache()
    
    def _load_cache(self) -> None:
        """从文件加载缓存"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for job_id, job_data in data.get('jobs', {}).items():
                        # 验证文件是否还存在
                        if self._verify_job_files(job_id):
                            self._cache[job_id] = CachedJob.from_dict(job_data)
                        else:
                            logger.info(f"Job {job_id} files missing, skipping")
                logger.info(f"Loaded {len(self._cache)} cached jobs")
        except Exception as e:
            logger.warning(f"Failed to load job cache: {e}")
            self._cache = {}
    
    def _save_cache(self) -> None:
        """保存缓存到文件"""
        try:
            self.temp_folder.mkdir(exist_ok=True)
            data = {
                'version': '1.0',
                'updated_at': time.time(),
                'jobs': {job_id: job.to_dict() for job_id, job in self._cache.items()}
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job cache: {e}")
    
    def _verify_job_files(self, job_id: str) -> bool:
        """验证任务的关键文件是否存在"""
        # 检查 ppstructure.json（可能在 temp 或 uploads 目录）
        ppstructure_in_temp = self.temp_folder / f"{job_id}_ppstructure.json"
        ppstructure_in_uploads = Path('uploads') / f"{job_id}_ppstructure.json"
        has_ppstructure = ppstructure_in_temp.exists() or ppstructure_in_uploads.exists()
        
        if not has_ppstructure:
            return False
        
        # 检查图片文件（PDF 转换的在 temp，直接上传的图片在 uploads）
        # temp 目录：PDF 转换后的 _page1.png
        image_in_temp = self.temp_folder / f"{job_id}_page1.png"
        if image_in_temp.exists():
            return True
        
        # uploads 目录：直接上传的图片文件（支持多种格式）
        for ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
            image_in_uploads = Path('uploads') / f"{job_id}.{ext}"
            if image_in_uploads.exists():
                return True
        
        return False
    
    def save_job(self, job_id: str, filename: str, processing_time: float,
                 confidence_score: Optional[float] = None, block_count: int = 0,
                 has_tables: bool = False, status: str = 'completed',
                 document_type_id: Optional[str] = None) -> None:
        """保存任务到缓存"""
        with self._lock:
            job = CachedJob(
                job_id=job_id,
                filename=filename,
                created_at=time.time(),
                processing_time=processing_time,
                status=status,
                confidence_score=confidence_score,
                block_count=block_count,
                has_tables=has_tables,
                document_type_id=document_type_id
            )
            self._cache[job_id] = job
            self._save_cache()
            logger.info(f"Cached job: {job_id} ({filename}) [doc_type: {document_type_id}]")
    
    def get_job(self, job_id: str) -> Optional[CachedJob]:
        """获取缓存的任务"""
        with self._lock:
            job = self._cache.get(job_id)
            if job and self._verify_job_files(job_id):
                return job
            return None
    
    def get_all_jobs(self, limit: int = 20) -> List[CachedJob]:
        """获取所有缓存的任务（按时间倒序）"""
        with self._lock:
            # 过滤掉文件已删除的任务
            valid_jobs = []
            invalid_ids = []
            
            for job_id, job in self._cache.items():
                if self._verify_job_files(job_id):
                    valid_jobs.append(job)
                else:
                    invalid_ids.append(job_id)
            
            # 清理无效任务
            for job_id in invalid_ids:
                del self._cache[job_id]
            
            if invalid_ids:
                self._save_cache()
            
            # 按创建时间倒序排序
            valid_jobs.sort(key=lambda x: x.created_at, reverse=True)
            return valid_jobs[:limit]
    
    def delete_job(self, job_id: str) -> bool:
        """删除缓存的任务"""
        with self._lock:
            if job_id in self._cache:
                del self._cache[job_id]
                self._save_cache()
                return True
            return False
    
    def get_latest_job(self) -> Optional[CachedJob]:
        """获取最新的任务"""
        jobs = self.get_all_jobs(limit=1)
        return jobs[0] if jobs else None
    
    def load_cached_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        加载缓存的识别结果
        
        返回与 /api/convert/{job_id}/result 相同格式的数据
        """
        job = self.get_job(job_id)
        if not job:
            return None
        
        try:
            # 加载 ppstructure.json（可能在 temp 或 uploads 目录）
            ppstructure_path = self.temp_folder / f"{job_id}_ppstructure.json"
            if not ppstructure_path.exists():
                ppstructure_path = Path('uploads') / f"{job_id}_ppstructure.json"
            
            with open(ppstructure_path, 'r', encoding='utf-8') as f:
                ppstructure_data = json.load(f)
            
            # 从 ppstructure 数据重建 Editor.js 格式
            blocks = self._rebuild_editor_blocks(ppstructure_data)
            
            # 加载置信度日志（如果有，可能在 temp 或 uploads 目录）
            confidence_log_path = self.temp_folder / f"{job_id}_confidence_log.md"
            if not confidence_log_path.exists():
                confidence_log_path = Path('uploads') / f"{job_id}_confidence_log.md"
            confidence_log = None
            if confidence_log_path.exists():
                with open(confidence_log_path, 'r', encoding='utf-8') as f:
                    confidence_log = f.read()
            
            # 加载 Markdown 内容（如果有）
            markdown_path = self.temp_folder / f"{job_id}_raw_ocr.md"
            if not markdown_path.exists():
                markdown_path = Path('uploads') / f"{job_id}_raw_ocr.md"
            markdown_content = None
            if markdown_path.exists():
                with open(markdown_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                logger.info(f"Loaded cached markdown for {job_id}")
            
            return {
                'job_id': job_id,
                'status': 'completed',
                'result': {
                    'time': int(job.created_at * 1000),
                    'blocks': blocks,
                    'version': '2.28.0'
                },
                'processing_time': job.processing_time,
                'confidence_report': {
                    'confidence_breakdown': {
                        'overall': {
                            'score': job.confidence_score or 0.85,
                            'level': self._get_confidence_level(job.confidence_score or 0.85),
                            'description': self._get_confidence_description(job.confidence_score or 0.85)
                        }
                    },
                    'warnings': [],
                    'has_warnings': False,
                    'warning_count': 0
                },
                'markdown': markdown_content,
                'cached': True,
                'cached_at': job.created_at,
                'document_type_id': job.document_type_id
            }
        except Exception as e:
            logger.error(f"Failed to load cached result for {job_id}: {e}")
            return None
    
    def _rebuild_editor_blocks(self, ppstructure_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 ppstructure 数据重建 Editor.js blocks"""
        blocks = []
        items = ppstructure_data.get('items', [])
        scale_info = ppstructure_data.get('scale_info', {})
        
        # 获取缩放比例（从预处理图像坐标转换回原始图像坐标）
        scale_x = scale_info.get('scale_x', 1.0)
        scale_y = scale_info.get('scale_y', 1.0)
        
        # 按 y 坐标排序
        sorted_items = sorted(items, key=lambda x: x.get('bbox', [0, 0, 0, 0])[1] if x.get('bbox') else 0)
        
        for idx, item in enumerate(sorted_items):
            item_type = item.get('type', 'text')
            res = item.get('res', {})
            bbox = item.get('bbox', [0, 0, 100, 30])
            confidence = item.get('confidence', 0.85)
            
            # 将坐标从预处理图像尺寸转换回原始图像尺寸
            x = bbox[0] * scale_x if len(bbox) > 0 else 0
            y = bbox[1] * scale_y if len(bbox) > 1 else 0
            width = (bbox[2] - bbox[0]) * scale_x if len(bbox) > 2 else 100
            height = (bbox[3] - bbox[1]) * scale_y if len(bbox) > 3 else 30
            
            block = {
                'id': f"block_{idx}",
                'type': 'table' if item_type == 'table' else 'paragraph',
                'data': {},
                'metadata': {
                    'originalCoordinates': {
                        'x': x,
                        'y': y,
                        'width': width,
                        'height': height
                    },
                    'confidence': confidence,
                    'originalStructType': item_type,
                    'editType': 'table' if item_type == 'table' else 'text'
                }
            }
            
            if item_type == 'table':
                html = res.get('html', '<table><tr><td>表格</td></tr></table>') if isinstance(res, dict) else '<table><tr><td>表格</td></tr></table>'
                block['data'] = {'tableHtml': html}
            else:
                text = self._extract_text(res)
                block['data'] = {'text': text}
            
            blocks.append(block)
        
        return blocks
    
    def _extract_text(self, res: Any) -> str:
        """从 res 提取文本"""
        if isinstance(res, str):
            return res
        if isinstance(res, list):
            texts = []
            for item in res:
                if isinstance(item, dict) and 'text' in item:
                    texts.append(item['text'])
            return ' '.join(texts)
        if isinstance(res, dict) and 'text' in res:
            return res['text']
        return ''
    
    def _get_confidence_level(self, score: float) -> str:
        if score >= 0.95:
            return 'excellent'
        elif score >= 0.85:
            return 'good'
        elif score >= 0.70:
            return 'fair'
        else:
            return 'poor'
    
    def _get_confidence_description(self, score: float) -> str:
        level = self._get_confidence_level(score)
        descriptions = {
            'excellent': 'Excellent - Very high accuracy expected',
            'good': 'Good - High accuracy with minimal errors',
            'fair': 'Fair - Moderate accuracy, review recommended',
            'poor': 'Poor - Low accuracy, manual review required'
        }
        return descriptions.get(level, 'Unknown')


# 全局实例
_job_cache: Optional[JobCacheService] = None


def init_job_cache(temp_folder: Path) -> JobCacheService:
    """初始化任务缓存服务"""
    global _job_cache
    _job_cache = JobCacheService(temp_folder)
    return _job_cache


def get_job_cache() -> Optional[JobCacheService]:
    """获取任务缓存服务实例"""
    return _job_cache
