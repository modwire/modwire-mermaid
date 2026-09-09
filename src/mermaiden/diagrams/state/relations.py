from pydantic import Field

from ...core.characters import OptionalIdentifier
from ...core.domain import Relation


class StateTransition(Relation):
    scope_id: str = Field(default="", pattern=OptionalIdentifier.pattern, description=OptionalIdentifier.description)
    source_terminal: bool = False
    target_terminal: bool = False
