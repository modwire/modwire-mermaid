from enum import StrEnum

from pydantic import Field

from ...core.characters import OptionalText
from ...core.domain import Entity


class CommitType(StrEnum):
    NORMAL = "NORMAL"
    REVERSE = "REVERSE"
    HIGHLIGHT = "HIGHLIGHT"


class Commit(Entity):
    commit_type: str = Field(
        default="",
        pattern=r"^(?:NORMAL|REVERSE|HIGHLIGHT)?$",
        json_schema_extra={"enum": ["", "NORMAL", "REVERSE", "HIGHLIGHT"]},
    )
    tag: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)


class Branch(Entity):
    order: int | None = None


class Checkout(Entity):
    pass
