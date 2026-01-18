"""
Unit tests for API endpoints
"""
import pytest
import json
import io
from werkzeug.datastructures import FileStorage

class TestAPIEndpoints:
    """Test API endpoint functionality"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'pdf-to-editable-web'

    def test_convert_endpoint_post(self, client):
        """Test convert endpoint rejects requests without files"""
        response = client.post('/api/convert')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'guidance' in data
        assert 'validated' in data['error']

    def test_convert_status_endpoint(self, client):
        """Test conversion status endpoint"""
        job_id = "test-job-id"
        response = client.get(f'/api/convert/{job_id}/status')
        
        # Job not found returns 404
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['job_id'] == job_id
        assert 'error' in data
        assert data['status'] == 'unknown'

    def test_convert_result_endpoint(self, client):
        """Test conversion result endpoint"""
        job_id = "test-job-id"
        response = client.get(f'/api/convert/{job_id}/result')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['job_id'] == job_id
        assert 'status' in data
        assert 'result' in data
        assert 'blocks' in data['result']

    def test_convert_endpoint_with_invalid_file_type(self, client):
        """Test convert endpoint rejects invalid file types"""
        # Create a fake text file
        data = {
            'file': (io.BytesIO(b'test content'), 'test.txt')
        }
        
        response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'supported' in data['error'].lower()

    def test_convert_endpoint_with_oversized_file(self, client):
        """Test convert endpoint rejects oversized files"""
        # Create a fake large file (11MB) - Flask will reject this before our validation
        large_content = b'x' * (11 * 1024 * 1024)
        data = {
            'file': (io.BytesIO(large_content), 'test.pdf')
        }
        
        response = client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        # Flask rejects the request with 413 before it reaches our validation
        # Our error handler catches it and returns 500 with system error message
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert 'system' in data['category']