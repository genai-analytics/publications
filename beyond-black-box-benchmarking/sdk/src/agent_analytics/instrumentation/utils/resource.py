from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
from enum import Enum
from datetime import datetime


class ResourceCategory(str, Enum):
    TEMPLATE = "TEMPLATE"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    CODE = "CODE"
    ENCODING = "ENCODING"
    FILE = "FILE"
    DB = "DB"


AttributeValue = Union[str, bool, int, float, List[Union[str, bool, int, float]]]


class ResourceData(BaseModel):
    """ResourceData class that inherits from BaseModel"""
    category: Union[ResourceCategory, str] = Field(
        None, description="Type of the resource. E.g. IMAGE, TEMPLATE"
    )
    format: Optional[str] = Field(
        None, description="Format of the resource. E.g. CSV, PDF"
    )
    payload: AttributeValue = Field(
        None, description="The actual serialized content (payload) of the resource."
    )
    
    def to_json(self, indent: int = 2, sort_keys: bool = True) -> str:
        return self.model_dump_json(indent=indent, sort_keys=sort_keys)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ResourceData":
        return cls.model_validate_json(json_str)
    
    def __str__(self) -> str:
        return self.to_json(indent=2)


class Resource(BaseModel):
    """Resource class that contains ResourceData"""
    _data: ResourceData = Field(
        description='The internal data representing the resource'
    )
    
    def __init__(
        self, 
        category: Union[ResourceCategory, str] = None,
        format: Optional[str] = None,
        payload: AttributeValue = None,
        _data: Optional[ResourceData] = None, 
        **data
    ):
        """
        Initialize a Resource object.
        
        Args:
            category: Type of the resource (e.g., IMAGE, TEXT)
            format: Format of the resource (e.g., CSV, PDF)
            payload: The actual serialized content of the resource
            _data: A pre-built ResourceData object (optional)
            **data: Additional data for BaseModel
        """
        # If _data is provided, use it directly
        if _data is not None:
            super().__init__(_data=_data, **data)
        # Otherwise, create a new ResourceData from attributes
        else:
            resource_data = ResourceData(
                category=category,
                format=format,
                payload=payload
            )
            super().__init__(_data=resource_data, **data)
    
    @property
    def category(self) -> Union[ResourceCategory, str]:
        return self._data.category
    
    @property
    def format(self) -> Optional[str]:
        return self._data.format
    
    @property
    def payload(self) -> Any:
        """Can later be replaced with an object properly representing the data."""
        return self._data.payload