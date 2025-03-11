from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
from .elements import Element

class RecommendationLevel(str, Enum):
    """
    Levels of impact.
    """
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"

class Recommendation(Element):
    generated_time: Optional[str] = Field(
        None, description="The time the recommendation was detected (ISO formatted string)"
    )
    affected_element_ids: List[str] = Field(
        default_factory=list, description="Elements affected by the recommendation"
    )
    effect: List[str] = Field(
        default_factory=list, description="The effect of the recommendation on the corresponding element"
    )
    level: RecommendationLevel = Field(
        default=RecommendationLevel.MODERATE, description="Severity level of the recommendation"
    )
