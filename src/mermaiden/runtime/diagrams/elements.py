from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from pydantic import ValidationError

from ...core.domain import Container, Diagram, Element, OperationError
from .state import DiagramData, DiagramState


@dataclass(frozen=True, slots=True)
class Elements:
    state: DiagramState

    def add(self, element: Element, parent_id: str, diagram: Diagram) -> DiagramData:
        self._validate_placement(element, self._parent(parent_id), diagram)
        elements = self._insert(self.state.current.elements, element, parent_id)
        return replace(self.state.current, elements=elements)

    def remove(self, id: str, descendant_ids: Sequence[str] = ()) -> tuple[DiagramData, tuple[str, ...]]:
        target = self.find(id)
        if target is None:
            raise OperationError(f"Element '{id}' does not exist.")
        selected = {*(item.id for item in self._walk((target,))), *descendant_ids}
        removed = tuple(item.id for item in self.walk() if item.id in selected)
        elements = self.state.current.elements
        for removed_id in removed:
            elements = self._remove(elements, removed_id)
        return replace(self.state.current, elements=elements), removed

    def update(self, id: str, kind: str, changes: Mapping[str, object]) -> DiagramData:
        target = self._require_unique(id)
        self._validate_update(target, kind, changes)
        values = target.model_dump(exclude={"elements"})
        values.update(changes)
        try:
            updated = type(target).model_validate(values)
        except ValidationError as error:
            raise OperationError(f"Element '{id}' changes are invalid: {error}") from error
        if isinstance(target, Container):
            updated = updated.model_copy(update={"elements": target.elements})
        elements = self._replace(self.state.current.elements, id, updated)
        return replace(self.state.current, elements=elements)

    def move(
        self,
        id: str,
        kind: str,
        parent_id: str,
        position: int | None,
        diagram: Diagram,
    ) -> DiagramData:
        target = self._require_unique(id)
        if target.kind != kind:
            raise OperationError(f"Element '{id}' has kind '{target.kind}', not '{kind}'.")
        parent = self._parent(parent_id)
        self._validate_placement(target, parent, diagram)
        if parent is not None and parent_id in {item.id for item in self._walk((target,))}:
            raise OperationError(f"Element '{id}' cannot be moved into its own subtree.")

        elements = self._remove(self.state.current.elements, id)
        members = elements if not parent_id else self._children(elements, parent_id)
        if position is not None and not 0 <= position <= len(members):
            raise OperationError(f"Position {position} is outside the range 0..{len(members)}.")
        insertion = len(members) if position is None else position
        moved = self._insert_at(elements, parent_id, target, insertion)
        return replace(self.state.current, elements=moved)

    def _parent(self, parent_id: str) -> Container | None:
        if not parent_id:
            return None
        parent = self._require_unique(parent_id)
        if not isinstance(parent, Container):
            raise OperationError(f"Parent element '{parent_id}' is not a container.")
        return parent

    def _validate_placement(self, element: Element, parent: Container | None, diagram: Diagram) -> None:
        if diagram.accepts_parent(type(element), None if parent is None else type(parent)):
            return
        destination = "$root" if parent is None else f"{parent.kind} '{parent.id}'"
        raise OperationError(f"Element '{element.id}' of kind '{element.kind}' cannot be placed in {destination}.")

    def reorder(self, parent_id: str, element_ids: Sequence[str]) -> DiagramData:
        elements = self.state.current.elements
        members = elements if not parent_id else self._children(elements, parent_id)
        current_ids = tuple(item.id for item in members)
        requested_ids = tuple(element_ids)
        if len(current_ids) != len(set(current_ids)):
            raise OperationError(f"Elements in '{parent_id or '$root'}' do not have unique IDs.")
        if len(requested_ids) != len(set(requested_ids)):
            raise OperationError("Element order must not contain duplicate IDs.")
        if len(requested_ids) != len(current_ids) or set(requested_ids) != set(current_ids):
            raise OperationError(f"Element order must be an exact permutation of '{parent_id or '$root'}'.")
        by_id = {item.id: item for item in members}
        ordered = tuple(by_id[item] for item in requested_ids)
        reordered = ordered if not parent_id else self._replace_children(elements, parent_id, ordered)
        return replace(self.state.current, elements=reordered)

    def find(self, id: str) -> Element | None:
        return next((item for item in self.walk() if item.id == id), None)

    def walk(self, parent_id: str = "") -> tuple[Element, ...]:
        roots = self.state.current.elements
        if parent_id:
            parent = self.find(parent_id)
            if not isinstance(parent, Container):
                return ()
            roots = parent.elements
        return self._walk(roots)

    def _require_unique(self, id: str) -> Element:
        matches = tuple(item for item in self._walk(self.state.current.elements) if item.id == id)
        if not matches:
            raise OperationError(f"Element '{id}' does not exist.")
        if len(matches) > 1:
            raise OperationError(f"Element '{id}' is duplicated.")
        return next(iter(matches))

    def _validate_update(
        self,
        target: Element,
        kind: str,
        changes: Mapping[str, object],
    ) -> None:
        if target.kind != kind:
            raise OperationError(f"Element '{target.id}' has kind '{target.kind}', not '{kind}'.")
        if not changes:
            raise OperationError("Element changes must contain at least one field.")
        immutable = set(changes).intersection({"id", "elements"})
        if immutable:
            raise OperationError(f"Element fields cannot be updated: {', '.join(sorted(immutable))}.")
        unknown = set(changes).difference(type(target).model_fields)
        if unknown:
            raise OperationError(f"Unknown element fields: {', '.join(sorted(unknown))}.")

    def _insert(
        self,
        elements: tuple[Element, ...],
        element: Element,
        parent_id: str,
    ) -> tuple[Element, ...]:
        if not parent_id:
            return (*elements, element)
        parent = self.find(parent_id)
        if parent is None:
            raise OperationError(f"Parent element '{parent_id}' does not exist.")
        if not isinstance(parent, Container):
            raise OperationError(f"Parent element '{parent_id}' is not a container.")
        return self._append_child(elements, parent_id, element)

    def _append_child(
        self,
        elements: tuple[Element, ...],
        parent_id: str,
        child: Element,
    ) -> tuple[Element, ...]:
        result: list[Element] = []
        for element in elements:
            if element.id == parent_id and isinstance(element, Container):
                result.append(element.model_copy(update={"elements": (*element.elements, child)}))
            elif isinstance(element, Container):
                result.append(
                    element.model_copy(update={"elements": self._append_child(element.elements, parent_id, child)})
                )
            else:
                result.append(element)
        return tuple(result)

    def _insert_at(
        self,
        elements: tuple[Element, ...],
        parent_id: str,
        element: Element,
        position: int,
    ) -> tuple[Element, ...]:
        if not parent_id:
            return (*elements[:position], element, *elements[position:])
        result: list[Element] = []
        for item in elements:
            if item.id == parent_id and isinstance(item, Container):
                children = (*item.elements[:position], element, *item.elements[position:])
                result.append(item.model_copy(update={"elements": children}))
            elif isinstance(item, Container):
                result.append(
                    item.model_copy(
                        update={
                            "elements": self._insert_at(
                                item.elements,
                                parent_id,
                                element,
                                position,
                            )
                        }
                    )
                )
            else:
                result.append(item)
        return tuple(result)

    def _children(
        self,
        elements: tuple[Element, ...],
        parent_id: str,
    ) -> tuple[Element, ...]:
        matches = tuple(item for item in self._walk(elements) if item.id == parent_id)
        if not matches:
            raise OperationError(f"Parent element '{parent_id}' does not exist.")
        if len(matches) > 1:
            raise OperationError(f"Parent element '{parent_id}' is duplicated.")
        parent = next(iter(matches))
        if not isinstance(parent, Container):
            raise OperationError(f"Parent element '{parent_id}' is not a container.")
        return parent.elements

    def _replace(
        self,
        elements: tuple[Element, ...],
        id: str,
        replacement: Element,
    ) -> tuple[Element, ...]:
        return tuple(
            replacement
            if item.id == id
            else item.model_copy(update={"elements": self._replace(item.elements, id, replacement)})
            if isinstance(item, Container)
            else item
            for item in elements
        )

    def _replace_children(
        self,
        elements: tuple[Element, ...],
        parent_id: str,
        children: tuple[Element, ...],
    ) -> tuple[Element, ...]:
        return tuple(
            item.model_copy(update={"elements": children})
            if item.id == parent_id and isinstance(item, Container)
            else item.model_copy(update={"elements": self._replace_children(item.elements, parent_id, children)})
            if isinstance(item, Container)
            else item
            for item in elements
        )

    def _remove(self, elements: tuple[Element, ...], id: str) -> tuple[Element, ...]:
        return tuple(
            element.model_copy(update={"elements": self._remove(element.elements, id)})
            if isinstance(element, Container)
            else element
            for element in elements
            if element.id != id
        )

    def _walk(self, elements: tuple[Element, ...]) -> tuple[Element, ...]:
        result: list[Element] = []
        for element in elements:
            result.append(element)
            if isinstance(element, Container):
                result.extend(self._walk(element.elements))
        return tuple(result)
