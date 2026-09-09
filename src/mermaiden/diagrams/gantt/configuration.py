from enum import StrEnum

from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class GanttWeekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class GanttConfiguration(MermaidDiagramConfiguration):
    title_top_margin: int = Field(default=25, ge=0)
    bar_height: int = Field(default=20, ge=0)
    top_padding: int = Field(default=50, ge=0)
    right_padding: int = Field(default=75, ge=0)
    left_padding: int = Field(default=75, ge=0)
    grid_line_start_padding: int = Field(default=35, ge=0)
    font_size: int = Field(default=11, ge=0)
    section_font_size: int = Field(default=11, ge=0)
    number_section_styles: int = Field(default=4, ge=0)
    axis_format: str = Field(default="%Y-%m-%d", pattern=Text.pattern, description=Text.description)
    use_max_width: bool = True
    top_axis: bool = False
    weekday: GanttWeekday = GanttWeekday.SUNDAY
