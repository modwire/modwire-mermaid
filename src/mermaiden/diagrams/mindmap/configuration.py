from pydantic import Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class MindmapDiagramConfiguration(MermaidDiagramConfiguration):
    use_max_width: bool = True
    padding: float = 10
    max_node_width: float = 200
    layout_algorithm: str = Field(default="cose-bilkent", pattern=Text.pattern, description=Text.description)
