from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Literal

from wireup import injectable

from ...core.characters import Identifier, OptionalText, Text
from ...core.domain import ChangeReport, Container, Element
from ..domain import (
    CommandDefault,
    DiagramCommandFeature,
    DiagramDefinition,
    DiagramFeature,
    DiagramModel,
)
from .configuration import GitGraphDiagramConfiguration
from .constraints import GitGraphDiagramConstraint
from .elements import Branch, Checkout, Commit, CommitType
from .relations import CommitRelation


@injectable(as_type=DiagramModel, qualifier="gitgraph", lifetime="transient")
@dataclass(frozen=True, slots=True)
class GitGraphDiagram(DiagramModel):
    constraints: Sequence[GitGraphDiagramConstraint]
    configuration: GitGraphDiagramConfiguration = field(default_factory=GitGraphDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "gitGraph",
        "Git Graph",
        "gitGraph",
        "GitGraphDiagramConfig",
    )

    feature: ClassVar[DiagramFeature] = DiagramFeature(
        configuration=GitGraphDiagramConfiguration,
        elements=(Commit, Branch, Checkout),
        relations=(CommitRelation,),
        annotations=(),
        commands=(
            DiagramCommandFeature(
                "add_commit",
                {
                    "id": Identifier,
                    "label": Text,
                    "commit_type": CommandDefault(CommitType | Literal[""], ""),
                    "tag": CommandDefault(OptionalText, ""),
                },
            ),
            DiagramCommandFeature(
                "add_branch", {"id": Identifier, "label": Text, "order": CommandDefault(int | None, None)}
            ),
            DiagramCommandFeature("checkout", {"id": Identifier, "branch": Identifier}),
        ),
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type in (Branch, Checkout, Commit) and parent_type is None

    def add_commit(self, id: str, label: str, commit_type: CommitType | str = "", tag: str = "") -> ChangeReport:
        return self._add_element(f"add commit '{id}'", Commit(id=id, label=label, commit_type=commit_type, tag=tag))

    def add_branch(self, id: str, label: str, order: int | None = None) -> ChangeReport:
        return self._add_element(f"add branch '{id}'", Branch(id=id, label=label, order=order))

    def checkout(self, id: str, branch: str) -> ChangeReport:
        return self._add_element(f"checkout branch '{branch}'", Checkout(id=id, label=branch))
