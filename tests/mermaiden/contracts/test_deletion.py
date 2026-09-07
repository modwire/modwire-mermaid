from typing import Any, cast

import pytest

from mermaiden import Application
from mermaiden.application import DiagramCommand


class TestDeletion:
    def test_rejects_an_unsafe_delete_without_changing_the_diagram(self) -> None:
        application, diagram = self._sequence_diagram_with_dependants()
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(RuntimeError, match="still has dependants; use cascade=True"):
            application.apply(diagram, DiagramCommand("remove_element", {"id": "group"}))

        assert application.snapshot(diagram).to_dict() == before

    def test_cascade_reports_every_removed_object_and_commits_atomically(self) -> None:
        application, diagram = self._sequence_diagram_with_dependants()

        report = application.apply(
            diagram,
            DiagramCommand("remove_element", {"id": "group", "cascade": True}),
        )

        assert report is not None
        assert report.accepted
        assert tuple((item.kind, item.id) for item in report.removed) == (
            ("element", "group"),
            ("element", "participant"),
            ("relation", "message"),
            ("annotation", "note"),
        )
        assert diagram.find_element("group") is None
        assert not diagram.find_relations()
        assert not diagram.find_annotations()

    def test_removes_relations_and_annotations_through_discovered_commands(self) -> None:
        application, diagram = self._sequence_diagram_with_dependants()

        annotation_report = application.apply(
            diagram,
            DiagramCommand("remove_annotation", {"id": "note"}),
        )
        relation_report = application.apply(
            diagram,
            DiagramCommand("remove_relation", {"id": "message"}),
        )

        assert annotation_report is not None
        assert tuple((item.kind, item.id) for item in annotation_report.removed) == (("annotation", "note"),)
        assert relation_report is not None
        assert tuple((item.kind, item.id) for item in relation_report.removed) == (("relation", "message"),)

    def test_requires_explicit_cascade_to_remove_a_relation_annotation(self) -> None:
        application, diagram = self._sequence_diagram_with_dependants()
        payload = application.snapshot(diagram).to_dict()
        annotation = cast(list[dict[str, Any]], payload["annotations"])[0]
        fields = cast(dict[str, Any], annotation["fields"])
        target = cast(list[dict[str, Any]], fields["targets"])[0]
        target_fields = cast(dict[str, Any], target["fields"])
        target_fields["id"] = "message"
        cast(dict[str, Any], target_fields["kind"])["value"] = "relation"
        restored = application.restore(payload)
        before = application.snapshot(restored).to_dict()

        with pytest.raises(RuntimeError, match="still has annotations"):
            application.apply(restored, DiagramCommand("remove_relation", {"id": "message"}))

        assert application.snapshot(restored).to_dict() == before

        report = application.apply(
            restored,
            DiagramCommand("remove_relation", {"id": "message", "cascade": True}),
        )

        assert report is not None
        assert tuple((item.kind, item.id) for item in report.removed) == (
            ("relation", "message"),
            ("annotation", "note"),
        )

    @staticmethod
    def _sequence_diagram_with_dependants():
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        for command in (
            DiagramCommand("add_box", {"id": "group", "label": "Group"}),
            DiagramCommand(
                "add_participant",
                {"id": "participant", "label": "Participant", "box_id": "group"},
            ),
            DiagramCommand("add_participant", {"id": "peer", "label": "Peer"}),
            DiagramCommand(
                "add_message",
                {"id": "message", "source_id": "participant", "target_id": "peer", "label": "Message"},
            ),
            DiagramCommand("add_note", {"id": "note", "text": "Note", "participant_ids": ["participant"]}),
        ):
            application.apply(diagram, command)
        return application, diagram

    @pytest.mark.parametrize("cascade", ("true", "false", 0, 1, 0.5, None))
    @pytest.mark.parametrize("operation,identifier", (("remove_element", "group"), ("remove_relation", "message")))
    def test_non_boolean_cascade_is_rejected_before_deleting_anything(
        self, cascade: object, operation: str, identifier: str
    ) -> None:
        application, diagram = self._sequence_diagram_with_dependants()
        before = application.snapshot(diagram).to_dict()
        source = application.render(diagram)

        with pytest.raises(RuntimeError, match="cascade"):
            application.execute(diagram, operation, {"id": identifier, "cascade": cascade})

        assert application.snapshot(diagram).to_dict() == before
        assert application.render(diagram) == source
