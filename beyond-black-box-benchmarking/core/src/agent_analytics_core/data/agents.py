from pydantic import Field
from typing import List, Optional, Any
from .iunits import IUnit
from .resources import Resource
from .workflows import Workflow

class Agent(IUnit):
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
