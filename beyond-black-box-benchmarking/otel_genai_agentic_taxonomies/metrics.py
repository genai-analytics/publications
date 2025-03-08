from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
from otel_genai_agentic_taxonomies.elements import Element

class MetricCategory(str, Enum):
    """
    Levels for report.
    """
    PERFORMANCE = "CRITICAL"
    QUALITY = "ERROR"
    COST = "WARNING"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"
    SECURITY = "SECURITY"
    INFO = "INFO"
    DEBUG = "DEBUG"

class Metric(Element):
    generation_time: Optional[str] = Field(
        None, description="The time the metric was calculated (ISO formatted string)"
    )
    affected_element_id: str = Field(
       ..., description="Element affected by the metric"
    )
    value: float = Field(
       ..., description="The value associated with the metric"
    )
    units: str = Field(
       ..., description="The units of the metric value"
    )
    confidence: Optional[float] = Field(
       ..., description="The confidence in the provided value"
    ) 
    category: MetricCategory = Field(
        default=MetricCategory.INFO, description="Severity level of the issue"
    )  

