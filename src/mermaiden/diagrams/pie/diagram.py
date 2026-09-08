from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import PieDiagramConfiguration
from .constraints import PieConstraint
from .elements import PieSlice


@injectable(as_type=DiagramModel, qualifier="pie", lifetime="transient")
@dataclass(frozen=True, slots=True)
class PieDiagram(DiagramModel):
    constraints: Sequence[PieConstraint]
    configuration: PieDiagramConfiguration = field(default_factory=PieDiagramConfiguration, init=False)
    title: str = field(default="", init=False)
    show_data: bool = field(default=False, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "pie",
        "Pie chart",
        "pie",
        "PieDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type is PieSlice and parent_type is None

    def set_title(self, title: str) -> None:
        object.__setattr__(self, "title", title)

    def show_values(self) -> None:
        object.__setattr__(self, "show_data", True)

    def add_slice(self, id: str, label: str, value: float) -> ChangeReport:
        return self._add_element(f"add pie slice '{id}'", PieSlice(id=id, label=label, value=value))
