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
from .configuration import EventModelingDiagramConfiguration
from .constraints import EventModelingDiagramConstraint
from .elements import Actor, Command, Event, Swimlane, View
from .relations import Flow


@injectable(as_type=DiagramModel, qualifier="eventmodeling", lifetime="transient")
@dataclass(frozen=True, slots=True)
class EventModelingDiagram(DiagramModel):
    constraints: Sequence[EventModelingDiagramConstraint]
    configuration: EventModelingDiagramConfiguration = field(
        default_factory=EventModelingDiagramConfiguration,
        init=False,
    )
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "eventmodeling",
        "Event Modeling diagram",
        "eventmodeling",
        "EventModelingDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=EventModelingDiagramConfiguration,
        elements=(Event, Command, View, Actor, Swimlane),
        relations=(Flow,),
        annotations=(),
        commands=(
            DiagramCommandFeature("add_swimlane", {"id": str, "label": str}),
            DiagramCommandFeature("add_actor", {"id": str, "label": str, "swimlane_id": str}),
            DiagramCommandFeature("add_command", {"id": str, "label": str, "swimlane_id": str}),
            DiagramCommandFeature("add_view", {"id": str, "label": str, "swimlane_id": str}),
            DiagramCommandFeature("add_event", {"id": str, "label": str, "swimlane_id": str}),
            DiagramCommandFeature("add_flow", {"id": str, "source_id": str, "target_id": str}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is Swimlane:
            return parent_type is None
        return element_type in (Actor, Command, Event, View) and parent_type is Swimlane

    def add_swimlane(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add swimlane '{id}'", Swimlane(id=id, label=label))

    def add_actor(self, id: str, label: str, swimlane_id: str) -> ChangeReport:
        return self._add_element(f"add actor '{id}'", Actor(id=id, label=label), swimlane_id)

    def add_command(self, id: str, label: str, swimlane_id: str) -> ChangeReport:
        return self._add_element(f"add command '{id}'", Command(id=id, label=label), swimlane_id)

    def add_view(self, id: str, label: str, swimlane_id: str) -> ChangeReport:
        return self._add_element(f"add view '{id}'", View(id=id, label=label), swimlane_id)

    def add_event(self, id: str, label: str, swimlane_id: str) -> ChangeReport:
        return self._add_element(f"add event '{id}'", Event(id=id, label=label), swimlane_id)

    def add_flow(self, id: str, source_id: str, target_id: str) -> ChangeReport:
        return self._add_relation(f"add flow '{id}'", Flow(id=id, element_ids=(source_id, target_id)))
