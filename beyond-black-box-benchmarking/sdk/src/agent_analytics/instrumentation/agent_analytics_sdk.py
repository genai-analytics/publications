import os
import json
import uuid
import inspect
import re
import platform
import sys
from typing import Optional, Dict, Any, Union 
from enum import Enum

from dotenv import load_dotenv
load_dotenv()

from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
# Get Agent Analytics extended frameworks
from .traceloop.sdk import Traceloop

from .configs import OTLPCollectorConfig



class agent_analytics_sdk:
    """
    A namespace to handle initialization and configuration of logging and tracing
    for different tracer types.

    Attributes:
        SUPPORTED_TRACER_TYPES (list): Supported tracer types for the SDK.
    """
    class SUPPORTED_TRACER_TYPES(Enum):
        LOG=1
        REMOTE=2

    @staticmethod
    def get_logs_dir_and_filename(logs_dir_path: str = None, log_filename: str = None):
        """
        Get the directory and filename for log files.

        If not provided, the directory defaults to a "log" folder in the caller's directory,
        and the filename defaults to the caller's file name.

        Args:
            logs_dir_path (str, optional): Custom path for the logs directory.
            log_filename (str, optional): Custom name for the log file.

        Returns:
            tuple: A tuple containing the log directory path and the log filename.

        Example:
            logs_dir, log_file = agent_analytics_sdk.get_logs_dir_and_filename()
        """
        # Get the caller's file information (two frames up in the stack)
        try: 
            caller_frame = inspect.stack()[2]
            caller_file_path = os.path.abspath(caller_frame.filename)
            caller_dir = os.path.dirname(caller_file_path)
            caller_file_name = os.path.splitext(os.path.basename(caller_file_path))[0]
        except Exception as e: 
            caller_dir = os.getcwd()
            caller_file_name = "default"          

        logs_dir_path = logs_dir_path if logs_dir_path else os.path.join(caller_dir, "log")

        if not os.path.exists(logs_dir_path):
            os.makedirs(logs_dir_path)

        log_filename = f"{log_filename}.log" if log_filename else f"{caller_file_name}_otel.log"

        return logs_dir_path, log_filename

    @staticmethod
    def initialize_logging(tracer_type: SUPPORTED_TRACER_TYPES = SUPPORTED_TRACER_TYPES.LOG, 
                           logs_dir_path: str = None, log_filename: str = None, 
                           config: OTLPCollectorConfig = None, resource_attributes: dict = {}):
        """
        Initialize logging for the specified tracer type.

        Supports "log" and "instana" tracer types. Each type initializes
        logging with its respective configuration.

        Args:
            tracer_type (str, optional): Type of tracer to initialize (default is "log").
            logs_dir_path (str, optional): Custom path for the logs directory.
            log_filename (str, optional): Custom name for the log file.
            config (TraceloopInstanaConfig, optional): Configuration
                object specific to the tracer type.

        Returns:
            Any: The exporter object initialized for the tracer type.

        Raises:
            ValueError: If an unsupported tracer type is specified or if required
                        configuration is missing.

        Example:
            exporter = agent_analytics_sdk.initialize_logging(
                tracer_type="log", log_filename="example"
            )
        """
        if tracer_type not in agent_analytics_sdk.SUPPORTED_TRACER_TYPES:
            raise ValueError(f"Unsupported tracer type: {tracer_type}")

        exporter = None
        
        if not config or not config.app_name:
            machine_name = platform.node()
            user_name = re.split(r'\W+', machine_name)[0]
            script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
            app_name = f"{user_name}_{script_name}"
        else:
            app_name = config.app_name

        # disable traceloop telemetry
        os.environ['TRACELOOP_TELEMETRY'] = "false"

        if tracer_type == agent_analytics_sdk.SUPPORTED_TRACER_TYPES.LOG:
            logs_dir_path, log_filename = agent_analytics_sdk.get_logs_dir_and_filename(logs_dir_path, log_filename)
            traceloop_log_file_path = os.path.join(logs_dir_path, log_filename)
            traceloop_log_file = open(traceloop_log_file_path, "w")
            exporter = ConsoleSpanExporter(out=traceloop_log_file)
            Traceloop.init(
                disable_batch=True, 
                exporter=exporter,
                app_name=app_name, 
                resource_attributes=resource_attributes,
            )
            print(f"logging initialized in {traceloop_log_file_path}")

        elif tracer_type == agent_analytics_sdk.SUPPORTED_TRACER_TYPES.REMOTE:
            if not isinstance(config, OTLPCollectorConfig):
                raise ValueError("For remote tracing, a OTLPCollectorConfig object must be provided as config")

            if not config.endpoint:
                raise ValueError("Endpoint must be provided in OTLPCollectorConfig.")      

            if config.is_grpc:
                exporter = GRPCSpanExporter(
                    endpoint=config.endpoint,
                    timeout=config.timeout,
                    insecure=config.insecure,
                    headers=config.headers or {} 
                )
            else:
                exporter = HTTPSpanExporter(
                    endpoint=config.endpoint,
                    timeout=config.timeout,
                    headers=config.headers or {}  
                )

            Traceloop.init(
                disable_batch=True, 
                app_name=app_name, 
                exporter=exporter,
                resource_attributes=resource_attributes,
            )
            print(f"{tracer_type} logging initialized. App name: {app_name}")

        else:
            raise ValueError(f"Unsupported tracer type: {tracer_type}")

        return exporter