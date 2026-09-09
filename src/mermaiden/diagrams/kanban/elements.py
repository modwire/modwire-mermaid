from enum import StrEnum

from pydantic import Field

from ...core.characters import OptionalText
from ...core.domain import Container, Entity


class KanbanPriority(StrEnum):
    VERY_HIGH = "Very High"
    HIGH = "High"
    LOW = "Low"
    VERY_LOW = "Very Low"


class Task(Entity):
    assigned: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)
    ticket: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)
    priority: str = Field(
        default="",
        pattern=r"^(?:Very High|High|Low|Very Low)?$",
        json_schema_extra={"enum": ["", "Very High", "High", "Low", "Very Low"]},
    )


class Column(Container):
    pass
