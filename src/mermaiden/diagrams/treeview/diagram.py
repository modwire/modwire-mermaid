from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .annotations import TreeAnnotations
from .configuration import TreeViewDiagramConfiguration
from .constraints.domain import TreeViewConstraint
from .elements import TreeItem, TreeItemType
from .relations import TreeBranch


@injectable(as_type=DiagramModel, qualifier="treeview", lifetime="transient")
@dataclass(frozen=True, slots=True)
class TreeView(DiagramModel):
    constraints: Sequence[TreeViewConstraint]
    configuration: TreeViewDiagramConfiguration = field(default_factory=TreeViewDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "treeView-beta",
        "Tree view",
        "treeView",
        "TreeViewDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type is TreeItem and parent_type is None

    @property
    def tree_roots(self) -> tuple[TreeItem, ...]:
        child_ids = {
            relation.child_id
            for relation in self.find_relations()
            if isinstance(relation, TreeBranch) and len(relation.element_ids) == 2
        }
        return tuple(item for item in self.root_elements if isinstance(item, TreeItem) and item.id not in child_ids)

    def add_item(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add tree item '{id}'", TreeItem(id=id, label=label))

    def add_directory(self, id: str, label: str) -> ChangeReport:
        return self._add_typed_item(id, label, TreeItemType.DIRECTORY)

    def add_file(self, id: str, label: str) -> ChangeReport:
        return self._add_typed_item(id, label, TreeItemType.FILE)

    def classify_item(self, id: str, item_type: TreeItemType) -> ChangeReport:
        return self.update_element(id, TreeItem.kind_for(), {"item_type": item_type})

    def add_branch(self, id: str, parent_id: str, child_id: str) -> ChangeReport:
        return self._add_relation(f"add tree branch '{id}'", TreeBranch(id=id, element_ids=(parent_id, child_id)))

    def add_annotation(
        self,
        id: str,
        element_id: str,
        *,
        highlight: bool = False,
        icon: str = "",
        description: str = "",
    ) -> ChangeReport:
        return self._annotate(
            f"add tree annotation '{id}'",
            TreeAnnotations(),
            id,
            {"highlight": highlight, "icon": icon, "description": description},
            (element_id,),
        )

    def _add_typed_item(self, id: str, label: str, item_type: TreeItemType) -> ChangeReport:
        operation = f"add tree {item_type.value} '{id}'"
        if "/" in label or "\\" in label:
            self._reject(
                operation, f"{item_type.value.capitalize()} '{id}' label must be a basename without path separators."
            )
        return self._add_element(operation, TreeItem(id=id, label=label, item_type=item_type))
