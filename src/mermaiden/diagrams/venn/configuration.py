from pydantic import Field

from ..domain import MermaidDiagramConfiguration


class VennConfiguration(MermaidDiagramConfiguration):
    width: float = Field(default=800, ge=1)
    height: float = Field(default=450, ge=1)
    padding: float = Field(default=8, ge=0)
    use_debug_layout: bool = False
