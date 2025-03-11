from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Any, Type, Callable, Dict, Union, Set
import json
from langgraph.graph.state import CompiledStateGraph
import inspect

from agent_analytics_core.data.graph import Graph

def is_langgraph_task(name: str) -> bool:
    return name == "LangGraph"

def get_compiled_graph():
    """ Get the compiled graph from the call stack """
    graph = None
    invocation_methods = ["invoke", "ainvoke", "stream", "astream"]
    frames = inspect.stack()
    for frame_info in frames[1:]:
        if frame_info.frame.f_code.co_name in invocation_methods:
            local_vars = frame_info.frame.f_locals
            graph = local_vars.get("self", None)
            graph = graph if isinstance(graph, CompiledStateGraph) else None
            break
    return graph
    
def build_node_graph(compiled_state_graph: CompiledStateGraph) -> Graph:
    """ Build node graph from CompiledStateGraph """
    node_graph = Graph()
    for node_name in compiled_state_graph.nodes.keys():
        if node_name not in ["__start__", "__end__"]:
            node_graph.add_node(node_name)
    # Process regular edges
    for edge in compiled_state_graph.builder.edges:
        node_graph.add_edge(edge[0],edge[1])
    for source in compiled_state_graph.builder.branches.keys():
        names = compiled_state_graph.builder.branches[source]
        for name in names.keys():
            branch = names[name]
            destinations = []
            for destination in branch.ends.values():
                destinations.append(destination)
            node_graph.add_edge(source,destinations)

    # Add waiting edges 
    for edge in compiled_state_graph.builder.waiting_edges:
        node_graph.add_edge(edge[0],edge[1])        
 
    return node_graph     

def get_graph_structure():
    """ Get graph structure as a json string """
    graph_structure = json.dumps({})
    graph = get_compiled_graph()
    if graph:
        node_graph = build_node_graph(graph)
        graph_structure = node_graph.to_json()

    return graph_structure        