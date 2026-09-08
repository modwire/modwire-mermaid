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
from .configuration import VennConfiguration
from .constraints import VennConstraint
from .elements import VennSet, VennText, VennUnion


@injectable(as_type=DiagramModel, qualifier="venn", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Venn(DiagramModel):
    constraints: Sequence[VennConstraint]
    configuration: VennConfiguration = field(default_factory=VennConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "venn-beta",
        "Venn diagram",
        "venn",
        "VennDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=VennConfiguration,
        elements=(VennSet, VennUnion, VennText),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("add_set", {"id": str, "label": str, "size": CommandDefault(float | None, None)}),
            DiagramCommandFeature(
                "add_union",
                {"id": str, "label": str, "set_ids": tuple[str, ...], "size": CommandDefault(float | None, None)},
            ),
            DiagramCommandFeature("add_text", {"id": str, "label": str, "parent_id": str}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type in (VennSet, VennUnion):
            return parent_type is None
        return element_type is VennText and parent_type in (VennSet, VennUnion)

    def add_set(self, id: str, label: str, size: float | None = None) -> ChangeReport:
        return self._add_element(f"add set '{id}'", VennSet(id=id, label=label, elements=(), size=size))

    def add_union(
        self,
        id: str,
        label: str,
        set_ids: tuple[str, ...],
        size: float | None = None,
    ) -> ChangeReport:
        return self._add_element(
            f"add union '{id}'", VennUnion(id=id, label=label, elements=(), set_ids=set_ids, size=size)
        )

    def add_text(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add text '{id}'", VennText(id=id, label=label), parent_id)
