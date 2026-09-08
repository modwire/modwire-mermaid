from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
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
