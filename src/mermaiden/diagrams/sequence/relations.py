from enum import StrEnum

from pydantic import Field

from ...core.domain import Relation


class MessageKind(StrEnum):
    SOLID = "solid"
    DOTTED = "dotted"
    OPEN = "open"
    DOTTED_OPEN = "dotted_open"


class ControlKind(StrEnum):
    LOOP = "loop"
    ALT = "alt"
    ELSE = "else"
    OPT = "opt"
    PAR = "par"
    AND = "and"
    CRITICAL = "critical"
    OPTION = "option"
    BREAK = "break"
    RECT = "rect"
    END = "end"


class DirectiveKind(StrEnum):
    AUTONUMBER = "autonumber"


class ParticipantAction(StrEnum):
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    CREATE = "create"
    DESTROY = "destroy"


class Message(Relation):
    message_kind: MessageKind = MessageKind.SOLID
    activate: bool = False
    deactivate: bool = False


class ParticipantEvent(Relation):
    action: str = Field(
        default="activate",
        pattern=r"^(?:activate|deactivate|create|destroy)$",
        json_schema_extra={"enum": ["activate", "deactivate", "create", "destroy"]},
    )


class Control(Relation):
    control_kind: ControlKind = ControlKind.END


class Directive(Relation):
    directive_kind: DirectiveKind = DirectiveKind.AUTONUMBER
