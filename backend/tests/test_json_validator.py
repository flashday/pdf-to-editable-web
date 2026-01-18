"""
Tests for JSON serialization validation service
"""
import pytest
import json
import math
from decimal import Decimal
from datetime import datetime, date
from backend.services.json_validator import JSONSerializationValidator, JSONValidationError

class TestJSONSerializationValidator:
    """Test cases for JSON serialization validator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = JSONSerializationValidator()
    
    def test_validate_json_serializable_basic_types(self):
        """Test validation of basic JSON serializable types"""
        test_cases = [
            ("string", True),
            (123, True),
            (45.67, True),
            (True, True),
            (False, True),
            (None, True),
            ([], True),
            ({}, True)
        ]
        
        for data, expected in test_cases:
            result = self.validator.validate_json_serializable(data)
            assert result['is_serializable'] == expected, f"Failed for {data}"
    
    def test_validate_json_serializable_complex_structures(self):
        """Test validation of complex data structures"""
        complex_data = {
            "name": "Test",
            "age": 30,
            "active": True,
            "scores": [85, 92, 78],
            "metadata": {
                "created": "2023-01-01",
                "tags": ["important", "test"]
            }
        }
        
        result = self.validator.validate_json_serializable(complex_data)
        
        assert result['is_serializable'] is True
        assert len(result['errors']) == 0
        assert result['depth'] > 0
    
    def test_validate_json_serializable_non_serializable_types(self):
        """Test validation with non-serializable types"""
        non_serializable_data = {
            "function": lambda x: x,
            "set": {1, 2, 3},
            "bytes": b"hello"
        }
        
        result = self.validator.validate_json_serializable(non_serializable_data)
        
        assert result['is_serializable'] is False
        assert len(result['errors']) > 0
    
    def test_validate_json_serializable_special_float_values(self):
        """Test validation with special float values"""
        test_cases = [
            (float('nan'), False),
            (float('inf'), False),
            (float('-inf'), False),
            (1.23, True),
            (0.0, True)
        ]
        
        for data, expected in test_cases:
            result = self.validator.validate_json_serializable(data)
            assert result['is_serializable'] == expected, f"Failed for {data}"
    
    def test_validate_json_serializable_large_numbers(self):
        """Test validation with large numbers"""
        large_int = 2**60  # Larger than JavaScript safe integer
        very_large_float = 1.5e308  # Very large but still within JSON limits
        
        result_int = self.validator.validate_json_serializable(large_int)
        result_float = self.validator.validate_json_serializable(very_large_float)
        
        # Should be serializable but with warnings
        assert result_int['is_serializable'] is True
        assert len(result_int['warnings']) > 0
        
        assert result_float['is_serializable'] is True
        # Very large floats may or may not have warnings depending on exact value
    
    def test_validate_json_serializable_deep_nesting(self):
        """Test validation with deeply nested structures"""
        # Create deeply nested structure
        deep_data = {"level": 0}
        current = deep_data
        for i in range(1, 50):  # Create 50 levels deep
            current["next"] = {"level": i}
            current = current["next"]
        
        result = self.validator.validate_json_serializable(deep_data)
        
        assert result['is_serializable'] is True
        assert result['depth'] == 50  # Actual depth including root
    
    def test_validate_json_serializable_max_depth_exceeded(self):
        """Test validation when maximum depth is exceeded"""
        # Create structure deeper than max_depth
        deep_data = {}
        current = deep_data
        for i in range(self.validator.max_depth + 10):
            current["next"] = {}
            current = current["next"]
        
        result = self.validator.validate_json_serializable(deep_data)
        
        assert result['is_serializable'] is False
        assert any("Maximum depth exceeded" in error for error in result['errors'])
    
    def test_validate_json_serializable_large_collections(self):
        """Test validation with large collections"""
        large_list = list(range(1000))
        large_dict = {f"key_{i}": i for i in range(1000)}
        
        result_list = self.validator.validate_json_serializable(large_list)
        result_dict = self.validator.validate_json_serializable(large_dict)
        
        assert result_list['is_serializable'] is True
        assert result_dict['is_serializable'] is True
        # Should have size info
        assert 'array_length' in result_list['size_info']
        assert 'object_keys' in result_dict['size_info']
    
    def test_validate_json_serializable_unicode_strings(self):
        """Test validation with Unicode strings"""
        unicode_data = {
            "english": "Hello World",
            "chinese": "你好世界",
            "emoji": "🌍🚀✨",
            "special": "café résumé naïve"
        }
        
        result = self.validator.validate_json_serializable(unicode_data)
        
        assert result['is_serializable'] is True
        assert len(result['errors']) == 0
    
    def test_validate_json_serializable_control_characters(self):
        """Test validation with control characters"""
        control_char_string = "Hello\x00\x01World"
        
        result = self.validator.validate_json_serializable(control_char_string)
        
        # Should be serializable but with warnings
        assert result['is_serializable'] is True
        assert len(result['warnings']) > 0
    
    def test_serialize_safely_success(self):
        """Test safe serialization with valid data"""
        data = {"name": "Test", "value": 123}
        
        success, result = self.validator.serialize_safely(data)
        
        assert success is True
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed == data
    
    def test_serialize_safely_failure(self):
        """Test safe serialization with invalid data"""
        data = {"function": lambda x: x}
        
        success, result = self.validator.serialize_safely(data)
        
        assert success is False
        assert isinstance(result, dict)
        assert 'error' in result
    
    def test_serialize_safely_with_options(self):
        """Test safe serialization with custom options"""
        data = {"b": 2, "a": 1}
        
        success, result = self.validator.serialize_safely(data, sort_keys=True, indent=2)
        
        assert success is True
        assert isinstance(result, str)
        # Should be formatted with indentation
        assert '\n' in result
        # Should be sorted
        assert result.index('"a"') < result.index('"b"')
    
    def test_deserialize_safely_success(self):
        """Test safe deserialization with valid JSON"""
        json_str = '{"name": "Test", "value": 123}'
        
        success, result = self.validator.deserialize_safely(json_str)
        
        assert success is True
        assert isinstance(result, dict)
        assert result == {"name": "Test", "value": 123}
    
    def test_deserialize_safely_failure(self):
        """Test safe deserialization with invalid JSON"""
        invalid_json = '{"name": "Test", "value": 123'  # Missing closing brace
        
        success, result = self.validator.deserialize_safely(invalid_json)
        
        assert success is False
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'line' in result or 'position' in result
    
    def test_deserialize_safely_empty_string(self):
        """Test safe deserialization with empty string"""
        success, result = self.validator.deserialize_safely("")
        
        assert success is False
        assert 'Empty JSON string' in result['error']
    
    def test_deserialize_safely_non_string(self):
        """Test safe deserialization with non-string input"""
        success, result = self.validator.deserialize_safely(123)
        
        assert success is False
        assert 'Input must be a string' in result['error']
    
    def test_validate_json_string_valid(self):
        """Test JSON string validation with valid JSON"""
        json_str = '{"name": "Test", "items": [1, 2, 3]}'
        
        result = self.validator.validate_json_string(json_str)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert 'root_type' in result['structure_info']
    
    def test_validate_json_string_invalid_syntax(self):
        """Test JSON string validation with syntax errors"""
        invalid_json = '{"name": "Test", "value": 123,}'  # Trailing comma
        
        result = self.validator.validate_json_string(invalid_json)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'JSON syntax error' in result['errors'][0]
    
    def test_validate_json_string_structure_info(self):
        """Test JSON string validation structure analysis"""
        json_dict = '{"a": 1, "b": 2, "c": 3}'
        json_array = '[1, 2, 3, 4, 5]'
        
        result_dict = self.validator.validate_json_string(json_dict)
        result_array = self.validator.validate_json_string(json_array)
        
        assert result_dict['structure_info']['root_type'] == 'dict'
        assert result_dict['structure_info']['keys_count'] == 3
        
        assert result_array['structure_info']['root_type'] == 'list'
        assert result_array['structure_info']['items_count'] == 5
    
    def test_validate_json_string_large_size(self):
        """Test JSON string validation with large strings"""
        large_json = '{"data": "' + 'x' * 2000000 + '"}'  # 2MB string
        
        result = self.validator.validate_json_string(large_json)
        
        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
        assert 'Very large JSON string' in result['warnings'][0]
    
    def test_fix_common_json_issues_special_floats(self):
        """Test fixing special float values"""
        data_with_issues = {
            "nan_value": float('nan'),
            "inf_value": float('inf'),
            "normal_value": 3.14
        }
        
        fixed_data = self.validator.fix_common_json_issues(data_with_issues)
        
        assert fixed_data["nan_value"] is None
        assert fixed_data["inf_value"] is None
        assert fixed_data["normal_value"] == 3.14
    
    def test_fix_common_json_issues_decimal(self):
        """Test fixing Decimal values"""
        data_with_decimal = {"price": Decimal("19.99")}
        
        fixed_data = self.validator.fix_common_json_issues(data_with_decimal)
        
        assert isinstance(fixed_data["price"], float)
        assert fixed_data["price"] == 19.99
    
    def test_fix_common_json_issues_datetime(self):
        """Test fixing datetime values"""
        test_date = datetime(2023, 1, 1, 12, 0, 0)
        data_with_datetime = {"created": test_date}
        
        fixed_data = self.validator.fix_common_json_issues(data_with_datetime)
        
        assert isinstance(fixed_data["created"], str)
        assert "2023-01-01T12:00:00" in fixed_data["created"]
    
    def test_fix_common_json_issues_bytes(self):
        """Test fixing bytes values"""
        data_with_bytes = {"data": b"hello world"}
        
        fixed_data = self.validator.fix_common_json_issues(data_with_bytes)
        
        assert isinstance(fixed_data["data"], str)
        assert fixed_data["data"] == "hello world"
    
    def test_fix_common_json_issues_sets_tuples(self):
        """Test fixing sets and tuples"""
        data_with_collections = {
            "tags": {"tag1", "tag2", "tag3"},
            "coordinates": (10, 20)
        }
        
        fixed_data = self.validator.fix_common_json_issues(data_with_collections)
        
        assert isinstance(fixed_data["tags"], list)
        assert len(fixed_data["tags"]) == 3
        assert isinstance(fixed_data["coordinates"], list)
        assert fixed_data["coordinates"] == [10, 20]
    
    def test_fix_common_json_issues_non_string_keys(self):
        """Test fixing non-string dictionary keys"""
        data_with_int_keys = {1: "one", 2: "two", "3": "three"}
        
        fixed_data = self.validator.fix_common_json_issues(data_with_int_keys)
        
        # All keys should be strings
        for key in fixed_data.keys():
            assert isinstance(key, str)
        
        assert fixed_data["1"] == "one"
        assert fixed_data["2"] == "two"
        assert fixed_data["3"] == "three"
    
    def test_roundtrip_serialization(self):
        """Test complete roundtrip serialization/deserialization"""
        original_data = {
            "string": "Hello, 世界!",
            "number": 42,
            "float": 3.14159,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3, "four"],
            "object": {
                "nested": "value",
                "count": 10
            }
        }
        
        # Serialize
        success, json_str = self.validator.serialize_safely(original_data)
        assert success is True
        
        # Deserialize
        success, parsed_data = self.validator.deserialize_safely(json_str)
        assert success is True
        
        # Should match original
        assert parsed_data == original_data
    
    def test_error_handling_edge_cases(self):
        """Test error handling with edge cases"""
        # Test with None input
        result = self.validator.validate_json_serializable(None)
        assert result['is_serializable'] is True
        
        # Test with empty structures
        result = self.validator.validate_json_serializable({})
        assert result['is_serializable'] is True
        
        result = self.validator.validate_json_serializable([])
        assert result['is_serializable'] is True