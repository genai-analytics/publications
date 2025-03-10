from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Dict

class OTLPCollectorConfig(BaseModel):
    """
    Configuration model for OTLP Collector integration.

    Attributes:
        endpoint (str): The URL endpoint for OTLP Collector.
        app_name (Optional[str]): The name of the application for tracing purposes. Defaults to None.
        insecure (Optional[bool]): Whether to use an insecure connection. Defaults to True.
        timeout (Optional[int]): The timeout for the connection in seconds. Defaults to 30.
        is_grpc (Optional[bool]): Flag indicating whether to dispatch grpc event. Defaults to False - hence sending HTTPS events.
    """
    endpoint: str = Field(..., description="Endpoint URL for OTLP Collector")
    app_name: Optional[str] = Field(None, description="Application name for tracing")
    insecure: Optional[bool] = Field(False, description="Use insecure connection")
    timeout: Optional[int] = Field(30, description="Timeout in seconds for the connection")
    is_grpc: Optional[bool] = Field(False, description="Is the target collector supporting GRPC")
    headers: Optional[Dict[str, str]] = Field(None, description="Additional HTTP headers to include in requests")
