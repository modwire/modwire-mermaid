import re
from typing import Annotated

from pydantic import Field

from ...core import domain
from ...core.characters import CharacterPolicy, OptionalText, Text


class EntityAttributeDataType(CharacterPolicy):
    pattern = re.compile(
        r"^(?![\s\S]*[\r\n])(?!(?:[Pp][Kk]|[Ff][Kk]|[Uu][Kk])(?:$|[^A-Za-z0-9_]))"
        r"(?:[\*A-Za-z_\u00C0-\uFFFF][A-Za-z0-9\-\_\[\]\(\)\.,\u00C0-\uFFFF\*]*\??"
        r"|[^\s]*~[^\r\n]*~[^\s]*|`[^`]+`\??)$"
    )
    description = "Mermaid entity-relationship attribute data type."
    root: str = Field(
        pattern=pattern,
        description=description,
        json_schema_extra={"x-character-policy": "EntityAttributeDataType"},
    )


class EntityAttribute(domain.Entity):
    data_type: str = Field(
        default="string", pattern=EntityAttributeDataType.pattern, description=EntityAttributeDataType.description
    )
    keys: tuple[Annotated[str, Field(pattern=Text.pattern, description=Text.description)], ...] = ()
    comment: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)


class Entity(domain.Container):
    pass
