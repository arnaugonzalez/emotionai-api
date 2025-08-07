"""
Data Validation for API Responses

Ensures all API responses have consistent data types and required fields
to prevent frontend parsing errors.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validate_emotional_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize emotional record data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "source": str(data.get("source", "manual")),
        "description": str(data.get("description", "")),
        "emotion": str(data.get("emotion", "neutral")),
        "color": _ensure_int(data.get("color"), default=7829367),  # Default gray
        "custom_emotion_name": data.get("custom_emotion_name"),
        "custom_emotion_color": data.get("custom_emotion_color"),
        "created_at": _ensure_datetime_string(data.get("created_at")),
        "intensity": _ensure_int(data.get("intensity"), min_val=1, max_val=10, default=5),
    }


def validate_breathing_session(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize breathing session data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "pattern": str(data.get("pattern", "Basic Breathing")),
        "rating": _ensure_float(data.get("rating"), min_val=1.0, max_val=5.0, default=3.0),
        "comment": data.get("comment"),  # Can be None
        "created_at": _ensure_datetime_string(data.get("created_at")),
    }


def validate_breathing_pattern(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize breathing pattern data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "name": str(data.get("name", "Unnamed Pattern")),
        "inhale_seconds": _ensure_int(data.get("inhale_seconds"), min_val=1, max_val=30, default=4),
        "hold_seconds": _ensure_int(data.get("hold_seconds"), min_val=0, max_val=30, default=4),
        "exhale_seconds": _ensure_int(data.get("exhale_seconds"), min_val=1, max_val=30, default=4),
        "cycles": _ensure_int(data.get("cycles"), min_val=1, max_val=20, default=4),
        "rest_seconds": _ensure_int(data.get("rest_seconds"), min_val=0, max_val=10, default=0),
    }


def validate_custom_emotion(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize custom emotion data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "name": str(data.get("name", "Custom Emotion")),
        "color": _ensure_int(data.get("color"), default=7829367),  # Default gray
        "created_at": _ensure_datetime_string(data.get("created_at")),
    }


def validate_api_response_list(
    data_list: List[Dict[str, Any]], 
    data_type: str
) -> List[Dict[str, Any]]:
    """Validate a list of API response items"""
    if not isinstance(data_list, list):
        logger.warning(f"Expected list for {data_type}, got {type(data_list)}")
        return []
    
    validated_items = []
    validation_functions = {
        "emotional_record": validate_emotional_record,
        "breathing_session": validate_breathing_session,
        "breathing_pattern": validate_breathing_pattern,
        "custom_emotion": validate_custom_emotion,
    }
    
    validator = validation_functions.get(data_type)
    if not validator:
        logger.warning(f"No validator found for data type: {data_type}")
        return data_list
    
    for item in data_list:
        try:
            if isinstance(item, dict):
                validated_item = validator(item)
                validated_items.append(validated_item)
            else:
                logger.warning(f"Skipping invalid item in {data_type} list: {item}")
        except Exception as e:
            logger.error(f"Error validating {data_type} item: {e}")
            # Skip invalid items rather than failing the entire request
            continue
    
    logger.info(f"Validated {len(validated_items)} out of {len(data_list)} {data_type} items")
    return validated_items


def _ensure_int(
    value: Any, 
    min_val: Optional[int] = None, 
    max_val: Optional[int] = None, 
    default: int = 0
) -> int:
    """Ensure value is an integer with optional range validation"""
    if value is None:
        return default
    
    try:
        if isinstance(value, (int, float)):
            result = int(value)
        else:
            result = int(str(value))
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert to int: {value}, using default: {default}")
        return default
    
    # Apply range validation
    if min_val is not None and result < min_val:
        return min_val
    if max_val is not None and result > max_val:
        return max_val
    
    return result


def _ensure_float(
    value: Any, 
    min_val: Optional[float] = None, 
    max_val: Optional[float] = None, 
    default: float = 0.0
) -> float:
    """Ensure value is a float with optional range validation"""
    if value is None:
        return default
    
    try:
        if isinstance(value, (int, float)):
            result = float(value)
        else:
            result = float(str(value))
    except (ValueError, TypeError):
        logger.warning(f"Failed to convert to float: {value}, using default: {default}")
        return default
    
    # Apply range validation
    if min_val is not None and result < min_val:
        return min_val
    if max_val is not None and result > max_val:
        return max_val
    
    return result


def _ensure_datetime_string(value: Any) -> str:
    """Ensure value is a valid datetime string"""
    if value is None:
        return datetime.now().isoformat()
    
    if isinstance(value, datetime):
        return value.isoformat()
    
    if isinstance(value, str):
        try:
            # Validate that it's a valid datetime string
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return value
        except ValueError:
            logger.warning(f"Invalid datetime string: {value}")
            return datetime.now().isoformat()
    
    logger.warning(f"Cannot convert to datetime string: {value}")
    return datetime.now().isoformat()


def hex_to_int(hex_color: str) -> int:
    """Convert hex color string to integer"""
    if not isinstance(hex_color, str):
        return 7829367  # Default gray
    
    try:
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        return int(hex_color, 16)
    except ValueError:
        logger.warning(f"Invalid hex color: {hex_color}")
        return 7829367  # Default gray


def validate_response_structure(response_data: Any, expected_type: str = "list") -> bool:
    """Validate the overall structure of API responses"""
    if expected_type == "list":
        return isinstance(response_data, list)
    elif expected_type == "dict":
        return isinstance(response_data, dict)
    else:
        return True 