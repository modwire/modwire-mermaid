from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, ClassVar

from pydantic import Field
from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    CommandDefault,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .configuration import WardleyDiagramConfiguration
from .constraints import WardleyDiagramConstraint
from .elements import Component, ComponentDecorator, Evolution, Pipeline
from .relations import Dependency


@injectable(as_type=DiagramModel, qualifier="wardley", lifetime="transient")
@dataclass(frozen=True, slots=True)
class WardleyDiagram(DiagramModel):
    constraints: Sequence[WardleyDiagramConstraint]
    configuration: WardleyDiagramConfiguration = field(default_factory=WardleyDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "wardley-beta",
        "Wardley map",
        "wardley-beta",
        "WardleyDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=WardleyDiagramConfiguration,
        elements=(Component, Evolution, Pipeline),
        relations=(Dependency,),
        annotations=(),
        commands=(
            DiagramCommandFeature(
                "add_component",
                {
                    "id": str,
                    "label": str,
                    "visibility": float,
                    "evolution": float,
                    "decorators": CommandDefault(Annotated[tuple[ComponentDecorator, ...], Field(max_length=1)], ()),
                },
            ),
            DiagramCommandFeature("add_anchor", {"id": str, "label": str, "visibility": float, "evolution": float}),
            DiagramCommandFeature(
                "add_dependency", {"id": str, "source_id": str, "target_id": str, "label": CommandDefault(str, "")}
            ),
            DiagramCommandFeature("add_evolution", {"id": str, "component_id": str, "target": float}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type in (Component, Evolution, Pipeline) and parent_type is None

    def add_component(
        self,
        id: str,
        label: str,
        visibility: float,
        evolution: float,
        decorators: Annotated[tuple[ComponentDecorator, ...], Field(max_length=1)] = (),
    ) -> ChangeReport:
        return self._add_element(
            f"add component '{id}'",
            Component(id=id, label=label, visibility=visibility, evolution=evolution, decorators=decorators),
        )

    def add_anchor(self, id: str, label: str, visibility: float, evolution: float) -> ChangeReport:
        return self._add_element(
            f"add anchor '{id}'", Component(id=id, label=label, visibility=visibility, evolution=evolution, anchor=True)
        )

    def add_dependency(self, id: str, source_id: str, target_id: str, label: str = "") -> ChangeReport:
        return self._add_relation(
            f"add dependency '{id}'", Dependency(id=id, element_ids=(source_id, target_id), label=label)
        )

    def add_evolution(self, id: str, component_id: str, target: float) -> ChangeReport:
        return self._add_element(f"add evolution '{id}'", Evolution(id=id, label=component_id, target=target))
