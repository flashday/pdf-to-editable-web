"""
Tests for content integrity preservation service
"""
import pytest
from backend.services.content_integrity import ContentIntegrityValidator, ContentIntegrityError

class TestContentIntegrityValidator:
    """Test cases for content integrity validator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = ContentIntegrityValidator()
    
    def test_calculate_checksum_sha256(self):
        """Test SHA256 checksum calculation"""
        content = "Hello, World!"
        
        checksum = self.validator.calculate_checksum(content, 'sha256')
        
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 produces 64 hex characters
        
        # Same content should produce same checksum
        checksum2 = self.validator.calculate_checksum(content, 'sha256')
        assert checksum == checksum2
    
    def test_calculate_checksum_md5(self):
        """Test MD5 checksum calculation"""
        content = "Test content"
        
        checksum = self.validator.calculate_checksum(content, 'md5')
        
        assert isinstance(checksum, str)
        assert len(checksum) == 32  # MD5 produces 32 hex characters
    
    def test_calculate_checksum_invalid_algorithm(self):
        """Test checksum calculation with invalid algorithm"""
        content = "Test"
        
        with pytest.raises(ContentIntegrityError):
            self.validator.calculate_checksum(content, 'invalid_algo')
    
    def test_verify_checksum_success(self):
        """Test successful checksum verification"""
        content = "Verify this content"
        checksum = self.validator.calculate_checksum(content, 'sha256')
        
        result = self.validator.verify_checksum(content, checksum, 'sha256')
        
        assert result is True
    
    def test_verify_checksum_failure(self):
        """Test failed checksum verification"""
        content = "Original content"
        wrong_checksum = "0" * 64  # Invalid checksum
        
        result = self.validator.verify_checksum(content, wrong_checksum, 'sha256')
        
        assert result is False
    
    def test_compare_content_identical(self):
        """Test content comparison with identical strings"""
        original = "This is the same content"
        processed = "This is the same content"
        
        result = self.validator.compare_content(original, processed)
        
        assert result['is_identical'] is True
        assert result['similarity_ratio'] == 1.0
        assert result['content_preserved'] is True
        assert result['integrity_score'] == 1.0
        assert len(result['differences']) == 0
    
    def test_compare_content_minor_differences(self):
        """Test content comparison with minor differences"""
        original = "Hello World"
        processed = "Hello World!"  # Added exclamation
        
        result = self.validator.compare_content(original, processed)
        
        assert result['is_identical'] is False
        assert result['similarity_ratio'] > 0.85
        assert result['content_preserved'] is True
        assert result['integrity_score'] > 0.85
    
    def test_compare_content_major_differences(self):
        """Test content comparison with major differences"""
        original = "This is the original text"
        processed = "Completely different content"
        
        result = self.validator.compare_content(original, processed)
        
        assert result['is_identical'] is False
        assert result['similarity_ratio'] < 0.5
        assert result['content_preserved'] is False
        assert result['integrity_score'] < 0.5
        assert len(result['differences']) > 0
    
    def test_compare_content_whitespace_normalization(self):
        """Test content comparison with whitespace differences"""
        original = "Hello    World"
        processed = "Hello World"
        
        result = self.validator.compare_content(original, processed)
        
        # Should be considered identical after normalization
        assert result['is_identical'] is True
        assert result['content_preserved'] is True
    
    def test_compare_content_statistics(self):
        """Test content comparison statistics"""
        original = "One two three"
        processed = "One two three four"
        
        result = self.validator.compare_content(original, processed)
        
        assert 'statistics' in result
        assert result['statistics']['original_length'] == len(original)
        assert result['statistics']['processed_length'] == len(processed)
        assert result['statistics']['original_words'] == 3
        assert result['statistics']['processed_words'] == 4
    
    def test_detect_data_loss_no_loss(self):
        """Test data loss detection with no loss"""
        original = {"name": "Test", "value": 123}
        processed = {"name": "Test", "value": 123}
        
        result = self.validator.detect_data_loss(original, processed)
        
        assert result['has_data_loss'] is False
        assert result['loss_severity'] == 'none'
        assert len(result['missing_fields']) == 0
    
    def test_detect_data_loss_missing_field(self):
        """Test data loss detection with missing field"""
        original = {"name": "Test", "value": 123, "extra": "data"}
        processed = {"name": "Test", "value": 123}
        
        result = self.validator.detect_data_loss(original, processed)
        
        assert result['has_data_loss'] is True
        assert len(result['missing_fields']) > 0
        assert result['loss_severity'] in ['minor', 'moderate', 'severe']
    
    def test_detect_data_loss_type_change(self):
        """Test data loss detection with type change"""
        original = {"value": 123}
        processed = {"value": "123"}  # Changed from int to string
        
        result = self.validator.detect_data_loss(original, processed)
        
        assert result['has_data_loss'] is True
        assert len(result['type_changes']) > 0
    
    def test_detect_data_loss_list_length_change(self):
        """Test data loss detection with list length change"""
        original = [1, 2, 3, 4, 5]
        processed = [1, 2, 3]  # Lost 2 elements
        
        result = self.validator.detect_data_loss(original, processed)
        
        assert result['has_data_loss'] is True
        assert any(loc['type'] == 'length_change' for loc in result['loss_locations'])
    
    def test_detect_data_loss_nested_structures(self):
        """Test data loss detection in nested structures"""
        original = {
            "user": {
                "name": "John",
                "email": "john@example.com",
                "age": 30
            }
        }
        processed = {
            "user": {
                "name": "John",
                "email": "john@example.com"
                # Missing 'age' field
            }
        }
        
        result = self.validator.detect_data_loss(original, processed)
        
        assert result['has_data_loss'] is True
        assert len(result['missing_fields']) > 0
    
    def test_detect_data_loss_string_content(self):
        """Test data loss detection in string content"""
        original = "This is a long piece of text with important information"
        processed = "This is text"  # Significant content loss
        
        result = self.validator.detect_data_loss(original, processed)
        
        assert result['has_data_loss'] is True
        assert len(result['value_changes']) > 0
    
    def test_validate_pipeline_integrity_no_loss(self):
        """Test pipeline integrity validation with no loss"""
        stages = [
            ("input", {"data": "test"}),
            ("processed", {"data": "test"}),
            ("output", {"data": "test"})
        ]
        
        result = self.validator.validate_pipeline_integrity(stages)
        
        assert result['overall_integrity'] is True
        assert result['integrity_score'] == 1.0
        assert len(result['stage_comparisons']) == 2
    
    def test_validate_pipeline_integrity_with_loss(self):
        """Test pipeline integrity validation with data loss"""
        stages = [
            ("input", {"data": "test", "metadata": "info"}),
            ("processed", {"data": "test"}),  # Lost metadata
            ("output", {"data": "test"})
        ]
        
        result = self.validator.validate_pipeline_integrity(stages)
        
        assert result['overall_integrity'] is False
        assert result['integrity_score'] < 1.0
        assert len(result['cumulative_loss']) > 0
        assert len(result['recommendations']) > 0
    
    def test_validate_pipeline_integrity_insufficient_stages(self):
        """Test pipeline validation with insufficient stages"""
        stages = [("single_stage", {"data": "test"})]
        
        result = self.validator.validate_pipeline_integrity(stages)
        
        assert len(result['recommendations']) > 0
        assert "at least 2 stages" in result['recommendations'][0]
    
    def test_validate_pipeline_integrity_severity_tracking(self):
        """Test pipeline integrity severity tracking"""
        stages = [
            ("input", {"a": 1, "b": 2, "c": 3, "d": 4}),
            ("stage1", {"a": 1, "b": 2, "c": 3}),  # Lost 'd'
            ("stage2", {"a": 1, "b": 2}),  # Lost 'c'
            ("output", {"a": 1})  # Lost 'b'
        ]
        
        result = self.validator.validate_pipeline_integrity(stages)
        
        assert result['overall_integrity'] is False
        assert len(result['stage_comparisons']) == 3
        # Should track cumulative loss
        assert len(result['cumulative_loss']) > 0
    
    def test_create_integrity_checkpoint_string(self):
        """Test checkpoint creation for string data"""
        data = "Test content for checkpoint"
        stage_name = "preprocessing"
        
        checkpoint = self.validator.create_integrity_checkpoint(data, stage_name)
        
        assert checkpoint['stage_name'] == stage_name
        assert 'timestamp' in checkpoint
        assert 'md5' in checkpoint['checksums']
        assert 'sha256' in checkpoint['checksums']
        assert checkpoint['metadata']['content_length'] == len(data)
        assert checkpoint['metadata']['word_count'] == len(data.split())
    
    def test_create_integrity_checkpoint_dict(self):
        """Test checkpoint creation for dictionary data"""
        data = {"key1": "value1", "key2": 123}
        stage_name = "normalization"
        
        checkpoint = self.validator.create_integrity_checkpoint(data, stage_name)
        
        assert checkpoint['stage_name'] == stage_name
        assert 'md5' in checkpoint['checksums']
        assert 'sha256' in checkpoint['checksums']
        assert checkpoint['metadata']['keys_count'] == 2
        assert 'json_size' in checkpoint['metadata']
    
    def test_create_integrity_checkpoint_list(self):
        """Test checkpoint creation for list data"""
        data = [1, 2, 3, 4, 5]
        stage_name = "transformation"
        
        checkpoint = self.validator.create_integrity_checkpoint(data, stage_name)
        
        assert checkpoint['stage_name'] == stage_name
        assert 'md5' in checkpoint['checksums']
        assert 'sha256' in checkpoint['checksums']
        assert checkpoint['metadata']['items_count'] == 5
        assert 'json_size' in checkpoint['metadata']
    
    def test_checksum_consistency(self):
        """Test that checksums are consistent across multiple calculations"""
        content = "Consistency test content"
        
        checksums = [
            self.validator.calculate_checksum(content, 'sha256')
            for _ in range(5)
        ]
        
        # All checksums should be identical
        assert len(set(checksums)) == 1
    
    def test_unicode_content_integrity(self):
        """Test content integrity with Unicode characters"""
        original = "Hello 世界 🌍 café"
        processed = "Hello 世界 🌍 café"
        
        result = self.validator.compare_content(original, processed)
        
        assert result['is_identical'] is True
        assert result['content_preserved'] is True
    
    def test_empty_content_handling(self):
        """Test handling of empty content"""
        original = ""
        processed = ""
        
        result = self.validator.compare_content(original, processed)
        
        assert result['is_identical'] is True
        assert result['content_preserved'] is True
    
    def test_loss_severity_calculation(self):
        """Test loss severity calculation"""
        # Test minor loss
        report_minor = {
            'has_data_loss': True,
            'missing_fields': [{'path': 'field1'}],
            'type_changes': [],
            'value_changes': []
        }
        severity_minor = self.validator._calculate_loss_severity(report_minor)
        assert severity_minor == 'minor'
        
        # Test severe loss
        report_severe = {
            'has_data_loss': True,
            'missing_fields': [{'path': f'field{i}'} for i in range(10)],
            'type_changes': [],
            'value_changes': []
        }
        severity_severe = self.validator._calculate_loss_severity(report_severe)
        assert severity_severe == 'severe'