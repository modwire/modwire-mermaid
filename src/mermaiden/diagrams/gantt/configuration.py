from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class GanttConfiguration(MermaidDiagramConfiguration):
    title_top_margin: int = 25
    bar_height: int = 20
    top_padding: int = 50
    right_padding: int = 75
    left_padding: int = 75
    grid_line_start_padding: int = 35
    font_size: int = 11
    section_font_size: int = 11
    number_section_styles: int = 4
    axis_format: str = Field(default="%Y-%m-%d", pattern=Text.pattern, description=Text.description)
    use_max_width: bool = True
    top_axis: bool = False
    weekday: str = Field(default="sunday", pattern=Text.pattern, description=Text.description)
