"""
Processing status tracking and update system
Implements real-time status updates and progress tracking
"""
import logging
import time
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)

class ProcessingStage(Enum):
    """Processing stage enumeration"""
    UPLOADING = "uploading"
    VALIDATING = "validating"
    PDF_PROCESSING = "pdf_processing"
    OCR_PROCESSING = "ocr_processing"
    LAYOUT_ANALYSIS = "layout_analysis"
    DATA_NORMALIZATION = "data_normalization"
    SCHEMA_VALIDATION = "schema_validation"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class StatusUpdate:
    """Status update for a processing job"""
    job_id: str
    stage: ProcessingStage
    progress: float  # 0.0 to 1.0
    message: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

class StatusTracker:
    """
    Track and manage processing status for jobs
    """
    
    def __init__(self):
        """Initialize status tracker"""
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.status_history: Dict[str, deque] = {}
        self.max_history_size = 100
        self.lock = threading.Lock()
        
        # Timeout configuration
        self.job_timeout = 300  # 5 minutes timeout for jobs
        self.timeout_check_interval = 30  # Check for timeouts every 30 seconds
        self.timeout_monitor_thread = None
        self.monitoring_active = False
        
        # Stage progress weights (for calculating overall progress)
        self.stage_weights = {
            ProcessingStage.UPLOADING: 0.1,
            ProcessingStage.VALIDATING: 0.1,
            ProcessingStage.PDF_PROCESSING: 0.15,
            ProcessingStage.OCR_PROCESSING: 0.3,
            ProcessingStage.LAYOUT_ANALYSIS: 0.15,
            ProcessingStage.DATA_NORMALIZATION: 0.1,
            ProcessingStage.SCHEMA_VALIDATION: 0.1
        }
        
        # Stage order for progress calculation
        self.stage_order = [
            ProcessingStage.UPLOADING,
            ProcessingStage.VALIDATING,
            ProcessingStage.PDF_PROCESSING,
            ProcessingStage.OCR_PROCESSING,
            ProcessingStage.LAYOUT_ANALYSIS,
            ProcessingStage.DATA_NORMALIZATION,
            ProcessingStage.SCHEMA_VALIDATION,
            ProcessingStage.COMPLETED
        ]
        
        # Start timeout monitoring
        self.start_timeout_monitoring()
    
    def create_job(self, job_id: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Create a new job tracking entry
        
        Args:
            job_id: Unique job identifier
            metadata: Optional metadata about the job
        """
        with self.lock:
            self.jobs[job_id] = {
                'job_id': job_id,
                'status': ProcessingStage.UPLOADING,
                'progress': 0.0,
                'message': 'Job created',
                'created_at': time.time(),
                'updated_at': time.time(),
                'metadata': metadata or {},
                'error': None,
                'completed': False,
                'failed': False
            }
            
            # Initialize status history
            self.status_history[job_id] = deque(maxlen=self.max_history_size)
            
            # Add initial status update
            self._add_status_update(job_id, ProcessingStage.UPLOADING, 0.0, 'Job created')
        
        logger.info(f"Created job tracking entry: {job_id}")
    
    def update_status(self, job_id: str, stage: ProcessingStage, 
                   progress: float, message: str, error: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None):
        """
        Update job status
        
        Args:
            job_id: Job identifier
            stage: Current processing stage
            progress: Progress within stage (0.0 to 1.0)
            message: Status message
            error: Optional error message
            metadata: Optional metadata about the update
        """
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found for status update")
                return
            
            job = self.jobs[job_id]
            
            # Update job information
            job['status'] = stage
            job['message'] = message
            job['updated_at'] = time.time()
            
            if error:
                job['error'] = error
                job['failed'] = True
            elif stage == ProcessingStage.COMPLETED:
                job['completed'] = True
                job['progress'] = 1.0
            elif stage == ProcessingStage.FAILED:
                job['failed'] = True
            else:
                # Calculate overall progress
                job['progress'] = self._calculate_overall_progress(stage, progress)
            
            # Update metadata if provided
            if metadata:
                job['metadata'].update(metadata)
            
            # Add to status history
            self._add_status_update(job_id, stage, progress, message, error, metadata)
        
        logger.debug(
            f"Updated job {job_id}: {stage.value} "
            f"(progress: {job['progress']:.2%}, message: {message})"
        )
    
    def _calculate_overall_progress(self, current_stage: ProcessingStage, 
                                 stage_progress: float) -> float:
        """
        Calculate overall progress based on current stage and progress within stage
        
        Args:
            current_stage: Current processing stage
            stage_progress: Progress within current stage (0.0 to 1.0)
            
        Returns:
            Overall progress (0.0 to 1.0)
        """
        # Find current stage index
        try:
            stage_index = self.stage_order.index(current_stage)
        except ValueError:
            stage_index = 0
        
        # Calculate progress from completed stages
        completed_progress = 0.0
        for i in range(stage_index):
            stage = self.stage_order[i]
            completed_progress += self.stage_weights.get(stage, 0.0)
        
        # Add progress from current stage
        current_stage_weight = self.stage_weights.get(current_stage, 0.0)
        total_progress = completed_progress + (current_stage_weight * stage_progress)
        
        # Ensure progress is within bounds
        return max(0.0, min(1.0, total_progress))
    
    def _add_status_update(self, job_id: str, stage: ProcessingStage, 
                        progress: float, message: str, error: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None):
        """
        Add status update to history
        
        Args:
            job_id: Job identifier
            stage: Processing stage
            progress: Progress within stage
            message: Status message
            error: Optional error message
            metadata: Optional metadata
        """
        status_update = StatusUpdate(
            job_id=job_id,
            stage=stage,
            progress=progress,
            message=message,
            timestamp=time.time(),
            metadata=metadata or {},
            error=error
        )
        
        self.status_history[job_id].append(status_update)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary or None if not found
        """
        with self.lock:
            if job_id not in self.jobs:
                return None
            
            job = self.jobs[job_id].copy()
            
            # Add formatted timestamp
            job['created_at_formatted'] = datetime.fromtimestamp(job['created_at']).isoformat()
            job['updated_at_formatted'] = datetime.fromtimestamp(job['updated_at']).isoformat()
            
            return job
    
    def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed progress information for a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Progress information dictionary or None if not found
        """
        with self.lock:
            if job_id not in self.jobs:
                return None
            
            job = self.jobs[job_id]
            
            return {
                'job_id': job_id,
                'stage': job['status'].value,
                'progress': job['progress'],
                'progress_percent': f"{job['progress'] * 100:.1f}%",
                'message': job['message'],
                'completed': job['completed'],
                'failed': job['failed'],
                'error': job['error'],
                'updated_at': job['updated_at'],
                'elapsed_time': time.time() - job['created_at']
            }
    
    def get_job_history(self, job_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get status update history for a job
        
        Args:
            job_id: Job identifier
            limit: Maximum number of history entries to return
            
        Returns:
            List of status updates
        """
        with self.lock:
            if job_id not in self.status_history:
                return []
            
            history = list(self.status_history[job_id])
            
            # Apply limit if specified
            if limit and limit < len(history):
                history = history[-limit:]
            
            # Convert to dictionaries
            return [
                {
                    'stage': update.stage.value,
                    'progress': update.progress,
                    'message': update.message,
                    'timestamp': update.timestamp,
                    'timestamp_formatted': datetime.fromtimestamp(update.timestamp).isoformat(),
                    'error': update.error,
                    'metadata': update.metadata
                }
                for update in history
            ]
    
    def mark_completed(self, job_id: str, result: Optional[Dict[str, Any]] = None):
        """
        Mark job as completed
        
        Args:
            job_id: Job identifier
            result: Optional result data
        """
        self.update_status(
            job_id,
            ProcessingStage.COMPLETED,
            1.0,
            'Processing completed successfully',
            metadata={'result': result} if result else None
        )
        
        logger.info(f"Job {job_id} marked as completed")
    
    def mark_failed(self, job_id: str, error: str):
        """
        Mark job as failed
        
        Args:
            job_id: Job identifier
            error: Error message
        """
        self.update_status(
            job_id,
            ProcessingStage.FAILED,
            0.0,
            f'Processing failed: {error}',
            error=error
        )
        
        logger.error(f"Job {job_id} marked as failed: {error}")
    
    def cleanup_job(self, job_id: str):
        """
        Clean up job tracking data
        
        Args:
            job_id: Job identifier
        """
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
            
            if job_id in self.status_history:
                del self.status_history[job_id]
        
        logger.info(f"Cleaned up job tracking data: {job_id}")
    
    def get_active_jobs(self) -> List[str]:
        """
        Get list of active (not completed/failed) jobs
        
        Returns:
            List of job IDs
        """
        with self.lock:
            return [
                job_id
                for job_id, job in self.jobs.items()
                if not job['completed'] and not job['failed']
            ]
    
    def get_job_count(self) -> Dict[str, int]:
        """
        Get count of jobs by status
        
        Returns:
            Dictionary with job counts
        """
        with self.lock:
            counts = {
                'total': len(self.jobs),
                'active': 0,
                'completed': 0,
                'failed': 0
            }
            
            for job in self.jobs.values():
                if job['completed']:
                    counts['completed'] += 1
                elif job['failed']:
                    counts['failed'] += 1
                else:
                    counts['active'] += 1
            
            return counts
    
    def start_timeout_monitoring(self):
        """Start background thread for timeout monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.timeout_monitor_thread = threading.Thread(
            target=self._timeout_monitor_loop,
            daemon=True
        )
        self.timeout_monitor_thread.start()
        logger.info("Started timeout monitoring thread")
    
    def stop_timeout_monitoring(self):
        """Stop timeout monitoring thread"""
        self.monitoring_active = False
        if self.timeout_monitor_thread:
            self.timeout_monitor_thread.join(timeout=5)
        logger.info("Stopped timeout monitoring thread")
    
    def _timeout_monitor_loop(self):
        """Background loop for checking job timeouts"""
        while self.monitoring_active:
            try:
                self._check_job_timeouts()
            except Exception as e:
                logger.error(f"Error in timeout monitor: {e}")
            
            # Sleep for check interval
            time.sleep(self.timeout_check_interval)
    
    def _check_job_timeouts(self):
        """Check for jobs that have exceeded timeout"""
        current_time = time.time()
        timed_out_jobs = []
        
        with self.lock:
            for job_id, job in self.jobs.items():
                # Skip completed or failed jobs
                if job['completed'] or job['failed']:
                    continue
                
                # Check if job has exceeded timeout
                elapsed_time = current_time - job['created_at']
                if elapsed_time > self.job_timeout:
                    timed_out_jobs.append(job_id)
        
        # Mark timed out jobs as failed (outside lock to avoid deadlock)
        for job_id in timed_out_jobs:
            elapsed_minutes = int(self.job_timeout / 60)
            self.mark_failed(
                job_id,
                f"Processing timeout: Job exceeded {elapsed_minutes} minute time limit"
            )
            logger.warning(f"Job {job_id} timed out after {elapsed_minutes} minutes")
    
    def set_job_timeout(self, timeout_seconds: int):
        """
        Set job timeout duration
        
        Args:
            timeout_seconds: Timeout in seconds
        """
        self.job_timeout = timeout_seconds
        logger.info(f"Job timeout set to {timeout_seconds} seconds")
    
    def get_job_timeout(self) -> int:
        """
        Get current job timeout setting
        
        Returns:
            Timeout in seconds
        """
        return self.job_timeout

# Global status tracker instance
status_tracker = StatusTracker()
