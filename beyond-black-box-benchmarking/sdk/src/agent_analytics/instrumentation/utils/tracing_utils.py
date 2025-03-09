import sys
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agent_analytics_core.data.resources import Resource
from agent_analytics_core.data.issues import Issue
from agent_analytics_core.data.events import AIEvent
from agent_analytics_core.data.elements import Element

from functools import wraps
import datetime
import inspect
from enum import Enum
import json

def record_exceptions_decorator(wrapped):
    """Decorator to record exceptions in the current span if available."""

    @wraps(wrapped)
    def wrapper(*args, **kwargs):
        # Get the current span as the potential parent
        current_span = trace.get_current_span()
        
        if current_span.get_span_context().is_valid:
            # Valid parent span exists; record exceptions here
            parent_span = current_span
        else:
            # No valid parent span; create a new span
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(f"{wrapped.__name__}_span") as new_span:
                try:
                    result = wrapped(*args, **kwargs)
                    return result
                except Exception as e:
                    # Record the exception in the new span
                    new_span.record_exception(e)
                    new_span.set_status(Status(StatusCode.ERROR, str(e)))
                    new_span.end()
                    raise
        try:
            result = wrapped(*args, **kwargs)
            return result
        except Exception as e:
            # Record the exception in the current span
            parent_span.record_exception(e)
            parent_span.set_status(Status(StatusCode.ERROR, str(e)))
            parent_span.end()
            raise
    return wrapper

def _get_caller_metadata(): 
    # Get caller function
    #TODO: remove hardcoded 
    caller_frame = inspect.stack()[2]
    caller_filename = caller_frame.filename
    caller_function = caller_frame.function
    return caller_filename, caller_function

def record_exception_in_span(e: Exception):
    # Get the current span
    current_span = trace.get_current_span()

    # Flag to indicate new span creation
    new_span = False 
    # Check if the current span context is valid
    if current_span.get_span_context().is_valid and current_span.is_recording():
        # Get recording sapn
        record_span = current_span
    else:  
        # No valid parent span; create a new span
        # Get caller function 
        caller_filename, caller_function = _get_caller_metadata()
        tracer = trace.get_tracer(caller_filename)
        span_name = f"{caller_function}.ExceptionHandling"
        record_span = tracer.start_span(span_name)
        new_span = True 
    
    # Record the exception in the span
    record_span.record_exception(e)
    record_span.set_status(Status(StatusCode.ERROR, str(e)))
    
    # End the span if it's a new one created within this function
    if new_span:
        record_span.end()

def _prepare_attribute_for_otel(value: Any) -> Any:
    """Helper function to prepare values for OpenTelemetry attributes."""
    if value is None:
        return None
    elif isinstance(value, (str, bool, int, float)):
        return value
    elif isinstance(value, Enum):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, list):
        if all(isinstance(item, (str, bool, int, float)) for item in value):
            return ", ".join(str(item) for item in value)
        else:
            try:
                return json.dumps([_prepare_attribute_for_otel(item) for item in value])
            except (TypeError, ValueError):
                return str(value)
    elif isinstance(value, dict):
        try:
            return json.dumps({k: _prepare_attribute_for_otel(v) for k, v in value.items()})
        except (TypeError, ValueError):
            return str(value)
    else:
        try:
            # Try to convert to dict if it's a Pydantic model
            if hasattr(value, "dict"):
                return json.dumps(value.dict())
            # Otherwise, use default JSON serialization
            return json.dumps(value)
        except (TypeError, ValueError):
            return str(value)

def capture_resource(resource: Resource):
    """Function to capture Resource objects in OpenTelemetry spans."""
    # Get the current span
    current_span = trace.get_current_span()

    # Flag to indicate new span creation
    new_span = False 
    # Check if the current span context is valid
    if current_span.get_span_context().is_valid and current_span.is_recording():
        # Get recording span
        record_span = current_span
    else:  
        # No valid parent span; create a new span
        caller_filename, caller_function = _get_caller_metadata()
        tracer = trace.get_tracer(caller_filename)
        span_name = f"{caller_function}.resource"
        record_span = tracer.start_span(span_name)
        new_span = True

    # Create attributes dictionary
    attributes = {
        "id": resource.id,
        "type": resource.type,
        "owner_id": resource.owner_id,
        "name": resource.name,
        "description": resource.description,
        "category": str(resource.category) if resource.category else None,
        "format": resource.format
    }
    
    # Handle tags
    if resource.tags:
        attributes["tags"] = _prepare_attribute_for_otel(resource.tags)
    
    # Handle payload - use json.dumps specifically for payload
    try:
        attributes["payload"] = json.dumps(resource.payload) if resource.payload is not None else None
    except (TypeError, ValueError):
        attributes["payload"] = str(resource.payload) if resource.payload is not None else None
    
    # Handle attributes dictionary
    if resource.attributes:
        for key, value in resource.attributes.items():
            attributes[f"attr_{key}"] = _prepare_attribute_for_otel(value)
    
    # Filter out None values
    attributes = {k: v for k, v in attributes.items() if v is not None}

    record_span.add_event(
        name=f"{resource.name}.resource",
        attributes=attributes
    )
    
    # End the span if it's a new one created within this function
    if new_span:
        record_span.end()

def capture_issue(issue: Issue):
    """Function to capture Issue objects in OpenTelemetry spans."""
    # Get the current span
    current_span = trace.get_current_span()

    # Flag to indicate new span creation
    new_span = False 
    # Check if the current span context is valid
    if current_span.get_span_context().is_valid and current_span.is_recording():
        # Get recording span
        record_span = current_span
    else:  
        # No valid parent span; create a new span
        caller_filename, caller_function = _get_caller_metadata()
        tracer = trace.get_tracer(caller_filename)
        span_name = f"{caller_function}.issue"
        record_span = tracer.start_span(span_name)
        new_span = True

    # Create attributes dictionary
    attributes = {
        "level": str(issue.level),
        "time": issue.time or datetime.now().isoformat(),
        "affected_element_ids": _prepare_attribute_for_otel(issue.affected_element_ids),
        "effect": _prepare_attribute_for_otel(issue.effect)
    }
    
    # Get any other attributes from the ElementData base class
    if hasattr(issue, "dict"):
        for key, value in issue.dict().items():
            if key not in attributes and key not in ["affected_element_ids", "effect", "level", "time"]:
                attributes[key] = _prepare_attribute_for_otel(value)
    
    # Filter out None values
    attributes = {k: v for k, v in attributes.items() if v is not None}

    record_span.add_event(
        name=f"{issue.name if issue.name else issue.id}.issue",
        attributes=attributes
    )
    
    # End the span if it's a new one created within this function
    if new_span:
        record_span.end()

def capture_ai_event(ai_event: AIEvent):
    """Function to capture AIEvent objects in OpenTelemetry spans."""
    # Get the current span
    current_span = trace.get_current_span()

    # Flag to indicate new span creation
    new_span = False 
    # Check if the current span context is valid
    if current_span.get_span_context().is_valid and current_span.is_recording():
        # Get recording span
        record_span = current_span
    else:  
        # No valid parent span; create a new span
        caller_filename, caller_function = _get_caller_metadata()
        tracer = trace.get_tracer(caller_filename)
        span_name = f"{caller_function}.ai_event"
        record_span = tracer.start_span(span_name)
        new_span = True

    # Create attributes dictionary starting with core fields
    attributes = {
        "id": ai_event.id,
        "type": ai_event.type,
        "status": str(ai_event.status) if ai_event.status else None,
        "name": ai_event.name,
        "owner_id": ai_event.owner_id,
        "description": ai_event.description
    }
    
    # Handle Event specific fields
    if hasattr(ai_event, "timestamp") and ai_event.timestamp:
        attributes["event_timestamp"] = _prepare_attribute_for_otel(ai_event.timestamp)
    
    # Handle tags
    if ai_event.tags:
        attributes["tags"] = _prepare_attribute_for_otel(ai_event.tags)
    
    # Handle Element attributes dictionary
    if ai_event.attributes:
        for key, value in ai_event.attributes.items():
            attributes[f"attr_{key}"] = _prepare_attribute_for_otel(value)
    
    # Handle Event attributes dictionary (from Event base class)
    event_attr_dict = getattr(ai_event, "attributes", {})
    if event_attr_dict and event_attr_dict != ai_event.attributes:  # Avoid duplicate processing
        for key, value in event_attr_dict.items():
            attributes[f"event_attr_{key}"] = _prepare_attribute_for_otel(value)
    
    # Filter out None values
    attributes = {k: v for k, v in attributes.items() if v is not None}

    record_span.add_event(
        name=f"{ai_event.name}.ai_event",
        attributes=attributes
    )
    
    # End the span if it's a new one created within this function
    if new_span:
        record_span.end()
