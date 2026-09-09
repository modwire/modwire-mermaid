from pydantic import Field

from ..domain import MermaidDiagramConfiguration


class CynefinDiagramConfiguration(MermaidDiagramConfiguration):
    width: float = Field(default=800, ge=1)
    height: float = Field(default=600, ge=1)
    padding: float = Field(default=40, ge=0)
    show_domain_descriptions: bool = True
    boundary_amplitude: float = Field(default=8, ge=0, le=50)
    seed: float = 1
