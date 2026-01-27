"""
LLM 调用日志记录器
记录每次 LLM 调用的详细信息，保存到 Job 相关的缓存目录
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# 默认临时目录 - 使用项目根目录的 temp 文件夹
# Path(__file__) = backend/services/llm_logger.py
# .parent.parent.parent = 项目根目录
TEMP_DIR = Path(__file__).parent.parent.parent / 'temp'


class LLMLogger:
    """LLM 调用日志记录器"""
    
    def __init__(self, temp_dir: str = None):
        self.temp_dir = Path(temp_dir) if temp_dir else TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_log_path(self, job_id: str) -> Path:
        """获取日志文件路径"""
        return self.temp_dir / f"{job_id}_llm_log.json"
    
    def _load_log(self, job_id: str) -> Dict[str, Any]:
        """加载现有日志"""
        log_path = self._get_log_path(job_id)
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load LLM log for {job_id}: {e}")
        
        return {
            "job_id": job_id,
            "created_at": datetime.now().isoformat(),
            "calls": []
        }
    
    def _save_log(self, job_id: str, log_data: Dict[str, Any]):
        """保存日志"""
        log_path = self._get_log_path(job_id)
        try:
            log_data["updated_at"] = datetime.now().isoformat()
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"LLM log saved for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to save LLM log for {job_id}: {e}")

    def log_call(
        self,
        job_id: str,
        call_type: str,
        prompt: str,
        response: str,
        success: bool,
        processing_time: float,
        model: str = None,
        error: str = None,
        metadata: Dict[str, Any] = None
    ):
        """
        记录一次 LLM 调用
        
        Args:
            job_id: 任务ID
            call_type: 调用类型 (extract-info, document-qa, checkpoint)
            prompt: 发送给 LLM 的 prompt
            response: LLM 返回的响应
            success: 是否成功
            processing_time: 处理时间（秒）
            model: 使用的模型名称
            error: 错误信息（如果有）
            metadata: 额外元数据
        """
        log_data = self._load_log(job_id)
        
        call_record = {
            "id": len(log_data["calls"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": call_type,
            "model": model,
            "prompt": prompt,
            "prompt_length": len(prompt) if prompt else 0,
            "response": response,
            "response_length": len(response) if response else 0,
            "success": success,
            "processing_time": round(processing_time, 3),
            "error": error
        }
        
        if metadata:
            call_record["metadata"] = metadata
        
        log_data["calls"].append(call_record)
        
        # 更新统计信息
        log_data["total_calls"] = len(log_data["calls"])
        log_data["successful_calls"] = sum(1 for c in log_data["calls"] if c["success"])
        log_data["failed_calls"] = log_data["total_calls"] - log_data["successful_calls"]
        log_data["total_processing_time"] = round(
            sum(c["processing_time"] for c in log_data["calls"]), 3
        )
        
        self._save_log(job_id, log_data)
        
        logger.info(
            f"LLM call logged: job={job_id}, type={call_type}, "
            f"success={success}, time={processing_time:.2f}s"
        )
    
    def get_log(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取指定 Job 的 LLM 日志"""
        log_path = self._get_log_path(job_id)
        if not log_path.exists():
            return None
        return self._load_log(job_id)
    
    def get_log_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取日志摘要（不包含完整的 prompt/response）"""
        log_data = self.get_log(job_id)
        if not log_data:
            return None
        
        summary = {
            "job_id": log_data["job_id"],
            "created_at": log_data.get("created_at"),
            "updated_at": log_data.get("updated_at"),
            "total_calls": log_data.get("total_calls", 0),
            "successful_calls": log_data.get("successful_calls", 0),
            "failed_calls": log_data.get("failed_calls", 0),
            "total_processing_time": log_data.get("total_processing_time", 0),
            "calls": []
        }
        
        for call in log_data.get("calls", []):
            summary["calls"].append({
                "id": call["id"],
                "timestamp": call["timestamp"],
                "type": call["type"],
                "model": call.get("model"),
                "success": call["success"],
                "processing_time": call["processing_time"],
                "prompt_length": call.get("prompt_length", 0),
                "response_length": call.get("response_length", 0),
                "error": call.get("error")
            })
        
        return summary


# 全局单例
_llm_logger_instance = None


def get_llm_logger() -> LLMLogger:
    """获取 LLM 日志记录器单例"""
    global _llm_logger_instance
    if _llm_logger_instance is None:
        _llm_logger_instance = LLMLogger()
    return _llm_logger_instance
