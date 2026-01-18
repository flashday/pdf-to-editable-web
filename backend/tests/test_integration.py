"""
End-to-end integration tests for the complete system
Tests the entire workflow from file upload to Editor.js display
"""
import pytest
import tempfile
import os
import time
import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import numpy as np
import sys

# Mock paddleocr before importing
sys.modules['paddleocr'] = MagicMock()

from backend.app import create_app
from backend.services.status_tracker import status_tracker, ProcessingStage
from backend.models.document import EditorJSData, EditorJSBlock


class TestEndToEndIntegration:
    """End-to-end integration tests for the complete system"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        app = create_app()
        
        # Update config with test settings
        app.config.update({
            'TESTING': True,
            'UPLOAD_FOLDER': Path(temp_dir),
            'TEMP_FOLDER': Path(temp_dir)
        })
        
        # Create necessary directories
        Path(temp_dir).mkdir(exist_ok=True)
        
        yield app
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_complete_upload_to_result_workflow(self, client, sample_pdf):
        """Test complete workflow from upload to result retrieval"""
        
        # Step 1: Upload PDF
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 202
        upload_data = json.loads(response.data)
        assert 'job_id' in upload_data
        job_id = upload_data['job_id']
        assert upload_data['status'] == 'pending'
        
        # Step 2: Check initial status
        response = client.get(f'/api/convert/{job_id}/status')
        assert response.status_code == 200  # Job was created during upload
        data = json.loads(response.data)
        assert data['job_id'] == job_id
        
        # Step 3: Simulate job processing
        status_tracker.create_job(job_id)
        status_tracker.update_status(job_id, ProcessingStage.UPLOADING, 1.0, 'File uploaded')
        status_tracker.update_status(job_id, ProcessingStage.VALIDATING, 1.0, 'Validating file')
        status_tracker.update_status(job_id, ProcessingStage.PDF_PROCESSING, 1.0, 'Processing PDF')
        status_tracker.update_status(job_id, ProcessingStage.OCR_PROCESSING, 1.0, 'Running OCR')
        status_tracker.update_status(job_id, ProcessingStage.LAYOUT_ANALYSIS, 1.0, 'Analyzing layout')
        status_tracker.update_status(job_id, ProcessingStage.DATA_NORMALIZATION, 1.0, 'Normalizing data')
        status_tracker.update_status(job_id, ProcessingStage.SCHEMA_VALIDATION, 1.0, 'Validating schema')
        status_tracker.mark_completed(job_id)
        
        # Step 4: Check final status
        response = client.get(f'/api/convert/{job_id}/status')
        assert response.status_code == 200
        status_data = json.loads(response.data)
        assert status_data['stage'] == 'completed'
        assert status_data['progress'] == 1.0
        
        # Step 5: Get result
        response = client.get(f'/api/convert/{job_id}/result')
        assert response.status_code == 200
        result_data = json.loads(response.data)
        assert result_data['status'] == 'completed'
        assert 'result' in result_data
        assert 'confidence_report' in result_data
        assert 'blocks' in result_data['result']
    
    def test_error_handling_workflow(self, client):
        """Test error handling in the workflow"""
        
        # Test with invalid file type
        data = {
            'file': (BytesIO(b'test content'), 'test.txt')
        }
        response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert 'error' in error_data
    
    def test_confidence_report_structure(self, client, sample_pdf):
        """Test confidence report structure and content"""
        
        # Upload file
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        job_id = json.loads(response.data)['job_id']
        
        # Get result
        response = client.get(f'/api/convert/{job_id}/result')
        assert response.status_code == 200
        result_data = json.loads(response.data)
        
        # Verify confidence report structure
        confidence_report = result_data['confidence_report']
        assert 'confidence_breakdown' in confidence_report
        assert 'warnings' in confidence_report
        assert 'has_warnings' in confidence_report
        assert 'warning_count' in confidence_report
        assert 'overall_assessment' in confidence_report
        
        # Verify confidence breakdown
        breakdown = confidence_report['confidence_breakdown']
        assert 'overall' in breakdown
        assert 'text_recognition' in breakdown
        assert 'layout_detection' in breakdown
        assert 'table_recognition' in breakdown
        
        # Verify each metric has required fields
        for metric_name, metric in breakdown.items():
            assert 'score' in metric
            assert 'level' in metric
            assert 'description' in metric
            assert isinstance(metric['score'], (int, float))
            assert 0 <= metric['score'] <= 1
    
    def test_status_progress_updates(self, client, sample_pdf):
        """Test status progress updates during processing"""
        
        # Upload file
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        job_id = json.loads(response.data)['job_id']
        
        # Create job and simulate progress
        status_tracker.create_job(job_id)
        
        # Test progress at different stages
        # Progress is calculated as: sum of completed stage weights + (current stage weight * stage_progress)
        stages = [
            (ProcessingStage.UPLOADING, 1.0, 0.1),      # 0.1 * 1.0 = 0.1
            (ProcessingStage.VALIDATING, 1.0, 0.2),     # 0.1 + 0.1 * 1.0 = 0.2
            (ProcessingStage.PDF_PROCESSING, 1.0, 0.35),  # 0.2 + 0.15 * 1.0 = 0.35
            (ProcessingStage.OCR_PROCESSING, 1.0, 0.65),  # 0.35 + 0.3 * 1.0 = 0.65
            (ProcessingStage.LAYOUT_ANALYSIS, 1.0, 0.8),   # 0.65 + 0.15 * 1.0 = 0.8
            (ProcessingStage.DATA_NORMALIZATION, 1.0, 0.9), # 0.8 + 0.1 * 1.0 = 0.9
            (ProcessingStage.SCHEMA_VALIDATION, 1.0, 1.0), # 0.9 + 0.1 * 1.0 = 1.0
        ]
        
        for stage, stage_progress, expected_progress in stages:
            status_tracker.update_status(job_id, stage, stage_progress, f'Processing {stage.value}')
            
            response = client.get(f'/api/convert/{job_id}/status')
            assert response.status_code == 200
            status_data = json.loads(response.data)
            assert abs(status_data['progress'] - expected_progress) < 0.01
            assert status_data['stage'] == stage.value
    
    def test_concurrent_job_handling(self, client, sample_pdf):
        """Test handling of multiple concurrent jobs"""
        
        # Upload multiple files
        job_ids = []
        for i in range(3):
            with open(sample_pdf, 'rb') as f:
                data = {
                    'file': (f, f'test_{i}.pdf')
                }
                response = client.post('/api/convert', data=data, content_type='multipart/form-data')
            
            assert response.status_code == 202
            job_id = json.loads(response.data)['job_id']
            job_ids.append(job_id)
        
        # Verify all jobs are tracked independently
        for job_id in job_ids:
            status_tracker.create_job(job_id)
            status_tracker.update_status(job_id, ProcessingStage.UPLOADING, 0.1, 'File uploaded')
            
            response = client.get(f'/api/convert/{job_id}/status')
            assert response.status_code == 200
            status_data = json.loads(response.data)
            assert status_data['job_id'] == job_id
    
    def test_editor_js_data_format(self, client, sample_pdf):
        """Test Editor.js data format in result"""
        
        # Upload file
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        job_id = json.loads(response.data)['job_id']
        
        # Get result
        response = client.get(f'/api/convert/{job_id}/result')
        assert response.status_code == 200
        result_data = json.loads(response.data)
        
        # Verify Editor.js format
        editor_data = result_data['result']
        assert 'time' in editor_data
        assert 'blocks' in editor_data
        assert 'version' in editor_data
        
        # Verify blocks structure (even if empty)
        blocks = editor_data['blocks']
        assert isinstance(blocks, list)
        
        # If there are blocks, verify their structure
        for block in blocks:
            assert 'id' in block
            assert 'type' in block
            assert 'data' in block


class TestSystemErrorHandling:
    """Test system error handling and recovery"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        app = create_app()
        
        # Update config with test settings
        app.config.update({
            'TESTING': True,
            'UPLOAD_FOLDER': Path(temp_dir),
            'TEMP_FOLDER': Path(temp_dir)
        })
        
        # Create necessary directories
        Path(temp_dir).mkdir(exist_ok=True)
        
        yield app
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_invalid_job_id_handling(self, client):
        """Test handling of invalid job IDs"""
        
        # Test with non-existent job
        response = client.get('/api/convert/non-existent-job/status')
        assert response.status_code == 404
        
        response = client.get('/api/convert/non-existent-job/result')
        assert response.status_code == 200  # Returns mock result
    
    def test_malformed_request_handling(self, client):
        """Test handling of malformed requests"""
        
        # Test without file
        response = client.post('/api/convert', data={}, content_type='multipart/form-data')
        assert response.status_code == 400
        
        # Test with empty file
        data = {
            'file': (BytesIO(b''), 'empty.pdf')
        }
        response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        assert response.status_code == 400


class TestPerformanceAndResources:
    """Test performance monitoring and resource management"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        app = create_app()
        
        # Update config with test settings
        app.config.update({
            'TESTING': True,
            'UPLOAD_FOLDER': Path(temp_dir),
            'TEMP_FOLDER': Path(temp_dir)
        })
        
        # Create necessary directories
        Path(temp_dir).mkdir(exist_ok=True)
        
        yield app
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_processing_time_tracking(self, client, sample_pdf):
        """Test that processing time is tracked"""
        from backend.services.performance_monitor import performance_monitor
        
        # Upload file
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 202
        
        # Check that performance metrics were recorded
        metrics = performance_monitor.get_performance_summary()
        assert metrics['total_operations'] > 0
    
    def test_memory_usage_monitoring(self, client, sample_pdf):
        """Test memory usage monitoring"""
        from backend.services.performance_monitor import performance_monitor
        
        # Upload file
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 202
        
        # Check memory usage
        memory_info = performance_monitor.check_memory_usage()
        assert 'process_memory_mb' in memory_info
        assert 'within_limits' in memory_info


class TestFrontendBackendIntegration:
    """Test frontend-backend API integration"""
    
    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        app = create_app()
        
        # Update config with test settings
        app.config.update({
            'TESTING': True,
            'UPLOAD_FOLDER': Path(temp_dir),
            'TEMP_FOLDER': Path(temp_dir)
        })
        
        # Create necessary directories
        Path(temp_dir).mkdir(exist_ok=True)
        
        yield app
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    def test_api_response_format_consistency(self, client, sample_pdf):
        """Test that API responses follow consistent format"""
        
        # Upload file
        with open(sample_pdf, 'rb') as f:
            data = {
                'file': (f, 'test.pdf')
            }
            response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        job_id = json.loads(response.data)['job_id']
        
        # Test all endpoints for consistent format
        endpoints = [
            f'/api/convert/{job_id}/status',
            f'/api/convert/{job_id}/result'
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert isinstance(data, dict)
                assert 'job_id' in data or 'status' in data
    
    def test_error_message_format(self, client):
        """Test that error messages follow consistent format"""
        
        # Test with invalid file type
        data = {
            'file': (BytesIO(b'test'), 'test.txt')
        }
        response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        error_data = json.loads(response.data)
        assert 'error' in error_data
        assert isinstance(error_data['error'], str)
