import json
from pydantic import Field
from typing import List, Any, Dict, Union, Optional
from enum import Enum
from .elements import Element, AttributeValue
from .iunits import IUnit, Relation, Relation


# ---------------------------------------------------------------------------
# Edge
class WorkflowEdgeCategory(str, Enum):
    ENTER = "ENTER"
    EXIT = "EXIT"
    JOIN = "JOIN"
    FORK = "FORK"
    SEQUENTIAL = "SEQUENTIAL"

class WorkflowEdge(Relation):
    is_conditional: bool = Field(False, description="Indicates if the control flow is conditionally triggered.")
    category: WorkflowEdgeCategory = Field(WorkflowEdgeCategory.SEQUENTIAL, description="Indicates if the control flow is conditionally triggered.")    

class WorkflowNode(IUnit):
    task_counter: Optional[int] = Field(0, description="Identifier of the associated workflow if exists")
    runnable_id: str = Field(..., description="Identifier of the associated runnable element")

class Workflow(Element):
    type: str = Field(default="Workflow", description="Workfllow element")

# ---------------------------------------------------------------------------
# Runnable

class Runable(IUnit):
    input_schema: Optional[str] = Field(None, description="Stringified input parameters JSON Schema")
    output_schema: Optional[str] = Field(None, description="Stringified output parameters JSON Schema")
    workflow_id: Optional[str] = Field(None, description="Identifier of the associated workflow if exists")
    task_counter: Optional[int] = Field(0, description="Identifier of the associated workflow if exists")

