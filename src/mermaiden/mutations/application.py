from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from wireup import injectable

from ..core.domain import ChangeReport, OperationError
from ..diagrams.domain import MutationKernel
from ..runtime.diagrams.aggregate import DiagramAggregate
from ..runtime.diagrams.state import DiagramData


@injectable(as_type=MutationKernel)
@dataclass(frozen=True, slots=True)
class DiagramMutationKernel(MutationKernel):
    def update_element(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport:
        operation = f"update element '{id}'"
        try:
            candidate = diagram.elements.update(id, kind, changes)
        except OperationError as error:
            diagram.runtime.transaction.reject(operation, str(error))
        except Exception:
            diagram.runtime.transaction.rollback()
            raise
        return self._commit(diagram, operation, candidate)

    def update_relation(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport:
        operation = f"update relation '{id}'"
        try:
            candidate = diagram.relations.update(id, kind, changes)
        except OperationError as error:
            diagram.runtime.transaction.reject(operation, str(error))
        except Exception:
            diagram.runtime.transaction.rollback()
            raise
        return self._commit(diagram, operation, candidate)

    def update_annotation(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        changes: Mapping[str, object],
    ) -> ChangeReport:
        operation = f"update annotation '{id}'"
        try:
            candidate = diagram.annotations.update(id, kind, changes)
        except OperationError as error:
            diagram.runtime.transaction.reject(operation, str(error))
        except Exception:
            diagram.runtime.transaction.rollback()
            raise
        return self._commit(diagram, operation, candidate)

    def move_element(
        self,
        diagram: DiagramAggregate,
        id: str,
        kind: str,
        parent_id: str,
        position: int | None,
    ) -> ChangeReport:
        operation = f"move element '{id}'"
        if position is not None and (type(position) is not int or position < 0):
            diagram.runtime.transaction.reject(operation, "position must be a nonnegative integer or None.")
        try:
            candidate = diagram.elements.move(id, kind, parent_id, position, diagram)
        except OperationError as error:
            diagram.runtime.transaction.reject(operation, str(error))
        except Exception:
            diagram.runtime.transaction.rollback()
            raise
        return self._commit(diagram, operation, candidate)

    def reorder_elements(
        self,
        diagram: DiagramAggregate,
        parent_id: str,
        element_ids: Sequence[str],
    ) -> ChangeReport:
        operation = f"reorder elements in '{parent_id or '$root'}'"
        try:
            candidate = diagram.elements.reorder(parent_id, element_ids)
        except OperationError as error:
            diagram.runtime.transaction.reject(operation, str(error))
        except Exception:
            diagram.runtime.transaction.rollback()
            raise
        return self._commit(diagram, operation, candidate)

    def _commit(
        self,
        diagram: DiagramAggregate,
        operation: str,
        candidate: DiagramData,
    ) -> ChangeReport:
        return diagram.runtime.transaction.apply_valid_candidate(
            operation,
            candidate,
            diagram,
            diagram.observer,
            (),
        )
