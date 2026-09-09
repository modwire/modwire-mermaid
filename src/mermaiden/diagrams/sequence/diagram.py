from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, ClassVar

from pydantic import Field
from wireup import injectable

from ...core.characters import Identifier, OneOrTwoIdentifiers, OptionalIdentifier, OptionalText, Text
from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    CommandDefault,
    CommandVariadic,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .annotations import NotePosition, SequenceNote, SequenceNotes
from .configuration import SequenceDiagramConfiguration
from .constraints import SequenceConstraint
from .elements import Participant, ParticipantBox, ParticipantKind
from .relations import (
    Control,
    ControlKind,
    Directive,
    DirectiveKind,
    Message,
    MessageKind,
    ParticipantAction,
    ParticipantEvent,
)


@injectable(as_type=DiagramModel, qualifier="sequence", lifetime="transient")
@dataclass(frozen=True, slots=True)
class SequenceDiagram(DiagramModel):
    constraints: Sequence[SequenceConstraint]
    configuration: SequenceDiagramConfiguration = field(default_factory=SequenceDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "sequenceDiagram",
        "Sequence diagram",
        "sequence",
        "SequenceDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=SequenceDiagramConfiguration,
        elements=(Participant, ParticipantBox),
        relations=(Message, ParticipantEvent, Control, Directive),
        annotations=(SequenceNote,),
        commands=(
            DiagramCommandFeature(
                "add_box",
                {"id": Identifier, "label": Text, "color": CommandDefault(OptionalText, "")},
            ),
            DiagramCommandFeature(
                "add_participant",
                {
                    "id": Identifier,
                    "label": Text,
                    "kind": CommandDefault(ParticipantKind, ParticipantKind.PARTICIPANT),
                    "box_id": CommandDefault(OptionalIdentifier, ""),
                    "created": CommandDefault(bool, False),
                },
            ),
            DiagramCommandFeature(
                "add_message",
                {
                    "id": Identifier,
                    "source_id": Identifier,
                    "target_id": Identifier,
                    "label": Text,
                    "kind": CommandDefault(MessageKind, MessageKind.SOLID),
                    "activate": CommandDefault(bool, False),
                    "deactivate": CommandDefault(bool, False),
                },
            ),
            DiagramCommandFeature("activate", {"id": Identifier, "participant_id": Identifier}),
            DiagramCommandFeature("deactivate", {"id": Identifier, "participant_id": Identifier}),
            DiagramCommandFeature("create", {"id": Identifier, "participant_id": Identifier}),
            DiagramCommandFeature("destroy", {"id": Identifier, "participant_id": Identifier}),
            DiagramCommandFeature(
                "control",
                {"id": Identifier, "kind": ControlKind, "label": CommandDefault(OptionalText, "")},
            ),
            DiagramCommandFeature("autonumber", {"id": Identifier}),
            DiagramCommandFeature(
                "add_note",
                {
                    "id": Identifier,
                    "text": Text,
                    "participant_ids": CommandVariadic(OneOrTwoIdentifiers),
                    "position": CommandDefault(NotePosition, NotePosition.OVER),
                },
            ),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is ParticipantBox:
            return parent_type is None
        return element_type is Participant and (parent_type is None or parent_type is ParticipantBox)

    def add_box(self, id: str, label: str, color: str = "") -> ChangeReport:
        return self._add_element(f"add box '{id}'", ParticipantBox(id=id, label=label, elements=(), color=color))

    def add_participant(
        self,
        id: str,
        label: str,
        kind: ParticipantKind = ParticipantKind.PARTICIPANT,
        box_id: str = "",
        created: bool = False,
    ) -> ChangeReport:
        return self._add_element(
            f"add participant '{id}'",
            Participant(id=id, label=label, participant_kind=kind, created=created),
            box_id,
        )

    def add_message(
        self,
        id: str,
        source_id: str,
        target_id: str,
        label: str,
        kind: MessageKind = MessageKind.SOLID,
        activate: bool = False,
        deactivate: bool = False,
    ) -> ChangeReport:
        return self._add_relation(
            f"add message '{id}'",
            Message(
                id=id,
                element_ids=(source_id, target_id),
                label=label,
                message_kind=kind,
                activate=activate,
                deactivate=deactivate,
            ),
        )

    def activate(self, id: str, participant_id: str) -> ChangeReport:
        return self._event(id, participant_id, ParticipantAction.ACTIVATE)

    def deactivate(self, id: str, participant_id: str) -> ChangeReport:
        return self._event(id, participant_id, ParticipantAction.DEACTIVATE)

    def create(self, id: str, participant_id: str) -> ChangeReport:
        return self._event(id, participant_id, ParticipantAction.CREATE)

    def destroy(self, id: str, participant_id: str) -> ChangeReport:
        return self._event(id, participant_id, ParticipantAction.DESTROY)

    def control(self, id: str, kind: ControlKind, label: str = "") -> ChangeReport:
        return self._add_relation(
            f"add {kind.value} '{id}'",
            Control(id=id, element_ids=self._anchors(f"add {kind.value} '{id}'"), label=label, control_kind=kind),
        )

    def autonumber(self, id: str) -> ChangeReport:
        return self._add_relation(
            f"add autonumber '{id}'",
            Directive(
                id=id,
                element_ids=self._anchors(f"add autonumber '{id}'"),
                label="",
                directive_kind=DirectiveKind.AUTONUMBER,
            ),
        )

    def add_note(
        self,
        id: str,
        text: str,
        *participant_ids: Annotated[str, Field(min_length=1, max_length=2)],
        position: NotePosition = NotePosition.OVER,
    ) -> ChangeReport:
        return self._annotate(
            f"add note '{id}'",
            SequenceNotes(),
            id,
            {"text": text, "position": position},
            participant_ids,
        )

    def _event(self, id: str, participant_id: str, action: ParticipantAction) -> ChangeReport:
        return self._add_relation(
            f"{action} '{participant_id}'",
            ParticipantEvent(id=id, element_ids=(participant_id, participant_id), label="", action=action),
        )

    def _anchors(self, operation: str) -> tuple[str, str]:
        participants = [item.id for item in self.walk_elements() if isinstance(item, Participant)]
        if len(participants) < 2:
            self._reject(operation, "Sequence directives require two participants.")
        return participants[0], participants[1]
