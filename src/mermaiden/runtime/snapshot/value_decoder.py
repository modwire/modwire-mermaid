from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import UnionType
from typing import Annotated, Any, cast, get_args, get_origin, get_type_hints

from wireup import injectable

from .domain import SnapshotError
from .type_resolver import SnapshotTypeResolver
from .value_validator import SnapshotValueValidator


@injectable
@dataclass(frozen=True, slots=True)
class SnapshotValueDecoder:
    types: SnapshotTypeResolver
    values: SnapshotValueValidator

    def decode(self, value: object, expected: Any = object) -> Any:
        origin = get_origin(expected)
        arguments = get_args(expected)
        if origin is Annotated:
            expected = arguments[0]
            origin = get_origin(expected)
            arguments = get_args(expected)
        if isinstance(value, Mapping) and "$enum" in value:
            enum_value = cast(Mapping[str, Any], value)
            enum = self.types.resolve(self.values.string(enum_value["$enum"], "$enum"), Enum)
            return cast(Callable[[object], Enum], enum)(enum_value["value"])
        if isinstance(value, Mapping) and "$type" in value:
            typed_value = cast(Mapping[str, Any], value)
            item_type = self.types.resolve(self.values.string(typed_value["$type"], "$type"), expected)
            values: dict[str, Any] = dict(self.values.mapping(typed_value.get("fields"), "fields"))
            hints: dict[str, Any] = get_type_hints(item_type, include_extras=True)
            parameters: dict[str, Any] = {}
            for name, item in values.items():
                try:
                    parameters[name] = self.decode(item, hints.get(name, object))
                except ValueError as error:
                    raise ValueError(f"Invalid snapshot field '{name}': {error}") from error
            return item_type(**parameters)
        if origin in (tuple, list):
            if not isinstance(value, list):
                raise SnapshotError("Snapshot collection is malformed.")
            item_type = arguments[0] if arguments else object
            items = [self.decode(item, item_type) for item in cast(list[Any], value)]
            return tuple(items) if origin is tuple else items
        if isinstance(origin, type) and issubclass(origin, Mapping):
            if not isinstance(value, Mapping):
                raise SnapshotError("Snapshot mapping is malformed.")
            value_type = arguments[1] if len(arguments) > 1 else object
            mapping = cast(Mapping[Any, Any], value)
            return {str(key): self.decode(item, value_type) for key, item in mapping.items()}
        if origin is UnionType:
            for item_type in arguments:
                if item_type is type(None) and value is None:
                    return None
                try:
                    return self.decode(cast(Any, value), item_type)
                except (TypeError, ValueError, SnapshotError):
                    continue
            raise SnapshotError("Snapshot value does not match its declared type.")
        if isinstance(expected, type) and issubclass(expected, Enum):
            return expected(value)
        return cast(Any, value)
