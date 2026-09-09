from typing import Annotated

from pydantic import Field

from ...core.characters import Text
from ...core.domain import Container, Entity


class JourneySection(Container):
    pass


class JourneyTask(Entity):
    score: int = 1
    actors: tuple[Annotated[str, Field(pattern=Text.pattern, description=Text.description)], ...] = ()
