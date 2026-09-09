from collections.abc import Mapping
from typing import cast

from mermaiden import Application


class TestCharacterPolicies:
    def test_every_advertised_string_field_has_an_explicit_rule(self) -> None:
        application = Application.create()

        for info in application.available_diagrams():
            description = application.diagram_description(info.id)
            schemas = [
                *(description.commands.values()),
                *(description.elements.values()),
                *(description.relations.values()),
                *(description.annotations.values()),
            ]
            for schema in schemas:
                pending: list[Mapping[str, object]] = [schema]
                while pending:
                    node = pending.pop()
                    if node.get("type") == "string":
                        assert any(rule in node for rule in ("pattern", "enum", "const")), (
                            f"{info.id} publishes an unconstrained string schema: {node}"
                        )
                    for value in node.values():
                        if isinstance(value, Mapping):
                            pending.append(cast(Mapping[str, object], value))
                        elif isinstance(value, list):
                            pending.extend(
                                cast(Mapping[str, object], item)
                                for item in cast(list[object], value)
                                if isinstance(item, Mapping)
                            )
