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

def _get_caller_metadata(): 
    # Get caller function
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
