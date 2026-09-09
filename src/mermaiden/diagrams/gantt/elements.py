from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ...core.characters import Identifier, OptionalText, Text
from ...core.domain import Container, Entity, ValueModel


class GanttDate(Text):
    pass


class GanttDateFormat(Text):
    pass


class TaskStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"


class DurationUnit(StrEnum):
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class AutomaticStart(ValueModel):
    kind: Literal["automatic"] = "automatic"


class DateStart(ValueModel):
    kind: Literal["date"] = "date"
    date: str = Field(pattern=GanttDate.pattern, description=GanttDate.description)


class DependencyStart(ValueModel):
    kind: Literal["dependencies"] = "dependencies"
    task_ids: Annotated[
        tuple[Annotated[str, Field(pattern=Identifier.pattern, description=Identifier.description)], ...],
        Field(min_length=1),
    ]


GanttStart = Annotated[AutomaticStart | DateStart | DependencyStart, Field(discriminator="kind")]


class DurationFinish(ValueModel):
    kind: Literal["duration"] = "duration"
    amount: Annotated[float, Field(ge=0)]
    unit: DurationUnit = DurationUnit.DAYS


class EndDateFinish(ValueModel):
    kind: Literal["end_date"] = "end_date"
    date: str = Field(pattern=GanttDate.pattern, description=GanttDate.description)


class UntilFinish(ValueModel):
    kind: Literal["until"] = "until"
    date: str = Field(pattern=GanttDate.pattern, description=GanttDate.description)


GanttFinish = Annotated[DurationFinish | EndDateFinish | UntilFinish, Field(discriminator="kind")]


class Task(Entity):
    status: TaskStatus = TaskStatus.PLANNED
    critical: bool = False
    start: GanttStart
    finish: GanttFinish


class Milestone(Entity):
    status: TaskStatus = TaskStatus.PLANNED
    critical: bool = False
    start: GanttStart
    finish: GanttFinish


class Marker(Entity):
    date: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)


class Section(Container):
    pass
