from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Union
from enum import Enum
from otel_genai_agentic_taxonomies.elements import Element
from otel_genai_agentic_taxonomies.traces import Event

class AIEvent(Event, Element):
    """
    Represents an OpenTelemetry event capturing the lifecycle stage of an AI element.
    """
    class Status(str, Enum):
        CREATION = "CREATION"
        UPDATE = "UPDATE"
        START = "START"
        END = "END"
        SUSPENSION = "SUSPENSION"
        ABORTION = "ABORTION"
        FAILURE = "FAILURE"
        DELETE = "DELETE"      
    
    status: Optional[Status] = Field(
        None, description="The lifecycle status of the AI element captured by this event"
    )
