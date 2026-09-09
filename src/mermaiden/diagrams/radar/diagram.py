from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar

from wireup import injectable

from ...core.characters import Identifier, Text
from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
    PersistedDiagramProperty,
)
from .configuration import RadarConfiguration
from .constraints import RadarConstraint
from .elements import RadarAxis, RadarCurve


class RadarGraticule(StrEnum):
    CIRCLE = "circle"
    POLYGON = "polygon"


@injectable(as_type=DiagramModel, qualifier="radar", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Radar(DiagramModel):
    constraints: Sequence[RadarConstraint]
    configuration: RadarConfiguration = field(default_factory=RadarConfiguration, init=False)
    title: str = field(default="", init=False)
    show_legend: bool = field(default=True, init=False)
    minimum: float | None = field(default=None, init=False)
    maximum: float | None = field(default=None, init=False)
    graticule: RadarGraticule = field(default=RadarGraticule.CIRCLE, init=False)
    ticks: int | None = field(default=None, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "radar-beta",
        "Radar chart",
        "radar",
        "RadarDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=RadarConfiguration,
        snapshot_properties=(
            PersistedDiagramProperty("title", str),
            PersistedDiagramProperty("show_legend", bool),
            PersistedDiagramProperty("minimum", float | None),
            PersistedDiagramProperty("maximum", float | None),
            PersistedDiagramProperty("graticule", RadarGraticule),
            PersistedDiagramProperty("ticks", int | None),
        ),
        elements=(RadarAxis, RadarCurve),
        relations=(),
        annotations=(),
        commands=(
            DiagramCommandFeature("set_title", {"title": Text}),
            DiagramCommandFeature("set_legend", {"visible": bool}),
            DiagramCommandFeature("set_range", {"minimum": float, "maximum": float}),
            DiagramCommandFeature("set_graticule", {"graticule": RadarGraticule}),
            DiagramCommandFeature("set_ticks", {"ticks": int}),
            DiagramCommandFeature("add_axis", {"id": Identifier, "label": Text}),
            DiagramCommandFeature("add_curve", {"id": Identifier, "label": Text, "values": tuple[float, ...]}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type in (RadarAxis, RadarCurve) and parent_type is None

    def set_title(self, title: str) -> None:
        object.__setattr__(self, "title", title)

    def set_legend(self, visible: bool) -> None:
        object.__setattr__(self, "show_legend", visible)

    def set_range(self, minimum: float, maximum: float) -> None:
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    def set_graticule(self, graticule: RadarGraticule) -> None:
        object.__setattr__(self, "graticule", graticule)

    def set_ticks(self, ticks: int) -> None:
        object.__setattr__(self, "ticks", ticks)

    def add_axis(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add axis '{id}'", RadarAxis(id=id, label=label))

    def add_curve(self, id: str, label: str, values: tuple[float, ...]) -> ChangeReport:
        return self._add_element(f"add curve '{id}'", RadarCurve(id=id, label=label, values=values))
