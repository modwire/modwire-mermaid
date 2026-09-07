from enum import StrEnum
from typing import Annotated

from pydantic import Field, StrictBool, field_validator

from ....core.domain import ValueModel
from .text import MemberName, TypeName


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    PACKAGE = "package"


class MethodModifier(StrEnum):
    INSTANCE = "instance"
    STATIC = "static"
    ABSTRACT = "abstract"


class ClassType(ValueModel):
    name: TypeName
    arguments: Annotated[tuple["ClassType", ...], Field(max_length=1)] = ()


class ClassAttribute(ValueModel):
    name: MemberName
    type: ClassType
    visibility: Visibility = Visibility.PUBLIC
    static: StrictBool = False


class ClassParameter(ValueModel):
    name: MemberName
    type: ClassType


class ClassMethod(ValueModel):
    name: MemberName
    parameters: tuple[ClassParameter, ...] = ()
    return_type: ClassType
    visibility: Visibility = Visibility.PUBLIC
    modifier: MethodModifier = MethodModifier.INSTANCE

    @field_validator("parameters")
    @classmethod
    def unique_parameters(cls, values: tuple[ClassParameter, ...]) -> tuple[ClassParameter, ...]:
        if len({item.name for item in values}) != len(values):
            raise ValueError("Parameter names must be unique within a method.")
        return values
