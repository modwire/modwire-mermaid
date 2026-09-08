from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .annotations import ClassNotes
from .configuration import ClassDiagramConfiguration
from .constraints import ClassDiagramConstraint
from .elements import Class, ClassNamespace
from .relations import ClassRelation, ClassRelationKind
from .values.members import ClassAttribute, ClassMethod
from .values.text import ClassIdentifier, ClassText, MemberName, OptionalClassText


@injectable(as_type=DiagramModel, qualifier="classdiagram", lifetime="transient")
@dataclass(frozen=True, slots=True)
class ClassDiagram(DiagramModel):
    constraints: Sequence[ClassDiagramConstraint]
    configuration: ClassDiagramConfiguration = field(default_factory=ClassDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "classDiagram",
        "Class diagram",
        "class",
        "ClassDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is ClassNamespace:
            return parent_type is None
        return element_type is Class and (parent_type is None or parent_type is ClassNamespace)

    def add_class(
        self,
        id: ClassIdentifier,
        label: ClassText,
        *,
        attributes: Sequence[ClassAttribute] = (),
        methods: Sequence[ClassMethod] = (),
        annotations: Sequence[MemberName] = (),
        comment: OptionalClassText = "",
        parent_id: str = "",
    ) -> ChangeReport:
        return self._add_element(
            f"add class '{id}'",
            Class(
                id=id,
                label=label,
                attributes=tuple(attributes),
                methods=tuple(methods),
                annotations=tuple(annotations),
                comment=comment,
            ),
            parent_id,
        )

    def add_namespace(
        self, id: ClassIdentifier, label: OptionalClassText = "", *, comment: OptionalClassText = ""
    ) -> ChangeReport:
        return self._add_element(
            f"add namespace '{id}'", ClassNamespace(id=id, label=label or id, elements=(), comment=comment)
        )

    def add_relation(
        self,
        id: ClassIdentifier,
        source_id: ClassIdentifier,
        target_id: ClassIdentifier,
        relation_kind: ClassRelationKind = ClassRelationKind.ASSOCIATION,
        label: OptionalClassText = "",
        source_label: OptionalClassText = "",
        target_label: OptionalClassText = "",
    ) -> ChangeReport:
        return self._add_relation(
            f"add class relation '{id}'",
            ClassRelation(
                id=id,
                element_ids=(source_id, target_id),
                label=label,
                relation_kind=relation_kind,
                source_label=source_label,
                target_label=target_label,
            ),
        )

    def add_note(self, id: ClassIdentifier, class_id: ClassIdentifier, text: ClassText) -> ChangeReport:
        return self._annotate(f"add class note '{id}'", ClassNotes(), id, {"text": text}, (class_id,))
