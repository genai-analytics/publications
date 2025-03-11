import json

from importlib_metadata import version as v
#from langtrace.trace_attributes import FrameworkSpanAttributes
from opentelemetry import baggage
from opentelemetry.trace import Span, SpanKind, Tracer
from opentelemetry.trace.status import Status, StatusCode

from langtrace_python_sdk.constants import LANGTRACE_SDK_NAME
from langtrace_python_sdk.constants.instrumentation.common import (
    LANGTRACE_ADDITIONAL_SPAN_ATTRIBUTES_KEY,
    SERVICE_PROVIDERS,
)
from langtrace_python_sdk.utils import set_span_attribute
from langtrace_python_sdk.utils.llm import get_span_name, set_span_attributes
from langtrace_python_sdk.utils.misc import serialize_args, serialize_kwargs

from .utils import is_crew_kickoff

def patch_memory(operation_name, version, tracer: Tracer):
    def traced_method(wrapped, instance, args, kwargs):
        service_provider = SERVICE_PROVIDERS["CREWAI"]
        extra_attributes = baggage.get_baggage(LANGTRACE_ADDITIONAL_SPAN_ATTRIBUTES_KEY)
        span_attributes = {
            "service.name": service_provider,
            "service.type": "framework",
            "service.version": version,
            **(extra_attributes if extra_attributes is not None else {}),
        }

        inputs = {}
        if len(args) > 0:
            inputs["args"] = serialize_args(*args)
        if len(kwargs) > 0:
            inputs["kwargs"] = serialize_kwargs(**kwargs)
        span_attributes["crewai.memory.storage.rag_storage.inputs"] = json.dumps(inputs)

        # attributes = FrameworkSpanAttributes(**span_attributes)
        attributes = span_attributes
        with tracer.start_as_current_span(
            get_span_name(operation_name), kind=SpanKind.CLIENT
        ) as span:

            try:
                set_span_attributes(span, attributes)
                result = wrapped(*args, **kwargs)
                if result is not None and len(result) > 0:
                    set_span_attribute(
                        span, "crewai.memory.storage.rag_storage.outputs", str(result)
                    )
                if result:
                    span.set_status(Status(StatusCode.OK))
                return result

            except Exception as err:
                # Record the exception in the span
                span.record_exception(err)

                # Set the span status to indicate an error
                span.set_status(Status(StatusCode.ERROR, str(err)))

                # Reraise the exception to ensure it's not swallowed
                raise

    return traced_method


def patch_crew(operation_name, version, tracer: Tracer):
    def traced_method(wrapped, instance, args, kwargs):
        service_provider = SERVICE_PROVIDERS["CREWAI"]
        extra_attributes = baggage.get_baggage(LANGTRACE_ADDITIONAL_SPAN_ATTRIBUTES_KEY)
        span_attributes = {
            "service.name": service_provider,
            "service.type": "framework",
            "service.version": version,
            **(extra_attributes if extra_attributes is not None else {}),
        }

        # attributes = FrameworkSpanAttributes(**span_attributes)
        attributes = span_attributes
        with tracer.start_as_current_span(
            get_span_name(operation_name), kind=SpanKind.CLIENT
        ) as span:
            try:
                # Add crew creation span on crew.kickoff 
                if is_crew_kickoff(operation_name):
                    on_crew_creation_span(tracer, instance)

                set_span_attributes(span, attributes)
                CrewAISpanAttributes(span=span, instance=instance)
                result = wrapped(*args, **kwargs)
                if result:
                    class_name = instance.__class__.__name__
                    span.set_attribute(
                        f"crewai.{class_name.lower()}.result", str(result)
                    )
                    span.set_status(Status(StatusCode.OK))
                    if class_name == "Crew":
                        for attr in ["tasks_output", "token_usage", "usage_metrics"]:
                            if hasattr(result, attr):
                                span.set_attribute(
                                    f"crewai.crew.{attr}", str(getattr(result, attr))
                                )
                return result

            except Exception as err:
                # Record the exception in the span
                span.record_exception(err)

                # Set the span status to indicate an error
                span.set_status(Status(StatusCode.ERROR, str(err)))

                # Reraise the exception to ensure it's not swallowed
                raise

    return traced_method

# TODO: Implement
# Work in progress 
def patch_tool(operation_name, version, tracer: Tracer):
    def traced_method(wrapped, instance, args, kwargs):
        service_provider = SERVICE_PROVIDERS["CREWAI"]
        extra_attributes = baggage.get_baggage(LANGTRACE_ADDITIONAL_SPAN_ATTRIBUTES_KEY)

        # Tool attributes based on langchain implementation with traceloop
        # TODO: remove hardcoded names 
        tool_attributes = {
            "traceloop.entity.name": str(instance.name),
            "traceloop.entity.input": json.dumps(kwargs)
        }

        span_attributes = {
            "service.name": service_provider,
            "service.type": "framework",
            "service.version": version,
            **(extra_attributes if extra_attributes is not None else {}),
            **(tool_attributes if tool_attributes is not None else {})
        }

        # attributes = FrameworkSpanAttributes(**span_attributes)

        attributes = span_attributes
        with tracer.start_as_current_span(
            f"{instance.name}.tool", kind=SpanKind.CLIENT
        ) as span:

            try:
                set_span_attributes(span, attributes)
                # No need, there is no tool specific implementation 
                # CrewAISpanAttributes(span=span, instance=instance)
                result = wrapped(*args, **kwargs)                
                output = ""
                if result:
                    span.set_status(Status(StatusCode.OK))
                    try:
                        output = json.dumps(result)
                    except: 
                        output = str(result)

                # add hardcoded output attribute
                set_span_attribute(
                        span, "traceloop.entity.output", output
                    )
                return result

            except Exception as err:
                # Record the exception in the span
                span.record_exception(err)

                # Set the span status to indicate an error
                span.set_status(Status(StatusCode.ERROR, str(err)))

                # Reraise the exception to ensure it's not swallowed
                raise

    return traced_method

class CrewAISpanAttributes:
    span: Span
    crew: dict

    def __init__(self, span: Span, instance) -> None:
        self.span = span
        self.instance = instance
        self.crew = {
            "crew_tasks": [],
            "crew_agents": [],
            "crew_number_of_agents": None,
            "crew_number_of_tasks": None, 
            "crew_process": None,
            "crew_key": None, 
            "crew_id": None,
            "crew_memory": None
        }

        self.run()

    def run(self):
        instance_name = self.instance.__class__.__name__
        if instance_name == "Crew":
            self.set_crew_attributes()
            for key, value in self.crew.items():
                key = f"{key}"
                if value is not None:
                    set_span_attribute(
                        self.span, key, json.dumps(value) if isinstance(value, list) else value
                    )

        elif instance_name == "Agent":
            agent = self.set_agent_attributes()
            for key, value in agent.items():
                key = f"crewai.agent.{key}"
                if value is not None:
                    set_span_attribute(
                        self.span, key, str(value) if isinstance(value, list) else value
                    )

        elif instance_name == "Task":
            task = self.set_task_attributes()
            for key, value in task.items():
                key = f"crewai.task.{key}"
                if value is not None:
                    set_span_attribute(
                        self.span, key, str(value) if isinstance(value, list) else value
                    )

    def set_crew_attributes(self):
        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            if key == "tasks":
                self._parse_tasks(value)
            elif key == "agents":
                self._parse_agents(value)
            elif key == "process":
                self.crew["crew_process"] = str(value).split(".")[-1]
            elif key == "id": 
                self.crew["crew_id"] = str(value)
            else:
                self.crew[key] = str(value)
        # add extra attributes
        self.crew["crew_key"] = str(self.instance.key)

    def set_agent_attributes(self):
        agent = {}
        for key, value in self.instance.__dict__.items():
            if key == "tools":
                value = self._parse_tools(value)
            if value is None:
                continue
            agent[key] = str(value)

        return agent

    def set_task_attributes(self):
        task = {}
        for key, value in self.instance.__dict__.items():
            if value is None:
                continue
            if key == "tools":
                value = self._parse_tools(value)
                task[key] = value
            elif key == "agent":
                task[key] = value.role
            else:
                task[key] = str(value)
        return task

    def _parse_agents(self, agents):
        for agent in agents:
            model = None
            if agent.llm is not None:
                if hasattr(agent.llm, "model"):
                    model = agent.llm.model
                elif hasattr(agent.llm, "model_name"):
                    model = agent.llm.model_name
            self.crew["crew_agents"].append(
                {
                    "key": agent.key,
                    "id": str(agent.id),
                    "role": agent.role,
                    "goal": agent.goal,
                    "backstory": agent.backstory,
                    "verbose?": agent.verbose,
                    "max_iter": agent.max_iter,
                    "max_rpm": agent.max_rpm,
                    "i18n": agent.i18n.prompt_file,
                    "llm": str(model if model is not None else ""),
                    "cache": agent.cache,
                    "config": agent.config,
                    "delegation_enabled?": agent.allow_delegation,
                    "tools_names": [
                        tool.name.casefold() for tool in agent.tools or []
                    ]
                    # "allow_delegation": agent.allow_delegation,
                    # "tools": agent.tools,
                }
            )
            self.crew["crew_number_of_agents"] = len(self.crew["crew_agents"])


    def _parse_tasks(self, tasks):
        for task in tasks:
            self.crew["crew_tasks"].append(
                {
                    "key": str(task.key),
                    "id": str(task.id),
#                    "agent": task.agent.role,
                    "description": task.description,
                    "expected_output": task.expected_output,
                    "async_execution?": task.async_execution,
                    "human_input?": task.human_input,
                    "agent_role": task.agent.role if task.agent else "None",
                    "agent_key": task.agent.key if task.agent else None,
                    "context": (
                        [task.description for task in task.context]
                        if task.context
                        else None
                    ),
                    "tools_names": [
                        tool.name.casefold() for tool in task.tools or []
                    ],
                    # "human_input": task.human_input,
                    # "tools": task.tools,
                    # "output_file": task.output_file,
                    # "agent_key": task.agent.key if task.agent else None,
                }
            )
        self.crew["crew_number_of_tasks"] = len(self.crew["crew_tasks"])


    def _parse_tools(self, tools):
        result = []
        for tool in tools:
            res = {}
            if hasattr(tool, "name") and tool.name is not None:
                res["name"] = tool.name
            if hasattr(tool, "description") and tool.description is not None:
                res["description"] = tool.description
            if res:
                result.append(res)
        result = [ tool.name.casefold() for tool in tools or []]
        return json.dumps(result)

def on_crew_creation_span(tracer, instance):
    """
    Record crew metadata in "crew.created" span when a crew gets created 
    """
    with tracer.start_as_current_span(
            "Crew.created", kind=SpanKind.CLIENT
        ) as span:
            CrewAISpanAttributes(span=span, instance=instance)