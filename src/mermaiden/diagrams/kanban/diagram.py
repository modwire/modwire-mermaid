from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import KanbanDiagramConfiguration
from .constraints import KanbanDiagramConstraint
from .elements import Column, KanbanPriority, Task


@injectable(as_type=DiagramModel, qualifier="kanban", lifetime="transient")
@dataclass(frozen=True, slots=True)
class KanbanDiagram(DiagramModel):
    constraints: Sequence[KanbanDiagramConstraint]
    configuration: KanbanDiagramConfiguration = field(default_factory=KanbanDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "kanban",
        "Kanban diagram",
        "kanban",
        "KanbanDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is Column:
            return parent_type is None
        return element_type is Task and parent_type is Column

    def add_column(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add column '{id}'", Column(id=id, label=label))

    def add_task(
        self,
        id: str,
        label: str,
        column_id: str,
        assigned: str = "",
        ticket: str = "",
        priority: KanbanPriority | str = "",
    ) -> ChangeReport:
        return self._add_element(
            f"add task '{id}'",
            Task(id=id, label=label, assigned=assigned, ticket=ticket, priority=priority),
            column_id,
        )
