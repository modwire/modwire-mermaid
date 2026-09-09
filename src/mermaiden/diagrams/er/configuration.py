from enum import StrEnum

from pydantic import ConfigDict, Field

from ...core.characters import Text
from ..domain import MermaidDiagramConfiguration


class EntityRelationshipDirection(StrEnum):
    TOP_BOTTOM = "TB"
    BOTTOM_TOP = "BT"
    LEFT_RIGHT = "LR"
    RIGHT_LEFT = "RL"


class EntityRelationshipDiagramConfiguration(MermaidDiagramConfiguration):
    model_config = ConfigDict(use_enum_values=True)

    title_top_margin: int = 25
    diagram_padding: int = 20
    layout_direction: EntityRelationshipDirection = Field(
        default=EntityRelationshipDirection.TOP_BOTTOM,
        validate_default=True,
    )
    min_entity_width: int = 100
    min_entity_height: int = 75
    entity_padding: int = 15
    stroke: str = Field(default="gray", pattern=Text.pattern, description=Text.description)
    fill: str = Field(default="honeydew", pattern=Text.pattern, description=Text.description)
    use_max_width: bool = True
