# PDF to Editable Web Layout System

A complete system that converts scanned PDF documents into structured, editable web content using OCR and Editor.js. The system provides an end-to-end workflow from file upload through OCR processing to interactive web-based editing.

## Features

- Upload PDF, JPG, or PNG files (up to 10MB)
- **Full support for Chinese filenames and content**
- OCR processing with layout analysis using PaddleOCR PP-Structure
- Convert to Editor.js compatible format
- Interactive web-based editing interface
- Preserve document structure (headings, paragraphs, tables)
- Real-time processing status updates
- Confidence reporting for conversion quality
- Multi-page PDF support (processes first page)
- IPv4/IPv6 compatible networking

## Architecture

- **Backend**: Python Flask API with OCR processing pipeline
- **Frontend**: JavaScript with Editor.js for content editing
- **OCR Engine**: PaddleOCR PP-Structure for layout analysis

### End-to-End Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │───▶│  Validate   │───▶│    OCR      │───▶│  Normalize  │
│   File      │    │   File      │    │  Process    │    │   Data      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Edit      │◀───│   Render    │◀───│  Validate   │◀───│  Convert to │
│  Content    │    │  Editor.js  │    │   Schema    │    │  Editor.js  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Project Structure

```
├── backend/                 # Python backend
│   ├── api/                # REST API endpoints
│   ├── models/             # Data models
│   ├── services/           # Business logic services
│   │   ├── ocr_service.py      # PaddleOCR integration
│   │   ├── data_normalizer.py  # OCR to Editor.js conversion
│   │   ├── document_processor.py # Main processing pipeline
│   │   └── status_tracker.py   # Real-time status updates
│   ├── tests/              # Backend tests
│   ├── app.py              # Application entry point
│   ├── config.py           # Configuration settings
│   └── requirements.txt    # Python dependencies
├── frontend/               # JavaScript frontend
│   ├── src/                # Source code
│   │   ├── services/       # Frontend services
│   │   │   ├── APIClient.js        # Backend API communication
│   │   │   ├── DocumentProcessor.js # File upload handling
│   │   │   ├── EditorManager.js    # Editor.js integration
│   │   │   ├── StatusPoller.js     # Real-time status polling
│   │   │   └── UIManager.js        # UI state management
│   │   ├── __tests__/      # Frontend tests
│   │   ├── index.html      # Main HTML file
│   │   └── index.js        # Application entry point
│   ├── package.json        # Node.js dependencies
│   └── vite.config.js      # Build configuration
├── run_dev.sh              # Development startup script
└── README.md               # This file
```

## Quick Start

### Prerequisites

**Important**: Install PaddleOCR before running the system:

**macOS/Linux**:
```bash
pip3 install paddleocr paddlepaddle
```

**Windows**:
```cmd
pip install paddleocr paddlepaddle
```

This will download approximately 200-300MB and may take 10-20 minutes. The first run will download additional model files (100-200MB).

### Using the Development Script

#### Option 1: Cross-Platform Python Script (Recommended)

Works on Windows, macOS, and Linux:

```bash
python run_dev.py
```

#### Option 2: Platform-Specific Scripts

**macOS/Linux**:
```bash
chmod +x run_dev.sh
./run_dev.sh
```

**Windows**:
```cmd
run_dev.bat
```

Or double-click `run_dev.bat` in File Explorer.

These scripts will:
1. Create a Python virtual environment
2. Install all dependencies
3. Start the backend on port 5000
4. Start the frontend on port 3000

### Manual Setup

#### Backend Setup

1. Create virtual environment:

**macOS/Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**:
```cmd
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies:

**macOS/Linux**:
```bash
pip install -r backend/requirements.txt
```

**Windows**:
```cmd
pip install -r backend\requirements.txt
```

3. Install PaddleOCR (required for OCR processing):

**macOS/Linux**:
```bash
pip install paddleocr paddlepaddle
```

**Windows**:
```cmd
pip install paddleocr paddlepaddle
```

4. Run backend server:

**All platforms**:
```bash
python3 start_backend.py  # macOS/Linux
python start_backend.py   # Windows
```

The backend will be available at `http://localhost:5000` or `http://127.0.0.1:5000`

#### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Run development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000` or `http://127.0.0.1:3000`

**Note**: If you encounter connection issues, use `http://127.0.0.1:3000` instead of `localhost` due to IPv4/IPv6 compatibility.

## Usage

1. Open `http://127.0.0.1:3000` in your browser
2. Drag and drop a PDF, JPG, or PNG file (or click to select)
   - **Chinese filenames are fully supported** (e.g., "上海理工大学 2026 硕士初试参考书目.pdf")
3. Wait for OCR processing (status updates shown in real-time)
4. Edit the converted content in the Editor.js interface
5. Use Ctrl/Cmd+S to save your changes

## Testing

### Backend Tests
```bash
python3 -m pytest backend/tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

## API Endpoints

- `GET /api/health` - Health check
- `POST /api/convert` - Upload file for conversion
- `GET /api/convert/{job_id}/status` - Check conversion status with progress
- `GET /api/convert/{job_id}/result` - Get conversion result with confidence report
- `GET /api/convert/{job_id}/history` - Get status update history

## Configuration

Environment variables:
- `OCR_USE_GPU` - Enable GPU acceleration (default: false)
- `OCR_LANG` - OCR language (default: ch for Chinese/English)
- `MEMORY_LIMIT_MB` - Memory limit for OCR processing (default: 1024)
- `UPLOAD_FOLDER` - Path for uploaded files
- `TEMP_FOLDER` - Path for temporary files

## Requirements

- Python 3.8+
- Node.js 16+
- 10MB maximum file size
- Supported formats: PDF, JPG, PNG

## System Requirements

- **Target OS**: MacOS 13+, Windows 11, or Linux
- **CPU**: Intel series (CPU-only processing)
- **Memory**: Minimum 4GB RAM for OCR processing
- **Storage**: 1GB free space for temporary files
- **Python**: 3.8 or higher
- **Node.js**: 16 or higher

## Platform-Specific Guides

- **Windows Users**: See [WINDOWS_SETUP_GUIDE.md](WINDOWS_SETUP_GUIDE.md) for detailed Windows 11 setup instructions
- **macOS/Linux Users**: Follow the Quick Start guide above

## License

This project is part of the PDF to Editable Web Layout specification.