from pydantic import Field
from typing import List, Optional, Any
from otel_genai_agentic_taxonomies.iunits import IUnit, IUnitData
from otel_genai_agentic_taxonomies.resources import Resource
from otel_genai_agentic_taxonomies.workflows import Workflow, Runnable

class Agent(IUnitData):
    resource_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="List of resource IDs that can be used by the agent."
    )
    tool_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="List of tools identifiers that can be used by the agent."
    )
    skill_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="List of runnable skill identifiers possessed by the agent."
    )
