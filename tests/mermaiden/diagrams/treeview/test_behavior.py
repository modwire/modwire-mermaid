import json
from typing import cast

import pytest

from mermaiden.application import Application, DiagramCommand, UnknownCommand
from mermaiden.diagrams.treeview.diagram import TreeView


class TestTreeView:
    def test_exercises_every_public_command_and_restores_identical_mermaid(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")

        commands = (
            DiagramCommand("configure", {"wrap": False}),
            DiagramCommand("add_directory", {"id": "root", "label": "root"}),
            DiagramCommand("add_item", {"id": "child", "label": 'child "one"'}),
            DiagramCommand("classify_item", {"id": "child", "item_type": "file"}),
            DiagramCommand("add_file", {"id": "readme", "label": "README.md"}),
            DiagramCommand("add_branch", {"id": "branch", "parent_id": "root", "child_id": "child"}),
            DiagramCommand("add_branch", {"id": "readme_branch", "parent_id": "root", "child_id": "readme"}),
            DiagramCommand(
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
        for command in commands:
            application.apply(diagram, command)

        source = application.render(diagram)
        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))

        assert set(application.diagram_description("treeView-beta").commands) == {
            item.operation for item in commands
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
        application.apply(diagram, DiagramCommand("add_directory", {"id": "root", "label": "root"}))

        with pytest.raises(UnknownCommand):
            application.apply(diagram, DiagramCommand("configure", {"missing": True}))
        with pytest.raises(RuntimeError, match=r"already exists"):
            application.apply(diagram, DiagramCommand("add_item", {"id": "root", "label": "again"}))
        with pytest.raises(RuntimeError, match=r"unknown|does not exist"):
            application.apply(
                diagram,
                DiagramCommand(
                    "add_annotation",
                    {"id": "annotation", "element_id": "missing", "description": "Missing"},
                ),
            )

    def test_rejects_unsupported_icon_characters_before_create_or_update(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.execute(diagram, "add_directory", {"id": "root", "label": "Root"})
        before_create = application.snapshot(diagram).to_dict()

        with pytest.raises(UnknownCommand) as rejected_create:
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

        with pytest.raises(UnknownCommand) as rejected_update:
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

    def test_rejects_unsupported_icon_characters_during_direct_mutation_and_restore(self) -> None:
        application = Application.create()
        diagram = cast(TreeView, application.create_diagram("treeView-beta"))
        application.execute(diagram, "add_directory", {"id": "root", "label": "Root"})
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(ValueError, match="icon"):
            diagram.add_annotation("note", "root", icon="📁")

        assert application.snapshot(diagram).to_dict() == before

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
            application.apply(diagram, DiagramCommand(operation, {"id": "nested", "label": label}))

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_file_parents_and_invalid_reclassification_atomically(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("treeView-beta")
        application.apply(diagram, DiagramCommand("add_directory", {"id": "root", "label": "root"}))
        application.apply(diagram, DiagramCommand("add_file", {"id": "leaf", "label": "leaf.txt"}))
        application.apply(diagram, DiagramCommand("add_item", {"id": "child", "label": "child"}))

        before_branch = application.snapshot(diagram).to_dict()
        with pytest.raises(RuntimeError, match=r"File 'leaf' cannot be the parent"):
            application.apply(
                diagram,
                DiagramCommand("add_branch", {"id": "invalid", "parent_id": "leaf", "child_id": "child"}),
            )
        assert application.snapshot(diagram).to_dict() == before_branch

        application.apply(
            diagram,
            DiagramCommand("add_branch", {"id": "valid", "parent_id": "root", "child_id": "leaf"}),
        )
        before_classification = application.snapshot(diagram).to_dict()
        with pytest.raises(RuntimeError, match=r"File 'root' cannot be the parent"):
            application.apply(diagram, DiagramCommand("classify_item", {"id": "root", "item_type": "file"}))
        assert application.snapshot(diagram).to_dict() == before_classification
