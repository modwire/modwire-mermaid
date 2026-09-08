from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel, MermaidDiagramConfiguration
from .configuration import EntityRelationshipDiagramConfiguration, EntityRelationshipDirection
from .constraints import EntityRelationshipDiagramConstraint
from .elements import Entity, EntityAttribute, EntityAttributeDataType
from .relations import Cardinality, EntityRelationship


@injectable(as_type=DiagramModel, qualifier="er", lifetime="transient")
@dataclass(frozen=True, slots=True)
class EntityRelationshipDiagram(DiagramModel):
    constraints: Sequence[EntityRelationshipDiagramConstraint]
    configuration: EntityRelationshipDiagramConfiguration = field(
        default_factory=EntityRelationshipDiagramConfiguration,
        init=False,
    )
    direction: str = field(default="TB", init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "erDiagram",
        "Entity relationship diagram",
        "er",
        "ErDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        if element_type is Entity:
            return parent_type is None
        return element_type is EntityAttribute and parent_type is Entity

    def configure(self, configuration: MermaidDiagramConfiguration) -> None:
        DiagramModel.configure(self, configuration)
        object.__setattr__(self, "direction", self.configuration.layout_direction)

    def set_direction(self, direction: EntityRelationshipDirection) -> None:
        values = self.configuration.model_dump()
        values["layout_direction"] = direction
        self.configure(EntityRelationshipDiagramConfiguration.model_validate(values))

    def add_entity(self, id: str, label: str) -> ChangeReport:
        return self._add_element(f"add entity '{id}'", Entity(id=id, label=label))

    def add_attribute(
        self,
        id: str,
        label: str,
        data_type: EntityAttributeDataType,
        entity_id: str,
        keys: tuple[str, ...] = (),
        comment: str = "",
    ) -> ChangeReport:
        return self._add_element(
            f"add attribute '{id}'",
            EntityAttribute(id=id, label=label, data_type=data_type, keys=keys, comment=comment),
            entity_id,
        )

    def add_relationship(
        self,
        id: str,
        source_id: str,
        target_id: str,
        label: str,
        source_cardinality: Cardinality = Cardinality.EXACTLY_ONE,
        target_cardinality: Cardinality = Cardinality.EXACTLY_ONE,
        identifying: bool = True,
    ) -> ChangeReport:
        return self._add_relation(
            f"add relationship '{id}'",
            EntityRelationship(
                id=id,
                element_ids=(source_id, target_id),
                label=label,
                source_cardinality=source_cardinality,
                target_cardinality=target_cardinality,
                identifying=identifying,
            ),
        )
