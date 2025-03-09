from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
from otel_genai_agentic_taxonomies.elements import Element, ElementData

class IssueLevel(str, Enum):
    """
    Levels for report.
    """
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"

class Issue(ElementData):
    time: Optional[str] = Field(
        None, description="The time the issue was detected (ISO formatted string)"
    )
    affected_element_ids: List[str] = Field(
        default_factory=list, description="Elements affected by the issue"
    )
    effect: List[str] = Field(
        default_factory=list, description="The effect of the issue on the corresponding element"
    )
    level: IssueLevel = Field(
        default=IssueLevel.WARNING, description="Severity level of the issue"
    )
