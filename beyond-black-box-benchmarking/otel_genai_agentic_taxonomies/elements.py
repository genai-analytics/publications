from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any, Union
from enum import Enum

AttributeValue = Union[str, bool, int, float, List[Union[str, bool, int, float]]]

class Tag(str, Enum):
    GENERAL = "GENERAL"
    VALIDATION = "VALIDATION"
    ROUTING = "ROUTING"
    MANAGING = "MANAGING"
    DECOMPOSITION = "DECOMPOSITION"
    LLM = "LLM"
    TOOLS = "TOOLS"
    CODING = "CODING"
    SUMMARIZATION = "SUMMARIZATION"
    RETRIEVAL = "RETRIEVAL"
    PROMPTING = "PROMPTING"
    CONTENT = "CONTENT"
    CONVERSATIONAL = "CONVERSATIONAL"
    QNA = "QNA"
    CLASSIFICATION = "CLASSIFICATION"
    TRANSLATION = "TRANSLATION"
    IMAGING = "IMAGING"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"

class Element(BaseModel):
    # Element is used to store data associated with the elements in the persistency layer
    id: str = Field(description="The unique identifier of the data element")
    type: str = Field(description="The type of the element")    
    owner_id: Optional[str] = Field(
        description="The identifier of the owner data element", default=None
    )
    name: Optional[str] = Field(description="The display name of the data element", default=None)
    description: Optional[str] = Field(
        description="Description of the data element in natural language", default=None
    )
    tags: Optional[List[Union[Tag,str]]] = Field(
        None, description="The tags that can be used to classify the data element"
    )
    attributes: dict[str, AttributeValue] = Field(
        description="A dictionary of data element specific fields", default_factory=dict
    )
    