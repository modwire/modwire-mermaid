from collections.abc import Mapping, Sequence
from typing import Annotated

from pydantic import Field, field_validator

from ...core.domain import Annotation, OperationError, TargetKind, TargetRef
from .values.text import ClassIdentifier, ClassText


class ClassNote(Annotation):
    id: str = Field(pattern=ClassIdentifier.pattern, description=ClassIdentifier.description)
    targets: Annotated[
        tuple[Annotated[TargetRef, Field(json_schema_extra={"properties": {"kind": {"const": "element"}}})], ...],
        Field(min_length=1, max_length=1),
    ]
    text: str = Field(pattern=ClassText.pattern, description=ClassText.description)

    @field_validator("targets")
    @classmethod
    def class_targets(cls, targets: tuple[TargetRef, ...]) -> tuple[TargetRef, ...]:
        if any(target.kind is not TargetKind.ELEMENT for target in targets):
            raise ValueError("Class notes require an element target.")
        return targets


class ClassNotes:
    def create(
        self,
        id: str,
        data: Mapping[str, object],
        element_ids: Sequence[str],
        relation_ids: Sequence[str],
    ) -> ClassNote:
        if relation_ids or len(element_ids) != 1:
            raise OperationError("Class notes target exactly one class.")
        if set(data) != {"text"} or not isinstance(data.get("text"), str):
            raise OperationError("Class notes require exactly one string 'text' value.")
        text = data["text"]
        assert isinstance(text, str)
        return ClassNote(id=id, targets=(TargetRef(kind=TargetKind.ELEMENT, id=element_ids[0]),), text=text)
