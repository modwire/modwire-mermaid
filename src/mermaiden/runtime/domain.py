from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Never

from ..core.domain import (
    BlockingConstraint,
    ChangeRejected,
    ChangeReport,
    ConstraintLevel,
    Diagram,
    DiagramObjectReference,
    ValidationReport,
    Violation,
)
from ..core.naming import ClassName
from .diagrams.annotations import Annotations
from .diagrams.elements import Elements
from .diagrams.relations import Relations
from .diagrams.state import DiagramData, DiagramState


class ConstraintInspection(ABC):
    @abstractmethod
    def inspect(self, diagram: Diagram) -> ValidationReport: ...


class StructureConstraint(BlockingConstraint):
    @property
    def code(self) -> str:
        return f"structure.{ClassName(type(self)).snake_case}"


@dataclass(frozen=True, slots=True)
class ChangeTransaction:
    state: DiagramState

    def apply(
        self,
        operation: str,
        candidate: DiagramData,
        diagram: Diagram,
        observer: ConstraintInspection,
        removed: tuple[DiagramObjectReference, ...],
    ) -> ChangeReport:
        return self._apply(operation, candidate, diagram, observer, removed, False)

    def apply_valid_candidate(
        self,
        operation: str,
        candidate: DiagramData,
        diagram: Diagram,
        observer: ConstraintInspection,
        removed: tuple[DiagramObjectReference, ...],
    ) -> ChangeReport:
        return self._apply(operation, candidate, diagram, observer, removed, True)

    def _apply(
        self,
        operation: str,
        candidate: DiagramData,
        diagram: Diagram,
        observer: ConstraintInspection,
        removed: tuple[DiagramObjectReference, ...],
        require_valid_candidate: bool,
    ) -> ChangeReport:
        before = observer.inspect(diagram)
        self.state.stage(candidate)
        try:
            after = observer.inspect(diagram)
            introduced_structure_violation = any(
                item.code.startswith("structure.") and item not in before.blocking for item in after.blocking
            )
            empty_draft = not candidate.elements and not candidate.relations and not candidate.annotations
            if (
                not after.can_commit
                and (require_valid_candidate or before.can_commit or introduced_structure_violation)
                and not (empty_draft and not require_valid_candidate)
            ):
                raise ChangeRejected(operation, after)
            self.state.commit()
        except Exception:
            self.state.rollback()
            raise
        return ChangeReport(operation, before, after, True, removed)

    def reject(self, operation: str, message: str) -> Never:
        self.state.rollback()
        current = ValidationReport(
            (
                Violation(
                    code="operation.rejected",
                    message=message,
                    path=operation,
                    level=ConstraintLevel.BLOCKING,
                ),
            )
        )
        raise ChangeRejected(operation, current)

    def rollback(self) -> None:
        self.state.rollback()


@dataclass(frozen=True, slots=True)
class DiagramRuntime:
    state: DiagramState = field(default_factory=DiagramState)
    elements: Elements = field(init=False)
    relations: Relations = field(init=False)
    annotations: Annotations = field(init=False)
    transaction: ChangeTransaction = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "elements", Elements(self.state))
        object.__setattr__(self, "relations", Relations(self.state))
        object.__setattr__(self, "annotations", Annotations(self.state))
        object.__setattr__(self, "transaction", ChangeTransaction(self.state))
