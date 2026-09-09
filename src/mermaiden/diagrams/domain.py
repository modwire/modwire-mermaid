from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, ClassVar, cast

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from ..core.domain import (
    Annotation,
    BlockingConstraint,
    ChangeReport,
    Constraint,
    ConstraintDiagram,
    Container,
    Diagram,
    Element,
    Relation,
    RequiresChildren,
    ValidationReport,
    Violation,
)
from ..core.naming import ClassName
from ..runtime.diagrams.aggregate import DiagramAggregate
from ..runtime.domain import ConstraintInspection


class MutationKernel(ABC):
    @abstractmethod
    def update_element(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport: ...

    @abstractmethod
    def update_relation(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport: ...

    @abstractmethod
    def update_annotation(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport: ...

    @abstractmethod
    def move_element(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        parent_id: str,
        position: int | None,
    ) -> ChangeReport: ...

    @abstractmethod
    def reorder_elements(
        self,
        diagram: DiagramAggregate,
        parent_id: str,
        element_ids: Sequence[str],
    ) -> ChangeReport: ...


class MermaidConfigurationNaming:
    def __call__(self, value: str) -> str:
        first, *remaining = value.split("_")
        return first + "".join(word.capitalize() for word in remaining)


class MermaidConfigurationModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=MermaidConfigurationNaming(),
        extra="forbid",
        frozen=True,
        populate_by_name=True,
        validate_default=True,
    )


class MermaidConfiguration(MermaidConfigurationModel):
    wrap: bool
    diagrams: Mapping[str, SerializeAsAny["MermaidDiagramConfiguration"]]

    def to_mermaid(self) -> dict[str, object]:
        document = self.model_dump(mode="json", by_alias=True, exclude={"diagrams"})
        diagrams = {
            key: value.model_dump(mode="json", by_alias=True, exclude={"wrap"}) for key, value in self.diagrams.items()
        }
        return {**document, **{key: value for key, value in diagrams.items() if value}}


class MermaidDiagramConfiguration(MermaidConfigurationModel):
    wrap: bool = True

    def document(self, source: str) -> MermaidConfiguration:
        return MermaidConfiguration(wrap=self.wrap, diagrams={source: self})


@dataclass(frozen=True, slots=True)
class DiagramObserver[ConstraintT: Constraint](ConstraintInspection):
    structure: ConstraintInspection
    constraints: Sequence[ConstraintT]

    def inspect(self, diagram: Diagram) -> ValidationReport:
        structural = self.structure.inspect(diagram)
        domain = tuple(violation for constraint in self.constraints for violation in diagram.accept(constraint))
        return ValidationReport((*structural.violations, *domain))


@dataclass(frozen=True, slots=True)
class DiagramConstraint(BlockingConstraint):
    @property
    def code(self) -> str:
        package = getattr(self, "package", type(self).__module__)
        boundary = "constraints" if ".constraints." in package else package.rsplit(".", maxsplit=1)[-1]
        return f"{boundary}.{ClassName(type(self)).snake_case}"


@dataclass(frozen=True, slots=True)
class Members(DiagramConstraint):
    elements: tuple[type[Element], ...]
    relations: tuple[type[Relation], ...]
    annotations: tuple[type[Annotation], ...]

    def visit(self, diagram: ConstraintDiagram) -> tuple[Violation, ...]:
        issues = [
            self.violation(
                f"Element '{item.id}' does not belong to this diagram.",
                path=f"elements.{item.id}",
            )
            for item in diagram.walk_elements("")
            if type(item) not in self.elements
        ]
        issues.extend(
            self.violation(
                f"Relation '{item.id}' does not belong to this diagram.",
                path=f"relations.{item.id}",
            )
            for item in diagram.find_relations("")
            if type(item) not in self.relations
        )
        issues.extend(
            self.violation(
                f"Annotation '{item.id}' does not belong to this diagram.",
                path=f"annotations.{item.id}",
            )
            for item in diagram.find_annotations("")
            if type(item) not in self.annotations
        )
        issues.extend(
            self.violation(
                f"Element '{item.id}' must contain at least one child.",
                path=f"elements.{item.id}",
            )
            for item in diagram.walk_elements("")
            if isinstance(item, RequiresChildren) and not cast(Container, item).elements
        )
        return tuple(issues)


@dataclass(frozen=True, slots=True)
class DiagramDefinition:
    syntax: str
    name: str
    config_key: str
    schema_definition: str


@dataclass(frozen=True, slots=True)
class CommandDefault:
    annotation: object
    value: object


@dataclass(frozen=True, slots=True)
class CommandVariadic:
    annotation: object


@dataclass(frozen=True, slots=True)
class DiagramCommandFeature:
    name: str
    parameters: Mapping[str, object]

    @property
    def variadic(self) -> str | None:
        return next((name for name, value in self.parameters.items() if isinstance(value, CommandVariadic)), None)


@dataclass(frozen=True, slots=True)
class PersistedDiagramProperty:
    name: str
    annotation: object


@dataclass(frozen=True, slots=True)
class DiagramFeature:
    configuration: type[MermaidDiagramConfiguration]
    elements: tuple[type[Element], ...] = ()
    relations: tuple[type[Relation], ...] = ()
    annotations: tuple[type[Annotation], ...] = ()
    commands: tuple[DiagramCommandFeature, ...] = ()
    snapshot_properties: tuple[PersistedDiagramProperty, ...] = ()


@dataclass(frozen=True, slots=True)
class DiagramModel(DiagramAggregate):
    definition: ClassVar[DiagramDefinition]
    feature: ClassVar[DiagramFeature]
    structure: ConstraintInspection
    constraints: Sequence[Constraint]
    configuration: MermaidDiagramConfiguration
    mutations: MutationKernel

    def accepts_parent(
        self,
        element_type: type[Element],
        parent_type: type[Container] | None,
    ) -> bool:
        return False

    def update_element(
        self,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport:
        return self.mutations.update_element(self, id, kind, changes)

    def update_relation(
        self,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport:
        return self.mutations.update_relation(self, id, kind, changes)

    def update_annotation(
        self,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport:
        return self.mutations.update_annotation(self, id, kind, changes)

    def move_element(
        self,
        id: str,
        kind: str,
        parent_id: str,
        position: int | None,
    ) -> ChangeReport:
        return self.mutations.move_element(self, id, kind, parent_id, position)

    def reorder_elements(
        self,
        parent_id: str,
        element_ids: Annotated[
            Sequence[Annotated[str, Field(min_length=1)]],
            Field(json_schema_extra={"uniqueItems": True}),
        ],
    ) -> ChangeReport:
        return self.mutations.reorder_elements(self, parent_id, element_ids)

    def configure(self, configuration: MermaidDiagramConfiguration) -> None:
        expected = type(self.configuration)
        if type(configuration) is not expected:
            raise TypeError(
                f"Configuration for '{self.kind}' must be '{expected.__name__}', "
                f"received '{type(configuration).__name__}'."
            )
        object.__setattr__(self, "configuration", configuration)

    @property
    def kind(self) -> str:
        return self.definition.syntax

    @property
    def mermaid_configuration(self) -> Mapping[str, object]:
        return self.configuration.document(self.definition.config_key).to_mermaid()

    @property
    def observer(self) -> DiagramObserver[Constraint]:
        members = Members(self.feature.elements, self.feature.relations, self.feature.annotations)
        return DiagramObserver(self.structure, (members, *self.constraints))


@dataclass(frozen=True, slots=True)
class DiagramInfo:
    id: str
    name: str
    diagram_type: type[DiagramModel]
    config_key: str
    schema_definition: str

    @classmethod
    def from_diagram(cls, diagram: DiagramModel) -> "DiagramInfo":
        return cls(
            id=diagram.definition.syntax,
            name=diagram.definition.name,
            diagram_type=type(diagram),
            config_key=diagram.definition.config_key,
            schema_definition=diagram.definition.schema_definition,
        )
