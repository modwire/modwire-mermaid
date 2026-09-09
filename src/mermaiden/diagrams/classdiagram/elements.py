from typing import Annotated

from pydantic import Field, field_validator

from ...core.domain import Container, Entity
from .values.members import ClassAttribute, ClassMethod
from .values.text import ClassIdentifier, ClassText, MemberName, OptionalClassText


class Class(Entity):
    id: str = Field(pattern=ClassIdentifier.pattern, description=ClassIdentifier.description)
    label: str = Field(pattern=ClassText.pattern, description=ClassText.description)
    attributes: tuple[ClassAttribute, ...] = ()
    methods: tuple[ClassMethod, ...] = ()
    annotations: tuple[Annotated[str, Field(pattern=MemberName.pattern, description=MemberName.description)], ...] = ()
    comment: str = Field(default="", pattern=OptionalClassText.pattern, description=OptionalClassText.description)

    @field_validator("attributes")
    @classmethod
    def unique_attributes(cls, values: tuple[ClassAttribute, ...]) -> tuple[ClassAttribute, ...]:
        if len({item.name for item in values}) != len(values):
            raise ValueError("Attribute names must be unique within a class.")
        return values

    @field_validator("methods")
    @classmethod
    def unique_methods(cls, values: tuple[ClassMethod, ...]) -> tuple[ClassMethod, ...]:
        signatures = {(item.name, tuple(parameter.type for parameter in item.parameters)) for item in values}
        if len(signatures) != len(values):
            raise ValueError("Method overloads must have distinct names or ordered parameter types.")
        return values


class ClassNamespace(Container):
    id: str = Field(pattern=ClassIdentifier.pattern, description=ClassIdentifier.description)
    label: str = Field(pattern=ClassText.pattern, description=ClassText.description)
    comment: str = Field(default="", pattern=OptionalClassText.pattern, description=OptionalClassText.description)
