from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Literal

from wireup import injectable

from ...core.characters import Identifier, OptionalText, Text
from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    CommandDefault,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
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

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=KanbanDiagramConfiguration,
        elements=(Task, Column),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("add_column", {"id": Identifier, "label": Text}),
            DiagramCommandFeature(
                "add_task",
                {
                    "id": Identifier,
                    "label": Text,
                    "column_id": Identifier,
                    "assigned": CommandDefault(OptionalText, ""),
                    "ticket": CommandDefault(OptionalText, ""),
                    "priority": CommandDefault(KanbanPriority | Literal[""], ""),
                },
            ),
        ),
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
