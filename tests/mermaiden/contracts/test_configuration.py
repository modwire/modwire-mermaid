from collections.abc import Mapping
from typing import cast

import pytest
from pydantic import ValidationError

from mermaiden import Application


class TestMermaidConfiguration:
    def _contains_json_null(self, value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, Mapping):
            mapping = cast(Mapping[object, object], value)
            return mapping.get("type") == "null" or any(self._contains_json_null(item) for item in mapping.values())
        if isinstance(value, list | tuple):
            return any(self._contains_json_null(item) for item in cast(list[object] | tuple[object, ...], value))
        return False

    def test_diagram_configuration_provides_a_source_keyed_mermaid_document(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.execute(diagram, "configure", {"padding": 12})
        application.execute(diagram, "add_block", {"id": "example", "label": "Example"})

        assert application.render(diagram).startswith(
            '---\nconfig:\n  wrap: true\n  block: {"padding": 12.0}\n---\nblock\n'
        )

    def test_diagram_configuration_validates_its_values_and_rejects_unknown_fields(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")

        with pytest.raises(RuntimeError, match="'configure' has invalid arguments"):
            application.execute(diagram, "configure", {"padding": "invalid"})

        with pytest.raises(RuntimeError, match="'configure' has invalid arguments"):
            application.execute(diagram, "configure", {"paddding": 12})

    def test_configuration_serialization_converts_nested_keys_to_camel_case(self) -> None:
        application = Application.create()
        git_graph = application.create_diagram("gitGraph")
        requirement = application.create_diagram("requirementDiagram")
        application.execute(git_graph, "add_commit", {"id": "commit", "label": "Commit"})
        application.execute(
            requirement,
            "add_requirement",
            {"id": "requirement", "requirement_id": "REQ-1", "text": "Requirement"},
        )

        assert '"nodeLabel": {"width": 75.0, "height": 100.0, "x": -25.0, "y": 0.0}' in application.render(git_graph)
        assert '"rectFill": "#f9f9f9"' in application.render(requirement)

    def test_architecture_configuration_uses_mermaids_concrete_defaults(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("architecture-beta")
        application.execute(diagram, "add_service", {"id": "example", "label": "Example"})
        source = application.render(diagram)

        assert '"useMaxWidth": true' in source
        assert '"padding": 40.0' in source
        assert '"nodeSeparation": 75.0' in source
        assert '"edgeElasticity": 0.45' in source
        assert '"numIter": 2500' in source

    @pytest.mark.parametrize(
        "values",
        (
            {"padding": -1},
            {"icon_size": 0},
            {"font_size": 0},
            {"node_separation": -1},
            {"ideal_edge_length_multiplier": 0},
            {"edge_elasticity": -0.01},
            {"edge_elasticity": 1.01},
            {"num_iter": 0},
        ),
    )
    def test_architecture_configuration_accepts_values_left_unbounded_by_mermaid(
        self,
        values: Mapping[str, object],
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("architecture-beta")

        application.execute(diagram, "configure", values)

    def test_c4_configuration_uses_mermaids_concrete_layout_defaults(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("C4Context")
        application.execute(diagram, "add_person", {"id": "example", "label": "Example"})
        source = application.render(diagram)

        assert '"diagramMarginX": 50' in source
        assert '"c4ShapePadding": 20' in source
        assert '"width": 216' in source
        assert '"c4ShapeInRow": 4' in source
        assert '"messageFontSize": 12.0' in source

    @pytest.mark.parametrize(
        "values",
        (
            {"diagram_margin_x": -1},
            {"diagram_margin_y": -1},
            {"c4_shape_margin": -1},
            {"c4_shape_padding": -1},
            {"width": -1},
            {"height": -1},
            {"box_margin": -1},
            {"c4_shape_in_row": -1},
            {"c4_boundary_in_row": -1},
            {"message_font_size": ""},
        ),
    )
    def test_c4_configuration_rejects_invalid_layout_values(
        self,
        values: Mapping[str, object],
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("C4Context")

        with pytest.raises(RuntimeError, match="'configure' has invalid arguments"):
            application.execute(diagram, "configure", values)

    @pytest.mark.parametrize(
        ("diagram_id", "field", "boundary", "outside"),
        (
            ("block", "padding", 0, -0.01),
            ("cynefin-beta", "width", 1, 0),
            ("cynefin-beta", "height", 1, 0),
            ("cynefin-beta", "padding", 0, -0.01),
            ("cynefin-beta", "boundaryAmplitude", 0, -0.01),
            ("cynefin-beta", "boundaryAmplitude", 50, 50.01),
            ("erDiagram", "titleTopMargin", 0, -1),
            ("erDiagram", "diagramPadding", 0, -1),
            ("erDiagram", "minEntityWidth", 0, -1),
            ("erDiagram", "minEntityHeight", 0, -1),
            ("erDiagram", "entityPadding", 0, -1),
            ("gantt", "titleTopMargin", 0, -1),
            ("gantt", "barHeight", 0, -1),
            ("gantt", "topPadding", 0, -1),
            ("gantt", "rightPadding", 0, -1),
            ("gantt", "leftPadding", 0, -1),
            ("gantt", "gridLineStartPadding", 0, -1),
            ("gantt", "fontSize", 0, -1),
            ("gantt", "sectionFontSize", 0, -1),
            ("gantt", "numberSectionStyles", 0, -1),
            ("gitGraph", "titleTopMargin", 0, -1),
            ("packet", "rowHeight", 1, 0),
            ("packet", "bitWidth", 1, 0),
            ("packet", "bitsPerRow", 1, 0),
            ("packet", "paddingX", 0, -0.01),
            ("packet", "paddingY", 0, -0.01),
            ("pie", "textPosition", 0, -0.01),
            ("pie", "textPosition", 1, 1.01),
            ("pie", "donutHole", 0, -0.01),
            ("pie", "donutHole", 0.9, 1),
            ("radar-beta", "width", 1, 0),
            ("radar-beta", "height", 1, 0),
            ("radar-beta", "marginTop", 0, -0.01),
            ("radar-beta", "marginRight", 0, -0.01),
            ("radar-beta", "marginBottom", 0, -0.01),
            ("radar-beta", "marginLeft", 0, -0.01),
            ("radar-beta", "axisScaleFactor", 0, -0.01),
            ("radar-beta", "axisLabelFactor", 0, -0.01),
            ("radar-beta", "curveTension", 0, -0.01),
            ("radar-beta", "curveTension", 1, 2),
            ("railroad-ebnf-beta", "padding", 0, -0.01),
            ("railroad-ebnf-beta", "verticalSeparation", 0, -0.01),
            ("railroad-ebnf-beta", "horizontalSeparation", 0, -0.01),
            ("railroad-ebnf-beta", "arcRadius", 0, -0.01),
            ("railroad-ebnf-beta", "fontSize", 0, -0.01),
            ("stateDiagram-v2", "titleTopMargin", 0, -1),
            ("venn-beta", "width", 1, 0),
            ("venn-beta", "height", 1, 0),
            ("venn-beta", "padding", 0, -0.01),
        ),
    )
    def test_configuration_enforces_mermaid_numeric_boundaries(
        self,
        diagram_id: str,
        field: str,
        boundary: float,
        outside: float,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram(diagram_id)

        application.execute(diagram, "configure", {field: boundary})

        with pytest.raises(RuntimeError, match="'configure' has invalid arguments"):
            application.execute(diagram, "configure", {field: outside})

    @pytest.mark.parametrize(
        "weekday",
        ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"),
    )
    def test_gantt_configuration_accepts_every_mermaid_weekday(self, weekday: str) -> None:
        application = Application.create()
        diagram = application.create_diagram("gantt")

        application.execute(diagram, "configure", {"weekday": weekday})

    @pytest.mark.parametrize(
        ("diagram_id", "values"),
        (
            ("erDiagram", {"layoutDirection": "XX"}),
            ("gantt", {"weekday": "funday"}),
        ),
    )
    def test_configuration_rejects_values_outside_mermaid_enums(
        self,
        diagram_id: str,
        values: Mapping[str, object],
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram(diagram_id)

        with pytest.raises(RuntimeError, match="'configure' has invalid arguments"):
            application.execute(diagram, "configure", values)

    def test_every_diagram_has_strict_non_nullable_configuration_defaults(self) -> None:
        application = Application.create()

        for info in application.available_diagrams():
            payload_type = application.command_payload(info.id, "configure")
            schema = payload_type.model_json_schema()
            configuration = payload_type.model_validate({})

            assert schema["additionalProperties"] is False
            assert not self._contains_json_null(schema)
            assert not self._contains_json_null(configuration.model_dump(mode="json", by_alias=True))

            with pytest.raises(ValidationError):
                payload_type.model_validate({"unknown_configuration_field": True})
