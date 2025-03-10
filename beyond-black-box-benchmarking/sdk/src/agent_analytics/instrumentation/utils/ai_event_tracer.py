import sys
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from agent_analytics_core.data.resources import Resource
from agent_analytics_core.data.issues import Issue
from agent_analytics_core.data.events import AIEvent
from agent_analytics_core.data.elements import Element
from agent_analytics_core.data.agents import Agent
from agent_analytics_core.data.iunits import IUnit, Relation
from agent_analytics_core.data.annotations import DataAnnotation
from agent_analytics_core.data.recommendations import Recommendation
from agent_analytics_core.data.service import Service
from agent_analytics_core.data.tasks import Task
from agent_analytics_core.data.workflows import Workflow, WorkflowNode, WorkflowEdge, Runable
from agent_analytics_core.data.organizations import Organization, Role

from functools import wraps
import datetime
import inspect
from enum import Enum
import json


class AIEventTracer:
    """Captures AI-related events."""

    @staticmethod
    def _get_caller_metadata():
        # Get caller function
        caller_frame = inspect.stack()[2]
        caller_filename = caller_frame.filename
        caller_function = caller_frame.function
        return caller_filename, caller_function

    @staticmethod
    def _prepare_attribute_for_otel(value: Any) -> Any:
        """Prepares values for OpenTelemetry attributes."""
        if value is None:
            return None
        elif isinstance(value, (str, bool, int, float)):
            return value
        elif isinstance(value, Enum):
            return str(value)
        elif isinstance(value, datetime.datetime):
            return value.isoformat()
        elif isinstance(value, list):
            if all(isinstance(item, (str, bool, int, float)) for item in value):
                return ", ".join(str(item) for item in value)
            else:
                try:
                    return json.dumps([AIEventTracer._prepare_attribute_for_otel(item) for item in value])
                except (TypeError, ValueError):
                    return str(value)
        elif isinstance(value, dict):
            try:
                return json.dumps({k: AIEventTracer._prepare_attribute_for_otel(v) for k, v in value.items()})
            except (TypeError, ValueError):
                return str(value)
        else:
            try:
                # Try to convert to dict if it's a Pydantic model
                if hasattr(value, "dict"):
                    return json.dumps(value.dict())
                # Otherwise, use default JSON serialization
                return json.dumps(value)
            except (TypeError, ValueError):
                return str(value)

    @staticmethod
    def _get_element_base_attributes(element: Element) -> dict:
        """Extract all base Element attributes."""
        attributes = {
            "id": element.id,
            "type": element.type,
            "owner_id": element.owner_id,
            "name": element.name,
            "description": element.description,
        }
        
        # Handle tags
        if element.tags:
            attributes["tags"] = AIEventTracer._prepare_attribute_for_otel(element.tags)
        
        # Handle attributes dictionary
        if element.attributes:
            for key, value in element.attributes.items():
                attributes[f"attr_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)
                
        return attributes
        
    @staticmethod
    def _get_iunit_attributes(iunit: 'IUnit') -> dict:
        """Extract all IUnit attributes."""
        attributes = {}
        
        if hasattr(iunit, "code_id"):
            attributes["code_id"] = iunit.code_id
            
        if hasattr(iunit, "is_generated"):
            attributes["is_generated"] = iunit.is_generated
            
        if hasattr(iunit, "consumed_resources"):
            attributes["consumed_resources"] = AIEventTracer._prepare_attribute_for_otel(iunit.consumed_resources)
            
        return attributes
        
    @staticmethod
    def _get_relation_attributes(relation: 'Relation') -> dict:
        """Extract all Relation attributes."""
        attributes = {}
        
        if hasattr(relation, "source_ids"):
            attributes["source_ids"] = AIEventTracer._prepare_attribute_for_otel(relation.source_ids)
            
        if hasattr(relation, "destination_ids"):
            attributes["destination_ids"] = AIEventTracer._prepare_attribute_for_otel(relation.destination_ids)
            
        if hasattr(relation, "weight"):
            attributes["weight"] = relation.weight
            
        return attributes

    @staticmethod
    def capture_resource(resource: Resource):
        """Captures Resource objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.resource"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(resource)
        
        # Add Resource specific attributes
        attributes.update({
            "category": str(resource.category) if resource.category else None,
            "format": resource.format
        })

        # Handle payload - use json.dumps specifically for payload
        try:
            attributes["payload"] = json.dumps(resource.payload) if resource.payload is not None else None
        except (TypeError, ValueError):
            attributes["payload"] = str(resource.payload) if resource.payload is not None else None

        # Get all other fields from the model if available
        if hasattr(resource, "dict"):
            resource_dict = resource.dict()
            for key, value in resource_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "payload"]:
                    attributes[key] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{resource.name or resource.id}.resource",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_role(role: Role):
        """Captures Role objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.role"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(role)
        
        # Add Relation specific attributes
        attributes.update(AIEventTracer._get_relation_attributes(role))
        
        # Add Role specific attributes
        if role.instructions:
            attributes["instructions"] = AIEventTracer._prepare_attribute_for_otel(role.instructions)

        # Get all fields from the model using dict()
        if hasattr(role, "dict"):
            role_dict = role.dict()
            for key, value in role_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "source_ids", "destination_ids", "weight", "instructions"]:
                    attributes[f"role_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{role.name or role.id}.role",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_organization(organization: Organization):
        """Captures Organization objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.organization"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(organization)
        
        # Add IUnit specific attributes (from Agent's parent class)
        attributes.update(AIEventTracer._get_iunit_attributes(organization))
        
        # Add Agent specific attributes
        if hasattr(organization, "resource_ids"):
            attributes["resource_ids"] = AIEventTracer._prepare_attribute_for_otel(organization.resource_ids)
        if hasattr(organization, "tool_ids"):
            attributes["tool_ids"] = AIEventTracer._prepare_attribute_for_otel(organization.tool_ids)
        if hasattr(organization, "skill_ids"):
            attributes["skill_ids"] = AIEventTracer._prepare_attribute_for_otel(organization.skill_ids)
        
        # Add Organization specific attributes
        if organization.roles:
            role_ids = [role.id for role in organization.roles if hasattr(role, 'id')]
            attributes["role_ids"] = AIEventTracer._prepare_attribute_for_otel(role_ids)
            
            # Also capture each role separately
            for role in organization.roles:
                AIEventTracer.capture_role(role)

        # Get all fields from the model using dict()
        if hasattr(organization, "dict"):
            org_dict = organization.dict(exclude={"roles"})  # Exclude roles as we handle them separately
            for key, value in org_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "resource_ids", "tool_ids", "skill_ids", "code_id", "is_generated", "consumed_resources", "roles"]:
                    attributes[f"organization_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{organization.name or organization.id}.organization",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_workflow(workflow: Workflow):
        """Captures Workflow objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.workflow"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(workflow)

        # Get all other fields from the model if available
        if hasattr(workflow, "dict"):
            workflow_dict = workflow.dict()
            for key, value in workflow_dict.items():
                if key not in attributes and key not in ["attributes", "tags"]:
                    attributes[f"workflow_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{workflow.name or workflow.id}.workflow",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_workflow_node(node: WorkflowNode):
        """Captures WorkflowNode objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.workflow_node"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(node)
        
        # Add IUnit specific attributes
        attributes.update(AIEventTracer._get_iunit_attributes(node))
        
        # Add WorkflowNode specific attributes
        attributes["task_counter"] = node.task_counter
        attributes["runnable_id"] = node.runnable_id

        # Get all fields from the model using dict()
        if hasattr(node, "dict"):
            node_dict = node.dict()
            for key, value in node_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "code_id", "is_generated", "consumed_resources", "task_counter", "runnable_id"]:
                    attributes[f"node_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{node.name or node.id}.workflow_node",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_workflow_edge(edge: WorkflowEdge):
        """Captures WorkflowEdge objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.workflow_edge"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(edge)
        
        # Add Relation specific attributes
        attributes.update(AIEventTracer._get_relation_attributes(edge))
        
        # Add WorkflowEdge specific attributes
        attributes["is_conditional"] = edge.is_conditional
        attributes["category"] = str(edge.category)

        # Get all fields from the model using dict()
        if hasattr(edge, "dict"):
            edge_dict = edge.dict()
            for key, value in edge_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "source_ids", "destination_ids", "weight", "is_conditional", "category"]:
                    attributes[f"edge_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{edge.name or edge.id}.workflow_edge",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_runable(runable: Runable):
        """Captures Runable objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.runable"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(runable)
        
        # Add IUnit specific attributes
        attributes.update(AIEventTracer._get_iunit_attributes(runable))
        
        # Add Runable specific attributes
        if runable.input_schema:
            attributes["input_schema"] = runable.input_schema
        if runable.output_schema:
            attributes["output_schema"] = runable.output_schema
        if runable.workflow_id:
            attributes["workflow_id"] = runable.workflow_id
        if runable.task_counter is not None:
            attributes["task_counter"] = runable.task_counter

        # Get all fields from the model using dict()
        if hasattr(runable, "dict"):
            runable_dict = runable.dict()
            for key, value in runable_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "code_id", "is_generated", "consumed_resources", "input_schema", "output_schema", "workflow_id", "task_counter"]:
                    attributes[f"runable_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{runable.name or runable.id}.runable",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_task(task: Task):
        """Captures Task objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.task"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(task)
        
        # Add Task specific attributes
        if task.input_resource_ids:
            attributes["input_resource_ids"] = AIEventTracer._prepare_attribute_for_otel(task.input_resource_ids)
        
        if task.input_data:
            attributes["input_data"] = task.input_data
            
        if task.output_data:
            attributes["output_data"] = AIEventTracer._prepare_attribute_for_otel(task.output_data)
            
        if task.output_data_ranking:
            attributes["output_data_ranking"] = AIEventTracer._prepare_attribute_for_otel(task.output_data_ranking)
            
        if task.created_resource_ids:
            attributes["created_resource_ids"] = AIEventTracer._prepare_attribute_for_otel(task.created_resource_ids)
            
        if task.dependencies_ids:
            attributes["dependencies_ids"] = AIEventTracer._prepare_attribute_for_otel(task.dependencies_ids)
            
        if task.runnable_id:
            attributes["runnable_id"] = task.runnable_id
            
        if task.expected_start_time:
            attributes["expected_start_time"] = task.expected_start_time
            
        if task.expected_end_time:
            attributes["expected_end_time"] = task.expected_end_time
            
        if task.priority is not None:
            attributes["priority"] = task.priority
            
        if task.is_generated is not None:
            attributes["is_generated"] = task.is_generated

        # Get any other fields from the model if available
        if hasattr(task, "dict"):
            task_dict = task.dict()
            for key, value in task_dict.items():
                if (key not in attributes and 
                    key not in ["attributes", "tags", "input_resource_ids", 
                              "input_data", "output_data", "output_data_ranking", 
                              "created_resource_ids", "dependencies_ids", "runnable_id",
                              "expected_start_time", "expected_end_time", "priority", "is_generated"]):
                    attributes[f"task_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{task.name or task.id}.task",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_service(service: Service):
        """Captures Service objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.service"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(service)
        
        # Add Service specific attributes with their OpenTelemetry standard aliases
        attributes.update({
            "service.name": service.name,
        })
        
        if service.namespace is not None:
            attributes["service.namespace"] = service.namespace
            
        if service.instance_id is not None:
            attributes["service.instance.id"] = service.instance_id
            
        if service.version is not None:
            attributes["service.version"] = service.version
            
        if service.environment is not None:
            attributes["service.environment"] = service.environment

        # Get all other fields from the model if available
        if hasattr(service, "dict"):
            service_dict = service.dict(by_alias=False)  # Get the values without aliases
            for key, value in service_dict.items():
                if (key not in attributes and 
                    key not in ["attributes", "tags", "name", "namespace", 
                               "instance_id", "version", "environment"]):
                    attributes[f"service_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{service.name}.service",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_recommendation(recommendation: Recommendation):
        """Captures Recommendation objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.recommendation"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(recommendation)
        
        # Add Recommendation specific attributes
        attributes.update({
            "level": str(recommendation.level),
            "generated_time": recommendation.generated_time or datetime.datetime.now().isoformat(),
            "affected_element_ids": AIEventTracer._prepare_attribute_for_otel(recommendation.affected_element_ids),
            "effect": AIEventTracer._prepare_attribute_for_otel(recommendation.effect)
        })

        # Get all fields from the model using dict()
        if hasattr(recommendation, "dict"):
            recommendation_dict = recommendation.dict()
            for key, value in recommendation_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "affected_element_ids", "effect", "level", "generated_time"]:
                    attributes[f"recommendation_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{recommendation.name or recommendation.id}.recommendation",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_data_annotation(annotation: DataAnnotation):
        """Captures DataAnnotation objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.data_annotation"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(annotation)
        
        # Add DataAnnotation specific attributes
        attributes.update({
            "element_id": annotation.element_id,
        })
        
        if annotation.segment_start is not None:
            attributes["segment_start"] = annotation.segment_start
        
        if annotation.segment_end is not None:
            attributes["segment_end"] = annotation.segment_end
            
        # Capture annotation type if present
        if hasattr(annotation, "type") and annotation.type is not None:
            attributes["annotation_type"] = str(annotation.type)
        
        # Get all other fields from the model if available
        if hasattr(annotation, "dict"):
            annotation_dict = annotation.dict()
            for key, value in annotation_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "element_id", "segment_start", "segment_end", "type"]:
                    attributes[f"annotation_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{annotation.name or annotation.id}.data_annotation",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_issue(issue: Issue):
        """Captures Issue objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.issue"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(issue)
        
        # Add Issue specific attributes
        attributes.update({
            "level": str(issue.level),
            "time": issue.time or datetime.datetime.now().isoformat(),
            "affected_element_ids": AIEventTracer._prepare_attribute_for_otel(issue.affected_element_ids),
            "effect": AIEventTracer._prepare_attribute_for_otel(issue.effect)
        })

        # Get any other fields from the model if available
        if hasattr(issue, "dict"):
            issue_dict = issue.dict()
            for key, value in issue_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "affected_element_ids", "effect", "level", "time"]:
                    attributes[key] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{issue.name or issue.id}.issue",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()

    @staticmethod
    def capture_ai_event(ai_event: AIEvent):
        """Captures AIEvent objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.ai_event"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes
        attributes = AIEventTracer._get_element_base_attributes(ai_event)
        
        # Add AIEvent specific attributes
        attributes.update({
            "status": str(ai_event.status) if ai_event.status else None,
        })

        # Handle Event fields from base Event class
        if hasattr(ai_event, "timestamp"):
            attributes["event_timestamp"] = AIEventTracer._prepare_attribute_for_otel(ai_event.timestamp)

        # Get all fields from the model if available
        if hasattr(ai_event, "dict"):
            ai_event_dict = ai_event.dict()
            for key, value in ai_event_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "status"]:
                    attributes[f"event_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{ai_event.name or ai_event.id}.ai_event",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
            
    @staticmethod
    def capture_agent(agent: Agent):
        """Captures Agent objects in spans."""
        # Get the current span
        current_span = trace.get_current_span()

        # Flag to indicate new span creation
        new_span = False
        # Check if the current span context is valid
        if current_span.get_span_context().is_valid and current_span.is_recording():
            # Get recording span
            record_span = current_span
        else:
            # No valid parent span; create a new span
            caller_filename, caller_function = AIEventTracer._get_caller_metadata()
            tracer = trace.get_tracer(caller_filename)
            span_name = f"{caller_function}.agent"
            record_span = tracer.start_span(span_name)
            new_span = True

        # Get base Element attributes from IUnit base class
        attributes = AIEventTracer._get_element_base_attributes(agent)
        
        # Add IUnit specific attributes
        attributes.update(AIEventTracer._get_iunit_attributes(agent))
        
        # Add Agent specific attributes
        if hasattr(agent, "resource_ids"):
            attributes["resource_ids"] = AIEventTracer._prepare_attribute_for_otel(agent.resource_ids)
        if hasattr(agent, "tool_ids"):
            attributes["tool_ids"] = AIEventTracer._prepare_attribute_for_otel(agent.tool_ids)
        if hasattr(agent, "skill_ids"):
            attributes["skill_ids"] = AIEventTracer._prepare_attribute_for_otel(agent.skill_ids)

        # Get all other fields from the model using dict()
        if hasattr(agent, "dict"):
            agent_dict = agent.dict()
            for key, value in agent_dict.items():
                if key not in attributes and key not in ["attributes", "tags", "resource_ids", "tool_ids", "skill_ids", "code_id", "is_generated", "consumed_resources"]:
                    attributes[f"agent_{key}"] = AIEventTracer._prepare_attribute_for_otel(value)

        # Filter out None values
        attributes = {k: v for k, v in attributes.items() if v is not None}

        record_span.add_event(
            name=f"{agent.name or agent.id}.agent",
            attributes=attributes
        )

        # End the span if it's a new one created within this function
        if new_span:
            record_span.end()
