"""
Data Validation for API Responses
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validate_emotional_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate emotional record data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "source": str(data.get("source", "manual")),
        "description": str(data.get("description", "")),
        "emotion": str(data.get("emotion", "neutral")),
        "color": int(data.get("color", 7829367)),
        "custom_emotion_name": data.get("custom_emotion_name"),
        "custom_emotion_color": data.get("custom_emotion_color"),
        "created_at": str(data.get("created_at", datetime.now().isoformat())),
        "intensity": max(1, min(10, int(data.get("intensity", 5)))),
    }


def validate_breathing_session(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate breathing session data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "pattern": str(data.get("pattern", "Basic Breathing")),
        "rating": max(1.0, min(5.0, float(data.get("rating", 3.0)))),
        "comment": data.get("comment"),
        "created_at": str(data.get("created_at", datetime.now().isoformat())),
    }


def validate_breathing_pattern(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate breathing pattern data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "name": str(data.get("name", "Unnamed Pattern")),
        "inhale_seconds": max(1, min(30, int(data.get("inhale_seconds", 4)))),
        "hold_seconds": max(0, min(30, int(data.get("hold_seconds", 4)))),
        "exhale_seconds": max(1, min(30, int(data.get("exhale_seconds", 4)))),
        "cycles": max(1, min(20, int(data.get("cycles", 4)))),
        "rest_seconds": max(0, min(10, int(data.get("rest_seconds", 0)))),
    }


def validate_custom_emotion(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate custom emotion data"""
    return {
        "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
        "name": str(data.get("name", "Custom Emotion")),
        "color": int(data.get("color", 7829367)),
        "created_at": str(data.get("created_at", datetime.now().isoformat())),
    }


def validate_response_list(data_list: List[Dict[str, Any]], data_type: str) -> List[Dict[str, Any]]:
    """Validate a list of responses"""
    if not isinstance(data_list, list):
        return []
    
    validators = {
        "emotional_record": validate_emotional_record,
        "breathing_session": validate_breathing_session,
        "breathing_pattern": validate_breathing_pattern,
        "custom_emotion": validate_custom_emotion,
    }
    
    validator = validators.get(data_type)
    if not validator:
        return data_list
    
    validated_items = []
    for item in data_list:
        try:
            if isinstance(item, dict):
                validated_items.append(validator(item))
        except Exception as e:
            logger.error(f"Error validating {data_type}: {e}")
            continue
    
    return validated_items 