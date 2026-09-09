from pydantic import Field

from ..domain import MermaidDiagramConfiguration


class RadarConfiguration(MermaidDiagramConfiguration):
    width: float = Field(default=600, ge=1)
    height: float = Field(default=600, ge=1)
    margin_top: float = Field(default=50, ge=0)
    margin_right: float = Field(default=50, ge=0)
    margin_bottom: float = Field(default=50, ge=0)
    margin_left: float = Field(default=50, ge=0)
    axis_scale_factor: float = Field(default=1, ge=0)
    axis_label_factor: float = Field(default=1.05, ge=0)
    curve_tension: float = Field(default=0.17, ge=0, le=1)
