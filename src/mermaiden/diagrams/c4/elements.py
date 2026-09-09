from pydantic import Field

from ...core.characters import OptionalText
from ...core.domain import Entity


class C4Element(Entity):
    description: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)
    technology: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)


class Person(C4Element):
    pass


class System(C4Element):
    pass


class SystemDb(C4Element):
    pass


class SystemQueue(C4Element):
    pass
