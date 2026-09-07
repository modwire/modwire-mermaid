from collections.abc import Mapping
from typing import cast
from xml.etree import ElementTree

import pytest

from mermaiden import Application


class TestRenderValidation:
    def test_class_text_preserves_slashes_in_mermaid_source_and_svg(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_class", {"id": "diagrams/api", "label": "diagrams/api"})

        snapshot = application.snapshot(diagram).to_dict()
        source = application.render(diagram)
        report = application.validate_render(diagram)
        element = cast(Mapping[str, object], cast(list[object], snapshot["elements"])[0])
        fields = cast(Mapping[str, object], element["fields"])

        assert fields["id"] == "diagrams/api"
        assert '["diagrams/api"]' in source
        assert "#47;" not in source
        assert report.success, report.diagnostics
        svg = ElementTree.fromstring(report.svg)
        assert any("diagrams/api" in "".join(element.itertext()) for element in svg.iter())
        assert "&#47;" not in report.svg

    def test_class_text_is_rendered_literally_in_labels_relations_and_notes(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_namespace", {"id": "sales", "label": "Old name"})
        application.execute(diagram, "add_class", {"id": "Order[Item]", "label": 'Order "żółć"', "parent_id": "sales"})
        application.execute(diagram, "add_class", {"id": "invoice", "label": "Invoice"})
        application.execute(
            diagram,
            "update_element",
            {
                "id": "sales",
                "kind": "class_namespace",
                "changes": {"label": 'Sales "core"'},
            },
        )
        application.execute(
            diagram,
            "add_relation",
            {
                "id": "billing",
                "source_id": "Order[Item]",
                "target_id": "invoice",
                "label": "bills: order",
                "source_label": 'one "order"',
                "target_label": "0..*",
            },
        )
        application.execute(
            diagram,
            "add_note",
            {
                "id": "note",
                "class_id": "Order[Item]",
                "text": 'Use "quotes", <b>literal</b> & #quot;',
            },
        )
        before = application.snapshot(diagram).to_dict()

        report = application.validate_render(application.restore(before))

        assert report.success, report.diagnostics
        svg = ElementTree.fromstring(report.svg)
        text = " ".join(
            "".join(element.itertext())
            for element in svg.iter()
            if element.tag in {"{http://www.w3.org/2000/svg}text", "{http://www.w3.org/1999/xhtml}span"}
        )
        for label in (
            'Order "żółć"',
            'Sales "core"',
            "Invoice",
            "bills: order",
            'one "order"',
            "0..*",
            'Use "quotes", <b>literal</b> & #quot;',
        ):
            assert label in text
        assert "Old name" not in text
        assert application.snapshot(diagram).to_dict() == before

    def test_class_members_render_with_their_types_visibility_and_parameter_order(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(
            diagram,
            "add_class",
            {
                "id": "catalog",
                "label": "Catalog",
                "attributes": [
                    {
                        "name": "items",
                        "type": {"name": "List", "arguments": [{"name": "Item"}]},
                        "visibility": "private",
                    },
                    {"name": "count", "type": {"name": "int"}, "visibility": "protected", "static": True},
                ],
                "methods": [
                    {
                        "name": "find",
                        "return_type": {"name": "Item"},
                        "visibility": "public",
                        "parameters": [
                            {"name": "key", "type": {"name": "str"}},
                            {"name": "limit", "type": {"name": "int"}},
                        ],
                    },
                    {
                        "name": "refresh",
                        "return_type": {"name": "void"},
                        "visibility": "package",
                        "modifier": "abstract",
                    },
                ],
            },
        )

        report = application.validate_render(diagram)

        assert report.success, report.diagnostics
        svg = ElementTree.fromstring(report.svg)
        text = " ".join(
            "".join(element.itertext())
            for element in svg.iter()
            if element.tag in {"{http://www.w3.org/2000/svg}text", "{http://www.w3.org/1999/xhtml}span"}
        )
        for member in ("-List<Item> items", "#int count", "+find(str key, int limit)", "Item", "~refresh()", "void"):
            assert member in text
        assert any(
            "".join(element.itertext()) == "#int count" and "underline" in element.attrib.get("style", "")
            for element in svg.iter()
        )
        assert any(
            "".join(element.itertext()).startswith("~refresh()") and "italic" in element.attrib.get("style", "")
            for element in svg.iter()
        )

    def test_draft_diagram_can_be_persisted_but_not_rendered(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")

        payload = application.snapshot(diagram).to_dict()
        restored = application.restore(payload)
        report = application.validate_render(diagram)

        assert application.snapshot(restored).to_dict() == payload
        assert not report.success
        assert report.diagram_id == "sequenceDiagram"
        assert report.mermaid_version == "11.16.0"
        assert report.diagnostics[0].code == "diagram_invalid"
        assert "Diagram requires at least one element" in report.diagnostics[0].details
        with pytest.raises(RuntimeError, match="Cannot render invalid diagram 'sequenceDiagram'"):
            application.render(restored)

    def test_a_valid_snapshot_tampered_into_an_invalid_state_cannot_be_restored(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.execute(
            diagram,
            "add_participant",
            {"id": "participant_example", "label": "Participant Example"},
        )
        payload = application.snapshot(diagram).to_dict()
        payload["elements"] = []

        with pytest.raises(RuntimeError, match="Cannot restore invalid diagram 'sequenceDiagram'"):
            application.restore(payload)

    def test_full_render_validation_is_a_non_mutating_application_operation(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")
        application.execute(
            diagram,
            "add_participant",
            {"id": "participant_example", "label": "Participant Example"},
        )
        before = application.snapshot(diagram).to_dict()

        report = application.validate_render(diagram)

        assert report.success
        assert report.diagram_id == "sequenceDiagram"
        assert report.mermaid_version == "11.16.0"
        assert report.svg.startswith("<svg")
        assert not report.diagnostics
        assert application.snapshot(diagram).to_dict() == before
