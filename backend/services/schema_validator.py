"""
Editor.js schema validation service with comprehensive validation rules
"""
import logging
import json
from typing import Dict, Any, List, Optional, Union
from backend.models.document import EditorJSData, EditorJSBlock

logger = logging.getLogger(__name__)

class EditorJSSchemaValidator:
    """
    Comprehensive schema validator for Editor.js data structures
    """
    
    def __init__(self):
        """Initialize the schema validator with Editor.js specifications"""
        self.supported_block_types = {
            "header", "paragraph", "table", "list", "image", "delimiter", "quote", "code"
        }
        
        # Define schema specifications for each block type
        self.block_schemas = {
            "header": {
                "required_fields": ["text", "level"],
                "field_types": {
                    "text": str,
                    "level": int
                },
                "field_constraints": {
                    "level": lambda x: 1 <= x <= 6,
                    "text": lambda x: len(x.strip()) > 0
                }
            },
            "paragraph": {
                "required_fields": ["text"],
                "field_types": {
                    "text": str
                },
                "field_constraints": {
                    "text": lambda x: isinstance(x, str)  # Allow empty paragraphs
                }
            },
            "table": {
                "required_fields": ["content", "withHeadings"],
                "field_types": {
                    "content": list,
                    "withHeadings": bool,
                    "stretched": bool  # Optional field
                },
                "field_constraints": {
                    "content": lambda x: len(x) > 0 and all(isinstance(row, list) for row in x),
                    "withHeadings": lambda x: isinstance(x, bool)
                }
            },
            "list": {
                "required_fields": ["style", "items"],
                "field_types": {
                    "style": str,
                    "items": list
                },
                "field_constraints": {
                    "style": lambda x: x in ["ordered", "unordered"],
                    "items": lambda x: len(x) > 0 and all(isinstance(item, str) for item in x)
                }
            },
            "image": {
                "required_fields": ["file"],
                "field_types": {
                    "file": dict,
                    "caption": str,  # Optional
                    "withBorder": bool,  # Optional
                    "withBackground": bool,  # Optional
                    "stretched": bool  # Optional
                },
                "field_constraints": {
                    "file": lambda x: "url" in x or "width" in x or "height" in x
                }
            }
        }
    
    def validate_editor_data(self, editor_data: EditorJSData) -> Dict[str, Any]:
        """
        Comprehensive validation of Editor.js data structure
        
        Args:
            editor_data: Editor.js data to validate
            
        Returns:
            Dictionary containing validation results and detailed error information
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "block_count": 0,
            "validation_details": {
                "structure_valid": True,
                "blocks_valid": True,
                "schema_compliant": True
            }
        }
        
        try:
            # Validate top-level structure
            structure_errors = self._validate_top_level_structure(editor_data)
            if structure_errors:
                validation_result["errors"].extend(structure_errors)
                validation_result["validation_details"]["structure_valid"] = False
                validation_result["is_valid"] = False
            
            # Validate blocks if structure is valid
            if validation_result["validation_details"]["structure_valid"]:
                block_errors, block_warnings = self._validate_all_blocks(editor_data.blocks)
                validation_result["errors"].extend(block_errors)
                validation_result["warnings"].extend(block_warnings)
                validation_result["block_count"] = len(editor_data.blocks)
                
                if block_errors:
                    validation_result["validation_details"]["blocks_valid"] = False
                    validation_result["is_valid"] = False
            
            # Validate JSON serialization
            serialization_errors = self._validate_json_serialization(editor_data)
            if serialization_errors:
                validation_result["errors"].extend(serialization_errors)
                validation_result["validation_details"]["schema_compliant"] = False
                validation_result["is_valid"] = False
            
            # Log validation summary
            if validation_result["is_valid"]:
                logger.info(f"Schema validation passed for {validation_result['block_count']} blocks")
            else:
                logger.warning(f"Schema validation failed with {len(validation_result['errors'])} errors")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Schema validation failed with exception: {e}")
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Validation exception: {str(e)}")
            return validation_result
    
    def _validate_top_level_structure(self, editor_data: EditorJSData) -> List[str]:
        """
        Validate top-level Editor.js data structure
        
        Args:
            editor_data: Editor.js data to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required attributes
        if not hasattr(editor_data, 'time'):
            errors.append("Missing required field: time")
        elif not isinstance(editor_data.time, int):
            errors.append("Field 'time' must be an integer")
        elif editor_data.time <= 0:
            errors.append("Field 'time' must be a positive integer")
        
        if not hasattr(editor_data, 'blocks'):
            errors.append("Missing required field: blocks")
        elif not isinstance(editor_data.blocks, list):
            errors.append("Field 'blocks' must be a list")
        
        if not hasattr(editor_data, 'version'):
            errors.append("Missing required field: version")
        elif not isinstance(editor_data.version, str):
            errors.append("Field 'version' must be a string")
        elif not editor_data.version.strip():
            errors.append("Field 'version' cannot be empty")
        
        return errors
    
    def _validate_all_blocks(self, blocks: List[EditorJSBlock]) -> tuple[List[str], List[str]]:
        """
        Validate all blocks in the Editor.js data
        
        Args:
            blocks: List of blocks to validate
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        if not blocks:
            warnings.append("No blocks found in Editor.js data")
            return errors, warnings
        
        # Track block IDs for uniqueness validation
        block_ids = set()
        
        for i, block in enumerate(blocks):
            # Validate individual block
            block_errors, block_warnings = self._validate_single_block(block, i)
            errors.extend(block_errors)
            warnings.extend(block_warnings)
            
            # Check block ID uniqueness
            if hasattr(block, 'id') and block.id:
                if block.id in block_ids:
                    errors.append(f"Block {i}: Duplicate block ID '{block.id}'")
                else:
                    block_ids.add(block.id)
        
        return errors, warnings
    
    def _validate_single_block(self, block: EditorJSBlock, index: int) -> tuple[List[str], List[str]]:
        """
        Validate a single Editor.js block
        
        Args:
            block: Block to validate
            index: Block index for error reporting
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        # Validate block structure
        structure_errors = self._validate_block_structure(block, index)
        errors.extend(structure_errors)
        
        if structure_errors:
            return errors, warnings  # Skip further validation if structure is invalid
        
        # Validate block type specific data
        type_errors, type_warnings = self._validate_block_type_data(block, index)
        errors.extend(type_errors)
        warnings.extend(type_warnings)
        
        # Validate metadata if present
        metadata_warnings = self._validate_block_metadata(block, index)
        warnings.extend(metadata_warnings)
        
        return errors, warnings
    
    def _validate_block_structure(self, block: EditorJSBlock, index: int) -> List[str]:
        """
        Validate basic block structure
        
        Args:
            block: Block to validate
            index: Block index for error reporting
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required attributes
        if not hasattr(block, 'id') or not block.id:
            errors.append(f"Block {index}: Missing or empty 'id' field")
        elif not isinstance(block.id, str):
            errors.append(f"Block {index}: Field 'id' must be a string")
        
        if not hasattr(block, 'type') or not block.type:
            errors.append(f"Block {index}: Missing or empty 'type' field")
        elif not isinstance(block.type, str):
            errors.append(f"Block {index}: Field 'type' must be a string")
        elif block.type not in self.supported_block_types:
            errors.append(f"Block {index}: Unsupported block type '{block.type}'")
        
        if not hasattr(block, 'data'):
            errors.append(f"Block {index}: Missing 'data' field")
        elif not isinstance(block.data, dict):
            errors.append(f"Block {index}: Field 'data' must be a dictionary")
        
        return errors
    
    def _validate_block_type_data(self, block: EditorJSBlock, index: int) -> tuple[List[str], List[str]]:
        """
        Validate block type specific data
        
        Args:
            block: Block to validate
            index: Block index for error reporting
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []
        
        block_type = block.type
        data = block.data
        
        if block_type not in self.block_schemas:
            warnings.append(f"Block {index}: No schema defined for block type '{block_type}'")
            return errors, warnings
        
        schema = self.block_schemas[block_type]
        
        # Check required fields
        for field in schema["required_fields"]:
            if field not in data:
                errors.append(f"Block {index}: Missing required field '{field}' for {block_type} block")
            else:
                # Check field type
                expected_type = schema["field_types"][field]
                actual_value = data[field]
                
                if not isinstance(actual_value, expected_type):
                    errors.append(f"Block {index}: Field '{field}' must be of type {expected_type.__name__}, got {type(actual_value).__name__}")
                else:
                    # Check field constraints
                    if field in schema["field_constraints"]:
                        constraint_func = schema["field_constraints"][field]
                        try:
                            if not constraint_func(actual_value):
                                errors.append(f"Block {index}: Field '{field}' violates constraint for {block_type} block")
                        except Exception as e:
                            errors.append(f"Block {index}: Constraint validation failed for field '{field}': {e}")
        
        # Check optional fields
        for field, field_type in schema["field_types"].items():
            if field not in schema["required_fields"] and field in data:
                if not isinstance(data[field], field_type):
                    warnings.append(f"Block {index}: Optional field '{field}' should be of type {field_type.__name__}")
        
        # Perform block-type specific validation
        if block_type == "table":
            table_errors = self._validate_table_specific(data, index)
            errors.extend(table_errors)
        elif block_type == "list":
            list_errors = self._validate_list_specific(data, index)
            errors.extend(list_errors)
        elif block_type == "image":
            image_errors = self._validate_image_specific(data, index)
            errors.extend(image_errors)
        
        return errors, warnings
    
    def _validate_table_specific(self, data: Dict[str, Any], index: int) -> List[str]:
        """
        Perform table-specific validation
        
        Args:
            data: Table block data
            index: Block index for error reporting
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if "content" in data:
            content = data["content"]
            
            if not content:
                errors.append(f"Block {index}: Table content cannot be empty")
                return errors
            
            # Validate table structure
            expected_cols = len(content[0]) if content else 0
            
            if expected_cols == 0:
                errors.append(f"Block {index}: Table first row cannot be empty")
            
            for row_idx, row in enumerate(content):
                if not isinstance(row, list):
                    errors.append(f"Block {index}: Table row {row_idx} must be a list")
                    continue
                
                if len(row) != expected_cols:
                    errors.append(f"Block {index}: Table row {row_idx} has {len(row)} columns, expected {expected_cols}")
                
                for col_idx, cell in enumerate(row):
                    if not isinstance(cell, str):
                        errors.append(f"Block {index}: Table cell [{row_idx}][{col_idx}] must be a string")
        
        return errors
    
    def _validate_list_specific(self, data: Dict[str, Any], index: int) -> List[str]:
        """
        Perform list-specific validation
        
        Args:
            data: List block data
            index: Block index for error reporting
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if "items" in data:
            items = data["items"]
            
            if not items:
                errors.append(f"Block {index}: List items cannot be empty")
            
            for item_idx, item in enumerate(items):
                if not isinstance(item, str):
                    errors.append(f"Block {index}: List item {item_idx} must be a string")
                elif not item.strip():
                    errors.append(f"Block {index}: List item {item_idx} cannot be empty")
        
        return errors
    
    def _validate_image_specific(self, data: Dict[str, Any], index: int) -> List[str]:
        """
        Perform image-specific validation
        
        Args:
            data: Image block data
            index: Block index for error reporting
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if "file" in data:
            file_data = data["file"]
            
            if not isinstance(file_data, dict):
                errors.append(f"Block {index}: Image file field must be a dictionary")
            else:
                # Check for at least one of the expected file fields
                expected_fields = ["url", "width", "height"]
                if not any(field in file_data for field in expected_fields):
                    errors.append(f"Block {index}: Image file must contain at least one of: {expected_fields}")
                
                # Validate field types if present
                if "url" in file_data and not isinstance(file_data["url"], str):
                    errors.append(f"Block {index}: Image file URL must be a string")
                
                if "width" in file_data and not isinstance(file_data["width"], (int, float)):
                    errors.append(f"Block {index}: Image file width must be a number")
                
                if "height" in file_data and not isinstance(file_data["height"], (int, float)):
                    errors.append(f"Block {index}: Image file height must be a number")
        
        return errors
    
    def _validate_block_metadata(self, block: EditorJSBlock, index: int) -> List[str]:
        """
        Validate block metadata if present
        
        Args:
            block: Block to validate
            index: Block index for error reporting
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        if hasattr(block, 'metadata') and block.metadata is not None:
            if not isinstance(block.metadata, dict):
                warnings.append(f"Block {index}: Metadata should be a dictionary")
            else:
                # Check for common metadata fields
                expected_metadata_fields = ["confidence", "originalCoordinates", "processingNotes"]
                
                for field in expected_metadata_fields:
                    if field not in block.metadata:
                        warnings.append(f"Block {index}: Missing recommended metadata field '{field}'")
                
                # Validate confidence if present
                if "confidence" in block.metadata:
                    confidence = block.metadata["confidence"]
                    if not isinstance(confidence, (int, float)):
                        warnings.append(f"Block {index}: Metadata confidence should be a number")
                    elif not (0.0 <= confidence <= 1.0):
                        warnings.append(f"Block {index}: Metadata confidence should be between 0.0 and 1.0")
        
        return warnings
    
    def _validate_json_serialization(self, editor_data: EditorJSData) -> List[str]:
        """
        Validate that the data can be properly serialized to JSON
        
        Args:
            editor_data: Editor.js data to validate
            
        Returns:
            List of serialization errors
        """
        errors = []
        
        try:
            # Convert to dictionary for JSON serialization test
            data_dict = {
                "time": editor_data.time,
                "blocks": [],
                "version": editor_data.version
            }
            
            for block in editor_data.blocks:
                block_dict = {
                    "id": block.id,
                    "type": block.type,
                    "data": block.data
                }
                
                if hasattr(block, 'metadata') and block.metadata:
                    block_dict["metadata"] = block.metadata
                
                data_dict["blocks"].append(block_dict)
            
            # Test JSON serialization
            json_str = json.dumps(data_dict, ensure_ascii=False, indent=2)
            
            # Test JSON deserialization
            parsed_data = json.loads(json_str)
            
            # Verify structure is preserved
            if len(parsed_data["blocks"]) != len(editor_data.blocks):
                errors.append("JSON serialization/deserialization changed block count")
            
        except TypeError as e:
            errors.append(f"JSON serialization failed - non-serializable data: {e}")
        except ValueError as e:
            errors.append(f"JSON serialization failed - invalid data: {e}")
        except Exception as e:
            errors.append(f"JSON serialization validation failed: {e}")
        
        return errors
    
    def generate_validation_report(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable validation report
        
        Args:
            validation_result: Result from validate_editor_data
            
        Returns:
            Formatted validation report string
        """
        report_lines = []
        
        # Header
        status = "PASSED" if validation_result["is_valid"] else "FAILED"
        report_lines.append(f"Editor.js Schema Validation Report - {status}")
        report_lines.append("=" * 50)
        
        # Summary
        report_lines.append(f"Total Blocks: {validation_result['block_count']}")
        report_lines.append(f"Errors: {len(validation_result['errors'])}")
        report_lines.append(f"Warnings: {len(validation_result['warnings'])}")
        report_lines.append("")
        
        # Validation details
        details = validation_result["validation_details"]
        report_lines.append("Validation Details:")
        report_lines.append(f"  Structure Valid: {details['structure_valid']}")
        report_lines.append(f"  Blocks Valid: {details['blocks_valid']}")
        report_lines.append(f"  Schema Compliant: {details['schema_compliant']}")
        report_lines.append("")
        
        # Errors
        if validation_result["errors"]:
            report_lines.append("ERRORS:")
            for error in validation_result["errors"]:
                report_lines.append(f"  - {error}")
            report_lines.append("")
        
        # Warnings
        if validation_result["warnings"]:
            report_lines.append("WARNINGS:")
            for warning in validation_result["warnings"]:
                report_lines.append(f"  - {warning}")
            report_lines.append("")
        
        return "\n".join(report_lines)