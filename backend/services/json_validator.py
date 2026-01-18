"""
JSON serialization validation service
Implements JSON format correctness checking, serialization error detection and handling
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union, Tuple
from decimal import Decimal
from datetime import datetime, date
import math

logger = logging.getLogger(__name__)

class JSONValidationError(Exception):
    """Custom exception for JSON validation errors"""
    pass

class JSONSerializationValidator:
    """
    Service for validating JSON serialization and format correctness
    """
    
    def __init__(self):
        """Initialize the JSON validator with configuration"""
        # Maximum depth to prevent infinite recursion
        self.max_depth = 100
        
        # Maximum string length for JSON values
        self.max_string_length = 1000000  # 1MB
        
        # Maximum array/object size
        self.max_collection_size = 10000
        
        # Supported JSON types
        self.json_types = (str, int, float, bool, type(None), list, dict)
        
        # Characters that need special handling in JSON
        self.problematic_json_chars = {
            '\b': '\\b',
            '\f': '\\f',
            '\n': '\\n',
            '\r': '\\r',
            '\t': '\\t',
            '"': '\\"',
            '\\': '\\\\',
            '/': '\\/'
        }
    
    def validate_json_serializable(self, data: Any, path: str = "root") -> Dict[str, Any]:
        """
        Validate that data can be serialized to JSON
        
        Args:
            data: Data to validate for JSON serialization
            path: Current path in data structure for error reporting
            
        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            'is_serializable': True,
            'errors': [],
            'warnings': [],
            'data_type': type(data).__name__,
            'size_info': {},
            'depth': 0
        }
        
        try:
            # Check data structure recursively
            depth_result = self._check_serializable_recursive(data, path, 0)
            validation_result.update(depth_result)
            
            # Perform actual serialization test
            serialization_result = self._test_serialization(data)
            validation_result['serialization_test'] = serialization_result
            
            if not serialization_result['success']:
                validation_result['is_serializable'] = False
                validation_result['errors'].extend(serialization_result['errors'])
            
            # Check for potential issues
            self._check_potential_issues(data, validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"JSON serialization validation failed: {e}")
            return {
                'is_serializable': False,
                'errors': [f"Validation exception: {str(e)}"],
                'warnings': [],
                'data_type': type(data).__name__,
                'size_info': {},
                'depth': 0,
                'serialization_test': {'success': False, 'errors': [str(e)]}
            }
    
    def _check_serializable_recursive(self, data: Any, path: str, depth: int) -> Dict[str, Any]:
        """
        Recursively check if data structure is JSON serializable
        
        Args:
            data: Data to check
            path: Current path for error reporting
            depth: Current recursion depth
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'is_serializable': True,
            'errors': [],
            'warnings': [],
            'depth': depth,
            'size_info': {}
        }
        
        # Check recursion depth
        if depth > self.max_depth:
            result['is_serializable'] = False
            result['errors'].append(f"Maximum depth exceeded at {path} (depth: {depth})")
            return result
        
        # Check data type
        if not isinstance(data, self.json_types):
            result['is_serializable'] = False
            result['errors'].append(f"Non-serializable type {type(data).__name__} at {path}")
            return result
        
        # Handle different data types
        if isinstance(data, str):
            string_result = self._validate_string(data, path, result)
            result.update(string_result)
            return result
        elif isinstance(data, (int, float)):
            number_result = self._validate_number(data, path, result)
            result.update(number_result)
            return result
        elif isinstance(data, list):
            array_result = self._validate_array(data, path, depth, result)
            result.update(array_result)
            return result
        elif isinstance(data, dict):
            object_result = self._validate_object(data, path, depth, result)
            result.update(object_result)
            return result
        elif data is None or isinstance(data, bool):
            # These are always serializable
            return result
        else:
            result['is_serializable'] = False
            result['errors'].append(f"Unexpected type {type(data).__name__} at {path}")
            return result
    
    def _validate_string(self, data: str, path: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate string data for JSON serialization"""
        if 'size_info' not in result:
            result['size_info'] = {}
        result['size_info']['string_length'] = len(data)
        
        # Check string length
        if len(data) > self.max_string_length:
            result['warnings'].append(f"Very long string at {path} ({len(data)} chars)")
        
        # Check for problematic characters
        problematic_chars = []
        for char in data:
            if ord(char) < 32 and char not in ['\n', '\r', '\t']:
                problematic_chars.append(f"\\u{ord(char):04x}")
        
        if problematic_chars:
            result['warnings'].append(f"Control characters found at {path}: {problematic_chars[:5]}")
        
        # Check for non-UTF-8 characters
        try:
            data.encode('utf-8')
        except UnicodeEncodeError as e:
            result['errors'].append(f"Non-UTF-8 characters at {path}: {e}")
            result['is_serializable'] = False
        
        return result
    
    def _validate_number(self, data: Union[int, float], path: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate numeric data for JSON serialization"""
        if isinstance(data, float):
            # Check for special float values
            if math.isnan(data):
                result['errors'].append(f"NaN value at {path} (not JSON serializable)")
                result['is_serializable'] = False
            elif math.isinf(data):
                result['errors'].append(f"Infinity value at {path} (not JSON serializable)")
                result['is_serializable'] = False
            elif abs(data) > 1.7976931348623157e+308:  # Maximum finite double-precision float
                result['errors'].append(f"Float value {data} at {path} exceeds maximum JSON value")
                result['is_serializable'] = False
            elif abs(data) > 1e308:  # JSON number limit
                result['warnings'].append(f"Very large number at {path} may cause issues")
        
        elif isinstance(data, int):
            # Check for very large integers
            if abs(data) > 2**53:  # JavaScript safe integer limit
                result['warnings'].append(f"Large integer at {path} may lose precision in JavaScript")
        
        return result
    
    def _validate_array(self, data: List[Any], path: str, depth: int, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate array data for JSON serialization"""
        if 'size_info' not in result:
            result['size_info'] = {}
        result['size_info']['array_length'] = len(data)
        
        # Check array size
        if len(data) > self.max_collection_size:
            result['warnings'].append(f"Large array at {path} ({len(data)} items)")
        
        # Validate each element
        for i, item in enumerate(data):
            item_path = f"{path}[{i}]"
            item_result = self._check_serializable_recursive(item, item_path, depth + 1)
            
            if not item_result['is_serializable']:
                result['is_serializable'] = False
            
            result['errors'].extend(item_result['errors'])
            result['warnings'].extend(item_result['warnings'])
            result['depth'] = max(result['depth'], item_result['depth'])
            
            # Merge size_info
            if 'size_info' in item_result:
                for key, value in item_result['size_info'].items():
                    if key in result['size_info']:
                        if isinstance(result['size_info'][key], (int, float)) and isinstance(value, (int, float)):
                            result['size_info'][key] += value
                    else:
                        result['size_info'][key] = value
        
        return result
    
    def _validate_object(self, data: Dict[str, Any], path: str, depth: int, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate object data for JSON serialization"""
        if 'size_info' not in result:
            result['size_info'] = {}
        result['size_info']['object_keys'] = len(data)
        
        # Check object size
        if len(data) > self.max_collection_size:
            result['warnings'].append(f"Large object at {path} ({len(data)} keys)")
        
        # Validate keys and values
        for key, value in data.items():
            # Validate key
            if not isinstance(key, str):
                result['errors'].append(f"Non-string key {repr(key)} at {path}")
                result['is_serializable'] = False
                continue
            
            # Validate key as string
            key_result = self._validate_string(key, f"{path}.{key}(key)", {'errors': [], 'warnings': [], 'is_serializable': True, 'size_info': {}})
            if not key_result['is_serializable']:
                result['is_serializable'] = False
                result['errors'].extend(key_result['errors'])
            result['warnings'].extend(key_result['warnings'])
            
            # Validate value
            value_path = f"{path}.{key}"
            value_result = self._check_serializable_recursive(value, value_path, depth + 1)
            
            if not value_result['is_serializable']:
                result['is_serializable'] = False
            
            result['errors'].extend(value_result['errors'])
            result['warnings'].extend(value_result['warnings'])
            result['depth'] = max(result['depth'], value_result['depth'])
            
            # Merge size_info
            if 'size_info' in value_result:
                for size_key, size_value in value_result['size_info'].items():
                    if size_key in result['size_info']:
                        if isinstance(result['size_info'][size_key], (int, float)) and isinstance(size_value, (int, float)):
                            result['size_info'][size_key] += size_value
                    else:
                        result['size_info'][size_key] = size_value
        
        return result
    
    def _test_serialization(self, data: Any) -> Dict[str, Any]:
        """
        Test actual JSON serialization
        
        Args:
            data: Data to serialize
            
        Returns:
            Dictionary with serialization test results
        """
        test_result = {
            'success': True,
            'errors': [],
            'json_size': 0,
            'serialization_time': 0
        }
        
        try:
            import time
            start_time = time.time()
            
            # Test serialization
            json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            test_result['json_size'] = len(json_str)
            test_result['serialization_time'] = time.time() - start_time
            
            # Test deserialization to ensure roundtrip works
            parsed_data = json.loads(json_str)
            
            # Basic structure comparison
            if type(parsed_data) != type(data):
                test_result['errors'].append(f"Type changed during roundtrip: {type(data)} -> {type(parsed_data)}")
            
        except TypeError as e:
            test_result['success'] = False
            test_result['errors'].append(f"Serialization TypeError: {e}")
        except ValueError as e:
            test_result['success'] = False
            test_result['errors'].append(f"Serialization ValueError: {e}")
        except OverflowError as e:
            test_result['success'] = False
            test_result['errors'].append(f"Serialization OverflowError: {e}")
        except Exception as e:
            test_result['success'] = False
            test_result['errors'].append(f"Serialization error: {e}")
        
        return test_result
    
    def _check_potential_issues(self, data: Any, result: Dict[str, Any]) -> None:
        """
        Check for potential issues that might cause problems
        
        Args:
            data: Data to check
            result: Result dictionary to update
        """
        try:
            # Check for circular references (basic check)
            seen_objects = set()
            self._check_circular_references(data, seen_objects, result)
            
            # Check for memory usage concerns
            if result['size_info']:
                total_size = sum(result['size_info'].values())
                if total_size > 100000:  # Large data structure
                    result['warnings'].append(f"Large data structure may impact performance (estimated size: {total_size})")
            
        except Exception as e:
            result['warnings'].append(f"Issue detection failed: {e}")
    
    def _check_circular_references(self, data: Any, seen_objects: set, result: Dict[str, Any]) -> None:
        """Check for circular references in data structure"""
        if isinstance(data, (list, dict)):
            obj_id = id(data)
            if obj_id in seen_objects:
                result['errors'].append("Circular reference detected")
                result['is_serializable'] = False
                return
            
            seen_objects.add(obj_id)
            
            if isinstance(data, list):
                for item in data:
                    self._check_circular_references(item, seen_objects.copy(), result)
            elif isinstance(data, dict):
                for value in data.values():
                    self._check_circular_references(value, seen_objects.copy(), result)
    
    def serialize_safely(self, data: Any, **kwargs) -> Tuple[bool, Union[str, Dict[str, Any]]]:
        """
        Safely serialize data to JSON with error handling
        
        Args:
            data: Data to serialize
            **kwargs: Additional arguments for json.dumps
            
        Returns:
            Tuple of (success, result_or_error_info)
        """
        try:
            # Validate first
            validation_result = self.validate_json_serializable(data)
            
            if not validation_result['is_serializable']:
                return False, {
                    'error': 'Data is not JSON serializable',
                    'validation_result': validation_result
                }
            
            # Set default serialization options
            serialize_options = {
                'ensure_ascii': False,
                'separators': (',', ':'),
                'sort_keys': False
            }
            serialize_options.update(kwargs)
            
            # Perform serialization
            json_str = json.dumps(data, **serialize_options)
            
            return True, json_str
            
        except Exception as e:
            logger.error(f"Safe JSON serialization failed: {e}")
            return False, {
                'error': f'Serialization failed: {e}',
                'exception_type': type(e).__name__
            }
    
    def deserialize_safely(self, json_str: str) -> Tuple[bool, Union[Any, Dict[str, Any]]]:
        """
        Safely deserialize JSON string with error handling
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Tuple of (success, result_or_error_info)
        """
        try:
            # Basic validation
            if not isinstance(json_str, str):
                return False, {'error': 'Input must be a string'}
            
            if not json_str.strip():
                return False, {'error': 'Empty JSON string'}
            
            # Perform deserialization
            data = json.loads(json_str)
            
            return True, data
            
        except json.JSONDecodeError as e:
            return False, {
                'error': f'JSON decode error: {e.msg}',
                'line': e.lineno,
                'column': e.colno,
                'position': e.pos
            }
        except Exception as e:
            logger.error(f"Safe JSON deserialization failed: {e}")
            return False, {
                'error': f'Deserialization failed: {e}',
                'exception_type': type(e).__name__
            }
    
    def validate_json_string(self, json_str: str) -> Dict[str, Any]:
        """
        Validate JSON string format and structure
        
        Args:
            json_str: JSON string to validate
            
        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'structure_info': {},
            'size_info': {
                'string_length': len(json_str) if isinstance(json_str, str) else 0
            }
        }
        
        try:
            # Basic checks
            if not isinstance(json_str, str):
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Input must be string, got {type(json_str).__name__}")
                return validation_result
            
            if not json_str.strip():
                validation_result['is_valid'] = False
                validation_result['errors'].append("Empty JSON string")
                return validation_result
            
            # Parse JSON
            try:
                parsed_data = json.loads(json_str)
                validation_result['structure_info']['root_type'] = type(parsed_data).__name__
                
                # Analyze structure
                if isinstance(parsed_data, dict):
                    validation_result['structure_info']['keys_count'] = len(parsed_data)
                elif isinstance(parsed_data, list):
                    validation_result['structure_info']['items_count'] = len(parsed_data)
                
            except json.JSONDecodeError as e:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"JSON syntax error: {e.msg} at line {e.lineno}, column {e.colno}")
                return validation_result
            
            # Check for potential issues
            if len(json_str) > 1000000:  # 1MB
                validation_result['warnings'].append("Very large JSON string may impact performance")
            
            # Check for common formatting issues
            if json_str.count('{') != json_str.count('}'):
                validation_result['warnings'].append("Unbalanced braces detected")
            
            if json_str.count('[') != json_str.count(']'):
                validation_result['warnings'].append("Unbalanced brackets detected")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"JSON string validation failed: {e}")
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation exception: {e}")
            return validation_result
    
    def fix_common_json_issues(self, data: Any) -> Any:
        """
        Fix common JSON serialization issues
        
        Args:
            data: Data with potential JSON issues
            
        Returns:
            Data with issues fixed
        """
        try:
            return self._fix_recursive(data)
        except Exception as e:
            logger.error(f"JSON issue fixing failed: {e}")
            return data
    
    def _fix_recursive(self, data: Any) -> Any:
        """Recursively fix JSON issues in data structure"""
        if isinstance(data, float):
            # Fix special float values
            if math.isnan(data):
                return None
            elif math.isinf(data):
                return None
            else:
                return data
        
        elif isinstance(data, Decimal):
            # Convert Decimal to float
            return float(data)
        
        elif isinstance(data, (datetime, date)):
            # Convert datetime to ISO string
            return data.isoformat()
        
        elif isinstance(data, bytes):
            # Convert bytes to string
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data.decode('utf-8', errors='replace')
        
        elif isinstance(data, set):
            # Convert set to list
            return [self._fix_recursive(item) for item in data]
        
        elif isinstance(data, tuple):
            # Convert tuple to list
            return [self._fix_recursive(item) for item in data]
        
        elif isinstance(data, list):
            # Fix list items
            return [self._fix_recursive(item) for item in data]
        
        elif isinstance(data, dict):
            # Fix dictionary keys and values
            fixed_dict = {}
            for key, value in data.items():
                # Ensure key is string
                if not isinstance(key, str):
                    key = str(key)
                fixed_dict[key] = self._fix_recursive(value)
            return fixed_dict
        
        else:
            # Return as-is for basic JSON types
            return data

# Global instance for easy access
json_validator = JSONSerializationValidator()