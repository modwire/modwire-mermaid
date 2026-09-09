from collections.abc import Iterator, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol, cast

from jsonschema import Draft201909Validator
from jsonschema.exceptions import ValidationError
from yaml import safe_load

from ..schema import MermaidConfigurationOverride, MermaidDiagramConfig


@dataclass(frozen=True, slots=True)
class ConfigurationViolation:
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class DiagramConfigurationContract:
    config_key: str
    schema_definition: str
    values: Mapping[str, Any]


class SchemaValidator(Protocol):
    def iter_errors(self, instance: Any) -> Iterator[ValidationError]: ...


@dataclass(frozen=True, slots=True)
class MermaidConfiguration:
    schema: Mapping[str, Any]
    overrides: Mapping[str, MermaidConfigurationOverride]

    facets = (
        "type",
        "nullability",
        "enum",
        "default",
        "minimum",
        "exclusiveMinimum",
        "maximum",
        "exclusiveMaximum",
        "multipleOf",
    )

    def local_contract(
        self,
        config_key: str,
        schema_definition: str,
        source: str,
    ) -> DiagramConfigurationContract:
        return DiagramConfigurationContract(config_key, schema_definition, self.extract(source))

    def validate(self, contract: DiagramConfigurationContract) -> tuple[ConfigurationViolation, ...]:
        validator = cast(SchemaValidator, Draft201909Validator(self._partial_schema()))
        errors = tuple(validator.iter_errors(contract.values))
        return tuple(
            ConfigurationViolation(".".join(str(segment) for segment in error.absolute_path), error.message)
            for error in sorted(errors, key=lambda error: list(error.absolute_path))
        )

    def extract(self, source: str) -> Mapping[str, Any]:
        if not source.startswith("---\n"):
            return {}
        _, frontmatter, _ = source.split("---\n", 2)
        payload: object = safe_load(frontmatter)
        if not isinstance(payload, Mapping):
            raise ValueError("Mermaid frontmatter must be a mapping.")
        config: object = cast(Mapping[str, object], payload).get("config", {})
        if not isinstance(config, Mapping):
            raise ValueError("Mermaid frontmatter config must be a mapping.")
        return cast(Mapping[str, Any], config)

    def supports(self, contract: DiagramConfigurationContract, upstream: MermaidDiagramConfig) -> bool:
        if contract.config_key != upstream.config_key or contract.schema_definition != upstream.schema_definition:
            return False
        properties = cast(Mapping[str, Any], self.schema["properties"])
        definitions = cast(Mapping[str, Any], self.schema["$defs"])
        expected = {"$ref": f"#/$defs/{upstream.schema_definition}"}
        return properties.get(upstream.config_key) == expected and upstream.schema_definition in definitions

    def compare(
        self,
        config_key: str,
        local: Mapping[str, Any],
        upstream: MermaidDiagramConfig,
    ) -> tuple[ConfigurationViolation, ...]:
        root_properties = cast(Mapping[str, Any], self.schema["properties"])
        expected = self._properties(self.schema, upstream.schema)
        expected["wrap"] = cast(dict[str, Any], root_properties["wrap"])
        actual = self._properties(local, local)
        differences = self._compare_properties(config_key, "", local, actual, self.schema, expected)

        violations: list[ConfigurationViolation] = []
        for path, facets in differences.items():
            override = self.overrides.get(path)
            if override is None:
                violations.append(
                    ConfigurationViolation(path, f"configuration schema differs in facets: {', '.join(sorted(facets))}")
                )
            elif override.facets != facets:
                violations.append(
                    ConfigurationViolation(
                        path,
                        "override facets "
                        f"{', '.join(sorted(override.facets))} do not match observed facets "
                        f"{', '.join(sorted(facets))}",
                    )
                )
        for path in sorted(self.overrides):
            if path.startswith(f"{config_key}.") and path not in differences:
                violations.append(ConfigurationViolation(path, "configuration override is stale"))
        return tuple(violations)

    def _compare_properties(
        self,
        config_key: str,
        parent: str,
        local_root: Mapping[str, Any],
        local: Mapping[str, Any],
        upstream_root: Mapping[str, Any],
        upstream: Mapping[str, Any],
    ) -> dict[str, frozenset[str]]:
        differences: dict[str, frozenset[str]] = {}
        for name in sorted(local.keys() | upstream.keys()):
            property_path = f"{parent}.{name}" if parent else name
            path = f"{config_key}.{property_path}"
            if name not in local:
                differences[path] = frozenset({"unsupported"})
                continue
            if name not in upstream:
                differences[path] = frozenset({"alias"})
                continue
            local_schema = self._resolve(local_root, local[name])
            upstream_schema = self._resolve(upstream_root, upstream[name])
            facets = frozenset(
                facet
                for facet in self.facets
                if self._facet(local_root, local_schema, facet) != self._facet(upstream_root, upstream_schema, facet)
            )
            if facets:
                differences[path] = facets
            local_children = self._properties(local_root, local_schema)
            upstream_children = self._properties(upstream_root, upstream_schema)
            if local_children or upstream_children:
                differences.update(
                    self._compare_properties(
                        config_key,
                        property_path,
                        local_root,
                        local_children,
                        upstream_root,
                        upstream_children,
                    )
                )
        return differences

    def _properties(self, root: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
        resolved = self._resolve(root, value)
        return dict(cast(Mapping[str, Any], resolved.get("properties", {})))

    def _resolve(self, root: Mapping[str, Any], value: Mapping[str, Any]) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/"):
            target: Any = root
            for segment in reference.removeprefix("#/").split("/"):
                target = cast(Mapping[str, Any], target)[segment.replace("~1", "/").replace("~0", "~")]
            resolved.update(self._resolve(root, cast(Mapping[str, Any], target)))
        for item in cast(list[Mapping[str, Any]], value.get("allOf", [])):
            inherited = self._resolve(root, item)
            resolved.update({key: child for key, child in inherited.items() if key != "properties"})
            resolved.setdefault("properties", {}).update(inherited.get("properties", {}))
        for key, item in value.items():
            if key not in {"$ref", "allOf", "properties"}:
                resolved[key] = item
        if "properties" in value:
            resolved.setdefault("properties", {}).update(cast(Mapping[str, Any], value["properties"]))
        return resolved

    def _facet(self, root: Mapping[str, Any], value: Mapping[str, Any], facet: str) -> Any:
        resolved = self._resolve(root, value)
        alternatives = cast(list[Mapping[str, Any]], resolved.get("anyOf", resolved.get("oneOf", [])))
        if facet in {"type", "nullability"}:
            types: set[str] = set()
            item_type = resolved.get("type")
            if isinstance(item_type, str):
                types.add(item_type)
            elif isinstance(item_type, list):
                types.update(cast(list[str], item_type))
            for alternative in alternatives:
                alternative_type = self._facet(root, alternative, "type")
                if isinstance(alternative_type, tuple):
                    types.update(cast(tuple[str, ...], alternative_type))
            if facet == "nullability":
                return "null" in types
            return tuple(sorted(types - {"null"}))
        if facet == "enum":
            values = resolved.get("enum")
            return tuple(cast(list[Any], values)) if isinstance(values, list) else None
        return facet in resolved, resolved.get(facet)

    def _partial_schema(self) -> dict[str, Any]:
        schema = deepcopy(dict(self.schema))
        self._remove_required(schema)
        return schema

    def _remove_required(self, value: Any) -> None:
        if isinstance(value, dict):
            mapping = cast(dict[str, Any], value)
            mapping.pop("required", None)
            for child in mapping.values():
                self._remove_required(child)
        if isinstance(value, list):
            items = cast(list[Any], value)
            for child in items:
                self._remove_required(child)
