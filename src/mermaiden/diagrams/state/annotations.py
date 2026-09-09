from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import Field

from ...core.characters import OptionalIdentifier, Text
from ...core.domain import Annotation, OperationError, TargetKind, TargetRef


class NotePosition(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class StateNote(Annotation):
    text: str = Field(pattern=Text.pattern, description=Text.description)
    position: NotePosition
    scope_id: str = Field(default="", pattern=OptionalIdentifier.pattern, description=OptionalIdentifier.description)


class StateNotes:
    def create(
        self,
        id: str,
        data: Mapping[str, object],
        element_ids: Sequence[str],
        relation_ids: Sequence[str],
    ) -> StateNote:
        if relation_ids or len(element_ids) != 1:
            raise OperationError("State notes target exactly one state node.")
        if set(data) != {"text", "position", "scope_id"}:
            raise OperationError("State notes require text, position, and scope.")
        text = data["text"]
        position = data["position"]
        scope_id = data["scope_id"]
        if not isinstance(text, str) or not isinstance(position, NotePosition) or not isinstance(scope_id, str):
            raise OperationError("State note data is invalid.")
        return StateNote(
            id=id,
            targets=(TargetRef(kind=TargetKind.ELEMENT, id=element_ids[0]),),
            text=text,
            position=position,
            scope_id=scope_id,
        )
