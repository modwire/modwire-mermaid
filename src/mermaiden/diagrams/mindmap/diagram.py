from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.characters import Identifier, Text
from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .configuration import MindmapDiagramConfiguration
from .constraints import MindmapConstraint
from .elements import Bang, Circle, Cloud, Hexagon, MindmapNode, RoundedSquare, Square


@injectable(as_type=DiagramModel, qualifier="mindmap", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Mindmap(DiagramModel):
    constraints: Sequence[MindmapConstraint]
    configuration: MindmapDiagramConfiguration = field(default_factory=MindmapDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "mindmap",
        "Mindmap",
        "mindmap",
        "MindmapDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=MindmapDiagramConfiguration,
        elements=(MindmapNode, Square, RoundedSquare, Circle, Bang, Cloud, Hexagon),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("add_root", {"id": Identifier, "label": Text}),
            DiagramCommandFeature("add_node", {"id": Identifier, "label": Text, "parent_id": Identifier}),
            DiagramCommandFeature("add_square", {"id": Identifier, "label": Text, "parent_id": Identifier}),
            DiagramCommandFeature("add_rounded_square", {"id": Identifier, "label": Text, "parent_id": Identifier}),
            DiagramCommandFeature("add_circle", {"id": Identifier, "label": Text, "parent_id": Identifier}),
            DiagramCommandFeature("add_bang", {"id": Identifier, "label": Text, "parent_id": Identifier}),
            DiagramCommandFeature("add_cloud", {"id": Identifier, "label": Text, "parent_id": Identifier}),
            DiagramCommandFeature("add_hexagon", {"id": Identifier, "label": Text, "parent_id": Identifier}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if not issubclass(element_type, MindmapNode):
            return False
        if parent_type is None:
            return element_type is MindmapNode
        return issubclass(parent_type, MindmapNode)

    def add_root(self, id: str, label: str) -> ChangeReport:
        return self._add_node(MindmapNode(id=id, label=label), "", "root")

    def add_node(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(MindmapNode(id=id, label=label), parent_id, "node")

    def add_square(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(Square(id=id, label=label), parent_id, "square")

    def add_rounded_square(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(RoundedSquare(id=id, label=label), parent_id, "rounded square")

    def add_circle(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(Circle(id=id, label=label), parent_id, "circle")

    def add_bang(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(Bang(id=id, label=label), parent_id, "bang")

    def add_cloud(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(Cloud(id=id, label=label), parent_id, "cloud")

    def add_hexagon(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_node(Hexagon(id=id, label=label), parent_id, "hexagon")

    def _add_node(self, node: MindmapNode, parent_id: str, kind: str) -> ChangeReport:
        return self._add_element(f"add {kind} '{node.id}'", node, parent_id)
