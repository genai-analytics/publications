from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Any, Tuple, Dict
from enum import Enum
from otel_genai_agentic_taxonomies.iunits import Relation
from otel_genai_agentic_taxonomies.agents import Agent

class Role(Relation):
    """
    Represents a role within the organization.
    
    Attributes:
        name: The name of the role.
        description: A brief description of the role.
        sources: Includes the organization ID  
        destinations: Includes the role to its intelligent unit.
        max_instances: Maximum number of simultaneous instances allowed for this role.
    """
    instructions: Optional[List[str]] = Field(
        None, description="List of instructions the agent should follow."
    )

class Organization(Agent):

    roles: List[Role] = Field(
        None, description="List of roles defined for the intelligent unit."
    )

