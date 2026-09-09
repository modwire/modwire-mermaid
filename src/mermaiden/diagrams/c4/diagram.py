from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.characters import Identifier, OptionalText, Text
from ...core.domain import ChangeReport, Container, Element
from ...core.naming import ClassName
from ..domain import (
    CommandDefault,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .configuration import C4ContextDiagramConfiguration
from .constraints import C4ContextDiagramConstraint
from .elements import C4Element, Person, System, SystemDb, SystemQueue
from .relations import Relationship, RelationshipDirection


@injectable(as_type=DiagramModel, qualifier="c4", lifetime="transient")
@dataclass(frozen=True, slots=True)
class C4ContextDiagram(DiagramModel):
    constraints: Sequence[C4ContextDiagramConstraint]
    configuration: C4ContextDiagramConfiguration = field(default_factory=C4ContextDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "C4Context",
        "C4 Context diagram",
        "c4",
        "C4DiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=C4ContextDiagramConfiguration,
        elements=(C4Element, Person, System, SystemDb, SystemQueue),
        relations=(Relationship,),
        annotations=(),
        commands=(
            DiagramCommandFeature(
                "add_person", {"id": Identifier, "label": Text, "description": CommandDefault(OptionalText, "")}
            ),
            DiagramCommandFeature(
                "add_system",
                {
                    "id": Identifier,
                    "label": Text,
                    "description": CommandDefault(OptionalText, ""),
                    "technology": CommandDefault(OptionalText, ""),
                },
            ),
            DiagramCommandFeature(
                "add_database",
                {
                    "id": Identifier,
                    "label": Text,
                    "description": CommandDefault(OptionalText, ""),
                    "technology": CommandDefault(OptionalText, ""),
                },
            ),
            DiagramCommandFeature(
                "add_queue",
                {
                    "id": Identifier,
                    "label": Text,
                    "description": CommandDefault(OptionalText, ""),
                    "technology": CommandDefault(OptionalText, ""),
                },
            ),
            DiagramCommandFeature(
                "add_relationship",
                {
                    "id": Identifier,
                    "source_id": Identifier,
                    "target_id": Identifier,
                    "label": Text,
                    "direction": CommandDefault(RelationshipDirection, RelationshipDirection.DEFAULT),
                },
            ),
            DiagramCommandFeature(
                "set_relationship_label_offset", {"id": Identifier, "offset_x": int, "offset_y": int}
            ),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type in (C4Element, Person, System, SystemDb, SystemQueue) and parent_type is None

    def add_person(self, id: str, label: str, description: str = "") -> ChangeReport:
        return self._add_element(f"add person '{id}'", Person(id=id, label=label, description=description))

    def add_system(self, id: str, label: str, description: str = "", technology: str = "") -> ChangeReport:
        return self._add_element(
            f"add system '{id}'", System(id=id, label=label, description=description, technology=technology)
        )

    def add_database(self, id: str, label: str, description: str = "", technology: str = "") -> ChangeReport:
        return self._add_element(
            f"add database '{id}'", SystemDb(id=id, label=label, description=description, technology=technology)
        )

    def add_queue(self, id: str, label: str, description: str = "", technology: str = "") -> ChangeReport:
        return self._add_element(
            f"add queue '{id}'", SystemQueue(id=id, label=label, description=description, technology=technology)
        )

    def add_relationship(
        self,
        id: str,
        source_id: str,
        target_id: str,
        label: str,
        direction: RelationshipDirection = RelationshipDirection.DEFAULT,
    ) -> ChangeReport:
        return self._add_relation(
            f"add relationship '{id}'",
            Relationship(id=id, element_ids=(source_id, target_id), label=label, direction=direction),
        )

    def set_relationship_label_offset(self, id: str, offset_x: int, offset_y: int) -> ChangeReport:
        return self.mutations.update_relation(
            self,
            id,
            ClassName(Relationship).snake_case,
            {"offset_x": offset_x, "offset_y": offset_y},
        )
