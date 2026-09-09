from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, cast, overload

from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import CoreSchema, SchemaSerializer, SchemaValidator, core_schema


class ApplicationError(RuntimeError):
    pass


class UnknownCommand(ApplicationError):
    pass


@dataclass(frozen=True, slots=True)
class DiagramCommand:
    operation: str
    arguments: Mapping[str, object]


class JsonSchema(Mapping[str, object], ABC):
    @overload
    @abstractmethod
    def __getitem__(self, key: Literal["properties", "$defs"]) -> Mapping[str, "JsonSchema"]: ...

    @overload
    @abstractmethod
    def __getitem__(self, key: Literal["required"]) -> Sequence[str]: ...

    @overload
    @abstractmethod
    def __getitem__(self, key: Literal["minItems", "maxItems"]) -> int: ...

    @overload
    @abstractmethod
    def __getitem__(self, key: str) -> object: ...


class ValidatedCommandPayload(Protocol):
    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] = "python",
        by_alias: bool = False,
        exclude_unset: bool = False,
    ) -> dict[str, object]: ...


class CommandPayload(Protocol):
    def model_validate(self, value: object) -> ValidatedCommandPayload: ...

    def model_json_schema(self) -> JsonSchema: ...


class CommandPayloadSchema:
    def __init__(self, schema: CoreSchema, invocation_defaults: Sequence[str], description: str = "") -> None:
        definitions: dict[str, CoreSchema] = {}
        normalized = cast(CoreSchema, self._definitions(schema, definitions))
        self._schema = core_schema.definitions_schema(normalized, list(definitions.values()))
        self._invocation_defaults = frozenset(invocation_defaults)
        self._description = description
        self._validator = SchemaValidator(self._schema)
        self._serializer = SchemaSerializer(self._schema)

    def _definitions(self, value: object, definitions: dict[str, CoreSchema]) -> object:
        if isinstance(value, dict):
            node = cast(dict[str, object], value)
            if node.get("type") == "definitions":
                for definition in cast(list[CoreSchema], node["definitions"]):
                    reference = definition.get("ref")
                    if not isinstance(reference, str):
                        raise TypeError("A shared schema definition must have a reference.")
                    if reference not in definitions:
                        definitions[reference] = definition
                        definitions[reference] = cast(CoreSchema, self._definitions(definition, definitions))
                return self._definitions(node["schema"], definitions)
            return {key: self._definitions(item, definitions) for key, item in node.items()}
        if isinstance(value, list):
            return [self._definitions(item, definitions) for item in cast(list[object], value)]
        return value

    def model_validate(self, value: object) -> ValidatedCommandPayload:
        fields_set: frozenset[str] = frozenset()
        if isinstance(value, Mapping):
            mapping = cast(Mapping[object, object], value)
            fields_set = frozenset(name for name in mapping if isinstance(name, str))
        validated = self._validator.validate_python(value)
        if not isinstance(validated, dict):
            raise TypeError("A command payload must validate to an object.")
        values: dict[str, object] = {}
        for name, item in cast(dict[object, object], validated).items():
            if not isinstance(name, str):
                raise TypeError("A command payload field name must be a string.")
            values[name] = item
        fields_set = fields_set.union(self._invocation_defaults.intersection(values))
        return CommandArguments(values, fields_set, self._serializer)

    def model_json_schema(self) -> JsonSchema:
        schema = GenerateJsonSchema().generate(self._schema)
        if self._description:
            schema["description"] = self._description
        return cast(JsonSchema, schema)


class CommandArguments:
    def __init__(
        self,
        values: dict[str, object],
        fields_set: frozenset[str],
        serializer: SchemaSerializer,
    ) -> None:
        self._values = values
        self._fields_set = fields_set
        self._serializer = serializer

    def model_dump(
        self,
        *,
        mode: Literal["json", "python"] = "python",
        by_alias: bool = False,
        exclude_unset: bool = False,
    ) -> dict[str, object]:
        serialized = self._serializer.to_python(self._values, mode=mode, by_alias=by_alias)
        if not isinstance(serialized, dict):
            raise TypeError("A command payload must serialize to an object.")
        values: dict[str, object] = {}
        for name, item in cast(dict[object, object], serialized).items():
            if not isinstance(name, str):
                raise TypeError("A command payload field name must be a string.")
            values[name] = item
        if exclude_unset:
            return {name: value for name, value in values.items() if name in self._fields_set}
        return values
