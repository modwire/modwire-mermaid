from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import PacketConfiguration
from .constraints import PacketConstraint
from .elements import PacketField


@injectable(as_type=DiagramModel, qualifier="packet", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Packet(DiagramModel):
    constraints: Sequence[PacketConstraint]
    configuration: PacketConfiguration = field(default_factory=PacketConfiguration, init=False)
    title: str = field(default="", init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "packet",
        "Packet diagram",
        "packet",
        "PacketDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type is PacketField and parent_type is None

    def set_title(self, title: str) -> None:
        object.__setattr__(self, "title", title)

    def add_field(self, id: str, label: str, start: int, end: int | None = None) -> ChangeReport:
        return self._add_element(f"add field '{id}'", PacketField(id=id, label=label, start=start, end=end))

    def add_bits(self, id: str, label: str, bits: int) -> ChangeReport:
        return self._add_element(f"add field '{id}'", PacketField(id=id, label=label, start=None, end=None, bits=bits))
