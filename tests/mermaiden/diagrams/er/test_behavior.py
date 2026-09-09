import json
import re
from collections.abc import Mapping
from typing import cast

import pytest

from mermaiden.application import Application, DiagramCommand, UnknownCommand


class TestEntityRelationshipDiagram:
    @pytest.mark.parametrize(
        "command",
        (
            DiagramCommand("configure", {"layoutDirection": "LR"}),
            DiagramCommand("set_direction", {"direction": "LR"}),
        ),
        ids=("configure", "set_direction"),
    )
    def test_direction_commands_keep_configuration_body_and_restored_snapshot_in_sync(
        self,
        command: DiagramCommand,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")
        application.apply(diagram, DiagramCommand("add_entity", {"id": "CUSTOMER", "label": "Customer"}))

        application.apply(diagram, command)
        source = application.render(diagram)
        snapshot = json.loads(json.dumps(application.snapshot(diagram).to_dict()))
        restored = application.restore(snapshot)

        assert '"layoutDirection": "LR"' in source
        assert "\nerDiagram\ndirection LR\n" in source
        assert snapshot["configuration"]["fields"]["layout_direction"] == "LR"
        assert snapshot["properties"]["direction"] == "LR"
        assert application.render(restored) == source
        assert application.snapshot(restored).to_dict() == snapshot

    @pytest.mark.parametrize(
        ("operation", "arguments", "field"),
        (
            ("configure", {"layoutDirection": "SIDEWAYS"}, "layoutDirection"),
            ("set_direction", {"direction": "SIDEWAYS"}, "direction"),
        ),
    )
    def test_direction_commands_advertise_and_enforce_supported_values(
        self,
        operation: str,
        arguments: dict[str, object],
        field: str,
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")
        schema = application.diagram_description("erDiagram").commands[operation]
        properties = cast(dict[str, dict[str, object]], schema["properties"])
        definitions = cast(dict[str, dict[str, object]], schema["$defs"])

        assert properties[field]["$ref"] == "#/$defs/EntityRelationshipDirection"
        assert definitions["EntityRelationshipDirection"]["enum"] == ["TB", "BT", "LR", "RL"]
        with pytest.raises(UnknownCommand, match=rf"'{operation}' has invalid arguments"):
            application.apply(diagram, DiagramCommand(operation, arguments))

    def test_exercises_every_public_command_and_restores_identical_mermaid(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")

        for command in (
            DiagramCommand("configure", {"layoutDirection": "LR", "entityPadding": 20}),
            DiagramCommand("set_direction", {"direction": "LR"}),
            DiagramCommand("add_entity", {"id": "CUSTOMER", "label": 'Customer "account"'}),
            DiagramCommand(
                "add_attribute",
                {
                    "id": "customer_id",
                    "label": "id",
                    "data_type": "int",
                    "entity_id": "CUSTOMER",
                    "keys": ["PK"],
                    "comment": "identifier",
                },
            ),
            DiagramCommand("add_entity", {"id": "ORDER", "label": "Order"}),
            DiagramCommand(
                "add_relationship",
                {
                    "id": "places",
                    "source_id": "CUSTOMER",
                    "target_id": "ORDER",
                    "label": 'references content; "protected" — while scoped: [v2] #1 & <trusted>',
                    "source_cardinality": "exactly_one",
                    "target_cardinality": "zero_or_more",
                    "identifying": True,
                },
            ),
        ):
            application.apply(diagram, command)

        source = application.render(diagram)
        restored = application.restore(json.loads(json.dumps(application.snapshot(diagram).to_dict())))

        assert set(application.diagram_description("erDiagram").commands) == {
            "configure",
            "set_direction",
            "add_entity",
            "add_attribute",
            "add_relationship",
            "update_element",
            "remove_element",
            "move_element",
            "reorder_elements",
            "update_relation",
            "remove_relation",
        }
        assert "direction LR" in source
        assert "int id PK" in source
        assert (
            'CUSTOMER ||--o{ ORDER : "references content; #quot;protected#quot; — while scoped: '
            '[v2] #35;1 #38; #60;trusted#62;"'
        ) in source
        assert application.render(restored) == source

    def test_rejects_invalid_configuration_duplicates_and_unknown_entities(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")
        application.apply(diagram, DiagramCommand("add_entity", {"id": "ONE", "label": "One"}))

        with pytest.raises(UnknownCommand):
            application.apply(diagram, DiagramCommand("configure", {"entityPadding": "wide"}))
        with pytest.raises(UnknownCommand):
            application.apply(
                diagram,
                DiagramCommand(
                    "add_relationship",
                    {
                        "id": "syntax",
                        "source_id": "ONE",
                        "target_id": "ONE",
                        "label": "syntax",
                        "notation": "||--||",
                    },
                ),
            )
        with pytest.raises(RuntimeError, match=r"already exists"):
            application.apply(diagram, DiagramCommand("add_entity", {"id": "ONE", "label": "Again"}))
        with pytest.raises(RuntimeError, match=r"unknown|does not exist"):
            application.apply(
                diagram,
                DiagramCommand("add_attribute", {"id": "x", "label": "x", "data_type": "int", "entity_id": "MISSING"}),
            )

    @pytest.mark.parametrize("data_type", ("positive int", "", "0int", "PK", "PK-type", "int??", "int\n"))
    def test_rejects_unrenderable_attribute_types_before_changing_the_snapshot(self, data_type: str) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")
        application.apply(diagram, DiagramCommand("add_entity", {"id": "CUSTOMER", "label": "Customer"}))
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(UnknownCommand, match="invalid arguments"):
            application.apply(
                diagram,
                DiagramCommand(
                    "add_attribute",
                    {"id": "revision", "label": "revision", "data_type": data_type, "entity_id": "CUSTOMER"},
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_an_unrenderable_attribute_type_update_without_changing_the_snapshot(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")
        application.apply(diagram, DiagramCommand("add_entity", {"id": "CUSTOMER", "label": "Customer"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_attribute",
                {"id": "revision", "label": "revision", "data_type": "int", "entity_id": "CUSTOMER"},
            ),
        )
        before = application.snapshot(diagram).to_dict()

        with pytest.raises(UnknownCommand, match="invalid arguments"):
            application.apply(
                diagram,
                DiagramCommand(
                    "update_element",
                    {
                        "id": "revision",
                        "kind": "entity_attribute",
                        "changes": {"data_type": "positive int"},
                    },
                ),
            )

        assert application.snapshot(diagram).to_dict() == before

    def test_rejects_a_persisted_unrenderable_attribute_type(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("erDiagram")
        application.apply(diagram, DiagramCommand("add_entity", {"id": "CUSTOMER", "label": "Customer"}))
        application.apply(
            diagram,
            DiagramCommand(
                "add_attribute",
                {"id": "revision", "label": "revision", "data_type": "int", "entity_id": "CUSTOMER"},
            ),
        )
        payload = json.loads(json.dumps(application.snapshot(diagram).to_dict()))
        entity = cast(dict[str, object], cast(list[object], payload["elements"])[0])
        entity_fields = cast(dict[str, object], entity["fields"])
        attribute = cast(dict[str, object], cast(list[object], entity_fields["elements"])[0])
        cast(dict[str, object], attribute["fields"])["data_type"] = "positive int"

        with pytest.raises(ValueError, match="data_type"):
            application.restore(payload)

    def test_publishes_the_same_attribute_type_restriction_for_add_update_and_persistence(self) -> None:
        application = Application.create()
        add_schema = application.command_payload("erDiagram", "add_attribute").model_json_schema()
        update_schema = application.command_payload("erDiagram", "update_element").model_json_schema()
        object_schema = application.diagram_description("erDiagram").elements["entity_attribute"]

        add_type = add_schema["properties"]["data_type"]
        update_changes = update_schema["$defs"]["EntityRelationshipDiagram_update_element_entity_attribute_changes"]
        update_type = update_changes["properties"]["data_type"]
        object_type = cast(Mapping[str, Mapping[str, object]], object_schema["properties"])["data_type"]

        reference = cast(str, add_type["$ref"]).removeprefix("#/$defs/")
        pattern = cast(str, add_schema["$defs"][reference]["pattern"])
        assert pattern == update_type["pattern"] == object_type["pattern"]
        assert re.search(pattern, "public.geometry(point,4326)?")
        assert re.search(pattern, "positive~ int ~")
        assert re.search(pattern, "`positive int`")
        assert not re.search(pattern, "positive int")
