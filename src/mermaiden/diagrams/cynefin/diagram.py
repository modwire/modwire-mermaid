from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

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
from .configuration import CynefinDiagramConfiguration
from .constraints import CynefinDiagramConstraint
from .elements import Domain, DomainKind
from .relations import Transition


@injectable(as_type=DiagramModel, qualifier="cynefin", lifetime="transient")
@dataclass(frozen=True, slots=True)
class CynefinDiagram(DiagramModel):
    constraints: Sequence[CynefinDiagramConstraint]
    configuration: CynefinDiagramConfiguration = field(default_factory=CynefinDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "cynefin-beta",
        "Cynefin diagram",
        "cynefin",
        "CynefinDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=CynefinDiagramConfiguration,
        elements=(Domain,),
        relations=(Transition,),
        annotations=(),
        commands=(
            DiagramCommandFeature("add_item", {"id": Identifier, "label": Text, "domain": DomainKind}),
            DiagramCommandFeature(
                "add_transition",
                {
                    "id": Identifier,
                    "source_id": Identifier,
                    "target_id": Identifier,
                    "label": CommandDefault(OptionalText, ""),
                },
            ),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type is Domain and parent_type is None

    def add_item(self, id: str, label: str, domain: DomainKind) -> ChangeReport:
        return self._add_element(f"add {domain.value} item '{id}'", Domain(id=id, label=label, domain=domain))

    def add_transition(self, id: str, source_id: str, target_id: str, label: str = "") -> ChangeReport:
        return self._add_relation(
            f"add transition '{id}'", Transition(id=id, element_ids=(source_id, target_id), label=label)
        )

    @property
    def domain_kinds(self) -> tuple[DomainKind, ...]:
        return tuple(DomainKind)
