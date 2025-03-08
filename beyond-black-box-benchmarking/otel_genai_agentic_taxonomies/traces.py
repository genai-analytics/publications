from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Union
from enum import Enum
from otel_genai_agentic_taxonomies.elements import Element, AttributeValue

# --- Supporting Models ---

class SpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"

class Event(BaseModel):
    name: str
    timestamp: datetime
    attributes: Optional[Dict[str, AttributeValue]] = Field(default_factory=dict)

class Context(BaseModel):
    trace_id: str = Field(..., description="Unique identifier for the trace.")
    span_id: str = Field(..., description="Unique identifier for the span.")
    trace_state: List[AttributeValue] = Field(default_factory=list, description="List of state attributes.")

class Link(BaseModel):
    trace_id: str
    span_id: str
    attributes: Optional[Dict[str, AttributeValue]] = Field(default_factory=dict)

# --- Data Classes ---

class Span(Element):
    context: Context = Field(..., description="The context of the trace.")
    parent_id: Optional[str] = Field(None, description="Identifier of the parent span, if any.")
    name: str = Field(..., description="Name of the span.")
    kind: SpanKind = Field(SpanKind.INTERNAL, description="The kind of span (e.g., internal, server, client).")
    start_time: datetime = Field(..., description="Timestamp marking the start of the span.")
    end_time: Optional[datetime] = Field(None, description="Timestamp marking the end of the span.")
    attributes: Dict[str, AttributeValue] = Field(default_factory=dict, description="Key-value pairs representing span attributes.")
    events: List[Event] = Field(default_factory=list, description="List of events recorded during the span.")
    links: List[Link] = Field(default_factory=list, description="Links to other spans in the trace.")

class Trace(Element):
    service_name: str = Field(..., description="The name of the associated service")
    start_time: datetime = Field(..., description="Start time of the trace")
    end_time: Optional[datetime] = Field(None, description="End time of the trace")

class TraceGroup(Element):
    traces_ids: List[str] = Field(..., description="List of trace IDs associated with the group")

