from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from .characters import Identifier, OptionalText, Text
from .naming import ClassName


class OperationError(Exception):
    pass


class ValueModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ClassifiedValueModel(ValueModel):
    @property
    def kind(self) -> str:
        return ClassName(type(self)).snake_case


class TargetKind(StrEnum):
    ELEMENT = "element"
    RELATION = "relation"


class TargetRef(ValueModel):
    kind: TargetKind
    id: str = Field(pattern=Identifier.pattern, description=Identifier.description)


class Annotation(ClassifiedValueModel):
    id: str = Field(pattern=Identifier.pattern, description=Identifier.description)
    targets: tuple[TargetRef, ...]


class DataAnnotation(Annotation):
    data: Mapping[str, object]


class Element(ClassifiedValueModel, ABC):
    id: str = Field(pattern=Identifier.pattern, description=Identifier.description)
    label: str = Field(pattern=Text.pattern, description=Text.description)


class Entity(Element):
    pass


class RequiresChildren:
    elements: tuple[Element, ...]


class Container(Element):
    elements: tuple[Element, ...] = ()


class Relation(ClassifiedValueModel):
    id: str = Field(pattern=Identifier.pattern, description=Identifier.description)
    element_ids: tuple[Annotated[str, Field(pattern=Identifier.pattern, description=Identifier.description)], ...]
    label: str = Field(default="", pattern=OptionalText.pattern, description=OptionalText.description)

    @property
    def source_id(self) -> str:
        return self.element_ids[0] if self.element_ids else ""

    @property
    def target_id(self) -> str:
        return self.element_ids[1] if len(self.element_ids) > 1 else ""


class ConditionalRelation(Relation):
    @property
    def condition(self) -> str:
        return self.label


class ConstraintLevel(StrEnum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class DiagramObjectKind(StrEnum):
    ELEMENT = "element"
    RELATION = "relation"
    ANNOTATION = "annotation"


@dataclass(frozen=True, slots=True)
class DiagramObjectReference:
    kind: DiagramObjectKind
    id: str


class ConstraintDiagram(ABC):
    @property
    @abstractmethod
    def root_elements(self) -> Sequence[Element]: ...

    @abstractmethod
    def walk_elements(self, parent_id: str) -> Sequence[Element]: ...

    @abstractmethod
    def find_relations(self, element_id: str) -> Sequence[Relation]: ...

    @abstractmethod
    def find_annotations(self, target_id: str) -> Sequence[Annotation]: ...


@dataclass(frozen=True, slots=True)
class Violation:
    code: str
    message: str
    path: str = ""
    level: ConstraintLevel = ConstraintLevel.ADVISORY


@dataclass(frozen=True, slots=True)
class ValidationReport:
    violations: tuple[Violation, ...] = ()

    @property
    def blocking(self) -> tuple[Violation, ...]:
        return tuple(item for item in self.violations if item.level is ConstraintLevel.BLOCKING)

    @property
    def advisory(self) -> tuple[Violation, ...]:
        return tuple(item for item in self.violations if item.level is ConstraintLevel.ADVISORY)

    @property
    def can_commit(self) -> bool:
        return not self.blocking

    @property
    def is_valid(self) -> bool:
        return not self.violations

    def __bool__(self) -> bool:
        return self.can_commit


@dataclass(frozen=True, slots=True)
class ChangeReport:
    operation: str
    before: ValidationReport
    after: ValidationReport
    accepted: bool
    removed: tuple[DiagramObjectReference, ...] = ()

    @property
    def introduced(self) -> tuple[Violation, ...]:
        return tuple(item for item in self.after.violations if item not in self.before.violations)

    @property
    def resolved(self) -> tuple[Violation, ...]:
        return tuple(item for item in self.before.violations if item not in self.after.violations)

    @property
    def current(self) -> ValidationReport:
        return self.after if self.accepted else self.before


@dataclass(frozen=True, slots=True)
class ChangeRejected(RuntimeError):
    operation: str
    report: ValidationReport

    def __str__(self) -> str:
        details = "; ".join(item.message for item in self.report.blocking)
        return f"Cannot {self.operation}: {details or 'the operation was rejected.'}"


class Constraint(ABC):
    @property
    @abstractmethod
    def code(self) -> str: ...

    @property
    def level(self) -> ConstraintLevel:
        return ConstraintLevel.ADVISORY

    def visit(self, diagram: ConstraintDiagram) -> tuple[Violation, ...]:
        return ()

    def violation(self, message: str, *, path: str) -> Violation:
        return Violation(code=self.code, message=message, path=path, level=self.level)


class BlockingConstraint(Constraint, ABC):
    @property
    def level(self) -> ConstraintLevel:
        return ConstraintLevel.BLOCKING


Result = TypeVar("Result", covariant=True)


class DiagramVisitor(Protocol[Result]):
    def visit(self, diagram: "Diagram") -> Result: ...


class DiagramView(ConstraintDiagram):
    @property
    @abstractmethod
    def kind(self) -> str: ...

    @property
    @abstractmethod
    def mermaid_configuration(self) -> Mapping[str, object]: ...

    @abstractmethod
    def find_element(self, id: str) -> Element | None: ...

    @abstractmethod
    def validate(self) -> ValidationReport: ...


class Diagram(DiagramView):
    @abstractmethod
    def accepts_parent(
        self,
        element_type: type[Element],
        parent_type: type[Container] | None,
    ) -> bool: ...

    @abstractmethod
    def remove_element(self, id: str, *, cascade: bool) -> ChangeReport: ...

    @abstractmethod
    def remove_relation(self, id: str, *, cascade: bool) -> ChangeReport: ...

    @abstractmethod
    def remove_annotation(self, id: str) -> ChangeReport: ...

    def accept(self, visitor: DiagramVisitor[Result]) -> Result:
        return visitor.visit(self)
