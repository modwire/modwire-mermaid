from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import UnionType
from typing import Annotated, Any, cast, get_args, get_origin

from pydantic import BaseModel
from wireup import injectable

from .domain import SnapshotContract, SnapshotError, SnapshotTypeRegistry
from .value_validator import SnapshotValueValidator


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class SnapshotValueDecoder:
    types: SnapshotTypeRegistry
    values: SnapshotValueValidator

    def decode(self, value: object, contract: SnapshotContract, expected: Any = object) -> Any:
        origin = get_origin(expected)
        arguments = get_args(expected)
        if origin is Annotated:
            expected = arguments[0]
            origin = get_origin(expected)
            arguments = get_args(expected)
        if isinstance(value, Mapping) and "$enum" in value:
            enum_value = cast(Mapping[str, Any], value)
            enum = self.types.resolve(
                contract.owner,
                self.values.string(enum_value["$enum"], "$enum"),
                Enum,
            )
            return cast(Callable[[object], Enum], enum)(enum_value["value"])
        if isinstance(value, Mapping) and "$type" in value:
            typed_value = cast(Mapping[str, Any], value)
            item_type = self.types.resolve(
                contract.owner,
                self.values.string(typed_value["$type"], "$type"),
                expected,
            )
            values = dict(self.values.mapping(typed_value.get("fields"), "fields"))
            if not issubclass(item_type, BaseModel):
                raise SnapshotError(f"Snapshot type '{item_type.__name__}' is not a value model.")
            expected_fields = set(item_type.model_fields)
            received_fields = set(values)
            if received_fields != expected_fields:
                missing = sorted(expected_fields - received_fields)
                extra = sorted(received_fields - expected_fields)
                details = [*(f"missing '{name}'" for name in missing), *(f"unsupported '{name}'" for name in extra)]
                raise SnapshotError(f"Snapshot fields are invalid: {', '.join(details)}.")
            parameters: dict[str, Any] = {}
            for name, item in values.items():
                try:
                    parameters[name] = self.decode(item, contract, item_type.model_fields[name].annotation)
                except SnapshotError as error:
                    raise SnapshotError(f"Invalid snapshot field '{name}': {error}") from error
                except ValueError as error:
                    raise ValueError(f"Invalid snapshot field '{name}': {error}") from error
            return item_type.model_validate(parameters)
        if origin in (tuple, list):
            if not isinstance(value, list):
                raise SnapshotError("Snapshot collection is malformed.")
            item_type = arguments[0] if arguments else object
            items = [self.decode(item, contract, item_type) for item in cast(list[Any], value)]
            return tuple(items) if origin is tuple else items
        if isinstance(origin, type) and issubclass(origin, Mapping):
            if not isinstance(value, Mapping):
                raise SnapshotError("Snapshot mapping is malformed.")
            value_type = arguments[1] if len(arguments) > 1 else object
            mapping = cast(Mapping[Any, Any], value)
            return {str(key): self.decode(item, contract, value_type) for key, item in mapping.items()}
        if origin is UnionType:
            for item_type in arguments:
                if item_type is type(None) and value is None:
                    return None
                try:
                    return self.decode(cast(Any, value), contract, item_type)
                except (TypeError, ValueError, SnapshotError):
                    continue
            raise SnapshotError("Snapshot value does not match its declared type.")
        if isinstance(expected, type) and issubclass(expected, Enum):
            return expected(value)
        return cast(Any, value)
