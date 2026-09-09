from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class RequirementDiagramConfiguration(MermaidDiagramConfiguration):
    use_max_width: bool = True
    rect_fill: str = Field(default="#f9f9f9", pattern=Text.pattern, description=Text.description)
    text_color: str = Field(default="#333", pattern=Text.pattern, description=Text.description)
    rect_border_size: str = Field(default="0.5px", pattern=Text.pattern, description=Text.description)
    rect_border_color: str = Field(default="#bbb", pattern=Text.pattern, description=Text.description)
    rect_min_width: int = 200
    rect_min_height: int = 200
    font_size: int = 14
    rect_padding: int = 10
    line_height: int = 20
