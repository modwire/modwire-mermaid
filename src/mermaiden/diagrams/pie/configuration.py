from enum import StrEnum

from pydantic import Field

from ...core.characters import OptionalText
from ..domain import MermaidDiagramConfiguration


class LegendPosition(StrEnum):
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"


class PieDiagramConfiguration(MermaidDiagramConfiguration):
    text_position: float = Field(default=0.75, ge=0, le=1)
    donut_hole: float = Field(default=0, ge=0, le=0.9)
    legend_position: LegendPosition = LegendPosition.RIGHT
    highlight_slice: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)
