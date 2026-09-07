import json
from collections.abc import Mapping, Sequence
from typing import cast

import pytest

from mermaiden.application import Application, DiagramCommand


class TestElementMovement:
    def test_gantt_add_and_move_reject_task_at_root_without_changing_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("gantt")
        application.apply(diagram, DiagramCommand("add_section", {"id": "section_example", "label": "Section"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_task",
                {
                    "id": "task_example",
                    "label": "Task",
                    "start": {"kind": "automatic"},
                    "finish": {"kind": "duration", "amount": 0},
                    "section_id": "section_example",
                },
            ),
        )
        before = application.snapshot(diagram).to_dict()

        rejected = (
            DiagramCommand(
                "add_task",
                {
                    "id": "root_task",
                    "label": "Root Task",
                    "start": {"kind": "automatic"},
                    "finish": {"kind": "duration", "amount": 0},
                    "section_id": "",
                },
            ),
            DiagramCommand(
                "move_element",
                {"id": "task_example", "kind": "task", "parent_id": ""},
            ),
        )
        for command in rejected:
            with pytest.raises(RuntimeError, match="cannot be placed in \\$root"):
                application.apply(diagram, command)
            assert application.snapshot(diagram).to_dict() == before

    def test_add_and_move_reject_incompatible_container_kind_without_changing_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("timeline")
        application.apply(diagram, DiagramCommand("add_section", {"id": "section_example", "label": "Section"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_period",
                {"id": "period_example", "label": "Period", "section_id": "section_example"},
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_event",
                {"id": "event_example", "label": "Event", "period_id": "period_example"},
            ),
        )
        before = application.snapshot(diagram).to_dict()

        rejected = (
            DiagramCommand(
                "add_event",
                {"id": "section_event", "label": "Event", "period_id": "section_example"},
            ),
            DiagramCommand(
                "move_element",
                {"id": "event_example", "kind": "timeline_event", "parent_id": "section_example"},
            ),
        )
        for command in rejected:
            with pytest.raises(RuntimeError, match="cannot be placed"):
                application.apply(diagram, command)
            assert application.snapshot(diagram).to_dict() == before

    @pytest.mark.parametrize(
        "element_ids",
        (
            ["first_example", "first_example"],
            ["first_example"],
            ["first_example", "second_example", "missing_example"],
        ),
    )
    def test_rejects_non_permutations_without_changing_the_snapshot(self, element_ids: Sequence[str]) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.apply(diagram, DiagramCommand("add_block", {"id": "first_example", "label": "First Example"}))
        application.apply(
            diagram,
            DiagramCommand("add_block", {"id": "second_example", "label": "Second Example"}),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError):
            application.apply(
                diagram,
                DiagramCommand("reorder_elements", {"parent_id": "", "element_ids": element_ids}),
            )

        assert application.snapshot(diagram).to_dict() == before

    @pytest.mark.parametrize("position", (-1, 3))
    def test_rejects_invalid_move_positions_without_changing_the_snapshot(self, position: int) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.apply(diagram, DiagramCommand("add_block", {"id": "first_example", "label": "First Example"}))
        application.apply(
            diagram,
            DiagramCommand("add_block", {"id": "second_example", "label": "Second Example"}),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError):
            application.apply(
                diagram,
                DiagramCommand(
                    "move_element",
                    {
                        "id": "first_example",
                        "kind": "block_node",
                        "parent_id": "",
                        "position": position,
                    },
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_non_container_parents_without_changing_the_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.apply(diagram, DiagramCommand("add_block", {"id": "first_example", "label": "First Example"}))
        application.apply(
            diagram,
            DiagramCommand("add_block", {"id": "second_example", "label": "Second Example"}),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match="not a container"):
            application.apply(
                diagram,
                DiagramCommand(
                    "move_element",
                    {
                        "id": "first_example",
                        "kind": "block_node",
                        "parent_id": "second_example",
                    },
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_moves_into_descendants_without_changing_the_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("flowchart")
        application.apply(
            diagram,
            DiagramCommand("add_group", {"id": "parent_example", "label": "Parent Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_group",
                {"id": "child_example", "label": "Child Example", "parent_id": "parent_example"},
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_start",
                {"id": "start_example", "label": "Start Example", "parent_id": "child_example"},
            ),
        )
        application.apply(diagram, DiagramCommand("add_end", {"id": "end_example", "label": "End Example"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_flow",
                {"id": "flow_example", "source_id": "start_example", "target_id": "end_example"},
            ),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match="own subtree"):
            application.apply(
                diagram,
                DiagramCommand(
                    "move_element",
                    {
                        "id": "parent_example",
                        "kind": "flow_group",
                        "parent_id": "child_example",
                    },
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_move_preserves_the_complete_subtree_references_and_snapshot_round_trip(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("flowchart")
        application.apply(
            diagram,
            DiagramCommand("add_group", {"id": "source_example", "label": "Source Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand("add_group", {"id": "target_example", "label": "Target Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_group",
                {"id": "moved_example", "label": "Moved Example", "parent_id": "source_example"},
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_start",
                {"id": "start_example", "label": "Start Example", "parent_id": "moved_example"},
            ),
        )
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
                "add_note",
                {"id": "note_example", "text": "Note Example", "element_ids": ["start_example"]},
            ),
        )

        application.apply(
            diagram,
            DiagramCommand(
                "move_element",
                {
                    "id": "moved_example",
                    "kind": "flow_group",
                    "parent_id": "target_example",
                    "position": 0,
                },
            ),
        )
        snapshot = application.snapshot(diagram).to_dict()
        target = self._element(snapshot, "target_example")
        target_fields = self._mapping(target["fields"])
        moved = self._element_fields(self._elements(target_fields["elements"]), "moved_example")
        moved_children = self._elements(moved["elements"])
        restored = application.restore(json.loads(json.dumps(snapshot)))
        report = application.validate_render(restored)

        assert self._element_fields(moved_children, "start_example")["id"] == "start_example"
        assert self._object(snapshot, "relations", "flow_example")
        assert self._object(snapshot, "annotations", "note_example")
        assert application.snapshot(restored).to_dict() == snapshot
        assert application.render(restored) == application.render(diagram)
        assert report.success
        assert report.svg.startswith("<svg")
        assert not report.diagnostics

    def test_reorders_root_and_direct_child_collections_deterministically(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.apply(
            diagram,
            DiagramCommand("add_group", {"id": "group_example", "label": "Group Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand("add_block", {"id": "root_example", "label": "Root Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_block",
                {"id": "first_example", "label": "First Example", "parent_id": "group_example"},
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_block",
                {"id": "second_example", "label": "Second Example", "parent_id": "group_example"},
            ),
        )

        application.apply(
            diagram,
            DiagramCommand(
                "reorder_elements",
                {"parent_id": "", "element_ids": ["root_example", "group_example"]},
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "reorder_elements",
                {"parent_id": "group_example", "element_ids": ["second_example", "first_example"]},
            ),
        )
        snapshot = application.snapshot(diagram).to_dict()
        roots = self._elements(snapshot["elements"])
        group = self._element_fields(roots, "group_example")
        children = self._elements(group["elements"])
        restored = application.restore(json.loads(json.dumps(snapshot)))
        report = application.validate_render(restored)

        assert self._ids(roots) == ("root_example", "group_example")
        assert self._ids(children) == ("second_example", "first_example")
        assert application.snapshot(restored).to_dict() == snapshot
        assert application.render(restored) == application.render(diagram)
        assert report.success
        assert report.svg.startswith("<svg")
        assert not report.diagnostics

    def test_accepts_current_move_and_order_as_snapshot_preserving_no_ops(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.apply(
            diagram,
            DiagramCommand("add_group", {"id": "group_example", "label": "Group Example"}),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "add_block",
                {"id": "block_example", "label": "Block Example", "parent_id": "group_example"},
            ),
        )
        before = application.snapshot(diagram).to_dict()
        source = application.render(diagram)

        application.apply(
            diagram,
            DiagramCommand(
                "move_element",
                {
                    "id": "block_example",
                    "kind": "block_node",
                    "parent_id": "group_example",
                    "position": 0,
                },
            ),
        )
        application.apply(
            diagram,
            DiagramCommand(
                "reorder_elements",
                {"parent_id": "group_example", "element_ids": ["block_example"]},
            ),
        )

        assert application.snapshot(diagram).to_dict() == before
        assert application.render(diagram) == source

    def test_catalog_publishes_strict_move_and_reorder_payloads_for_every_diagram(self) -> None:
        application = Application.create()

        for info in application.available_diagrams():
            description = application.diagram_description(info.id)
            assert "move_element" in description.commands
            assert "reorder_elements" in description.commands
            move_schema = application.command_payload(info.id, "move_element").model_json_schema()
            for kind in description.elements:
                variant = self._variant(move_schema, kind)
                assert variant["additionalProperties"] is False
                assert variant["required"] == ["id", "kind", "parent_id"]
                properties = self._mapping(variant["properties"])
                assert set(properties) == {"id", "kind", "parent_id", "position"}
                assert self._mapping(properties["kind"])["const"] == kind
                assert self._mapping(properties["position"])["minimum"] == 0
            reorder_schema = application.command_payload(info.id, "reorder_elements").model_json_schema()
            assert reorder_schema["additionalProperties"] is False
            assert reorder_schema["required"] == ["parent_id", "element_ids"]
            element_ids = self._mapping(self._mapping(reorder_schema["properties"])["element_ids"])
            assert element_ids["type"] == "array"
            assert element_ids["uniqueItems"] is True
            assert self._mapping(element_ids["items"])["minLength"] == 1

    def _variant(self, schema: Mapping[str, object], kind: str) -> Mapping[str, object]:
        discriminator = self._mapping(schema["discriminator"])
        mapping = self._mapping(discriminator["mapping"])
        return self._reference(schema, mapping[kind])

    def _reference(self, schema: Mapping[str, object], reference: object) -> Mapping[str, object]:
        assert isinstance(reference, str) and reference.startswith("#/$defs/")
        return self._mapping(self._mapping(schema["$defs"])[reference.removeprefix("#/$defs/")])

    def _element(self, snapshot: Mapping[str, object], id: str) -> Mapping[str, object]:
        return self._object(snapshot, "elements", id)

    def _object(self, snapshot: Mapping[str, object], collection: str, id: str) -> Mapping[str, object]:
        return next(
            item
            for value in cast(list[object], snapshot[collection])
            if (item := self._mapping(value))
            if self._mapping(item["fields"])["id"] == id
        )

    def _element_fields(
        self,
        elements: Sequence[Mapping[str, object]],
        id: str,
    ) -> Mapping[str, object]:
        return self._mapping(next(item for item in elements if self._mapping(item["fields"])["id"] == id)["fields"])

    def _elements(self, value: object) -> Sequence[Mapping[str, object]]:
        assert isinstance(value, list)
        return tuple(self._mapping(item) for item in cast(list[object], value))

    def _ids(self, elements: Sequence[Mapping[str, object]]) -> tuple[object, ...]:
        return tuple(self._mapping(item["fields"])["id"] for item in elements)

    def _mapping(self, value: object) -> Mapping[str, object]:
        assert isinstance(value, Mapping)
        return cast(Mapping[str, object], value)

    @pytest.mark.parametrize("position", ("0", False, True, 0.5, -1, None))
    def test_invalid_positions_preserve_order_and_allow_a_subsequent_valid_move(self, position: object) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.execute(diagram, "add_block", {"id": "first", "label": "First"})
        application.execute(diagram, "add_block", {"id": "second", "label": "Second"})
        before = application.snapshot(diagram).to_dict()
        source = application.render(diagram)

        with pytest.raises(RuntimeError, match="position"):
            application.execute(
                diagram, "move_element", {"id": "second", "kind": "block_node", "parent_id": "", "position": position}
            )

        assert application.snapshot(diagram).to_dict() == before
        assert application.render(diagram) == source
        application.execute(
            diagram, "move_element", {"id": "second", "kind": "block_node", "parent_id": "", "position": 0}
        )
        assert [element.id for element in diagram.root_elements] == ["second", "first"]
