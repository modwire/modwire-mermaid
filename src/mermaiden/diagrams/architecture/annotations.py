from collections.abc import Mapping, Sequence

from pydantic import Field

from ...core.characters import Text
from ...core.domain import Annotation, OperationError, TargetKind, TargetRef


class ArchitectureNote(Annotation):
    text: str = Field(pattern=Text.pattern, description=Text.description)


class ArchitectureNotes:
    def create(
        self, id: str, data: Mapping[str, object], element_ids: Sequence[str], relation_ids: Sequence[str]
    ) -> ArchitectureNote:
        if relation_ids or len(element_ids) != 1 or set(data) != {"text"} or not isinstance(data.get("text"), str):
            raise OperationError("Architecture notes require one element and one string 'text' value.")
        text = data["text"]
        assert isinstance(text, str)
        return ArchitectureNote(id=id, targets=(TargetRef(kind=TargetKind.ELEMENT, id=element_ids[0]),), text=text)
