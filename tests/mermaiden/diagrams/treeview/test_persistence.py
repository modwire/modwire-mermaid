import json
from collections.abc import Mapping
from typing import cast

import pytest

from mermaiden import Application


class TestTreeViewPersistence:
    def test_uses_branches_as_the_only_public_nesting_operation(self) -> None:
        application = Application.create()
        schema = application.command_payload("treeView-beta", "add_item").model_json_schema()
        description = application.diagram_description("treeView-beta")
        element_schema = description.elements["tree_item"]
        definitions = cast(Mapping[str, object], element_schema["$defs"])
        item_type_schema = cast(Mapping[str, object], definitions["TreeItemType"])
        properties = cast(Mapping[str, object], element_schema["properties"])
        item_type_property = cast(Mapping[str, object], properties["item_type"])

        assert "parent_id" not in schema["properties"]
        assert item_type_schema["enum"] == ["item", "directory", "file"]
        assert item_type_property["default"] == "item"

        removal_schema = application.command_payload("treeView-beta", "remove_element").model_json_schema()
        removal_description = cast(str, removal_schema["description"])
        assert "complete diagram-defined subtree" in removal_description
        assert "removed atomically" in removal_description

    def test_preserves_addressability_through_incremental_branches_and_annotations(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        revisions = (
            ("add_directory", {"id": "example_root", "label": "root"}),
            ("add_directory", {"id": "example_child_one", "label": "child-one"}),
            ("add_directory", {"id": "example_child_two", "label": "child-two"}),
            ("add_file", {"id": "example_grandchild", "label": "leaf.txt"}),
            (
                "add_annotation",
                {"id": "before_branch", "element_id": "example_child_one", "icon": "folder"},
            ),
            (
                "add_branch",
                {"id": "first_sibling", "parent_id": "example_root", "child_id": "example_child_one"},
            ),
            (
                "add_branch",
                {"id": "second_sibling", "parent_id": "example_root", "child_id": "example_child_two"},
            ),
            (
                "add_annotation",
                {"id": "after_branch", "element_id": "example_child_two", "description": "Second child"},
            ),
            (
                "add_branch",
                {"id": "nested", "parent_id": "example_child_one", "child_id": "example_grandchild"},
            ),
            (
                "add_annotation",
                {"id": "after_nested_branch", "element_id": "example_grandchild", "highlight": True},
            ),
        )
        expected_ids: set[str] = set()
        source = ""

        for operation, arguments in revisions:
            report = application.execute(diagram, operation, arguments)
            if operation in {"add_item", "add_directory", "add_file"}:
                expected_ids.add(cast(str, arguments["id"]))
            snapshot = application.snapshot(diagram).to_dict()
            persisted_ids = {
                cast(str, cast(Mapping[str, object], cast(Mapping[str, object], element)["fields"])["id"])
                for element in cast(list[object], snapshot["elements"])
            }
            diagram = application.restore(json.loads(json.dumps(snapshot)))
            source = application.render(diagram)

            assert report is not None
            assert report.accepted
            assert persisted_ids == expected_ids
            assert source.startswith("---\nconfig:\n  wrap: true\n---\ntreeView-beta\n")

        assert source.endswith(
            "treeView-beta\nroot/\n  child-one/ icon(folder)\n    leaf.txt :::highlight\n  child-two/ ## Second child\n"
        )

    def test_restores_legacy_items_without_a_type_as_generic_items(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_item", {"id": "legacy", "label": "legacy/"})
        snapshot = application.snapshot(diagram).to_dict()
        cast(dict[str, object], cast(Mapping[str, object], cast(list[object], snapshot["elements"])[0])["fields"]).pop(
            "item_type"
        )

        restored = application.restore(json.loads(json.dumps(snapshot)))
        restored_snapshot = application.snapshot(restored).to_dict()
        restored_fields = cast(
            Mapping[str, object],
            cast(Mapping[str, object], cast(list[object], restored_snapshot["elements"])[0])["fields"],
        )

        assert restored_fields["item_type"] == {
            "$enum": "mermaiden.diagrams.treeview.elements:TreeItemType",
            "value": "item",
        }
        assert application.render(restored).endswith("treeView-beta\nlegacy/\n")

    def test_round_trip_preserves_types_and_classification_preserves_branches(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_directory", {"id": "root", "label": "root"})
        application.execute(diagram, "add_item", {"id": "leaf", "label": "README.md"})
        application.execute(diagram, "add_file", {"id": "license", "label": "LICENSE"})
        application.execute(
            diagram,
            "add_branch",
            {"id": "contains", "parent_id": "root", "child_id": "leaf"},
        )
        application.execute(
            diagram,
            "add_branch",
            {"id": "licenses", "parent_id": "root", "child_id": "license"},
        )

        application.execute(diagram, "classify_item", {"id": "leaf", "item_type": "file"})
        snapshot = application.snapshot(diagram).to_dict()
        restored = application.restore(json.loads(json.dumps(snapshot)))

        fields_by_id = {
            cast(str, fields["id"]): fields
            for encoded in cast(list[object], snapshot["elements"])
            for fields in (cast(Mapping[str, object], cast(Mapping[str, object], encoded)["fields"]),)
        }
        assert fields_by_id["root"]["item_type"] == {
            "$enum": "mermaiden.diagrams.treeview.elements:TreeItemType",
            "value": "directory",
        }
        assert fields_by_id["leaf"]["item_type"] == {
            "$enum": "mermaiden.diagrams.treeview.elements:TreeItemType",
            "value": "file",
        }
        assert fields_by_id["license"]["item_type"] == {
            "$enum": "mermaiden.diagrams.treeview.elements:TreeItemType",
            "value": "file",
        }
        assert application.snapshot(restored).to_dict() == snapshot
        assert application.render(restored).endswith("treeView-beta\nroot/\n  README.md\n  LICENSE\n")

    def test_restores_and_edits_the_empty_draft_after_removing_the_final_item(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_file", {"id": "only", "label": "only.txt"})

        report = application.execute(diagram, "remove_element", {"id": "only"})
        snapshot = application.snapshot(diagram).to_dict()
        validation = application.validate_render(diagram)

        assert report is not None
        assert tuple((item.kind, item.id) for item in report.removed) == (("element", "only"),)
        assert snapshot["draft"] is True
        assert snapshot["elements"] == []
        assert snapshot["relations"] == []
        assert snapshot["annotations"] == []
        assert not validation.success
        assert validation.svg == ""
        assert validation.diagnostics[0].code == "diagram_invalid"
        with pytest.raises(RuntimeError, match="Cannot render invalid diagram 'treeView-beta'"):
            application.render(diagram)

        restored = application.restore(json.loads(json.dumps(snapshot)))
        application.execute(restored, "add_directory", {"id": "replacement", "label": "replacement"})

        assert application.render(restored).endswith("treeView-beta\nreplacement/\n")
