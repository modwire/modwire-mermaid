from typing import Annotated

from pydantic import Field

from ...core.characters import Identifier
from ...core.domain import Container, Entity


class VennSet(Container):
    size: float | None = None


class VennUnion(Container):
    set_ids: tuple[Annotated[str, Field(pattern=Identifier.pattern, description=Identifier.description)], ...] = ()
    size: float | None = None


class VennText(Entity):
    pass
