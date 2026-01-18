"""
Content integrity preservation service
Implements text content comparison, data loss detection, and integrity validation
"""
import logging
import hashlib
import difflib
from typing import Any, Dict, List, Optional, Tuple, Union
import json

logger = logging.getLogger(__name__)

class ContentIntegrityError(Exception):
    """Custom exception for content integrity errors"""
    pass

class ContentIntegrityValidator:
    """
    Service for validating content integrity throughout the processing pipeline
    """
    
    def __init__(self):
        """Initialize the content integrity validator"""
        # Thresholds for integrity validation
        self.similarity_threshold = 0.95  # 95% similarity required
        self.max_acceptable_loss = 0.05   # Maximum 5% content loss
        
        # Checksum algorithms
        self.checksum_algorithms = ['md5', 'sha256']
        
        # Content comparison settings
        self.ignore_whitespace_changes = True
        self.ignore_case = False
        self.normalize_unicode = True
    
    def calculate_checksum(self, content: str, algorithm: str = 'sha256') -> str:
        """
        Calculate checksum for content
        
        Args:
            content: Text content to checksum
            algorithm: Hash algorithm to use ('md5' or 'sha256')
            
        Returns:
            Hexadecimal checksum string
        """
        try:
            if algorithm not in self.checksum_algorithms:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            # Encode content to bytes
            content_bytes = content.encode('utf-8')
            
            # Calculate hash
            if algorithm == 'md5':
                hash_obj = hashlib.md5(content_bytes)
            elif algorithm == 'sha256':
                hash_obj = hashlib.sha256(content_bytes)
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Checksum calculation failed: {e}")
            raise ContentIntegrityError(f"Failed to calculate checksum: {e}")
    
    def verify_checksum(self, content: str, expected_checksum: str, algorithm: str = 'sha256') -> bool:
        """
        Verify content against expected checksum
        
        Args:
            content: Text content to verify
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm used
            
        Returns:
            True if checksum matches, False otherwise
        """
        try:
            actual_checksum = self.calculate_checksum(content, algorithm)
            return actual_checksum == expected_checksum
            
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False
    
    def compare_content(self, original: str, processed: str) -> Dict[str, Any]:
        """
        Compare original and processed content for integrity
        
        Args:
            original: Original text content
            processed: Processed text content
            
        Returns:
            Dictionary containing comparison results
        """
        comparison_result = {
            'is_identical': False,
            'similarity_ratio': 0.0,
            'content_preserved': False,
            'differences': [],
            'statistics': {},
            'integrity_score': 0.0
        }
        
        try:
            # Normalize content if configured
            original_normalized = self._normalize_content(original)
            processed_normalized = self._normalize_content(processed)
            
            # Check if identical
            comparison_result['is_identical'] = (original_normalized == processed_normalized)
            
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(None, original_normalized, processed_normalized)
            comparison_result['similarity_ratio'] = similarity.ratio()
            
            # Collect statistics
            comparison_result['statistics'] = {
                'original_length': len(original),
                'processed_length': len(processed),
                'length_difference': len(processed) - len(original),
                'original_words': len(original.split()),
                'processed_words': len(processed.split()),
                'word_difference': len(processed.split()) - len(original.split())
            }
            
            # Detect differences
            if not comparison_result['is_identical']:
                differences = self._detect_differences(original_normalized, processed_normalized)
                comparison_result['differences'] = differences[:10]  # Limit to first 10 differences
            
            # Calculate integrity score
            comparison_result['integrity_score'] = self._calculate_integrity_score(comparison_result)
            
            # Determine if content is preserved
            comparison_result['content_preserved'] = (
                comparison_result['similarity_ratio'] >= self.similarity_threshold
            )
            
            return comparison_result
            
        except Exception as e:
            logger.error(f"Content comparison failed: {e}")
            return {
                'is_identical': False,
                'similarity_ratio': 0.0,
                'content_preserved': False,
                'differences': [f"Comparison failed: {e}"],
                'statistics': {},
                'integrity_score': 0.0
            }
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for comparison
        
        Args:
            content: Content to normalize
            
        Returns:
            Normalized content
        """
        normalized = content
        
        # Normalize whitespace if configured
        if self.ignore_whitespace_changes:
            # Replace multiple whitespace with single space
            normalized = ' '.join(normalized.split())
        
        # Normalize case if configured
        if self.ignore_case:
            normalized = normalized.lower()
        
        # Normalize Unicode if configured
        if self.normalize_unicode:
            import unicodedata
            normalized = unicodedata.normalize('NFC', normalized)
        
        return normalized
    
    def _detect_differences(self, original: str, processed: str) -> List[Dict[str, Any]]:
        """
        Detect specific differences between original and processed content
        
        Args:
            original: Original content
            processed: Processed content
            
        Returns:
            List of difference descriptions
        """
        differences = []
        
        try:
            # Use difflib to find differences
            differ = difflib.Differ()
            diff = list(differ.compare(original.splitlines(), processed.splitlines()))
            
            for i, line in enumerate(diff):
                if line.startswith('- '):
                    differences.append({
                        'type': 'deletion',
                        'line': i,
                        'content': line[2:],
                        'description': f"Line deleted: {line[2:][:50]}"
                    })
                elif line.startswith('+ '):
                    differences.append({
                        'type': 'addition',
                        'line': i,
                        'content': line[2:],
                        'description': f"Line added: {line[2:][:50]}"
                    })
                elif line.startswith('? '):
                    # Character-level difference indicator
                    if differences:
                        differences[-1]['details'] = line[2:]
            
        except Exception as e:
            logger.warning(f"Difference detection failed: {e}")
            differences.append({
                'type': 'error',
                'description': f"Could not detect differences: {e}"
            })
        
        return differences
    
    def _calculate_integrity_score(self, comparison_result: Dict[str, Any]) -> float:
        """
        Calculate overall integrity score
        
        Args:
            comparison_result: Comparison result dictionary
            
        Returns:
            Integrity score (0.0 to 1.0)
        """
        try:
            # Base score from similarity ratio
            score = comparison_result['similarity_ratio']
            
            # Adjust for length changes
            stats = comparison_result['statistics']
            if stats.get('original_length', 0) > 0:
                length_ratio = abs(stats.get('length_difference', 0)) / stats['original_length']
                if length_ratio > self.max_acceptable_loss:
                    score *= (1.0 - length_ratio)
            
            # Adjust for word count changes
            if stats.get('original_words', 0) > 0:
                word_ratio = abs(stats.get('word_difference', 0)) / stats['original_words']
                if word_ratio > self.max_acceptable_loss:
                    score *= (1.0 - word_ratio * 0.5)
            
            # Ensure score is between 0 and 1
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.warning(f"Integrity score calculation failed: {e}")
            return 0.0
    
    def detect_data_loss(self, original: Any, processed: Any, path: str = "root") -> Dict[str, Any]:
        """
        Detect data loss throughout the processing pipeline
        
        Args:
            original: Original data structure
            processed: Processed data structure
            path: Current path in data structure
            
        Returns:
            Dictionary containing data loss analysis
        """
        loss_report = {
            'has_data_loss': False,
            'loss_locations': [],
            'missing_fields': [],
            'type_changes': [],
            'value_changes': [],
            'loss_severity': 'none'
        }
        
        try:
            # Compare data types
            if type(original) != type(processed):
                loss_report['has_data_loss'] = True
                loss_report['type_changes'].append({
                    'path': path,
                    'original_type': type(original).__name__,
                    'processed_type': type(processed).__name__
                })
            
            # Handle different data types
            if isinstance(original, dict) and isinstance(processed, dict):
                self._detect_dict_loss(original, processed, path, loss_report)
            elif isinstance(original, list) and isinstance(processed, list):
                self._detect_list_loss(original, processed, path, loss_report)
            elif isinstance(original, str) and isinstance(processed, str):
                self._detect_string_loss(original, processed, path, loss_report)
            elif original != processed:
                loss_report['has_data_loss'] = True
                loss_report['value_changes'].append({
                    'path': path,
                    'original': str(original)[:100],
                    'processed': str(processed)[:100]
                })
            
            # Determine loss severity
            loss_report['loss_severity'] = self._calculate_loss_severity(loss_report)
            
            return loss_report
            
        except Exception as e:
            logger.error(f"Data loss detection failed: {e}")
            return {
                'has_data_loss': True,
                'loss_locations': [f"Detection failed at {path}: {e}"],
                'missing_fields': [],
                'type_changes': [],
                'value_changes': [],
                'loss_severity': 'unknown'
            }
    
    def _detect_dict_loss(self, original: dict, processed: dict, path: str, report: Dict[str, Any]) -> None:
        """Detect data loss in dictionary structures"""
        # Check for missing keys
        missing_keys = set(original.keys()) - set(processed.keys())
        for key in missing_keys:
            report['has_data_loss'] = True
            report['missing_fields'].append({
                'path': f"{path}.{key}",
                'type': 'missing_key',
                'original_value': str(original[key])[:100]
            })
        
        # Check for added keys (not necessarily loss, but worth noting)
        added_keys = set(processed.keys()) - set(original.keys())
        for key in added_keys:
            report['loss_locations'].append({
                'path': f"{path}.{key}",
                'type': 'added_key',
                'note': 'New field added during processing'
            })
        
        # Recursively check common keys
        common_keys = set(original.keys()) & set(processed.keys())
        for key in common_keys:
            sub_report = self.detect_data_loss(
                original[key],
                processed[key],
                f"{path}.{key}"
            )
            if sub_report['has_data_loss']:
                report['has_data_loss'] = True
                report['loss_locations'].extend(sub_report['loss_locations'])
                report['missing_fields'].extend(sub_report['missing_fields'])
                report['type_changes'].extend(sub_report['type_changes'])
                report['value_changes'].extend(sub_report['value_changes'])
    
    def _detect_list_loss(self, original: list, processed: list, path: str, report: Dict[str, Any]) -> None:
        """Detect data loss in list structures"""
        # Check for length changes
        if len(original) != len(processed):
            report['has_data_loss'] = True
            report['loss_locations'].append({
                'path': path,
                'type': 'length_change',
                'original_length': len(original),
                'processed_length': len(processed),
                'difference': len(processed) - len(original)
            })
        
        # Compare elements up to the shorter length
        min_length = min(len(original), len(processed))
        for i in range(min_length):
            sub_report = self.detect_data_loss(
                original[i],
                processed[i],
                f"{path}[{i}]"
            )
            if sub_report['has_data_loss']:
                report['has_data_loss'] = True
                report['loss_locations'].extend(sub_report['loss_locations'])
                report['missing_fields'].extend(sub_report['missing_fields'])
                report['type_changes'].extend(sub_report['type_changes'])
                report['value_changes'].extend(sub_report['value_changes'])
    
    def _detect_string_loss(self, original: str, processed: str, path: str, report: Dict[str, Any]) -> None:
        """Detect data loss in string content"""
        # Use content comparison for strings
        comparison = self.compare_content(original, processed)
        
        if not comparison['content_preserved']:
            report['has_data_loss'] = True
            report['value_changes'].append({
                'path': path,
                'type': 'string_content',
                'similarity': comparison['similarity_ratio'],
                'original_length': len(original),
                'processed_length': len(processed),
                'differences_count': len(comparison['differences'])
            })
    
    def _calculate_loss_severity(self, report: Dict[str, Any]) -> str:
        """
        Calculate severity of data loss
        
        Args:
            report: Data loss report
            
        Returns:
            Severity level: 'none', 'minor', 'moderate', 'severe'
        """
        if not report['has_data_loss']:
            return 'none'
        
        # Count different types of losses
        total_issues = (
            len(report['missing_fields']) +
            len(report['type_changes']) +
            len(report['value_changes'])
        )
        
        if total_issues == 0:
            return 'none'
        elif total_issues <= 2:
            return 'minor'
        elif total_issues <= 5:
            return 'moderate'
        else:
            return 'severe'
    
    def validate_pipeline_integrity(self, stages: List[Tuple[str, Any]]) -> Dict[str, Any]:
        """
        Validate content integrity across multiple pipeline stages
        
        Args:
            stages: List of (stage_name, data) tuples representing pipeline stages
            
        Returns:
            Dictionary containing pipeline integrity validation results
        """
        validation_result = {
            'overall_integrity': True,
            'stage_comparisons': [],
            'cumulative_loss': {},
            'integrity_score': 1.0,
            'recommendations': []
        }
        
        try:
            if len(stages) < 2:
                validation_result['recommendations'].append("Need at least 2 stages to validate pipeline")
                return validation_result
            
            # Compare consecutive stages
            for i in range(len(stages) - 1):
                stage_name_1, data_1 = stages[i]
                stage_name_2, data_2 = stages[i + 1]
                
                # Detect data loss between stages
                loss_report = self.detect_data_loss(data_1, data_2, f"{stage_name_1}->{stage_name_2}")
                
                stage_comparison = {
                    'from_stage': stage_name_1,
                    'to_stage': stage_name_2,
                    'has_loss': loss_report['has_data_loss'],
                    'severity': loss_report['loss_severity'],
                    'details': loss_report
                }
                
                validation_result['stage_comparisons'].append(stage_comparison)
                
                if loss_report['has_data_loss']:
                    validation_result['overall_integrity'] = False
                    
                    # Add to cumulative loss tracking
                    for field in loss_report['missing_fields']:
                        field_path = field['path']
                        if field_path not in validation_result['cumulative_loss']:
                            validation_result['cumulative_loss'][field_path] = []
                        validation_result['cumulative_loss'][field_path].append(stage_name_2)
            
            # Calculate overall integrity score
            if validation_result['stage_comparisons']:
                severity_scores = {
                    'none': 1.0,
                    'minor': 0.9,
                    'moderate': 0.7,
                    'severe': 0.4
                }
                
                scores = [
                    severity_scores.get(comp['severity'], 0.5)
                    for comp in validation_result['stage_comparisons']
                ]
                validation_result['integrity_score'] = sum(scores) / len(scores)
            
            # Generate recommendations
            if not validation_result['overall_integrity']:
                validation_result['recommendations'].append(
                    "Data loss detected in pipeline - review stage transitions"
                )
                
                if validation_result['cumulative_loss']:
                    validation_result['recommendations'].append(
                        f"Critical fields lost: {list(validation_result['cumulative_loss'].keys())[:5]}"
                    )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Pipeline integrity validation failed: {e}")
            return {
                'overall_integrity': False,
                'stage_comparisons': [],
                'cumulative_loss': {},
                'integrity_score': 0.0,
                'recommendations': [f"Validation failed: {e}"]
            }
    
    def create_integrity_checkpoint(self, data: Any, stage_name: str) -> Dict[str, Any]:
        """
        Create an integrity checkpoint for data at a specific stage
        
        Args:
            data: Data to checkpoint
            stage_name: Name of the processing stage
            
        Returns:
            Dictionary containing checkpoint information
        """
        try:
            checkpoint = {
                'stage_name': stage_name,
                'timestamp': None,
                'checksums': {},
                'metadata': {}
            }
            
            # Add timestamp
            from datetime import datetime
            checkpoint['timestamp'] = datetime.now().isoformat()
            
            # Calculate checksums for string content
            if isinstance(data, str):
                checkpoint['checksums']['md5'] = self.calculate_checksum(data, 'md5')
                checkpoint['checksums']['sha256'] = self.calculate_checksum(data, 'sha256')
                checkpoint['metadata']['content_length'] = len(data)
                checkpoint['metadata']['word_count'] = len(data.split())
            
            elif isinstance(data, dict):
                # Serialize dict to JSON for checksumming
                json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
                checkpoint['checksums']['md5'] = self.calculate_checksum(json_str, 'md5')
                checkpoint['checksums']['sha256'] = self.calculate_checksum(json_str, 'sha256')
                checkpoint['metadata']['keys_count'] = len(data)
                checkpoint['metadata']['json_size'] = len(json_str)
            
            elif isinstance(data, list):
                # Serialize list to JSON for checksumming
                json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
                checkpoint['checksums']['md5'] = self.calculate_checksum(json_str, 'md5')
                checkpoint['checksums']['sha256'] = self.calculate_checksum(json_str, 'sha256')
                checkpoint['metadata']['items_count'] = len(data)
                checkpoint['metadata']['json_size'] = len(json_str)
            
            return checkpoint
            
        except Exception as e:
            logger.error(f"Checkpoint creation failed: {e}")
            return {
                'stage_name': stage_name,
                'error': str(e)
            }

# Global instance for easy access
content_integrity_validator = ContentIntegrityValidator()