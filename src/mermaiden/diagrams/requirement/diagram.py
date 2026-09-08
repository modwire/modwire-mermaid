from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .configuration import RequirementDiagramConfiguration
from .constraints import RequirementDiagramConstraint
from .elements import (
    Requirement,
    RequirementElement,
    RequirementType,
    Risk,
    VerificationMethod,
)
from .relations import RequirementRelation, RequirementRelationKind


@injectable(as_type=DiagramModel, qualifier="requirement", lifetime="transient")
@dataclass(frozen=True, slots=True)
class RequirementDiagram(DiagramModel):
    constraints: Sequence[RequirementDiagramConstraint]
    configuration: RequirementDiagramConfiguration = field(default_factory=RequirementDiagramConfiguration, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "requirementDiagram",
        "Requirement diagram",
        "requirement",
        "RequirementDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return element_type in (Requirement, RequirementElement) and parent_type is None

    def add_requirement(
        self,
        id: str,
        requirement_id: str,
        text: str,
        requirement_type: RequirementType = RequirementType.REQUIREMENT,
        risk: Risk = Risk.MEDIUM,
        verification_method: VerificationMethod = VerificationMethod.ANALYSIS,
    ) -> ChangeReport:
        return self._add_element(
            f"add requirement '{id}'",
            Requirement(
                id=id,
                label=id,
                requirement_id=requirement_id,
                text=text,
                requirement_type=requirement_type,
                risk=risk,
                verification_method=verification_method,
            ),
        )

    def add_element(self, id: str, element_type: str, document_reference: str) -> ChangeReport:
        return self._add_element(
            f"add element '{id}'",
            RequirementElement(id=id, label=id, element_type=element_type, document_reference=document_reference),
        )

    def add_relation(
        self,
        id: str,
        source_id: str,
        target_id: str,
        relation_kind: RequirementRelationKind,
    ) -> ChangeReport:
        return self._add_relation(
            f"add {relation_kind.value} relation '{id}'",
            RequirementRelation(id=id, element_ids=(source_id, target_id), label="", relation_kind=relation_kind),
        )

    def remove_relation(self, id: str, *, cascade: bool = False) -> ChangeReport:
        return DiagramModel.remove_relation(self, id, cascade=cascade)
