from pydantic import Field
from typing import Optional
from elements import Element

class Service(Element):
    name: str = Field(..., alias="service.name", description="The logical name of the service")
    namespace: Optional[str] = Field(None, alias="service.namespace", description="The namespace or grouping of the service")
    instance_id: Optional[str] = Field(None, alias="service.instance.id", description="Unique identifier for the service instance")
    version: Optional[str] = Field(None, alias="service.version", description="The version of the service")
    environment: Optional[str] = Field(None, alias="service.environment", description="The deployment environment (e.g., production, staging)")
    class Config:
        allow_population_by_field_name = True
