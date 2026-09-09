import json

import pytest

from mermaiden.application import Application, DiagramCommand


class TestKanban:
    def test_exercises_every_public_command_and_restores_identical_mermaid(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("kanban")

        commands = (
            DiagramCommand("configure", {"padding": 12, "sectionWidth": 240, "ticketBaseUrl": "https://tracker/"}),
            DiagramCommand("add_column", {"id": "todo", "label": 'To "do"'}),
            DiagramCommand(
                "add_task",
                {
                    "id": "docs",
                    "label": "Write docs",
                    "column_id": "todo",
                    "assigned": "Ada",
                    "ticket": "DOC-1",
                    "priority": "High",
                },
            ),
        )
        for command in commands:
            application.apply(diagram, command)

        source = application.render(diagram)
        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))

        assert set(application.diagram_description("kanban").commands) == {item.operation for item in commands} | {
            "update_element",
            "remove_element",
            "move_element",
            "reorder_elements",
        }
        assert 'todo["To \\"do\\""]' in source
        assert 'docs["Write docs"]' in source
        assert 'assigned: "Ada"' in source
        assert 'ticket: "DOC-1"' in source
        assert 'priority: "High"' in source
        assert application.render(restored) == source

    def test_rejects_invalid_priorities_duplicates_and_unknown_columns(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("kanban")
        application.apply(diagram, DiagramCommand("add_column", {"id": "todo", "label": "Todo"}))

        with pytest.raises(RuntimeError, match=r"'add_task' has invalid arguments"):
            application.apply(
                diagram,
                DiagramCommand("add_task", {"id": "bad", "label": "Bad", "column_id": "todo", "priority": "Urgent"}),
            )
        with pytest.raises(RuntimeError, match=r"already exists"):
            application.apply(diagram, DiagramCommand("add_column", {"id": "todo", "label": "Again"}))
        with pytest.raises(RuntimeError, match=r"unknown|does not exist"):
            application.apply(
                diagram, DiagramCommand("add_task", {"id": "orphan", "label": "Orphan", "column_id": "missing"})
            )
