from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.characters import Identifier, OptionalIdentifier, OptionalText, Text
from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    CommandDefault,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from ..flowchart.elements import Direction
from .annotations import NotePosition, StateNote, StateNotes
from .configuration import StateDiagramConfiguration
from .constraints.domain import StateDiagramConstraint
from .elements import Choice, CompositeState, Final, Fork, Initial, Join, State, StateNode
from .relations import StateTransition


@injectable(as_type=DiagramModel, qualifier="state", lifetime="transient")
@dataclass(frozen=True, slots=True)
class StateDiagram(DiagramModel):
    constraints: Sequence[StateDiagramConstraint]
    configuration: StateDiagramConfiguration = field(default_factory=StateDiagramConfiguration, init=False)
    direction: Direction = field(default=Direction.TOP_DOWN, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "stateDiagram-v2",
        "State diagram",
        "state",
        "StateDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=StateDiagramConfiguration,
        elements=(StateNode, State, Initial, Final, Choice, Fork, Join, CompositeState),
        relations=(StateTransition,),
        annotations=(StateNote,),
        commands=(
            DiagramCommandFeature(
                "add_state", {"id": Identifier, "label": Text, "composite_id": CommandDefault(OptionalIdentifier, "")}
            ),
            DiagramCommandFeature(
                "add_initial",
                {"id": Identifier, "composite_id": CommandDefault(OptionalIdentifier, "")},
            ),
            DiagramCommandFeature(
                "add_final",
                {"id": Identifier, "composite_id": CommandDefault(OptionalIdentifier, "")},
            ),
            DiagramCommandFeature(
                "add_composite",
                {"id": Identifier, "label": Text, "composite_id": CommandDefault(OptionalIdentifier, "")},
            ),
            DiagramCommandFeature(
                "add_choice",
                {
                    "id": Identifier,
                    "label": CommandDefault(OptionalText, ""),
                    "composite_id": CommandDefault(OptionalIdentifier, ""),
                },
            ),
            DiagramCommandFeature(
                "add_fork",
                {
                    "id": Identifier,
                    "label": CommandDefault(OptionalText, ""),
                    "composite_id": CommandDefault(OptionalIdentifier, ""),
                },
            ),
            DiagramCommandFeature(
                "add_join",
                {
                    "id": Identifier,
                    "label": CommandDefault(OptionalText, ""),
                    "composite_id": CommandDefault(OptionalIdentifier, ""),
                },
            ),
            DiagramCommandFeature(
                "add_transition",
                {
                    "id": Identifier,
                    "source_id": Identifier,
                    "target_id": Identifier,
                    "label": CommandDefault(OptionalText, ""),
                    "composite_id": CommandDefault(OptionalIdentifier, ""),
                },
            ),
            DiagramCommandFeature(
                "add_note",
                {
                    "id": Identifier,
                    "state_id": Identifier,
                    "text": Text,
                    "position": CommandDefault(NotePosition, NotePosition.RIGHT),
                    "composite_id": CommandDefault(OptionalIdentifier, ""),
                },
            ),
            DiagramCommandFeature("remove_transition", {"id": Identifier}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return (element_type is CompositeState or issubclass(element_type, StateNode)) and (
            parent_type is None or parent_type is CompositeState
        )

    def add_state(self, id: str, label: str, composite_id: str = "") -> ChangeReport:
        return self._add_node(State(id=id, label=label), composite_id, "state")

    def add_initial(self, id: str, composite_id: str = "") -> ChangeReport:
        return self._add_node(Initial(id=id, label="initial"), composite_id, "initial state")

    def add_final(self, id: str, composite_id: str = "") -> ChangeReport:
        return self._add_node(Final(id=id, label="final"), composite_id, "final state")

    def add_composite(self, id: str, label: str, composite_id: str = "") -> ChangeReport:
        return self._add_node(CompositeState(id=id, label=label), composite_id, "composite state")

    def add_choice(self, id: str, label: str = "", composite_id: str = "") -> ChangeReport:
        return self._add_node(Choice(id=id, label=label), composite_id, "choice")

    def add_fork(self, id: str, label: str = "", composite_id: str = "") -> ChangeReport:
        return self._add_node(Fork(id=id, label=label), composite_id, "fork")

    def add_join(self, id: str, label: str = "", composite_id: str = "") -> ChangeReport:
        return self._add_node(Join(id=id, label=label), composite_id, "join")

    def add_transition(
        self,
        id: str,
        source_id: str,
        target_id: str,
        label: str = "",
        composite_id: str = "",
    ) -> ChangeReport:
        return self._add_relation(
            f"add transition '{id}'",
            StateTransition(
                id=id,
                element_ids=(source_id, target_id),
                label=label,
                scope_id=composite_id,
                source_terminal=isinstance(self.find_element(source_id), Initial),
                target_terminal=isinstance(self.find_element(target_id), Final),
            ),
        )

    def add_note(
        self,
        id: str,
        state_id: str,
        text: str,
        position: NotePosition = NotePosition.RIGHT,
        composite_id: str = "",
    ) -> ChangeReport:
        return self._annotate(
            f"add note '{id}'",
            StateNotes(),
            id,
            {"text": text, "position": position, "scope_id": composite_id},
            (state_id,),
        )

    def transitions_for(self, composite_id: str = "") -> tuple[StateTransition, ...]:
        return tuple(
            item
            for item in self.find_relations()
            if isinstance(item, StateTransition) and item.scope_id == composite_id
        )

    def notes_for(self, composite_id: str = "") -> tuple[StateNote, ...]:
        return tuple(
            item for item in self.find_annotations() if isinstance(item, StateNote) and item.scope_id == composite_id
        )

    def remove_transition(self, id: str) -> ChangeReport:
        return self.remove_relation(id)

    def _add_node(self, node: StateNode | CompositeState, composite_id: str, kind: str) -> ChangeReport:
        return self._add_element(f"add {kind} '{node.id}'", node, composite_id)
