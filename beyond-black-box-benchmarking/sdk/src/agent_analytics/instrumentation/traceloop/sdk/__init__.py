import os
import sys
from pathlib import Path

from typing import Optional, Set
from colorama import Fore
from opentelemetry.sdk.trace import SpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.sdk.metrics.export import MetricExporter
from opentelemetry.sdk._logs.export import LogExporter
from opentelemetry.sdk.resources import SERVICE_NAME
from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry.util.re import parse_env_headers

from traceloop.sdk.images.image_uploader import ImageUploader
from traceloop.sdk.metrics.metrics import MetricsWrapper
from traceloop.sdk.logging.logging import LoggerWrapper
from traceloop.sdk.telemetry import Telemetry
# Use our instruments 
# from traceloop.sdk.instruments import Instruments
from .instruments import Instruments

from traceloop.sdk.config import (
    is_content_tracing_enabled,
    is_tracing_enabled,
    is_metrics_enabled,
    is_logging_enabled,
)
from traceloop.sdk.fetcher import Fetcher
# Use our tracing 
# from traceloop.sdk.tracing.tracing import (
#     TracerWrapper,
#     set_association_properties,
#     set_external_prompt_tracing_context,
# )
from .tracing.tracing import (
    TracerWrapper,
    set_association_properties,
    set_external_prompt_tracing_context,
)

from typing import Dict


class Traceloop:
    AUTO_CREATED_KEY_PATH = str(
        Path.home() / ".cache" / "traceloop" / "auto_created_key"
    )
    AUTO_CREATED_URL = str(Path.home() / ".cache" / "traceloop" / "auto_created_url")

    __tracer_wrapper: TracerWrapper
    __fetcher: Fetcher = None

    @staticmethod
    def init(
        app_name: Optional[str] = sys.argv[0],
        api_endpoint: str = "https://api.traceloop.com",
        api_key: str = None,
        headers: Dict[str, str] = {},
        disable_batch=False,
        exporter: SpanExporter = None,
        metrics_exporter: MetricExporter = None,
        metrics_headers: Dict[str, str] = None,
        logging_exporter: LogExporter = None,
        logging_headers: Dict[str, str] = None,
        processor: SpanProcessor = None,
        propagator: TextMapPropagator = None,
        traceloop_sync_enabled: bool = False,
        should_enrich_metrics: bool = True,
        resource_attributes: dict = {},
        instruments: Optional[Set[Instruments]] = None,
        image_uploader: Optional[ImageUploader] = None,
    ) -> None:
        Telemetry()

        api_endpoint = os.getenv("TRACELOOP_BASE_URL") or api_endpoint
        api_key = os.getenv("TRACELOOP_API_KEY") or api_key

        if (
            traceloop_sync_enabled
            and api_endpoint.find("traceloop.com") != -1
            and api_key
            and not exporter
            and not processor
        ):
            Traceloop.__fetcher = Fetcher(base_url=api_endpoint, api_key=api_key)
            Traceloop.__fetcher.run()
            print(
                Fore.GREEN + "Traceloop syncing configuration and prompts" + Fore.RESET
            )

        if not is_tracing_enabled():
            print(Fore.YELLOW + "Tracing is disabled" + Fore.RESET)
            return

        enable_content_tracing = is_content_tracing_enabled()

        if exporter or processor:
            print(Fore.GREEN + "Traceloop exporting traces to a custom exporter")

        headers = os.getenv("TRACELOOP_HEADERS") or headers

        if isinstance(headers, str):
            headers = parse_env_headers(headers)

        if (
            not exporter
            and not processor
            and api_endpoint == "https://api.traceloop.com"
            and not api_key
        ):
            print(
                Fore.RED
                + "Error: Missing Traceloop API key,"
                + " go to https://app.traceloop.com/settings/api-keys to create one"
            )
            print("Set the TRACELOOP_API_KEY environment variable to the key")
            print(Fore.RESET)
            return

        if not exporter and not processor and headers:
            print(
                Fore.GREEN
                + f"Traceloop exporting traces to {api_endpoint}, authenticating with custom headers"
            )

        if api_key and not exporter and not processor and not headers:
            print(
                Fore.GREEN
                + f"Traceloop exporting traces to {api_endpoint} authenticating with bearer token"
            )
            headers = {
                "Authorization": f"Bearer {api_key}",
            }

        print(Fore.RESET)

        # Tracer init
        resource_attributes.update({SERVICE_NAME: app_name})
        TracerWrapper.set_static_params(
            resource_attributes, enable_content_tracing, api_endpoint, headers
        )
        Traceloop.__tracer_wrapper = TracerWrapper(
            disable_batch=disable_batch,
            processor=processor,
            propagator=propagator,
            exporter=exporter,
            should_enrich_metrics=should_enrich_metrics,
            image_uploader=image_uploader or ImageUploader(api_endpoint, api_key),
            instruments=instruments,
        )

        if not is_metrics_enabled() or not metrics_exporter and exporter:
            print(Fore.YELLOW + "Metrics are disabled" + Fore.RESET)
        else:
            metrics_endpoint = os.getenv("TRACELOOP_METRICS_ENDPOINT") or api_endpoint
            metrics_headers = (
                os.getenv("TRACELOOP_METRICS_HEADERS") or metrics_headers or headers
            )
            if metrics_exporter or processor:
                print(Fore.GREEN + "Traceloop exporting metrics to a custom exporter")

            MetricsWrapper.set_static_params(
                resource_attributes, metrics_endpoint, metrics_headers
            )
            Traceloop.__metrics_wrapper = MetricsWrapper(exporter=metrics_exporter)

        if is_logging_enabled() and (logging_exporter or not exporter):
            logging_endpoint = os.getenv("TRACELOOP_LOGGING_ENDPOINT") or api_endpoint
            logging_headers = (
                os.getenv("TRACELOOP_LOGGING_HEADERS") or logging_headers or headers
            )
            if logging_exporter or processor:
                print(Fore.GREEN + "Traceloop exporting logs to a custom exporter")

            LoggerWrapper.set_static_params(
                resource_attributes, logging_endpoint, logging_headers
            )
            Traceloop.__logger_wrapper = LoggerWrapper(exporter=logging_exporter)

    def set_association_properties(properties: dict) -> None:
        set_association_properties(properties)

    def set_prompt(template: str, variables: dict, version: int):
        set_external_prompt_tracing_context(template, variables, version)

    def report_score(
        association_property_name: str,
        association_property_id: str,
        score: float,
    ):
        if not Traceloop.__fetcher:
            print(
                Fore.RED
                + "Error: Cannot report score. Missing Traceloop API key,"
                + " go to https://app.traceloop.com/settings/api-keys to create one"
            )
            print("Set the TRACELOOP_API_KEY environment variable to the key")
            print(Fore.RESET)
            return

        Traceloop.__fetcher.post(
            "score",
            {
                "entity_name": f"traceloop.association.properties.{association_property_name}",
                "entity_id": association_property_id,
                "score": score,
            },
        )