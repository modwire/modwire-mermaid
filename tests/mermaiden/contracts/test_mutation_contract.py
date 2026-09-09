import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, cast

from jsonschema import Draft202012Validator

from mermaiden import Application

ROOT = Path(__file__).resolve().parents[3]
CONTRACT_ROOT = ROOT / "docs" / "contracts" / "diagram-mutations"
CONTRACT_PATH = CONTRACT_ROOT / "contract.json"
DIAGRAMS_PATH = CONTRACT_ROOT / "diagrams"
DOCUMENT_PATH = CONTRACT_ROOT / "README.md"
CHARACTER_POLICIES_PATH = CONTRACT_ROOT / "character-policies.json"
CHARACTER_DIAGRAMS_PATH = CONTRACT_ROOT / "characters"
RENDER_COMMAND = ROOT / "scripts" / "render_mutation_contract.py"

CATEGORIES = ("elements", "relations", "annotations")
CLASSIFICATIONS = {"updateable", "move_or_reorder_only", "immutable"}
UPDATE_COMMANDS = {
    "elements": "update_element",
    "relations": "update_relation",
    "annotations": "update_annotation",
}


class SchemaValidator(Protocol):
    def is_valid(self, instance: object) -> bool: ...


class TestMutationContract:
    def test_covers_every_registered_diagram_object_and_public_field_exactly_once(
        self,
    ) -> None:
        application = Application.create()
        contract = self._load_contract()
        assert set(contract) == {
            "contract_version",
            "schema_dialect",
            "schema_source",
            "payload_schema_sources",
            "generation_command",
            "semantics",
            "commands",
            "classifications",
            "diagrams",
        }
        classifications = self._object(contract["classifications"])
        assert set(classifications) == CLASSIFICATIONS
        assert all(isinstance(reason, str) and reason.strip() for reason in classifications.values())
        diagrams = self._object(contract["diagrams"])
        available = application.available_diagrams()

        assert set(diagrams) == {item.id for item in available}
        for info in available:
            description = application.diagram_description(info.id)
            diagram = self._object(diagrams[info.id])
            assert set(diagram) == {"root_collection", *CATEGORIES}
            for category in CATEGORIES:
                catalogued = cast(
                    Mapping[str, Mapping[str, object]],
                    getattr(description, category),
                )
                objects = self._object(diagram[category])
                assert tuple(objects) == tuple(catalogued)
                for kind, model_schema in catalogued.items():
                    item = self._object(objects[kind])
                    properties = self._object(model_schema["properties"])
                    fields = self._object(item["fields"])
                    assert tuple(fields) == tuple(properties)
                    assert item["update_command"] == UPDATE_COMMANDS[category]
                    assert item["kind_classification"] == "immutable"
                    for field_name, classification in fields.items():
                        assert classification in CLASSIFICATIONS
                        if field_name == "id":
                            assert classification == "immutable"
                        elif field_name == "elements":
                            assert classification == "move_or_reorder_only"
                        else:
                            assert classification == "updateable"

    def test_defines_compatible_element_placement_and_one_order_owner(self) -> None:
        application = Application.create()
        contract = self._load_contract()
        for diagram_id, value in self._object(contract["diagrams"]).items():
            description = application.diagram_description(diagram_id)
            diagram = self._object(value)
            elements = self._object(diagram["elements"])
            root = self._object(diagram["root_collection"])
            assert root == {
                "reorder_command": "reorder_elements",
                "membership": "Exact permutation of current root element IDs.",
            }
            containers = {
                kind for kind, item in elements.items() if "elements" in self._object(self._object(item)["fields"])
            }
            for kind, value in elements.items():
                item = self._object(value)
                placement = self._object(item["placement"])
                parents = self._strings(placement["allowed_parents"])
                assert parents == description.placements[kind].allowed_parents
                assert parents, f"{diagram_id}.{kind} has no compatible placement"
                assert set(parents) <= {"$root", *containers}
                assert placement["move_command"] == "move_element"
                if kind in containers:
                    assert self._object(item["child_collection"]) == {
                        "reorder_command": "reorder_elements",
                        "membership": "Exact permutation of current direct child IDs.",
                    }
                else:
                    assert "child_collection" not in item

    def test_defines_relation_and_annotation_retargeting_without_identity_loss(
        self,
    ) -> None:
        contract = self._load_contract()
        for diagram_id, value in self._object(contract["diagrams"]).items():
            diagram = self._object(value)
            for category, target_field in (
                ("relations", "element_ids"),
                ("annotations", "targets"),
            ):
                for kind, object_value in self._object(diagram[category]).items():
                    item = self._object(object_value)
                    fields = self._object(item["fields"])
                    retargeting = self._object(item["retargeting"])
                    assert target_field in fields, f"{diagram_id}.{category}.{kind} has no target field"
                    assert retargeting == {
                        "field": target_field,
                        "ordered": True,
                    }

    def test_resolves_every_supported_mutation_to_a_complete_strict_json_schema(
        self,
    ) -> None:
        application = Application.create()
        contract = self._load_contract()
        commands = self._object(contract["commands"])
        assert tuple(commands) == (
            "update_element",
            "update_relation",
            "update_annotation",
            "move_element",
            "reorder_elements",
        )
        for info in application.available_diagrams():
            description = application.diagram_description(info.id)
            diagram = self._object(self._object(contract["diagrams"])[info.id])
            for category in CATEGORIES:
                catalogued = cast(
                    Mapping[str, Mapping[str, Any]],
                    getattr(description, category),
                )
                objects = self._object(diagram[category])
                for kind, model_schema in catalogued.items():
                    item = self._object(objects[kind])
                    operation = cast(str, item["update_command"])
                    update_schema = self._build_payload_schema(
                        contract,
                        operation,
                        object_kind=kind,
                        object_contract=item,
                        model_schema=model_schema,
                    )
                    self._assert_update_schema(update_schema, item)
                    if category == "elements":
                        move_schema = self._build_payload_schema(
                            contract,
                            "move_element",
                            object_kind=kind,
                            object_contract=item,
                            model_schema=model_schema,
                        )
                        self._assert_strict_schema(move_schema, ("id", "kind", "parent_id"))
        reorder_schema = self._build_payload_schema(contract, "reorder_elements")
        self._assert_strict_schema(reorder_schema, ("parent_id", "element_ids"))
        element_ids = self._object(self._object(reorder_schema["properties"])["element_ids"])
        assert element_ids["uniqueItems"] is True

    def test_resolved_update_schema_enforces_null_and_unknown_field_policy(
        self,
    ) -> None:
        application = Application.create()
        contract = self._load_contract()
        model_schema = cast(
            Mapping[str, Any],
            application.diagram_description("flowchart").elements["flow_group"],
        )
        diagram = self._object(self._object(contract["diagrams"])["flowchart"])
        item = self._object(self._object(diagram["elements"])["flow_group"])
        schema = self._build_payload_schema(
            contract,
            "update_element",
            object_kind="flow_group",
            object_contract=item,
            model_schema=model_schema,
        )
        validator = cast(SchemaValidator, Draft202012Validator(schema))

        assert validator.is_valid({"id": "group", "kind": "flow_group", "changes": {"direction": None}})
        assert not validator.is_valid({"id": "group", "kind": "flow_group", "changes": {"label": None}})
        assert not validator.is_valid({"id": "group", "kind": "flow_group", "changes": {"id": "renamed"}})
        assert not validator.is_valid({"id": "group", "kind": "flow_group", "changes": {}})

    def test_documents_all_decisions_without_open_implementation_choices(
        self,
    ) -> None:
        contract = self._load_contract()
        semantics = {
            self._object(item)["name"]: self._object(item)["rule"] for item in self._list(contract["semantics"])
        }
        assert set(semantics) == {
            "Stable identity",
            "Partial update",
            "Null",
            "Strict payloads",
            "Move",
            "Reorder",
            "Retarget",
            "No-op",
            "Atomic rejection",
            "Invalid pre-state",
            "Discovery",
        }
        assert all(isinstance(rule, str) and rule.strip() for rule in semantics.values())
        assert contract["schema_source"] == "Application.diagram_description()"
        sources = self._object(contract["payload_schema_sources"])
        assert sources == {
            "object.id_schema": "The selected object's public id property schema.",
            "object.kind_const": ("A string const containing the selected catalogued object kind."),
            "object.updateable_field_schemas": (
                "The selected object's public property schemas whose matrix classification is updateable."
            ),
        }
        used_sources: set[str] = set()

        def collect_sources(value: object) -> None:
            if isinstance(value, list):
                for item in cast(list[object], value):
                    collect_sources(item)
            elif isinstance(value, dict):
                mapping = cast(dict[str, object], value)
                source = mapping.get("$source")
                if isinstance(source, str):
                    used_sources.add(source)
                for item in mapping.values():
                    collect_sources(item)

        collect_sources(contract["commands"])
        assert used_sources == set(sources)

    def test_generated_markdown_has_no_drift(self) -> None:
        result = subprocess.run(
            (sys.executable, str(RENDER_COMMAND), "--check"),
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )

        assert result.returncode == 0, result.stderr or result.stdout
        assert DOCUMENT_PATH.is_file()
        assert CHARACTER_POLICIES_PATH.is_file()
        assert {path.stem for path in CHARACTER_DIAGRAMS_PATH.glob("*.json")} == {
            info.id for info in Application.create().available_diagrams()
        }
        json_stems = {path.stem for path in DIAGRAMS_PATH.glob("*.json")}
        markdown_stems = {path.stem for path in DIAGRAMS_PATH.glob("*.md")}
        assert markdown_stems == json_stems
        assert not (ROOT / "docs" / "contracts" / "diagram-mutations.json").exists()
        assert not (ROOT / "docs" / "contracts" / "diagram-mutations.md").exists()

    def _build_payload_schema(
        self,
        contract: Mapping[str, Any],
        operation: str,
        *,
        object_kind: str | None = None,
        object_contract: Mapping[str, Any] | None = None,
        model_schema: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        command = self._object(self._object(contract["commands"])[operation])
        template = self._object(command["payload_schema"])

        def resolve(value: object) -> object:
            if isinstance(value, list):
                return [resolve(item) for item in cast(list[object], value)]
            if not isinstance(value, dict):
                return value
            mapping = cast(dict[str, object], value)
            source = mapping.get("$source")
            if source is not None:
                assert len(mapping) == 1 and isinstance(source, str)
                return source_value(source)
            return {key: resolve(item) for key, item in mapping.items()}

        def source_value(source: str) -> object:
            assert object_kind is not None
            assert object_contract is not None
            assert model_schema is not None
            properties = self._object(model_schema["properties"])
            fields = self._object(object_contract["fields"])
            if source == "object.id_schema":
                return properties["id"]
            if source == "object.kind_const":
                return {"const": object_kind, "type": "string"}
            assert source == "object.updateable_field_schemas"
            return {name: properties[name] for name, classification in fields.items() if classification == "updateable"}

        result = self._object(resolve(template))
        if model_schema is not None and "$defs" in model_schema:
            result["$defs"] = model_schema["$defs"]
        result["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        return result

    @classmethod
    def _load_contract(cls) -> dict[str, Any]:
        contract = cls._read_json_object(CONTRACT_PATH)
        diagrams: dict[str, Any] = {}
        for path in sorted(DIAGRAMS_PATH.glob("*.json")):
            diagram = cls._read_json_object(path)
            assert diagram.pop("diagram_id", None) == path.stem
            diagrams[path.stem] = diagram
        assert diagrams
        contract["diagrams"] = diagrams
        return contract

    def _assert_update_schema(self, schema: Mapping[str, Any], item: Mapping[str, Any]) -> None:
        self._assert_strict_schema(schema, ("id", "kind", "changes"))
        changes = self._object(self._object(schema["properties"])["changes"])
        assert changes["additionalProperties"] is False
        assert changes["minProperties"] == 1
        expected = {
            name for name, classification in self._object(item["fields"]).items() if classification == "updateable"
        }
        assert set(self._object(changes["properties"])) == expected

    @staticmethod
    def _assert_strict_schema(schema: Mapping[str, Any], required: tuple[str, ...]) -> None:
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False
        assert tuple(schema["required"]) == required

    @staticmethod
    def _read_json_object(path: Path) -> dict[str, Any]:
        value: object = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(value, dict)
        return cast(dict[str, Any], value)

    @staticmethod
    def _object(value: object) -> dict[str, Any]:
        assert isinstance(value, dict)
        return cast(dict[str, Any], value)

    @staticmethod
    def _list(value: object) -> list[object]:
        assert isinstance(value, list)
        return cast(list[object], value)

    @classmethod
    def _strings(cls, value: object) -> tuple[str, ...]:
        result: list[str] = []
        for item in cls._list(value):
            assert isinstance(item, str)
            result.append(item)
        return tuple(result)
