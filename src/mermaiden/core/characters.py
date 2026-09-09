import re
from typing import ClassVar

from pydantic import Field, RootModel


class CharacterPolicy(RootModel[str]):
    pattern: ClassVar[str | re.Pattern[str]]
    description: ClassVar[str]
    root: str


class Identifier(CharacterPolicy):
    pattern = r"^[^\s\x00-\x1f\x7f-\x9f](?:[^\x00-\x1f\x7f-\x9f]*[^\s\x00-\x1f\x7f-\x9f])?$"
    description = "Non-empty identifier without surrounding whitespace or control characters."
    root: str = Field(pattern=pattern, description=description, json_schema_extra={"x-character-policy": "Identifier"})


class OptionalIdentifier(CharacterPolicy):
    pattern = r"^(?:[^\s\x00-\x1f\x7f-\x9f](?:[^\x00-\x1f\x7f-\x9f]*[^\s\x00-\x1f\x7f-\x9f])?)?$"
    description = "Empty root reference or an identifier without surrounding whitespace or control characters."
    root: str = Field(
        pattern=pattern,
        description=description,
        json_schema_extra={"x-character-policy": "OptionalIdentifier"},
    )


class Text(CharacterPolicy):
    pattern = r"^[^\s\x00-\x1f\x7f-\x9f](?:[^\x00-\x1f\x7f-\x9f]*[^\s\x00-\x1f\x7f-\x9f])?$"
    description = "Non-empty single-line text without surrounding whitespace or control characters."
    root: str = Field(pattern=pattern, description=description, json_schema_extra={"x-character-policy": "Text"})


class OptionalText(CharacterPolicy):
    pattern = r"^(?:[^\s\x00-\x1f\x7f-\x9f](?:[^\x00-\x1f\x7f-\x9f]*[^\s\x00-\x1f\x7f-\x9f])?)?$"
    description = "Empty or single-line text without surrounding whitespace or control characters."
    root: str = Field(
        pattern=pattern,
        description=description,
        json_schema_extra={"x-character-policy": "OptionalText"},
    )


class Identifiers(RootModel[tuple[Identifier, ...]]):
    root: tuple[Identifier, ...]


class OrderedIdentifiers(Identifiers):
    root: tuple[Identifier, ...] = Field(min_length=1, json_schema_extra={"uniqueItems": True})


class Texts(RootModel[tuple[Text, ...]]):
    root: tuple[Text, ...]


class OneOrTwoIdentifiers(RootModel[tuple[Identifier, ...]]):
    root: tuple[Identifier, ...] = Field(min_length=1, max_length=2)
