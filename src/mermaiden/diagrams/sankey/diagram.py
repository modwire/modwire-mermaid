from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import SankeyDiagramConfiguration
from .constraints import SankeyConstraint
from .elements import SankeyNode
from .relations import SankeyLink


@injectable(as_type=DiagramModel, qualifier="sankey", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Sankey(DiagramModel):
    constraints: Sequence[SankeyConstraint]
    configuration: SankeyDiagramConfiguration = field(default_factory=SankeyDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "sankey",
        "Sankey diagram",
        "sankey",
        "SankeyDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type is SankeyNode and parent_type is None

    def add_node(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add node '{id}'", SankeyNode(id=id, label=label))

    def add_flow(self, id: str, source_id: str, target_id: str, value: float) -> ChangeReport:
        return self._add_relation(
            f"add flow '{id}'", SankeyLink(id=id, element_ids=(source_id, target_id), label="", value=value)
        )
