"""
Core data models for document processing pipeline
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class ProcessingStatus(Enum):
    """Document processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class RegionType(Enum):
    """OCR region classification types"""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    LIST = "list"

@dataclass
class BoundingBox:
    """Bounding box coordinates for regions"""
    x: float
    y: float
    width: float
    height: float

@dataclass
class Region:
    """OCR detected region with classification"""
    coordinates: BoundingBox
    classification: RegionType
    confidence: float
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TableStructure:
    """Table structure information"""
    rows: int
    columns: int
    cells: List[List[str]]
    coordinates: BoundingBox
    has_headers: bool = False

@dataclass
class LayoutResult:
    """OCR layout analysis result"""
    regions: List[Region]
    tables: List[TableStructure]
    confidence_score: float
    processing_time: float

@dataclass
class ConfidenceMetrics:
    """Confidence metrics for processing results"""
    overall_confidence: float
    text_confidence: float
    layout_confidence: float
    table_confidence: float

@dataclass
class EditorJSBlock:
    """Editor.js block structure"""
    id: str
    type: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class EditorJSData:
    """Complete Editor.js data structure"""
    time: int
    blocks: List[EditorJSBlock]
    version: str = "2.28.2"

@dataclass
class Document:
    """Main document model for processing pipeline"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str = ""
    file_type: str = ""
    file_size: int = 0
    upload_timestamp: datetime = field(default_factory=datetime.now)
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    conversion_result: Optional[EditorJSData] = None
    error_message: Optional[str] = None
    confidence_metrics: Optional[ConfidenceMetrics] = None
    processing_duration: Optional[float] = None