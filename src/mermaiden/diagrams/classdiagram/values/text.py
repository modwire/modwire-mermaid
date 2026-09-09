from pydantic import Field

from ....core.characters import CharacterPolicy, Identifier, OptionalText, Text


class ClassText(Text):
    pass


class OptionalClassText(OptionalText):
    pass


class ClassIdentifier(Identifier):
    pass


class MemberName(CharacterPolicy):
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"
    description = "ASCII class member name."
    root: str = Field(pattern=pattern, description=description, json_schema_extra={"x-character-policy": "MemberName"})


class TypeName(CharacterPolicy):
    pattern = r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
    description = "Dot-qualified ASCII type name."
    root: str = Field(pattern=pattern, description=description, json_schema_extra={"x-character-policy": "TypeName"})
