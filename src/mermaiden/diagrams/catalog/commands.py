from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from typing import cast

from pydantic import StrictBool, TypeAdapter, ValidationError
from pydantic_core import core_schema
from wireup import injectable

from ...core.characters import Identifier, OptionalIdentifier, OrderedIdentifiers
from ...domain import CommandPayload, CommandPayloadSchema, ValidatedCommandPayload
from ..application import DiagramsApplication
from ..domain import CommandDefault, CommandVariadic, DiagramCommandFeature, DiagramInfo, DiagramModel
from .domain import MutationPayloadFactory
from .objects import DiagramObjectCatalog


@injectable(lifetime="scoped")
@dataclass(frozen=True)
class DiagramCommandCatalog:
    registry: DiagramsApplication
    objects: DiagramObjectCatalog
    mutation_payloads: MutationPayloadFactory

    def names(self, info: DiagramInfo) -> tuple[str, ...]:
        return tuple(sorted(self._commands[info.id]))

    def feature(self, diagram_id: str, command_name: str) -> DiagramCommandFeature:
        self.registry.get(diagram_id)
        try:
            return self._commands[diagram_id][command_name]
        except KeyError:
            raise KeyError(f"Unknown command '{command_name}' for diagram '{diagram_id}'.") from None

    def payload(self, diagram_id: str, command_name: str) -> CommandPayload:
        self.feature(diagram_id, command_name)
        return self._payloads[(diagram_id, command_name)]

    @cached_property
    def _commands(self) -> dict[str, dict[str, DiagramCommandFeature]]:
        commands: dict[str, dict[str, DiagramCommandFeature]] = {}
        for info in self.registry:
            feature = self.registry.get_diagram(info.id).feature
            declared = {command.name: command for command in feature.commands}
            declared["configure"] = DiagramCommandFeature("configure", {})
            if feature.elements:
                declared.update(
                    {
                        "update_element": DiagramCommandFeature("update_element", {}),
                        "move_element": DiagramCommandFeature("move_element", {}),
                        "reorder_elements": DiagramCommandFeature(
                            "reorder_elements",
                            {
                                "parent_id": OptionalIdentifier,
                                "element_ids": OrderedIdentifiers,
                            },
                        ),
                        "remove_element": DiagramCommandFeature(
                            "remove_element", {"id": Identifier, "cascade": CommandDefault(StrictBool, False)}
                        ),
                    }
                )
            if feature.relations:
                declared.update(
                    {
                        "update_relation": DiagramCommandFeature("update_relation", {}),
                        "remove_relation": DiagramCommandFeature(
                            "remove_relation", {"id": Identifier, "cascade": CommandDefault(StrictBool, False)}
                        ),
                    }
                )
            if feature.annotations:
                declared.update(
                    {
                        "update_annotation": DiagramCommandFeature("update_annotation", {}),
                        "remove_annotation": DiagramCommandFeature("remove_annotation", {"id": Identifier}),
                    }
                )
            commands[info.id] = declared
        return commands

    @cached_property
    def _payloads(self) -> dict[tuple[str, str], CommandPayload]:
        return {
            (info.id, name): self._payload(info, command)
            for info in self.registry
            for name, command in self._commands[info.id].items()
        }

    def _payload(self, info: DiagramInfo, command: DiagramCommandFeature) -> CommandPayload:
        diagram = self.registry.get_diagram(info.id)
        if command.name == "configure":
            return cast(CommandPayload, diagram.feature.configuration)
        if command.name == "update_element":
            return self.mutation_payloads.element(info.diagram_type.__name__, self.objects.elements(info))
        if command.name == "update_relation":
            return self.mutation_payloads.relation(info.diagram_type.__name__, self.objects.relations(info))
        if command.name == "update_annotation":
            return self.mutation_payloads.annotation(info.diagram_type.__name__, self.objects.annotations(info))
        if command.name == "move_element":
            return self.mutation_payloads.move_element(info.diagram_type.__name__, self.objects.elements(info))
        fields: dict[str, core_schema.TypedDictField] = {}
        for name, declaration in command.parameters.items():
            default = declaration if isinstance(declaration, CommandDefault) else None
            annotation = (
                declaration.annotation if isinstance(declaration, CommandDefault | CommandVariadic) else declaration
            )
            field_schema = TypeAdapter[object](annotation).core_schema
            if default is not None:
                field_schema = core_schema.with_default_schema(
                    field_schema,
                    default=default.value,
                    validate_default=True,
                )
            fields[name] = core_schema.typed_dict_field(field_schema, required=default is None)
        schema = core_schema.typed_dict_schema(fields, extra_behavior="forbid")
        return CommandPayloadSchema(schema, ())

    def validate(
        self,
        diagram: DiagramModel,
        command_name: str,
        payload: Mapping[str, object],
    ) -> ValidatedCommandPayload:
        try:
            return self.payload(diagram.kind, command_name).model_validate(payload)
        except ValidationError as error:
            diagnostics: list[str] = []
            for item in error.errors(include_url=False):
                location = ".".join(str(part) for part in item["loc"])
                received = item.get("input")
                characters = ""
                if isinstance(received, str):
                    characters = "; characters " + ", ".join(
                        f"{character!r} (U+{ord(character):04X})" for character in received
                    )
                context = item.get("ctx")
                rule = ""
                if isinstance(context, dict):
                    if "pattern" in context:
                        rule = f"; rule pattern {context['pattern']!r}"
                    elif "expected" in context:
                        rule = f"; rule {context['expected']}"
                diagnostics.append(f"{location}: {item['msg']}{characters}{rule}")
            details = "; ".join(diagnostics)
            raise ValueError(f"Command '{command_name}' has an invalid payload: {details}") from error
