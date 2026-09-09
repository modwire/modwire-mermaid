import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from inspect import isabstract
from types import UnionType
from typing import Annotated, Any, get_args, get_origin

from pydantic import BaseModel, TypeAdapter
from wireup import injectable

from ...core.naming import ClassName
from ...runtime.snapshot.domain import SnapshotContract, SnapshotError, SnapshotType, SnapshotTypeRegistry
from ..application import DiagramsApplication


@injectable(as_type=SnapshotTypeRegistry, lifetime="scoped")
@dataclass(frozen=True)
class DiagramSnapshotRegistry:
    diagrams: DiagramsApplication

    def contract(self, owner: str) -> SnapshotContract:
        try:
            return self.contracts[owner]
        except KeyError:
            raise SnapshotError(f"Snapshot diagram kind '{owner}' is not registered.") from None

    def reference(self, owner: str, value_type: type[object]) -> str:
        contract = self.contract(owner)
        match = next((item.discriminator for item in contract.types if item.value_type is value_type), None)
        if match is None:
            raise SnapshotError(f"Snapshot type '{value_type.__name__}' is not registered for '{owner}'.")
        return match

    def resolve(self, owner: str, discriminator: str, expected: Any) -> type[Any]:
        contract = self.contract(owner)
        match = next((item.value_type for item in contract.types if item.discriminator == discriminator), None)
        if match is None:
            raise SnapshotError(f"Snapshot discriminator '{discriminator}' is not registered for '{owner}'.")
        origin = get_origin(expected)
        candidates = get_args(expected) if origin is UnionType else (expected,)
        valid = expected is object or any(
            isinstance(candidate, type) and issubclass(match, candidate) for candidate in candidates
        )
        if not valid:
            raise SnapshotError(f"Snapshot discriminator '{discriminator}' is not valid here.")
        return match

    @cached_property
    def contracts(self) -> dict[str, SnapshotContract]:
        contracts: dict[str, SnapshotContract] = {}
        for info in self.diagrams:
            diagram = self.diagrams.get_diagram(info.id)
            feature = diagram.feature
            roots = (
                self._type(info.id, "configuration", type(diagram.configuration)),
                *(self._type(info.id, "element", item) for item in feature.elements),
                *(self._type(info.id, "relation", item) for item in feature.relations),
                *(self._type(info.id, "annotation", item) for item in feature.annotations),
            )
            registered = {item.value_type: item for item in roots}
            expanded: set[type[object]] = set()
            pending: list[object] = [*(item.value_type for item in roots)]
            pending.extend(item.annotation for item in feature.snapshot_properties)
            while pending:
                annotation = pending.pop()
                origin = get_origin(annotation)
                if origin is Annotated:
                    pending.append(get_args(annotation)[0])
                    continue
                if origin is not None:
                    pending.extend(get_args(annotation))
                    continue
                if not isinstance(annotation, type):
                    continue
                if annotation in expanded:
                    continue
                expanded.add(annotation)
                if issubclass(annotation, Enum):
                    registered.setdefault(annotation, self._type(info.id, "enum", annotation))
                    continue
                if not issubclass(annotation, BaseModel) or isabstract(annotation):
                    continue
                registered.setdefault(annotation, self._type(info.id, "value", annotation))
                pending.extend(field.annotation for field in annotation.model_fields.values())

            discriminators = [item.discriminator for item in registered.values()]
            if len(discriminators) != len(set(discriminators)):
                raise RuntimeError(f"Snapshot discriminators for '{info.id}' are not unique.")
            contracts[info.id] = SnapshotContract(
                owner=info.id,
                configuration=roots[0],
                elements=roots[1 : 1 + len(feature.elements)],
                relations=roots[1 + len(feature.elements) : 1 + len(feature.elements) + len(feature.relations)],
                annotations=roots[1 + len(feature.elements) + len(feature.relations) :],
                values=tuple(item for item in registered.values() if "/value/" in item.discriminator),
                enums=tuple(item for item in registered.values() if "/enum/" in item.discriminator),
                properties={item.name: item.annotation for item in feature.snapshot_properties},
            )
        return contracts

    @cached_property
    def fingerprint(self) -> str:
        document = {
            owner: {
                "types": {
                    item.discriminator: self._schema(item.value_type)
                    for item in sorted(contract.types, key=lambda candidate: candidate.discriminator)
                },
                "properties": {
                    name: TypeAdapter(annotation).json_schema()
                    for name, annotation in sorted(contract.properties.items())
                },
            }
            for owner, contract in sorted(self.contracts.items())
        }
        encoded = json.dumps(document, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        return hashlib.sha256(encoded.encode()).hexdigest()

    def _type(self, owner: str, category: str, value_type: type[Any]) -> SnapshotType:
        return SnapshotType(f"mermaiden/{category}/{owner}/{ClassName(value_type).snake_case}", value_type)

    def _schema(self, value_type: type[Any]) -> object:
        if issubclass(value_type, BaseModel):
            return value_type.model_json_schema()
        if issubclass(value_type, Enum):
            return TypeAdapter(value_type).json_schema()
        raise TypeError(f"Snapshot type '{value_type.__name__}' has no schema.")
