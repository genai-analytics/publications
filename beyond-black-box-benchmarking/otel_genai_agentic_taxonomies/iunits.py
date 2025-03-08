from pydantic import Field
from typing import List, Any, Dict, Union, Optional
from enum import Enum
import json
from otel_genai_agentic_taxonomies.elements import Element  
from otel_genai_agentic_taxonomies.resources import Resource  

class IUnit(Element):
    """
    Intelligent Unit (IUnit) is an element reflecting the non-deterministic nature of agentic systems.
    """
    code_id: Optional[str] = Field(
        None, description="The code identifier of the unit, if exists. E,g.: module.class.method name"
    )
    is_generated: bool = Field(
        None, description="Reflects if the unit is dynamically generated e.g. by GenAI"
    )
    consumed_resources: Optional[List[str]] = Field(
        None, description="List of resource IDs consumed by the unit"
    )

class Relation(Element):
    source_ids: Optional[List[str]] = Field(
        None, description="Optional list of source intelligent units IDs."
    )
    destination_ids: Optional[List[str]] = Field(
        None, description="Optional list of destination intelligent units IDs."
    )
    weight: Optional[int] = Field(
        None, description="The weight associated with the relation."
    )

