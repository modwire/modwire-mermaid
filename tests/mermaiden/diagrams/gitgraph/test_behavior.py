import json

import pytest

from mermaiden.application import Application, DiagramCommand


class TestGitGraph:
    def test_exercises_every_public_command_and_restores_identical_mermaid(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("gitGraph")

        commands = (
            DiagramCommand("configure", {"mainBranchName": "main", "showCommitLabel": False}),
            DiagramCommand("add_commit", {"id": "initial", "label": 'ZERO "root"', "tag": "v1"}),
            DiagramCommand("add_branch", {"id": "develop", "label": "develop", "order": 1}),
            DiagramCommand("checkout", {"id": "checkout_develop", "branch": "develop"}),
            DiagramCommand("add_commit", {"id": "feature", "label": "FEATURE", "commit_type": "HIGHLIGHT"}),
        )
        for command in commands:
            application.apply(diagram, command)

        source = application.render(diagram)
        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))

        assert set(application.diagram_description("gitGraph").commands) == {item.operation for item in commands} | {
            "update_element",
            "remove_element",
            "move_element",
            "reorder_elements",
            "update_relation",
            "remove_relation",
        }
        assert 'commit id: "ZERO \\"root\\"" tag: "v1"' in source
        assert "branch develop order: 1" in source
        assert "checkout develop" in source
        assert 'commit id: "FEATURE" type: HIGHLIGHT' in source
        assert application.render(restored) == source

    def test_rejects_invalid_commit_types_duplicate_ids_and_unknown_branches(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("gitGraph")
        application.apply(diagram, DiagramCommand("add_commit", {"id": "first", "label": "FIRST"}))

        with pytest.raises(RuntimeError, match=r"'add_commit' has invalid arguments"):
            application.apply(
                diagram, DiagramCommand("add_commit", {"id": "bad", "label": "BAD", "commit_type": "LOUD"})
            )
        with pytest.raises(RuntimeError, match=r"already exists"):
            application.apply(diagram, DiagramCommand("add_commit", {"id": "first", "label": "AGAIN"}))
        with pytest.raises(RuntimeError, match=r"unknown|does not exist"):
            application.apply(diagram, DiagramCommand("checkout", {"id": "missing", "branch": "missing"}))
