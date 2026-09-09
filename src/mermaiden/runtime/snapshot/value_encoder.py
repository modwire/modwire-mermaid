from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel
from wireup import injectable

from .domain import SnapshotTypeRegistry


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class SnapshotValueEncoder:
    types: SnapshotTypeRegistry

    def encode(self, value: object, owner: str) -> Any:
        if isinstance(value, Enum):
            return {"$enum": self.types.reference(owner, type(value)), "value": value.value}
        if isinstance(value, BaseModel):
            return {
                "$type": self.types.reference(owner, type(value)),
                "fields": {name: self.encode(getattr(value, name), owner) for name in type(value).model_fields},
            }
        if isinstance(value, Mapping):
            mapping = cast(Mapping[Any, Any], value)
            return {str(key): self.encode(item, owner) for key, item in mapping.items()}
        if isinstance(value, tuple | list):
            items = cast(list[Any] | tuple[Any, ...], value)
            return [self.encode(item, owner) for item in items]
        return value
