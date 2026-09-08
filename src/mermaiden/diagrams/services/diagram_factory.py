from dataclasses import dataclass

from wireup import ScopedSyncContainer, injectable

from ..application import DiagramsApplication
from ..domain import DiagramModel


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class DiagramFactory:
    scope: ScopedSyncContainer
    registry: DiagramsApplication

    def create(self, diagram_id: str) -> DiagramModel:
        qualifier = self.registry.qualifier(diagram_id)
        return self.scope.get(DiagramModel, qualifier=qualifier)
