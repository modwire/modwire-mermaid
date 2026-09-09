import json
from typing import cast

import pytest

from mermaiden import Application


class TestTreeView:
    def test_exercises_every_public_command_and_restores_identical_mermaid(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")

        commands = (
            ("configure", {"wrap": False}),
            ("add_directory", {"id": "root", "label": "root"}),
            ("add_item", {"id": "child", "label": 'child "one"'}),
            ("classify_item", {"id": "child", "item_type": "file"}),
            ("add_file", {"id": "readme", "label": "README.md"}),
            ("add_branch", {"id": "branch", "parent_id": "root", "child_id": "child"}),
            ("add_branch", {"id": "readme_branch", "parent_id": "root", "child_id": "readme"}),
            (
                "add_annotation",
                {
                    "id": "annotation",
                    "element_id": "child",
                    "highlight": True,
                    "icon": "folder",
                    "description": "Docs",
                },
            ),
        )
        for operation, arguments in commands:
            application.execute(diagram, operation, arguments)

        source = application.render(diagram)
        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))

        assert set(application.diagram_description("treeView-beta").commands) == {
            operation for operation, _arguments in commands
        } | {
            "update_element",
            "remove_element",
            "move_element",
            "reorder_elements",
            "update_relation",
            "remove_relation",
            "update_annotation",
            "remove_annotation",
        }
        assert "root/" in source
        assert '"child \\"one\\"" :::highlight icon(folder) ## Docs' in source
        assert "  README.md" in source
        assert application.render(restored) == source

    def test_rejects_invalid_configuration_and_unknown_annotation_targets(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_directory", {"id": "root", "label": "root"})

        with pytest.raises(RuntimeError):
            application.execute(diagram, "configure", {"missing": True})
        with pytest.raises(RuntimeError, match=r"already exists"):
            application.execute(diagram, "add_item", {"id": "root", "label": "again"})
        with pytest.raises(RuntimeError, match=r"unknown|does not exist"):
            application.execute(
                diagram,
                "add_annotation",
                {"id": "annotation", "element_id": "missing", "description": "Missing"},
            )

    def test_rejects_unsupported_icon_characters_before_create_or_update(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_directory", {"id": "root", "label": "Root"})
        before_create = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError) as rejected_create:
            application.execute(
                diagram,
                "add_annotation",
                {"id": "note", "element_id": "root", "icon": "📁"},
            )

        diagnostic = str(rejected_create.value)
        assert "add_annotation" in diagnostic
        assert "icon" in diagnostic
        assert "'📁' (U+1F4C1)" in diagnostic
        assert "rule pattern" in diagnostic
        assert application.snapshot(diagram).to_dict() == before_create

        application.execute(
            diagram,
            "add_annotation",
            {"id": "note", "element_id": "root", "icon": "folder"},
        )
        before_update = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError) as rejected_update:
            application.execute(
                diagram,
                "update_annotation",
                {"id": "note", "kind": "tree_annotation", "changes": {"icon": "📁"}},
            )

        diagnostic = str(rejected_update.value)
        assert "update_annotation" in diagnostic
        assert "changes.icon" in diagnostic
        assert "'📁' (U+1F4C1)" in diagnostic
        assert application.snapshot(diagram).to_dict() == before_update

    def test_rejects_unsupported_icon_characters_during_restore(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_directory", {"id": "root", "label": "Root"})
        application.execute(
            diagram,
            "add_annotation",
            {"id": "note", "element_id": "root", "icon": "folder"},
        )
        payload = application.snapshot(diagram).to_dict()
        annotations = cast(list[dict[str, object]], payload["annotations"])
        fields = cast(dict[str, object], annotations[0]["fields"])
        fields["icon"] = "📁"

        with pytest.raises(ValueError, match="icon"):
            application.restore(payload)

    @pytest.mark.parametrize("operation", ["add_directory", "add_file"])
    @pytest.mark.parametrize("label", ["src/package", r"src\package"])
    def test_rejects_typed_paths_atomically(self, operation: str, label: str) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match=r"basename without path separators"):
            application.execute(diagram, operation, {"id": "nested", "label": label})

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_file_parents_and_invalid_reclassification_atomically(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_directory", {"id": "root", "label": "root"})
        application.execute(diagram, "add_file", {"id": "leaf", "label": "leaf.txt"})
        application.execute(diagram, "add_item", {"id": "child", "label": "child"})

        before_branch = application.snapshot(diagram).to_dict()
        with pytest.raises(RuntimeError, match=r"File 'leaf' cannot be the parent"):
            application.execute(
                diagram,
                "add_branch",
                {"id": "invalid", "parent_id": "leaf", "child_id": "child"},
            )
        assert application.snapshot(diagram).to_dict() == before_branch

        application.execute(
            diagram,
            "add_branch",
            {"id": "valid", "parent_id": "root", "child_id": "leaf"},
        )
        before_classification = application.snapshot(diagram).to_dict()
        with pytest.raises(RuntimeError, match=r"File 'root' cannot be the parent"):
            application.execute(diagram, "classify_item", {"id": "root", "item_type": "file"})
        assert application.snapshot(diagram).to_dict() == before_classification

    def test_removes_the_complete_branch_subtree_and_its_dependants_atomically(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        for operation, arguments in (
            ("add_directory", {"id": "root", "label": "root"}),
            ("add_directory", {"id": "nested", "label": "nested"}),
            ("add_file", {"id": "leaf", "label": "leaf.txt"}),
            ("add_file", {"id": "sibling", "label": "sibling.txt"}),
            ("add_directory", {"id": "outside", "label": "outside"}),
            ("add_branch", {"id": "root_nested", "parent_id": "root", "child_id": "nested"}),
            ("add_branch", {"id": "nested_leaf", "parent_id": "nested", "child_id": "leaf"}),
            ("add_branch", {"id": "root_sibling", "parent_id": "root", "child_id": "sibling"}),
            ("add_annotation", {"id": "root_note", "element_id": "root", "highlight": True}),
            ("add_annotation", {"id": "nested_note", "element_id": "nested", "highlight": True}),
            ("add_annotation", {"id": "leaf_note", "element_id": "leaf", "highlight": True}),
            ("add_annotation", {"id": "sibling_note", "element_id": "sibling", "highlight": True}),
            ("add_annotation", {"id": "outside_note", "element_id": "outside", "highlight": True}),
        ):
            application.execute(diagram, operation, arguments)

        before = application.snapshot(diagram).to_dict()
        source = application.render(diagram)
        with pytest.raises(RuntimeError, match="still has dependants; use cascade=True"):
            application.execute(diagram, "remove_element", {"id": "root"})
        assert application.snapshot(diagram).to_dict() == before
        assert application.render(diagram) == source

        report = application.execute(diagram, "remove_element", {"id": "root", "cascade": True})

        assert report is not None
        assert tuple((item.kind, item.id) for item in report.removed) == (
            ("element", "root"),
            ("element", "nested"),
            ("element", "leaf"),
            ("element", "sibling"),
            ("relation", "root_nested"),
            ("relation", "nested_leaf"),
            ("relation", "root_sibling"),
            ("annotation", "root_note"),
            ("annotation", "nested_note"),
            ("annotation", "leaf_note"),
            ("annotation", "sibling_note"),
        )
        assert tuple(item.id for item in diagram.walk_elements()) == ("outside",)
        assert not diagram.find_relations()
        assert tuple(item.id for item in diagram.find_annotations()) == ("outside_note",)
        assert application.render(diagram).endswith("treeView-beta\noutside/ :::highlight\n")
