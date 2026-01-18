"""
Confidence-based warning system for OCR and processing results
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from backend.models.document import ConfidenceMetrics, LayoutResult, EditorJSData
from backend.services.error_handler import error_handler, ErrorCategory, ErrorSeverity

class ConfidenceLevel(Enum):
    """Confidence level classifications"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 75-89%
    FAIR = "fair"           # 60-74%
    POOR = "poor"           # 40-59%
    VERY_POOR = "very_poor" # 0-39%

class WarningType(Enum):
    """Types of confidence warnings"""
    LOW_OVERALL_CONFIDENCE = "low_overall_confidence"
    LOW_TEXT_CONFIDENCE = "low_text_confidence"
    LOW_LAYOUT_CONFIDENCE = "low_layout_confidence"
    LOW_TABLE_CONFIDENCE = "low_table_confidence"
    MIXED_CONFIDENCE = "mixed_confidence"
    PROCESSING_UNCERTAINTY = "processing_uncertainty"

@dataclass
class ConfidenceWarning:
    """Confidence warning data structure"""
    warning_type: WarningType
    confidence_level: ConfidenceLevel
    confidence_score: float
    message: str
    recommendation: str
    affected_areas: List[str]
    severity: str

class ConfidenceMonitor:
    """Monitor and generate warnings based on confidence scores"""
    
    # Confidence thresholds
    THRESHOLDS = {
        'excellent': 0.90,
        'good': 0.75,
        'fair': 0.60,
        'poor': 0.40,
        'very_poor': 0.0
    }
    
    # Warning thresholds
    WARNING_THRESHOLDS = {
        'overall_confidence': 0.70,
        'text_confidence': 0.75,
        'layout_confidence': 0.65,
        'table_confidence': 0.70,
        'mixed_threshold': 0.20  # Difference threshold for mixed confidence warning
    }
    
    def __init__(self):
        self.logger = error_handler.logger
    
    def classify_confidence_level(self, confidence_score: float) -> ConfidenceLevel:
        """
        Classify confidence score into appropriate level
        
        Args:
            confidence_score: Confidence score (0.0 to 1.0)
            
        Returns:
            ConfidenceLevel enum value
        """
        if confidence_score >= self.THRESHOLDS['excellent']:
            return ConfidenceLevel.EXCELLENT
        elif confidence_score >= self.THRESHOLDS['good']:
            return ConfidenceLevel.GOOD
        elif confidence_score >= self.THRESHOLDS['fair']:
            return ConfidenceLevel.FAIR
        elif confidence_score >= self.THRESHOLDS['poor']:
            return ConfidenceLevel.POOR
        else:
            return ConfidenceLevel.VERY_POOR
    
    def check_confidence_thresholds(self, metrics: ConfidenceMetrics) -> List[ConfidenceWarning]:
        """
        Check confidence metrics against thresholds and generate warnings
        
        Args:
            metrics: Confidence metrics from processing
            
        Returns:
            List of confidence warnings
        """
        warnings = []
        
        # Check overall confidence
        if metrics.overall_confidence < self.WARNING_THRESHOLDS['overall_confidence']:
            warning = self._create_overall_confidence_warning(metrics.overall_confidence)
            warnings.append(warning)
        
        # Check text confidence
        if metrics.text_confidence < self.WARNING_THRESHOLDS['text_confidence']:
            warning = self._create_text_confidence_warning(metrics.text_confidence)
            warnings.append(warning)
        
        # Check layout confidence
        if metrics.layout_confidence < self.WARNING_THRESHOLDS['layout_confidence']:
            warning = self._create_layout_confidence_warning(metrics.layout_confidence)
            warnings.append(warning)
        
        # Check table confidence
        if metrics.table_confidence < self.WARNING_THRESHOLDS['table_confidence']:
            warning = self._create_table_confidence_warning(metrics.table_confidence)
            warnings.append(warning)
        
        # Check for mixed confidence levels (high variance)
        confidence_scores = [
            metrics.overall_confidence,
            metrics.text_confidence,
            metrics.layout_confidence,
            metrics.table_confidence
        ]
        
        max_confidence = max(confidence_scores)
        min_confidence = min(confidence_scores)
        
        if (max_confidence - min_confidence) > self.WARNING_THRESHOLDS['mixed_threshold']:
            warning = self._create_mixed_confidence_warning(confidence_scores, metrics)
            warnings.append(warning)
        
        return warnings
    
    def _create_overall_confidence_warning(self, confidence_score: float) -> ConfidenceWarning:
        """Create warning for low overall confidence"""
        level = self.classify_confidence_level(confidence_score)
        
        if level == ConfidenceLevel.VERY_POOR:
            message = "The document conversion has very low confidence. Results may be significantly inaccurate."
            recommendation = "Consider uploading a higher quality scan or a different document format."
            severity = "high"
        elif level == ConfidenceLevel.POOR:
            message = "The document conversion has low confidence. Some content may be inaccurate."
            recommendation = "Please review the converted content carefully and make necessary corrections."
            severity = "medium"
        else:
            message = "The document conversion has moderate confidence. Minor inaccuracies may be present."
            recommendation = "Review the converted content for any errors, especially in complex areas."
            severity = "low"
        
        return ConfidenceWarning(
            warning_type=WarningType.LOW_OVERALL_CONFIDENCE,
            confidence_level=level,
            confidence_score=confidence_score,
            message=message,
            recommendation=recommendation,
            affected_areas=["entire_document"],
            severity=severity
        )
    
    def _create_text_confidence_warning(self, confidence_score: float) -> ConfidenceWarning:
        """Create warning for low text recognition confidence"""
        level = self.classify_confidence_level(confidence_score)
        
        if level == ConfidenceLevel.VERY_POOR:
            message = "Text recognition confidence is very low. Many words may be incorrectly recognized."
            recommendation = "Consider uploading a clearer scan with better text quality."
        elif level == ConfidenceLevel.POOR:
            message = "Text recognition confidence is low. Some words may be incorrectly recognized."
            recommendation = "Carefully review all text content for recognition errors."
        else:
            message = "Text recognition confidence is moderate. Minor text errors may be present."
            recommendation = "Review text content, especially in areas with small fonts or poor quality."
        
        return ConfidenceWarning(
            warning_type=WarningType.LOW_TEXT_CONFIDENCE,
            confidence_level=level,
            confidence_score=confidence_score,
            message=message,
            recommendation=recommendation,
            affected_areas=["text_content", "paragraphs", "headers"],
            severity="medium"
        )
    
    def _create_layout_confidence_warning(self, confidence_score: float) -> ConfidenceWarning:
        """Create warning for low layout detection confidence"""
        level = self.classify_confidence_level(confidence_score)
        
        if level == ConfidenceLevel.VERY_POOR:
            message = "Layout detection confidence is very low. Document structure may be incorrectly identified."
            recommendation = "Check that headers, paragraphs, and other elements are properly organized."
        elif level == ConfidenceLevel.POOR:
            message = "Layout detection confidence is low. Some structural elements may be misclassified."
            recommendation = "Review the document structure and reorganize elements if necessary."
        else:
            message = "Layout detection confidence is moderate. Minor structural issues may be present."
            recommendation = "Verify that document sections are properly organized and classified."
        
        return ConfidenceWarning(
            warning_type=WarningType.LOW_LAYOUT_CONFIDENCE,
            confidence_level=level,
            confidence_score=confidence_score,
            message=message,
            recommendation=recommendation,
            affected_areas=["document_structure", "headers", "sections"],
            severity="medium"
        )
    
    def _create_table_confidence_warning(self, confidence_score: float) -> ConfidenceWarning:
        """Create warning for low table recognition confidence"""
        level = self.classify_confidence_level(confidence_score)
        
        if level == ConfidenceLevel.VERY_POOR:
            message = "Table recognition confidence is very low. Table structure and content may be incorrect."
            recommendation = "Manually verify all table data and structure. Consider reformatting tables if needed."
        elif level == ConfidenceLevel.POOR:
            message = "Table recognition confidence is low. Some table cells or structure may be incorrect."
            recommendation = "Carefully review all table content and structure for accuracy."
        else:
            message = "Table recognition confidence is moderate. Minor table issues may be present."
            recommendation = "Check table alignment and cell content for any recognition errors."
        
        return ConfidenceWarning(
            warning_type=WarningType.LOW_TABLE_CONFIDENCE,
            confidence_level=level,
            confidence_score=confidence_score,
            message=message,
            recommendation=recommendation,
            affected_areas=["tables", "table_structure", "table_content"],
            severity="medium"
        )
    
    def _create_mixed_confidence_warning(self, confidence_scores: List[float], 
                                       metrics: ConfidenceMetrics) -> ConfidenceWarning:
        """Create warning for mixed confidence levels across different areas"""
        max_score = max(confidence_scores)
        min_score = min(confidence_scores)
        
        # Identify which areas have low confidence
        low_areas = []
        if metrics.text_confidence < self.WARNING_THRESHOLDS['text_confidence']:
            low_areas.append("text_recognition")
        if metrics.layout_confidence < self.WARNING_THRESHOLDS['layout_confidence']:
            low_areas.append("layout_detection")
        if metrics.table_confidence < self.WARNING_THRESHOLDS['table_confidence']:
            low_areas.append("table_recognition")
        
        message = f"Mixed confidence levels detected. Some areas processed well while others have lower accuracy."
        recommendation = f"Pay special attention to: {', '.join(low_areas)}. These areas may need manual review."
        
        return ConfidenceWarning(
            warning_type=WarningType.MIXED_CONFIDENCE,
            confidence_level=self.classify_confidence_level(metrics.overall_confidence),
            confidence_score=metrics.overall_confidence,
            message=message,
            recommendation=recommendation,
            affected_areas=low_areas,
            severity="medium"
        )
    
    def generate_confidence_report(self, metrics: ConfidenceMetrics) -> Dict[str, Any]:
        """
        Generate comprehensive confidence report for API response
        
        Args:
            metrics: Confidence metrics from processing
            
        Returns:
            Dictionary containing confidence report
        """
        warnings = self.check_confidence_thresholds(metrics)
        
        # Create confidence breakdown
        confidence_breakdown = {
            'overall': {
                'score': round(metrics.overall_confidence, 3),
                'level': self.classify_confidence_level(metrics.overall_confidence).value,
                'description': self._get_confidence_description(metrics.overall_confidence)
            },
            'text_recognition': {
                'score': round(metrics.text_confidence, 3),
                'level': self.classify_confidence_level(metrics.text_confidence).value,
                'description': self._get_confidence_description(metrics.text_confidence)
            },
            'layout_detection': {
                'score': round(metrics.layout_confidence, 3),
                'level': self.classify_confidence_level(metrics.layout_confidence).value,
                'description': self._get_confidence_description(metrics.layout_confidence)
            },
            'table_recognition': {
                'score': round(metrics.table_confidence, 3),
                'level': self.classify_confidence_level(metrics.table_confidence).value,
                'description': self._get_confidence_description(metrics.table_confidence)
            }
        }
        
        # Format warnings for API response
        formatted_warnings = []
        for warning in warnings:
            formatted_warnings.append({
                'type': warning.warning_type.value,
                'severity': warning.severity,
                'message': warning.message,
                'recommendation': warning.recommendation,
                'affected_areas': warning.affected_areas,
                'confidence_score': round(warning.confidence_score, 3)
            })
        
        return {
            'confidence_breakdown': confidence_breakdown,
            'warnings': formatted_warnings,
            'has_warnings': len(warnings) > 0,
            'warning_count': len(warnings),
            'overall_assessment': self._get_overall_assessment(metrics, warnings)
        }
    
    def _get_confidence_description(self, confidence_score: float) -> str:
        """Get human-readable description of confidence level"""
        level = self.classify_confidence_level(confidence_score)
        
        descriptions = {
            ConfidenceLevel.EXCELLENT: "Excellent - Very high accuracy expected",
            ConfidenceLevel.GOOD: "Good - High accuracy with minimal errors",
            ConfidenceLevel.FAIR: "Fair - Moderate accuracy, some review recommended",
            ConfidenceLevel.POOR: "Poor - Lower accuracy, careful review needed",
            ConfidenceLevel.VERY_POOR: "Very Poor - Low accuracy, significant review required"
        }
        
        return descriptions[level]
    
    def _get_overall_assessment(self, metrics: ConfidenceMetrics, 
                              warnings: List[ConfidenceWarning]) -> str:
        """Generate overall assessment message"""
        if not warnings:
            return "Document processed successfully with high confidence. Results should be accurate."
        
        high_severity_warnings = [w for w in warnings if w.severity == "high"]
        medium_severity_warnings = [w for w in warnings if w.severity == "medium"]
        
        if high_severity_warnings:
            return "Document processed with significant confidence concerns. Careful review is strongly recommended."
        elif len(medium_severity_warnings) > 2:
            return "Document processed with multiple confidence concerns. Review is recommended for accuracy."
        elif medium_severity_warnings:
            return "Document processed with some confidence concerns. Review of specific areas is recommended."
        else:
            return "Document processed with minor confidence concerns. Overall results should be reliable."
    
    def log_confidence_analysis(self, metrics: ConfidenceMetrics, warnings: List[ConfidenceWarning],
                              document_id: str):
        """
        Log confidence analysis results for monitoring and debugging
        
        Args:
            metrics: Confidence metrics
            warnings: Generated warnings (can be ConfidenceWarning objects or dicts)
            document_id: Document identifier
        """
        # Handle both ConfidenceWarning objects and dict format
        warning_types = []
        for w in warnings:
            if isinstance(w, dict):
                warning_types.append(w.get('type', 'unknown'))
            else:
                warning_types.append(w.warning_type.value)
        
        context = {
            'document_id': document_id,
            'operation': 'confidence_analysis',
            'overall_confidence': metrics.overall_confidence,
            'text_confidence': metrics.text_confidence,
            'layout_confidence': metrics.layout_confidence,
            'table_confidence': metrics.table_confidence,
            'warning_count': len(warnings),
            'warning_types': warning_types
        }
        
        if warnings:
            # Log as warning if there are confidence concerns
            self.logger.warning(f"Confidence concerns detected for document {document_id}: {context}")
        else:
            # Log as info for successful high-confidence processing
            self.logger.info(f"High confidence processing completed for document {document_id}: {context}")


# Global confidence monitor instance
confidence_monitor = ConfidenceMonitor()