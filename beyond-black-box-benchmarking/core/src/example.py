# Example : one possible implementation of data manager - in memory
from collections import defaultdict
from typing import Any, Dict, List, Optional, Type, cast
from agent_analytics_core.data.artifact import BaseArtifact, Flow, Issue, Metric
from agent_analytics_core.data.base_data_manager import T, DataManager


class InMemoryDataManager(DataManager):
    """
    In-memory implementation of the DataManager as example
    """

    def __init__(self):
        # Storage structure: {artifact_type: {artifact_id: artifact}}        
        self.storage: Dict[str, Dict[str, BaseArtifact]] = defaultdict(dict)

    def store(self, artifact: BaseArtifact) -> None:
        """
        Stores the artifact in memory.
        """
        artifact_type = artifact.__class__.__name__
        if artifact_type not in self.storage:
            self.storage[artifact_type] = {}
        self.storage[artifact_type][artifact.artifact_id] = artifact

    def get_by_id(self, artifact_id: str, artifact_type: Type[T]) -> Optional[T]:
        """
        Retrieves an artifact by its ID and type.
        """
        artifact_type_name = artifact_type.__name__
        if artifact_type_name in self.storage:
            artifact = self.storage[artifact_type_name].get(artifact_id)
            return cast(Optional[T], artifact)
        return None

    def get_children(
        self, parent_id: str, child_type: Type[T]
    ) -> List[T]:
        """
        Retrieves all children of a specific type for a given parent ID.
        """
        child_type_name = child_type.__name__
        if child_type_name not in self.storage:
            return []
        children = [
            artifact
            for artifact in self.storage[child_type_name].values()
            if artifact.parent_id == parent_id
        ]
        return cast(List[T], children)

    def delete(self, artifact_id: str, artifact_type: Type[T]) -> None:
        """
        Deletes an artifact by its ID and type.
        """
        artifact_type_name = artifact_type.__name__
        if artifact_type_name in self.storage:
            self.storage[artifact_type_name].pop(artifact_id, None)

    def get_all(self, artifact_type: Type[T]) -> List[T]:
        """
        Retrieves all artifacts of a specific type.
        """
        artifact_type_name = artifact_type.__name__
        if artifact_type_name in self.storage:
           return cast(List[T], list(self.storage[artifact_type_name].values()))
        return []
    
    def search(self, artifact_type: Type[T], query: Dict[str, Any]) -> List[T]:
        """
        Searches for artifacts of the specified type based on a query.
        """
        artifact_type_name = artifact_type.__name__
        if artifact_type_name not in self.storage:
            return []

        def matches_query(artifact: BaseArtifact) -> bool:
            return all(
                getattr(artifact, key, None) == value
                for key, value in query.items()
            )

        results = [
            artifact
            for artifact in self.storage[artifact_type_name].values()
            if matches_query(artifact)
        ]
        return cast(List[T], results)
    
    # Example Usage - store a flow and some metrics and issues 
if __name__ == "__main__":
    manager = InMemoryDataManager()

    # Create a Flow
    flow = Flow(
        artifact_id="flow1",        
        parent_id=None,
    )
    manager.store(flow)

    # Create Metrics associated with the Flow
    metric1 = Metric(
        artifact_id="metric1",       
        parent_id="flow1",
    )
    metric2 = Metric(
        artifact_id="metric2",        
        parent_id="flow1",
    )
    manager.store(metric1)
    manager.store(metric2)

    # Create Issues associated with the Flow
    issue = Issue(
        artifact_id="issue1",       
        parent_id="flow1",
    )
    manager.store(issue)

    # Fetch children (Metrics) of the Flow
    metrics = manager.get_children("flow1", Metric)
    print(f"Metrics for Flow 'flow1': {[m.model_dump() for m in metrics]}")

    # Fetch children (Issues) of the Flow
    issues = manager.get_children("flow1", Issue)
    print(f"Issues for Flow 'flow1': {[i.model_dump() for i in issues]}")

    query_all_metrics = {"parent_id": "flow1"}
    results_all_metrics = manager.search(Metric, query_all_metrics)
    print(f"All metrics for flow1: {[r.model_dump() for r in results_all_metrics]}")

    query_particular_metric = {"parent_id": "flow1", "artifact_id": "metric2"}
    results_particular_metric = manager.search(Metric, query_particular_metric)
    print(f"Particular metric for flow1: {[r.model_dump() for r in results_particular_metric]}")