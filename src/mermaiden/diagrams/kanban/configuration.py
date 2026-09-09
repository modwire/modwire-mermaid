from pydantic import Field

from ...core.characters import OptionalText
from ..domain import MermaidDiagramConfiguration


class KanbanDiagramConfiguration(MermaidDiagramConfiguration):
    padding: float = 8
    section_width: float = 200
    ticket_base_url: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)
