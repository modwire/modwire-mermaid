from typing import cast

import pytest

from mermaiden import Application


class TestPersistence:
    @pytest.mark.parametrize("version", (1, 2, 3, 5))
    def test_rejects_a_snapshot_from_an_unsupported_contract_version(self, version: int) -> None:
        application = Application.create()
        diagram = application.create_diagram("block")
        application.execute(diagram, "add_block", {"id": "example", "label": "Example"})
        payload = application.snapshot(diagram).to_dict()
        payload["version"] = version
        del payload["configuration"]

        with pytest.raises(RuntimeError, match=f"version '{version}'; expected version '4'"):
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
