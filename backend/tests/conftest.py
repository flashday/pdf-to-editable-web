"""
Pytest configuration and fixtures
"""
import pytest
import tempfile
import os
from pathlib import Path
from io import BytesIO
from backend.app import create_app
from backend.config import Config

class TestConfig(Config):
    """Test configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = Path(tempfile.mkdtemp())
    TEMP_FOLDER = Path(tempfile.mkdtemp())

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app(TestConfig)
    
    with app.app_context():
        yield app
    
    # Cleanup
    import shutil
    shutil.rmtree(TestConfig.UPLOAD_FOLDER, ignore_errors=True)
    shutil.rmtree(TestConfig.TEMP_FOLDER, ignore_errors=True)

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing"""
    from PyPDF2 import PdfWriter
    
    # Create a simple PDF with content
    output = PdfWriter()
    output.add_blank_page(width=612, height=792)
    
    pdf_bytes = BytesIO()
    output.write(pdf_bytes)
    
    # Get the PDF content
    pdf_content = pdf_bytes.getvalue()
    
    # Verify the PDF has content
    assert len(pdf_content) > 0, "PDF should have content"
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(pdf_content)
        tmp.flush()
        # Verify file was written
        assert os.path.getsize(tmp.name) > 0, "PDF file should have size > 0"
        yield tmp.name
        os.unlink(tmp.name)

@pytest.fixture
def sample_pdf_path():
    """Create a sample PDF file for testing"""
    # This would be implemented with actual PDF creation in later tasks
    return None

@pytest.fixture
def sample_image_path():
    """Create a sample image file for testing"""
    # This would be implemented with actual image creation in later tasks
    return None