from collections.abc import Mapping, Sequence
from enum import StrEnum

from pydantic import Field

from ...core.characters import Text
from ...core.domain import Annotation, OperationError, TargetKind, TargetRef


class NotePosition(StrEnum):
    LEFT = "left of"
    RIGHT = "right of"
    OVER = "over"


class SequenceNote(Annotation):
    text: str = Field(pattern=Text.pattern, description=Text.description)
    position: NotePosition = NotePosition.OVER


class SequenceNotes:
    def create(
        self, id: str, data: Mapping[str, object], element_ids: Sequence[str], relation_ids: Sequence[str]
    ) -> SequenceNote:
        if relation_ids or not 1 <= len(element_ids) <= 2:
            raise OperationError("Sequence notes target one or two participants.")
        text = data.get("text")
        position = data.get("position", NotePosition.OVER)
        if set(data) - {"text", "position"} or not isinstance(text, str):
            raise OperationError("Sequence notes require text and an optional position.")
        try:
            note_position = NotePosition(position)
        except ValueError as error:
            raise OperationError("Sequence note position is invalid.") from error
        if len(element_ids) == 2 and note_position is not NotePosition.OVER:
            raise OperationError("Notes over two participants require position 'over'.")
        return SequenceNote(
            id=id,
            targets=tuple(TargetRef(kind=TargetKind.ELEMENT, id=item) for item in element_ids),
            text=text,
            position=note_position,
        )
