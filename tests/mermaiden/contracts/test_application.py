import json
from collections.abc import Mapping
from typing import cast

import pytest

from mermaiden import Application
from mermaiden.application import DiagramCommand, UnknownCommand


class TestApplication:
    def _contains_none(self, value: object) -> bool:
        if value is None:
            return True
        if isinstance(value, Mapping):
            return any(self._contains_none(item) for item in cast(Mapping[object, object], value).values())
        if isinstance(value, list | tuple):
            return any(self._contains_none(item) for item in cast(list[object] | tuple[object, ...], value))
        return False

    def test_creates_mutates_persists_restores_and_renders_a_diagram(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")

        application.apply(diagram, DiagramCommand("add_participant", {"id": "client", "label": "Client"}))
        application.apply(diagram, DiagramCommand("add_participant", {"id": "api", "label": "API"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_message",
                {"id": "request", "source_id": "client", "target_id": "api", "label": "Request"},
            ),
        )

        payload = application.snapshot(diagram).to_dict()
        restored = application.restore(json.loads(json.dumps(payload)))

        assert application.render(restored) == application.render(diagram)
        assert application.render(restored).endswith(
            "sequenceDiagram\n"
            'participant client@{ "type": "participant" } as Client\n'
            'participant api@{ "type": "participant" } as API\n'
            "client->>api: Request\n"
        )

    def test_creates_independent_diagram_instances_of_the_same_kind(self) -> None:
        application = Application.create()
        first = application.create_diagram("sequenceDiagram")
        second = application.create_diagram("sequenceDiagram")

        application.apply(first, DiagramCommand("add_participant", {"id": "first", "label": "First"}))

        assert first is not second
        assert "participant first" in application.render(first)
        assert not second.root_elements

    def test_coerces_json_enum_command_arguments(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("sequenceDiagram")

        application.apply(
            diagram,
            DiagramCommand("add_participant", {"id": "actor", "label": "Actor", "kind": "actor"}),
        )

        assert "actor actor as Actor" in application.render(diagram)

    def test_preserves_and_renders_a_class_identifier_separately_from_its_label(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")

        application.apply(
            diagram,
            DiagramCommand("add_class", {"id": "example_class", "label": "Example Class"}),
        )

        snapshot = application.snapshot(diagram).to_dict()
        element = cast(Mapping[str, object], cast(list[object], snapshot["elements"])[0])
        fields = cast(Mapping[str, object], element["fields"])

        assert fields["id"] == "example_class"
        assert fields["label"] == "Example Class"
        assert 'class c_v_example_class["Example Class"] {' in application.render(diagram)

    def test_replaces_the_complete_configuration_using_concrete_defaults(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")

        application.apply(diagram, DiagramCommand("configure", {"padding": 12}))
        application.apply(diagram, DiagramCommand("add_block", {"id": "example", "label": "Example"}))
        assert 'block: {"padding": 12}' in application.render(diagram)

        application.apply(diagram, DiagramCommand("configure", {}))

        assert 'block: {"padding": 8}' in application.render(diagram)

    def test_rejects_unknown_configuration_fields(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")

        with pytest.raises(UnknownCommand, match="'configure' has invalid arguments"):
            application.apply(diagram, DiagramCommand("configure", {"paddding": 12}))

    @pytest.mark.parametrize(
        ("diagram_id", "configuration", "setup"),
        (
            ("block", {"padding": 12}, DiagramCommand("add_block", {"id": "example", "label": "Example"})),
            (
                "architecture-beta",
                {"nodeSeparation": 96, "seed": 7},
                DiagramCommand("add_service", {"id": "example", "label": "Example"}),
            ),
            (
                "C4Context",
                {"c4ShapeInRow": 3, "messageFontSize": 16},
                DiagramCommand("add_person", {"id": "example", "label": "Example"}),
            ),
            (
                "pie",
                {"legendPosition": "top"},
                DiagramCommand("add_slice", {"id": "example", "label": "Example", "value": 1}),
            ),
            (
                "gitGraph",
                {"nodeLabel": {"width": 90, "height": 110, "x": -20, "y": 5}},
                DiagramCommand("add_commit", {"id": "example", "label": "Example"}),
            ),
        ),
    )
    def test_persists_scalar_enum_and_nested_configurations(
        self,
        diagram_id: str,
        configuration: Mapping[str, object],
        setup: DiagramCommand,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram(diagram_id)
        application.apply(diagram, DiagramCommand("configure", configuration))
        application.apply(diagram, setup)
        source = application.render(diagram)

        payload = application.snapshot(diagram).to_dict()
        restored = application.restore(json.loads(json.dumps(payload)))

        assert payload["version"] == 4
        assert "configuration" not in cast(Mapping[str, object], payload["properties"])
        assert not self._contains_none(payload["configuration"])
        assert application.snapshot(restored).to_dict() == payload
        assert application.render(restored) == source

    def test_serializes_non_default_architecture_configuration(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("architecture-beta")

        application.apply(
            diagram,
            DiagramCommand(
                "configure",
                {
                    "useMaxWidth": False,
                    "padding": 48,
                    "iconSize": 96,
                    "fontSize": 18,
                    "randomize": True,
                    "nodeSeparation": 120,
                    "idealEdgeLengthMultiplier": 2,
                    "edgeElasticity": 0.7,
                    "numIter": 3000,
                    "seed": 7,
                },
            ),
        )
        application.apply(diagram, DiagramCommand("add_service", {"id": "example", "label": "Example"}))

        assert (
            'architecture: {"useMaxWidth": false, "padding": 48.0, "iconSize": 96.0, '
            '"fontSize": 18.0, "randomize": true, "nodeSeparation": 120.0, '
            '"idealEdgeLengthMultiplier": 2.0, "edgeElasticity": 0.7, "numIter": 3000, "seed": 7.0}'
            in application.render(diagram)
        )

    def test_serializes_non_default_c4_configuration(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("C4Context")

        application.apply(
            diagram,
            DiagramCommand(
                "configure",
                {
                    "diagramMarginX": 64,
                    "diagramMarginY": 24,
                    "c4ShapeMargin": 56,
                    "c4ShapePadding": 28,
                    "width": 240,
                    "height": 72,
                    "boxMargin": 16,
                    "useMaxWidth": False,
                    "c4ShapeInRow": 3,
                    "nextLinePaddingX": 12,
                    "c4BoundaryInRow": 1,
                    "messageFontSize": 16,
                },
            ),
        )
        application.apply(diagram, DiagramCommand("add_person", {"id": "example", "label": "Example"}))

        assert (
            'c4: {"diagramMarginX": 64, "diagramMarginY": 24, "c4ShapeMargin": 56, '
            '"c4ShapePadding": 28, "width": 240, "height": 72, "boxMargin": 16, '
            '"useMaxWidth": false, "c4ShapeInRow": 3, "nextLinePaddingX": 12.0, '
            '"c4BoundaryInRow": 1, "messageFontSize": 16.0}' in application.render(diagram)
        )
