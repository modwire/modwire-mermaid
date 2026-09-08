from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, ClassVar

from pydantic import Field
from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .annotations import ArchitectureNotes
from .configuration import ArchitectureDiagramConfiguration
from .constraints.structure import ArchitectureConstraint
from .elements import ArchitectureGroup, Junction, Service
from .relations import Alignment, AlignmentAxis, Edge, Port


@injectable(as_type=DiagramModel, qualifier="architecture", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Architecture(DiagramModel):
    constraints: Sequence[ArchitectureConstraint]
    configuration: ArchitectureDiagramConfiguration = field(
        default_factory=ArchitectureDiagramConfiguration,
        init=False,
    )
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "architecture-beta",
        "Architecture diagram",
        "architecture",
        "ArchitectureDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type in (ArchitectureGroup, Junction, Service) and (
            parent_type is None or parent_type is ArchitectureGroup
        )

    def add_group(
        self,
        id: str,
        label: str,
        parent_id: str = "",
        columns: Annotated[int, Field(ge=1)] = 1,
    ) -> ChangeReport:
        return self._add_element(
            f"add group '{id}'", ArchitectureGroup(id=id, label=label, elements=(), columns=columns), parent_id
        )

    def add_service(self, id: str, label: str, group_id: str = "") -> ChangeReport:
        return self._add_element(f"add service '{id}'", Service(id=id, label=label), group_id)

    def add_junction(self, id: str, label: str = "", group_id: str = "") -> ChangeReport:
        return self._add_element(f"add junction '{id}'", Junction(id=id, label=label or id), group_id)

    def add_edge(
        self,
        id: str,
        source_id: str,
        target_id: str,
        source_port: Port = Port.RIGHT,
        target_port: Port = Port.LEFT,
        label: str = "",
    ) -> ChangeReport:
        return self._add_relation(
            f"add edge '{id}'",
            Edge(
                id=id, element_ids=(source_id, target_id), label=label, source_port=source_port, target_port=target_port
            ),
        )

    def add_alignment(self, id: str, axis: AlignmentAxis, member_ids: tuple[str, ...]) -> ChangeReport:
        operation = f"add alignment '{id}'"
        if len(member_ids) < 2:
            self._reject(operation, f"Alignment '{id}' requires at least two members.")
        if len(set(member_ids)) != len(member_ids):
            self._reject(operation, f"Alignment '{id}' members must be unique.")
        for member_id in member_ids:
            member = self.find_element(member_id)
            if member is None:
                self._reject(operation, f"Alignment '{id}' references unknown member '{member_id}'.")
            if not isinstance(member, Service | Junction):
                self._reject(operation, f"Alignment '{id}' member '{member_id}' must be a service or junction.")
        return self._add_relation(operation, Alignment(id=id, element_ids=member_ids, axis=axis))

    def add_note(self, id: str, element_id: str, text: str) -> ChangeReport:
        return self._annotate(f"add note '{id}'", ArchitectureNotes(), id, {"text": text}, (element_id,))
