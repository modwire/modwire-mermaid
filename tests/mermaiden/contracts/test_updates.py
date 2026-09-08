import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from mermaiden.application import Application, DiagramCommand

MATRIX_ROOT = Path(__file__).resolve().parents[3] / "docs" / "contracts" / "diagram-mutations" / "diagrams"


class TestObjectUpdates:
    @pytest.mark.parametrize(
        ("arguments", "message"),
        (
            ({"id": "participant_example", "kind": "participant", "changes": {}}, "invalid arguments"),
            (
                {"id": "participant_example", "kind": "participant", "changes": {"id": "renamed_example"}},
                "invalid arguments",
            ),
            (
                {"id": "participant_example", "kind": "participant", "changes": {"unknown_example": True}},
                "invalid arguments",
            ),
            (
                {
                    "id": "participant_example",
                    "kind": "participant",
                    "changes": {"label": "Changed Example"},
                    "extra_example": True,
                },
                "invalid arguments",
            ),
            (
                {"id": "participant_example", "kind": "participant_box", "changes": {"label": "Changed Example"}},
                "has kind 'participant'",
            ),
            (
                {"id": "missing_example", "kind": "participant", "changes": {"label": "Changed Example"}},
                "does not exist",
            ),
        ),
    )
    def test_rejects_invalid_element_updates_without_changing_the_snapshot(
        self,
        arguments: Mapping[str, object],
        message: str,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "participant_example", "label": "Participant Example"}),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match=message):
            application.apply(diagram, DiagramCommand("update_element", arguments))

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_invalid_relation_references_without_changing_the_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "first_example", "label": "First Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "second_example", "label": "Second Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_message",
                {
                    "id": "message_example",
                    "source_id": "first_example",
                    "target_id": "second_example",
                    "label": "Message Example",
                },
            ),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match="unknown"):
            application.apply(
                diagram,
                DiagramCommand(
                    "update_relation",
                    {
                        "id": "message_example",
                        "kind": "message",
                        "changes": {"element_ids": ["first_example", "missing_example"]},
                    },
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_invalid_annotation_targets_without_changing_the_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "first_example", "label": "First Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_note",
                {"id": "note_example", "text": "Note Example", "participant_ids": ["first_example"]},
            ),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match="unknown"):
            application.apply(
                diagram,
                DiagramCommand(
                    "update_annotation",
                    {
                        "id": "note_example",
                        "kind": "sequence_note",
                        "changes": {"targets": [{"kind": "element", "id": "missing_example"}]},
                    },
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_catalog_exposes_every_matrix_approved_update_field_with_a_strict_schema(self) -> None:
        application = Application.create()

        for info in application.available_diagrams():
            description = application.diagram_description(info.id)
            matrix = self._matrix(info.id)
            catalogued = {
                "elements": description.elements,
                "relations": description.relations,
                "annotations": description.annotations,
            }
            for category, command_name in (
                ("elements", "update_element"),
                ("relations", "update_relation"),
                ("annotations", "update_annotation"),
            ):
                contracts = self._mapping(matrix[category])
                assert set(catalogued[category]) == set(contracts)
                if not contracts:
                    assert command_name not in description.commands
                    continue
                assert command_name in description.commands
                schema = application.command_payload(info.id, command_name).model_json_schema()
                for kind, contract_value in contracts.items():
                    contract = self._mapping(contract_value)
                    variant = self._variant(schema, kind)
                    assert variant["additionalProperties"] is False
                    assert variant["required"] == ["id", "kind", "changes"]
                    kind_schema = self._mapping(self._mapping(variant["properties"])["kind"])
                    assert kind_schema["const"] == kind
                    changes = self._reference(schema, self._mapping(variant["properties"])["changes"])
                    expected = {
                        name
                        for name, classification in self._mapping(contract["fields"]).items()
                        if classification == "updateable"
                    }
                    assert changes["additionalProperties"] is False
                    assert changes["minProperties"] == 1
                    assert set(self._mapping(changes["properties"])) == expected

    def test_partial_element_updates_distinguish_omission_from_explicit_null(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("flowchart")
        application.apply(diagram, DiagramCommand("add_start", {"id": "start_example", "label": "Start Example"}))
        application.apply(diagram, DiagramCommand("add_end", {"id": "end_example", "label": "End Example"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_flow",
                {"id": "flow_example", "source_id": "start_example", "target_id": "end_example"},
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_group",
                {"id": "group_example", "label": "Group Example", "direction": "LR"},
            ),
        )

        application.apply(
            diagram,
            DiagramCommand(
                "update_element",
                {
                    "id": "group_example",
                    "kind": "flow_group",
                    "changes": {"label": "Updated Group Example"},
                },
            ),
        )
        omitted = self._fields(application.snapshot(diagram).to_dict(), "elements", "group_example")
        application.apply(
            diagram,
            DiagramCommand(
                "update_element",
                {"id": "group_example", "kind": "flow_group", "changes": {"direction": None}},
            ),
        )
        cleared = self._fields(application.snapshot(diagram).to_dict(), "elements", "group_example")

        assert omitted["id"] == "group_example"
        assert omitted["label"] == "Updated Group Example"
        assert omitted["direction"] is not None
        assert cleared["id"] == "group_example"
        assert cleared["label"] == "Updated Group Example"
        assert cleared["direction"] is None

    def test_relation_updates_preserve_identity_and_relation_targeted_annotations(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "first_example", "label": "First Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "second_example", "label": "Second Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_message",
                {
                    "id": "message_example",
                    "source_id": "first_example",
                    "target_id": "second_example",
                    "label": "Message Example",
                },
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_note",
                {"id": "note_example", "text": "Note Example", "participant_ids": ["first_example"]},
            ),
        )
        payload = application.snapshot(diagram).to_dict()
        note = self._object(payload, "annotations", "note_example")
        targets = cast(list[object], self._mapping(note["fields"])["targets"])
        target = cast(dict[str, object], targets[0])
        target_fields = cast(dict[str, object], target["fields"])
        target_fields["id"] = "message_example"
        cast(dict[str, object], target_fields["kind"])["value"] = "relation"
        diagram = application.restore(payload)
        note_before = self._object(application.snapshot(diagram).to_dict(), "annotations", "note_example")

        application.apply(
            diagram,
            DiagramCommand(
                "update_relation",
                {
                    "id": "message_example",
                    "kind": "message",
                    "changes": {"label": "Updated Message Example"},
                },
            ),
        )
        snapshot = application.snapshot(diagram).to_dict()
        restored = application.restore(json.loads(json.dumps(snapshot)))

        assert self._fields(snapshot, "relations", "message_example")["id"] == "message_example"
        assert self._object(snapshot, "annotations", "note_example") == note_before
        assert "Updated Message Example" in application.render(diagram)
        assert application.snapshot(restored).to_dict() == snapshot
        assert application.render(restored) == application.render(diagram)

    def test_annotation_updates_preserve_target_order_and_survive_restore(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "first_example", "label": "First Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "second_example", "label": "Second Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_note",
                {"id": "note_example", "text": "Note Example", "participant_ids": ["first_example"]},
            ),
        )

        application.apply(
            diagram,
            DiagramCommand(
                "update_annotation",
                {
                    "id": "note_example",
                    "kind": "sequence_note",
                    "changes": {
                        "targets": [
                            {"kind": "element", "id": "second_example"},
                            {"kind": "element", "id": "first_example"},
                        ],
                        "text": "Updated Note Example",
                    },
                },
            ),
        )
        snapshot = application.snapshot(diagram).to_dict()
        targets = cast(list[object], self._fields(snapshot, "annotations", "note_example")["targets"])
        target_ids = tuple(self._mapping(self._mapping(target)["fields"])["id"] for target in targets)
        restored = application.restore(json.loads(json.dumps(snapshot)))

        assert target_ids == ("second_example", "first_example")
        assert "Note over second_example,first_example: Updated Note Example" in application.render(diagram)
        assert application.snapshot(restored).to_dict() == snapshot
        assert application.render(restored) == application.render(diagram)

    def test_layout_sensitive_relation_updates_complete_full_render_validation(
        self,
        successful_mermaid_render: None,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("architecture-beta")
        for id in ("first_example", "second_example", "third_example"):
            application.apply(
                diagram,
                DiagramCommand("add_service", {"id": id, "label": id.replace("_", " ").title()}),
            )
        application.apply(
            diagram,
            DiagramCommand(
                "add_alignment",
                {
                    "id": "alignment_example",
                    "axis": "row",
                    "member_ids": ["first_example", "second_example", "third_example"],
                },
            ),
        )

        application.apply(
            diagram,
            DiagramCommand(
                "update_relation",
                {
                    "id": "alignment_example",
                    "kind": "alignment",
                    "changes": {
                        "axis": "column",
                        "element_ids": ["third_example", "second_example", "first_example"],
                    },
                },
            ),
        )
        report = application.validate_render(diagram)

        assert report.success
        assert report.svg.startswith("<svg")
        assert not report.diagnostics

    def _matrix(self, diagram_id: str) -> Mapping[str, object]:
        value: object = json.loads((MATRIX_ROOT / f"{diagram_id}.json").read_text(encoding="utf-8"))
        return self._mapping(value)

    def _variant(self, schema: Mapping[str, object], kind: str) -> Mapping[str, object]:
        discriminator = schema.get("discriminator")
        if discriminator is not None:
            mapping = self._mapping(self._mapping(discriminator)["mapping"])
            return self._reference(schema, mapping[kind])
        return self._reference(schema, schema["$ref"])

    def _reference(self, schema: Mapping[str, object], reference: object) -> Mapping[str, object]:
        if isinstance(reference, dict):
            reference = cast(dict[str, object], reference)["$ref"]
        assert isinstance(reference, str) and reference.startswith("#/$defs/")
        return self._mapping(self._mapping(schema["$defs"])[reference.removeprefix("#/$defs/")])

    def _object(
        self,
        snapshot: Mapping[str, object],
        collection: str,
        id: str,
    ) -> Mapping[str, object]:
        values = cast(list[object], snapshot[collection])
        for value in values:
            item = self._mapping(value)
            if self._mapping(item["fields"])["id"] == id:
                return item
        raise AssertionError(f"Object '{id}' is absent from '{collection}'.")

    def _fields(
        self,
        snapshot: Mapping[str, object],
        collection: str,
        id: str,
    ) -> Mapping[str, object]:
        return self._mapping(self._object(snapshot, collection, id)["fields"])

    def _mapping(self, value: object) -> Mapping[str, object]:
        assert isinstance(value, Mapping)
        return cast(Mapping[str, object], value)
