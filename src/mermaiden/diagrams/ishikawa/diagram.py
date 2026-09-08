from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import IshikawaDiagramConfiguration
from .constraints import IshikawaDiagramConstraint
from .elements import Category, Cause, Effect


@injectable(as_type=DiagramModel, qualifier="ishikawa", lifetime="transient")
@dataclass(frozen=True, slots=True)
class IshikawaDiagram(DiagramModel):
    constraints: Sequence[IshikawaDiagramConstraint]
    configuration: IshikawaDiagramConfiguration = field(default_factory=IshikawaDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "ishikawa-beta",
        "Ishikawa diagram",
        "ishikawa",
        "IshikawaDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is Effect:
            return parent_type is None
        if element_type is Category:
            return parent_type is None or parent_type is Category
        return element_type is Cause and parent_type is Category

    def add_effect(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add effect '{id}'", Effect(id=id, label=label))

    def add_category(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_element(f"add category '{id}'", Category(id=id, label=label), parent_id)

    def add_cause(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add cause '{id}'", Cause(id=id, label=label), parent_id)
