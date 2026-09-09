import json
from collections.abc import Mapping
from typing import cast

import pytest

from mermaiden import Application


class TestPersistence:
    @pytest.mark.parametrize("version", (1, 2, 3, 4, 6))
    def test_rejects_a_snapshot_from_an_unsupported_contract_version(self, version: int) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.execute(diagram, "add_block", {"id": "example", "label": "Example"})
        payload = application.snapshot(diagram).to_dict()
        payload["version"] = version
        del payload["configuration"]

        with pytest.raises(RuntimeError, match=f"version '{version}'; expected version '5'"):
            application.restore(payload)

    @pytest.mark.parametrize("field,value", (("name", "submit()"), ("type", None), ("visibility", "+")))
    def test_restore_rejects_invalid_member_values_in_an_otherwise_valid_snapshot(
        self, field: str, value: object
    ) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(
            diagram,
            "add_class",
            {
                "id": "order",
                "label": "Order",
                "attributes": [{"name": "total", "type": {"name": "Decimal"}}],
            },
        )
        payload = application.snapshot(diagram).to_dict()
        element = cast(list[dict[str, object]], payload["elements"])[0]
        attributes = cast(list[dict[str, object]], cast(dict[str, object], element["fields"])["attributes"])
        member = cast(dict[str, object], attributes[0]["fields"])
        member[field] = value

        with pytest.raises((RuntimeError, ValueError), match=field):
            application.restore(payload)

        restored = application.restore(application.snapshot(diagram).to_dict())
        assert application.render(restored) == application.render(diagram)

    def test_uses_stable_registered_discriminators_for_nested_values_and_enums(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(
            diagram,
            "add_class",
            {
                "id": "order",
                "label": "Order",
                "attributes": [
                    {"name": "total", "type": {"name": "Decimal"}, "visibility": "private"},
                ],
            },
        )

        payload = application.snapshot(diagram).to_dict()
        encoded = json.dumps(payload)
        element = cast(Mapping[str, object], cast(list[object], payload["elements"])[0])
        fields = cast(Mapping[str, object], element["fields"])
        attribute = cast(Mapping[str, object], cast(list[object], fields["attributes"])[0])
        attribute_fields = cast(Mapping[str, object], attribute["fields"])
        visibility = cast(Mapping[str, object], attribute_fields["visibility"])

        assert element["$type"] == "mermaiden/element/classDiagram/class"
        assert attribute["$type"] == "mermaiden/value/classDiagram/class_attribute"
        assert visibility["$enum"] == "mermaiden/enum/classDiagram/visibility"
        assert "mermaiden.diagrams" not in encoded
        assert application.snapshot(application.restore(json.loads(encoded))).to_dict() == payload

    @pytest.mark.parametrize(
        ("change", "message"),
        (
            ({"remove": "draft"}, "draft.*required"),
            ({"add": "unexpected"}, "Additional properties"),
            ({"version": "5"}, "version must be an integer"),
        ),
    )
    def test_rejects_malformed_snapshot_envelopes(self, change: Mapping[str, object], message: str) -> None:
        application = Application.create()
        payload = application.snapshot(application.create_diagram("block")).to_dict()
        removed = change.get("remove")
        added = change.get("add")
        if isinstance(removed, str):
            del payload[removed]
        if isinstance(added, str):
            payload[added] = True
        if "version" in change:
            payload["version"] = change["version"]

        with pytest.raises(RuntimeError, match=message):
            application.restore(payload)

    @pytest.mark.parametrize(
        "discriminator",
        (
            "mermaiden.diagrams.classdiagram.elements:Class",
            "mermaiden/element/classDiagram/missing",
            "mermaiden/element/treeView-beta/tree_item",
        ),
    )
    def test_rejects_unregistered_or_foreign_discriminators(self, discriminator: str) -> None:
        application = Application.create()
        diagram = application.create_diagram("classDiagram")
        application.execute(diagram, "add_class", {"id": "order", "label": "Order"})
        payload = application.snapshot(diagram).to_dict()
        element = cast(dict[str, object], cast(list[object], payload["elements"])[0])
        element["$type"] = discriminator

        with pytest.raises(RuntimeError, match=r"discriminator|does not match"):
            application.restore(payload)

    def test_requires_the_exact_registered_model_fields_and_diagram_properties(self) -> None:
        application = Application.create()
        diagram = application.create_diagram("flowchart")
        application.execute(diagram, "add_start", {"id": "start", "label": "Start"})
        payload = application.snapshot(diagram).to_dict()
        element = cast(dict[str, object], cast(list[object], payload["elements"])[0])
        fields = cast(dict[str, object], element["fields"])
        del fields["label"]

        with pytest.raises(RuntimeError, match="missing 'label'"):
            application.restore(payload)

        payload = application.snapshot(diagram).to_dict()
        properties = cast(dict[str, object], payload["properties"])
        properties["unexpected"] = True
        with pytest.raises(RuntimeError, match="unsupported 'unexpected'"):
            application.restore(payload)

    def test_every_registered_empty_snapshot_validates_and_round_trips(self) -> None:
        application = Application.create()

        for info in application.available_diagrams():
            payload = application.snapshot(application.create_diagram(info.id)).to_dict()
            restored = application.restore(json.loads(json.dumps(payload)))

            assert payload["version"] == 5
            assert application.snapshot(restored).to_dict() == payload
