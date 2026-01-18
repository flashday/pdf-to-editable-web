"""
Tests for real-time status updates and timeout handling
"""
import pytest
import time
import threading
from backend.services.status_tracker import StatusTracker, ProcessingStage


class TestStatusUpdates:
    """Test status update functionality"""
    
    def test_create_job_and_track_status(self):
        """Test creating a job and tracking its status"""
        tracker = StatusTracker()
        
        # Create a job
        job_id = "test-job-123"
        tracker.create_job(job_id, {'filename': 'test.pdf'})
        
        # Get initial status
        status = tracker.get_job_status(job_id)
        assert status is not None
        assert status['job_id'] == job_id
        assert status['status'] == ProcessingStage.UPLOADING
        assert status['progress'] == 0.0
        
        # Update status
        tracker.update_status(
            job_id,
            ProcessingStage.OCR_PROCESSING,
            0.5,
            'Processing OCR'
        )
        
        # Get updated status
        status = tracker.get_job_status(job_id)
        assert status['status'] == ProcessingStage.OCR_PROCESSING
        assert status['progress'] > 0.0
        assert status['message'] == 'Processing OCR'
    
    def test_progress_calculation(self):
        """Test overall progress calculation across stages"""
        tracker = StatusTracker()
        job_id = "test-job-456"
        
        tracker.create_job(job_id)
        
        # Progress through stages
        tracker.update_status(job_id, ProcessingStage.UPLOADING, 1.0, 'Upload complete')
        progress1 = tracker.get_job_progress(job_id)
        
        tracker.update_status(job_id, ProcessingStage.VALIDATING, 1.0, 'Validation complete')
        progress2 = tracker.get_job_progress(job_id)
        
        tracker.update_status(job_id, ProcessingStage.OCR_PROCESSING, 0.5, 'OCR in progress')
        progress3 = tracker.get_job_progress(job_id)
        
        # Progress should increase
        assert progress2['progress'] > progress1['progress']
        assert progress3['progress'] > progress2['progress']
    
    def test_job_completion(self):
        """Test marking job as completed"""
        tracker = StatusTracker()
        job_id = "test-job-789"
        
        tracker.create_job(job_id)
        tracker.mark_completed(job_id, {'blocks': []})
        
        status = tracker.get_job_status(job_id)
        assert status['completed'] is True
        assert status['progress'] == 1.0
        assert status['status'] == ProcessingStage.COMPLETED
    
    def test_job_failure(self):
        """Test marking job as failed"""
        tracker = StatusTracker()
        job_id = "test-job-fail"
        
        tracker.create_job(job_id)
        tracker.mark_failed(job_id, 'OCR processing failed')
        
        status = tracker.get_job_status(job_id)
        assert status['failed'] is True
        assert status['error'] == 'OCR processing failed'
        assert status['status'] == ProcessingStage.FAILED
    
    def test_status_history(self):
        """Test status update history tracking"""
        tracker = StatusTracker()
        job_id = "test-job-history"
        
        tracker.create_job(job_id)
        tracker.update_status(job_id, ProcessingStage.VALIDATING, 0.5, 'Validating')
        tracker.update_status(job_id, ProcessingStage.OCR_PROCESSING, 0.3, 'OCR started')
        
        history = tracker.get_job_history(job_id)
        
        # Should have at least 3 entries (create + 2 updates)
        assert len(history) >= 3
        assert history[0]['stage'] == ProcessingStage.UPLOADING.value
        assert history[-1]['stage'] == ProcessingStage.OCR_PROCESSING.value
    
    def test_timeout_monitoring(self):
        """Test timeout monitoring for long-running jobs"""
        tracker = StatusTracker()
        
        # Set a very short timeout for testing
        tracker.set_job_timeout(1)  # 1 second timeout
        
        job_id = "test-job-timeout"
        tracker.create_job(job_id)
        
        # Wait for timeout to trigger
        time.sleep(2)
        
        # Manually trigger timeout check
        tracker._check_job_timeouts()
        
        # Job should be marked as failed
        status = tracker.get_job_status(job_id)
        assert status['failed'] is True
        assert 'timeout' in status['error'].lower()
    
    def test_get_active_jobs(self):
        """Test getting list of active jobs"""
        tracker = StatusTracker()
        
        # Create multiple jobs
        tracker.create_job("job-1")
        tracker.create_job("job-2")
        tracker.create_job("job-3")
        
        # Complete one job
        tracker.mark_completed("job-1")
        
        # Fail one job
        tracker.mark_failed("job-2", "Test failure")
        
        # Get active jobs
        active_jobs = tracker.get_active_jobs()
        
        # Only job-3 should be active
        assert len(active_jobs) == 1
        assert "job-3" in active_jobs
    
    def test_job_count(self):
        """Test getting job counts by status"""
        tracker = StatusTracker()
        
        # Create jobs with different statuses
        tracker.create_job("job-1")
        tracker.create_job("job-2")
        tracker.create_job("job-3")
        
        tracker.mark_completed("job-1")
        tracker.mark_failed("job-2", "Test failure")
        
        counts = tracker.get_job_count()
        
        assert counts['total'] == 3
        assert counts['completed'] == 1
        assert counts['failed'] == 1
        assert counts['active'] == 1
    
    def test_cleanup_job(self):
        """Test cleaning up job data"""
        tracker = StatusTracker()
        job_id = "test-job-cleanup"
        
        tracker.create_job(job_id)
        
        # Verify job exists
        status = tracker.get_job_status(job_id)
        assert status is not None
        
        # Clean up job
        tracker.cleanup_job(job_id)
        
        # Verify job is removed
        status = tracker.get_job_status(job_id)
        assert status is None
    
    def test_concurrent_status_updates(self):
        """Test thread-safe concurrent status updates"""
        tracker = StatusTracker()
        job_id = "test-job-concurrent"
        
        tracker.create_job(job_id)
        
        def update_status():
            for i in range(10):
                tracker.update_status(
                    job_id,
                    ProcessingStage.OCR_PROCESSING,
                    i / 10.0,
                    f'Progress {i}'
                )
        
        # Create multiple threads updating status
        threads = [threading.Thread(target=update_status) for _ in range(3)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Job should still be valid
        status = tracker.get_job_status(job_id)
        assert status is not None
        assert status['job_id'] == job_id


class TestStatusEndpoints:
    """Test status API endpoints"""
    
    def test_get_status_endpoint(self, client):
        """Test getting job status via API"""
        from backend.services.status_tracker import status_tracker
        
        # Create a job
        job_id = "test-api-job"
        status_tracker.create_job(job_id, {'filename': 'test.pdf'})
        status_tracker.update_status(
            job_id,
            ProcessingStage.OCR_PROCESSING,
            0.5,
            'Processing'
        )
        
        # Get status via API
        response = client.get(f'/api/convert/{job_id}/status')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['job_id'] == job_id
        assert data['status'] == ProcessingStage.OCR_PROCESSING.value
        assert 'progress' in data
        assert 'message' in data
        
        # Clean up
        status_tracker.cleanup_job(job_id)
    
    def test_get_status_not_found(self, client):
        """Test getting status for non-existent job"""
        response = client.get('/api/convert/non-existent-job/status')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_get_history_endpoint(self, client):
        """Test getting job history via API"""
        from backend.services.status_tracker import status_tracker
        
        # Create a job with history
        job_id = "test-history-job"
        status_tracker.create_job(job_id)
        status_tracker.update_status(job_id, ProcessingStage.VALIDATING, 0.5, 'Validating')
        status_tracker.update_status(job_id, ProcessingStage.OCR_PROCESSING, 0.3, 'OCR')
        
        # Get history via API
        response = client.get(f'/api/convert/{job_id}/history')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['job_id'] == job_id
        assert 'history' in data
        assert len(data['history']) >= 3
        
        # Clean up
        status_tracker.cleanup_job(job_id)
    
    def test_get_history_with_limit(self, client):
        """Test getting limited job history"""
        from backend.services.status_tracker import status_tracker
        
        # Create a job with multiple updates
        job_id = "test-history-limit"
        status_tracker.create_job(job_id)
        
        for i in range(10):
            status_tracker.update_status(
                job_id,
                ProcessingStage.OCR_PROCESSING,
                i / 10.0,
                f'Update {i}'
            )
        
        # Get limited history
        response = client.get(f'/api/convert/{job_id}/history?limit=5')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['history']) == 5
        
        # Clean up
        status_tracker.cleanup_job(job_id)
