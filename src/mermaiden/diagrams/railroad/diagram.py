from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import RailroadDiagramConfiguration
from .constraints import RailroadDiagramConstraint
from .elements import (
    AlternativeExpression,
    CompositeExpression,
    GroupExpression,
    NonTerminal,
    OptionalExpression,
    RepetitionExpression,
    SequenceExpression,
    Special,
    Terminal,
)


@injectable(as_type=DiagramModel, qualifier="railroad", lifetime="transient")
@dataclass(frozen=True, slots=True)
class RailroadDiagram(DiagramModel):
    constraints: Sequence[RailroadDiagramConstraint]
    configuration: RailroadDiagramConfiguration = field(default_factory=RailroadDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "railroad-ebnf-beta",
        "Railroad diagram",
        "railroad",
        "RailroadDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        supported = element_type in (
            AlternativeExpression,
            CompositeExpression,
            GroupExpression,
            NonTerminal,
            OptionalExpression,
            RepetitionExpression,
            SequenceExpression,
            Special,
            Terminal,
        )
        if not supported:
            return False
        if parent_type is None:
            return element_type is SequenceExpression
        return issubclass(parent_type, CompositeExpression)

    def add_rule(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add rule '{id}'", SequenceExpression(id=id, label=label))

    def add_terminal(self, id: str, label: str, rule_id: str) -> ChangeReport:
        return self._add_element(f"add terminal '{id}'", Terminal(id=id, label=label), rule_id)

    def add_non_terminal(self, id: str, label: str, rule_id: str) -> ChangeReport:
        return self._add_element(f"add non-terminal '{id}'", NonTerminal(id=id, label=label), rule_id)

    def add_special(self, id: str, label: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add special sequence '{id}'", Special(id=id, label=label), parent_id)

    def add_alternative(self, id: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add alternative '{id}'", AlternativeExpression(id=id, label=id), parent_id)

    def add_optional(self, id: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add optional '{id}'", OptionalExpression(id=id, label=id), parent_id)

    def add_repetition(self, id: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add repetition '{id}'", RepetitionExpression(id=id, label=id), parent_id)

    def add_group(self, id: str, parent_id: str) -> ChangeReport:
        return self._add_element(f"add group '{id}'", GroupExpression(id=id, label=id), parent_id)
