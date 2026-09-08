from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    CommandDefault,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .configuration import BlockDiagramConfiguration
from .constraints import BlockDiagramConstraint
from .elements import BlockGroup, BlockNode, BlockSpace


@injectable(as_type=DiagramModel, qualifier="block", lifetime="transient")
@dataclass(frozen=True, slots=True)
class BlockDiagram(DiagramModel):
    constraints: Sequence[BlockDiagramConstraint]
    configuration: BlockDiagramConfiguration = field(default_factory=BlockDiagramConfiguration, init=False)
    columns: int | None = field(default=None, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "block",
        "Block diagram",
        "block",
        "BlockDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=BlockDiagramConfiguration,
        elements=(BlockGroup, BlockNode, BlockSpace),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("set_columns", {"columns": int}),
            DiagramCommandFeature(
                "add_group",
                {
                    "id": str,
                    "label": str,
                    "columns": CommandDefault(int | None, None),
                    "span": CommandDefault(int | None, None),
                },
            ),
            DiagramCommandFeature(
                "add_block",
                {
                    "id": str,
                    "label": str,
                    "span": CommandDefault(int | None, None),
                    "parent_id": CommandDefault(str, ""),
                },
            ),
            DiagramCommandFeature(
                "add_space", {"id": str, "span": CommandDefault(int | None, None), "parent_id": CommandDefault(str, "")}
            ),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is BlockGroup:
            return parent_type is None
        return element_type in (BlockNode, BlockSpace) and (parent_type is None or parent_type is BlockGroup)

    def set_columns(self, columns: int) -> None:
        object.__setattr__(self, "columns", columns)

    def add_group(self, id: str, label: str, columns: int | None = None, span: int | None = None) -> ChangeReport:
        return self._add_element(
            f"add group '{id}'", BlockGroup(id=id, label=label, elements=(), columns=columns, span=span)
        )

    def add_block(self, id: str, label: str, span: int | None = None, parent_id: str = "") -> ChangeReport:
        return self._add_element(f"add block '{id}'", BlockNode(id=id, label=label, span=span), parent_id)

    def add_space(self, id: str, span: int | None = None, parent_id: str = "") -> ChangeReport:
        return self._add_element(f"add space '{id}'", BlockSpace(id=id, label="space", span=span), parent_id)
