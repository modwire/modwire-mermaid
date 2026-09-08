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
from .configuration import TimelineDiagramConfiguration
from .constraints import TimelineConstraint
from .elements import TimelineEvent, TimelinePeriod, TimelineSection


@injectable(as_type=DiagramModel, qualifier="timeline", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Timeline(DiagramModel):
    constraints: Sequence[TimelineConstraint]
    configuration: TimelineDiagramConfiguration = field(default_factory=TimelineDiagramConfiguration, init=False)
    title: str = field(default="", init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "timeline",
        "Timeline",
        "timeline",
        "TimelineDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=TimelineDiagramConfiguration,
        elements=(TimelineSection, TimelinePeriod, TimelineEvent),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("set_title", {"title": str}),
            DiagramCommandFeature("add_section", {"id": str, "label": str}),
            DiagramCommandFeature("add_period", {"id": str, "label": str, "section_id": CommandDefault(str, "")}),
            DiagramCommandFeature("add_event", {"id": str, "label": str, "period_id": str}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is TimelineSection:
            return parent_type is None
        if element_type is TimelinePeriod:
            return parent_type is None or parent_type is TimelineSection
        return element_type is TimelineEvent and parent_type is TimelinePeriod

    def set_title(self, title: str) -> None:
        object.__setattr__(self, "title", title)

    def add_section(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add section '{id}'", TimelineSection(id=id, label=label))

    def add_period(self, id: str, label: str, section_id: str = "") -> ChangeReport:
        return self._add_element(f"add period '{id}'", TimelinePeriod(id=id, label=label), section_id)

    def add_event(self, id: str, label: str, period_id: str) -> ChangeReport:
        return self._add_element(f"add event '{id}'", TimelineEvent(id=id, label=label), period_id)
