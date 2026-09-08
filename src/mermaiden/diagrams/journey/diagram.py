from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .configuration import JourneyDiagramConfiguration
from .constraints import JourneyConstraint
from .elements import JourneySection, JourneyTask


@injectable(as_type=DiagramModel, qualifier="journey", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Journey(DiagramModel):
    constraints: Sequence[JourneyConstraint]
    configuration: JourneyDiagramConfiguration = field(default_factory=JourneyDiagramConfiguration, init=False)
    title: str = field(default="", init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "journey",
        "User journey",
        "journey",
        "JourneyDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=JourneyDiagramConfiguration,
        elements=(JourneySection, JourneyTask),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("set_title", {"title": str}),
            DiagramCommandFeature("add_section", {"id": str, "label": str}),
            DiagramCommandFeature(
                "add_task", {"id": str, "label": str, "score": int, "actors": tuple[str, ...], "section_id": str}
            ),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is JourneySection:
            return parent_type is None
        return element_type is JourneyTask and parent_type is JourneySection

    def set_title(self, title: str) -> None:
        object.__setattr__(self, "title", title)

    def add_section(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add section '{id}'", JourneySection(id=id, label=label))

    def add_task(self, id: str, label: str, score: int, actors: tuple[str, ...], section_id: str) -> ChangeReport:
        return self._add_element(
            f"add task '{id}'", JourneyTask(id=id, label=label, score=score, actors=actors), section_id
        )
