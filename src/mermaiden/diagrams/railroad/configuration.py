from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class RailroadDiagramConfiguration(MermaidDiagramConfiguration):
    compact_mode: bool = False
    padding: float = Field(default=10, ge=0)
    vertical_separation: float = Field(default=8, ge=0)
    horizontal_separation: float = Field(default=10, ge=0)
    arc_radius: float = Field(default=10, ge=0)
    font_size: float = Field(default=14, ge=0)
    font_family: str = Field(default="monospace", pattern=Text.pattern, description=Text.description)
