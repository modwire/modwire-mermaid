from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class RailroadDiagramConfiguration(MermaidDiagramConfiguration):
    compact_mode: bool = False
    padding: float = 10
    vertical_separation: float = 8
    horizontal_separation: float = 10
    arc_radius: float = 10
    font_size: float = 14
    font_family: str = Field(default="monospace", pattern=Text.pattern, description=Text.description)
