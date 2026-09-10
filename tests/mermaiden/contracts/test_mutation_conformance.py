import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

from mermaiden.application import Application, DiagramCommand

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = ROOT / "docs" / "contracts" / "diagram-mutations"
MATRIX_ROOT = CONTRACT_ROOT / "diagrams"


class TestMutationConformance:
    def test_public_boundary_applies_mutation_commands_and_round_trips(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        commands = (
            DiagramCommand("add_group", {"id": "source_example", "label": "Source Example"}),
            DiagramCommand("add_group", {"id": "target_example", "label": "Target Example"}),
            DiagramCommand(
                "add_block",
                {"id": "first_example", "label": "First Example", "parent_id": "source_example"},
            ),
            DiagramCommand(
                "add_block",
                {"id": "second_example", "label": "Second Example", "parent_id": "source_example"},
            ),
            DiagramCommand(
                "update_element",
                {
                    "id": "first_example",
                    "kind": "block_node",
                    "changes": {"label": "Updated First Example"},
                },
            ),
            DiagramCommand(
                "move_element",
                {
                    "id": "first_example",
                    "kind": "block_node",
                    "parent_id": "target_example",
                    "position": 0,
                },
            ),
            DiagramCommand(
                "reorder_elements",
                {"parent_id": "source_example", "element_ids": ["second_example"]},
            ),
        )

        for command in commands:
            application.apply(diagram, command)

        snapshot = application.snapshot(diagram).to_dict()
        restored = application.restore(json.loads(json.dumps(snapshot)))

        assert application.snapshot(restored).to_dict() == snapshot
        assert application.render(restored) == application.render(diagram)

    def test_matrix_catalog_and_payload_schemas_have_exact_coverage(self) -> None:
        application = Application.create()
        matrices = self._matrices()
        contract_operations = set(self._mapping(self._json(CONTRACT_ROOT / "contract.json")["commands"]))
        available = application.available_diagrams()

        assert set(matrices) == {info.id for info in available}
        for info in available:
            matrix = matrices[info.id]
            description = application.diagram_description(info.id)
            expected_operations = self._expected_operations(matrix)
            catalogued_operations = set(description.commands).intersection(contract_operations)
            assert catalogued_operations == expected_operations

            for category in ("elements", "relations", "annotations"):
                objects = self._mapping(matrix[category])
                catalogued = cast(Mapping[str, Mapping[str, object]], getattr(description, category))
                assert tuple(catalogued) == tuple(objects)
                if not objects:
                    continue
                operation = self._operation(objects)
                schema = application.command_payload(info.id, operation).model_json_schema()
                assert set(self._discriminator_mapping(schema)) == set(objects)
                for kind, value in objects.items():
                    item = self._mapping(value)
                    variant = self._variant(schema, kind)
                    changes = self._reference(schema, self._mapping(variant["properties"])["changes"])
                    expected_fields = {
                        name
                        for name, classification in self._mapping(item["fields"]).items()
                        if classification == "updateable"
                    }
                    assert variant["additionalProperties"] is False
                    assert variant["required"] == ["id", "kind", "changes"]
                    assert changes["additionalProperties"] is False
                    assert changes["minProperties"] == 1
                    assert set(self._mapping(changes["properties"])) == expected_fields

            elements = self._mapping(matrix["elements"])
            if elements:
                assert {
                    kind: self._strings(self._mapping(self._mapping(value)["placement"])["allowed_parents"])
                    for kind, value in elements.items()
                } == {kind: placement.allowed_parents for kind, placement in description.placements.items()}
                move_operation = cast(
                    str,
                    self._mapping(self._mapping(next(iter(elements.values())))["placement"])["move_command"],
                )
                move_schema = application.command_payload(info.id, move_operation).model_json_schema()
                assert set(self._discriminator_mapping(move_schema)) == set(elements)
                reorder_operation = cast(str, self._mapping(matrix["root_collection"])["reorder_command"])
                reorder_schema = application.command_payload(info.id, reorder_operation).model_json_schema()
                assert reorder_schema["additionalProperties"] is False
                assert reorder_schema["required"] == ["parent_id", "element_ids"]

    def test_every_matrix_approved_field_and_collection_has_one_strict_case(self) -> None:
        application = Application.create()
        matrices = self._matrices()
        expected_cases = self._expected_cases(matrices)
        covered_cases: set[tuple[str, str, str, str]] = set()

        for diagram_id, matrix in matrices.items():
            for category in ("elements", "relations", "annotations"):
                objects = self._mapping(matrix[category])
                if not objects:
                    continue
                operation = self._operation(objects)
                payload = application.command_payload(diagram_id, operation)
                schema = payload.model_json_schema()
                for kind, value in objects.items():
                    item = self._mapping(value)
                    variant = self._variant(schema, kind)
                    changes = self._reference(schema, self._mapping(variant["properties"])["changes"])
                    properties = self._mapping(changes["properties"])
                    for field_name, classification in self._mapping(item["fields"]).items():
                        if classification != "updateable":
                            continue
                        arguments = {
                            "id": "object_example",
                            "kind": kind,
                            "changes": {field_name: self._example(schema, self._mapping(properties[field_name]))},
                        }
                        validated = payload.model_validate(arguments).model_dump(mode="json", exclude_unset=True)
                        validated_changes = self._mapping(validated["changes"])
                        assert set(validated_changes) == {field_name}
                        covered_cases.add((diagram_id, category, kind, field_name))

            elements = self._mapping(matrix["elements"])
            if not elements:
                continue
            first = self._mapping(next(iter(elements.values())))
            move_operation = cast(str, self._mapping(first["placement"])["move_command"])
            move_payload = application.command_payload(diagram_id, move_operation)
            for kind in elements:
                validated = move_payload.model_validate(
                    {"id": "element_example", "kind": kind, "parent_id": ""}
                ).model_dump(mode="json", exclude_unset=True)
                assert validated == {"id": "element_example", "kind": kind, "parent_id": "", "position": None}
                covered_cases.add((diagram_id, "elements", kind, "move"))

            reorder_operation = cast(str, self._mapping(matrix["root_collection"])["reorder_command"])
            reorder_payload = application.command_payload(diagram_id, reorder_operation)
            owners = [""]
            owners.extend(
                f"{kind}_example" for kind, value in elements.items() if "child_collection" in self._mapping(value)
            )
            for owner in owners:
                validated = reorder_payload.model_validate(
                    {"parent_id": owner, "element_ids": ["element_example"]}
                ).model_dump(mode="json", exclude_unset=True)
                assert validated == {"parent_id": owner, "element_ids": ["element_example"]}
                kind = "$root" if not owner else owner.removesuffix("_example")
                covered_cases.add((diagram_id, "elements", kind, "reorder"))

        assert covered_cases == expected_cases, (
            f"missing conformance cases: {sorted(expected_cases.difference(covered_cases))}; "
            f"extra conformance cases: {sorted(covered_cases.difference(expected_cases))}"
        )

    def test_matrix_unsupported_operations_are_absent_and_rejected(self) -> None:
        application = Application.create()
        contract_operations = set(self._mapping(self._json(CONTRACT_ROOT / "contract.json")["commands"]))

        for diagram_id, matrix in self._matrices().items():
            description = application.diagram_description(diagram_id)
            unsupported = contract_operations.difference(self._expected_operations(matrix))
            for operation in unsupported:
                assert operation not in description.commands
                with pytest.raises(KeyError, match="Unknown command"):
                    application.command_payload(diagram_id, operation)
                diagram = application.create_diagram(diagram_id)
                with pytest.raises(RuntimeError, match="invalid arguments"):
                    application.apply(diagram, DiagramCommand(operation, {}))

    def _matrices(self) -> dict[str, Mapping[str, object]]:
        matrices: dict[str, Mapping[str, object]] = {}
        for path in sorted(MATRIX_ROOT.glob("*.json")):
            matrix = self._json(path)
            diagram_id = cast(str, matrix["diagram_id"])
            assert diagram_id == path.stem
            matrices[diagram_id] = matrix
        return matrices

    def _expected_operations(self, matrix: Mapping[str, object]) -> set[str]:
        operations: set[str] = set()
        for category in ("elements", "relations", "annotations"):
            objects = self._mapping(matrix[category])
            for value in objects.values():
                item = self._mapping(value)
                operations.add(cast(str, item["update_command"]))
                placement = item.get("placement")
                if placement is not None:
                    operations.add(cast(str, self._mapping(placement)["move_command"]))
                child_collection = item.get("child_collection")
                if child_collection is not None:
                    operations.add(cast(str, self._mapping(child_collection)["reorder_command"]))
        root = self._mapping(matrix["root_collection"])
        operations.add(cast(str, root["reorder_command"]))
        return operations

    def _expected_cases(
        self,
        matrices: Mapping[str, Mapping[str, object]],
    ) -> set[tuple[str, str, str, str]]:
        cases: set[tuple[str, str, str, str]] = set()
        for diagram_id, matrix in matrices.items():
            for category in ("elements", "relations", "annotations"):
                for kind, value in self._mapping(matrix[category]).items():
                    item = self._mapping(value)
                    cases.update(
                        (diagram_id, category, kind, field_name)
                        for field_name, classification in self._mapping(item["fields"]).items()
                        if classification == "updateable"
                    )
                    if category == "elements":
                        cases.add((diagram_id, category, kind, "move"))
                        if "child_collection" in item:
                            cases.add((diagram_id, category, kind, "reorder"))
            cases.add((diagram_id, "elements", "$root", "reorder"))
        return cases

    def _operation(self, objects: Mapping[str, object]) -> str:
        operations = {cast(str, self._mapping(value)["update_command"]) for value in objects.values()}
        assert len(operations) == 1
        return operations.pop()

    def _variant(self, schema: Mapping[str, object], kind: str) -> Mapping[str, object]:
        return self._reference(schema, self._discriminator_mapping(schema)[kind])

    def _discriminator_mapping(self, schema: Mapping[str, object]) -> Mapping[str, object]:
        return self._mapping(self._mapping(schema["discriminator"])["mapping"])

    def _reference(self, root: Mapping[str, object], value: object) -> Mapping[str, object]:
        reference = cast(dict[str, object], value).get("$ref") if isinstance(value, dict) else value
        assert isinstance(reference, str) and reference.startswith("#/$defs/")
        return self._mapping(self._mapping(root["$defs"])[reference.removeprefix("#/$defs/")])

    def _example(self, root: Mapping[str, object], schema: Mapping[str, object]) -> object:
        reference = schema.get("$ref")
        if reference is not None:
            return self._example(root, self._reference(root, reference))
        if "const" in schema:
            return schema["const"]
        enum = schema.get("enum")
        if enum is not None:
            return next(value for value in self._sequence(enum) if value is not None)
        for keyword in ("anyOf", "oneOf"):
            alternatives = schema.get(keyword)
            if alternatives is not None:
                for value in self._sequence(alternatives):
                    alternative = self._mapping(value)
                    if alternative.get("type") != "null":
                        return self._example(root, alternative)
        schema_type = schema.get("type")
        if isinstance(schema_type, list):
            schema_type = next(value for value in cast(list[object], schema_type) if value != "null")
        if schema_type == "string":
            return self._string_example(schema)
        if schema_type == "integer":
            return self._number_example(schema, integral=True)
        if schema_type == "number":
            return self._number_example(schema, integral=False)
        if schema_type == "boolean":
            return True
        if schema_type == "array":
            count = max(1, cast(int, schema.get("minItems", 0)))
            item = self._mapping(schema["items"])
            return [self._example(root, item) for _ in range(count)]
        if schema_type == "object" or "properties" in schema:
            properties = self._mapping(schema.get("properties", {}))
            required = self._strings(schema.get("required", []))
            return {name: self._example(root, self._mapping(properties[name])) for name in required}
        raise AssertionError(f"Cannot derive example from schema: {schema}")

    def _string_example(self, schema: Mapping[str, object]) -> str:
        value = "value_example"
        minimum = cast(int, schema.get("minLength", 0))
        if len(value) < minimum:
            value += "x" * (minimum - len(value))
        return value

    def _number_example(self, schema: Mapping[str, object], *, integral: bool) -> int | float:
        minimum = schema.get("minimum", schema.get("exclusiveMinimum", 0))
        value = float(cast(int | float, minimum))
        if "exclusiveMinimum" in schema:
            value += 1
        maximum = schema.get("maximum", schema.get("exclusiveMaximum"))
        if maximum is not None and value >= float(cast(int | float, maximum)):
            value = float(cast(int | float, maximum)) - 1
        return int(value) if integral else value

    def _json(self, path: Path) -> Mapping[str, object]:
        return self._mapping(json.loads(path.read_text(encoding="utf-8")))

    def _mapping(self, value: object) -> Mapping[str, object]:
        assert isinstance(value, dict)
        return cast(dict[str, object], value)

    def _sequence(self, value: object) -> Sequence[object]:
        assert isinstance(value, list)
        return cast(list[object], value)

    def _strings(self, value: object) -> tuple[str, ...]:
        sequence = self._sequence(value)
        assert all(isinstance(item, str) for item in sequence)
        return tuple(cast(str, item) for item in sequence)
