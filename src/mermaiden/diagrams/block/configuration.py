from pydantic import Field

from ..domain import MermaidDiagramConfiguration


class BlockDiagramConfiguration(MermaidDiagramConfiguration):
    padding: float = Field(default=8, ge=0)
