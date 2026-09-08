from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cached_property
from inspect import Parameter, signature
from typing import Annotated, cast, get_args, get_origin, get_type_hints

from pydantic import TypeAdapter, ValidationError
from pydantic_core import CoreSchema, core_schema
from wireup import injectable

from ...core.domain import ChangeReport
from ...domain import CommandPayload, CommandPayloadSchema, ValidatedCommandPayload
from ..application import DiagramsApplication
from ..domain import DiagramInfo, DiagramModel
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

    def payload(self, diagram_id: str, command_name: str) -> CommandPayload:
        self.registry.get(diagram_id)
        try:
            return self._payloads[(diagram_id, command_name)]
        except KeyError:
            raise KeyError(f"Unknown command '{command_name}' for diagram '{diagram_id}'.") from None

    @cached_property
    def _commands(self) -> dict[str, dict[str, Callable[..., ChangeReport | None]]]:
        return {info.id: self._methods(info) for info in self.registry}

    @cached_property
    def _payloads(self) -> dict[tuple[str, str], CommandPayload]:
        return {
            (info.id, name): self._payload(info, method)
            for info in self.registry
            for name, method in self._commands[info.id].items()
        }

    def _payload(
        self,
        info: DiagramInfo,
        method: Callable[..., ChangeReport | None],
    ) -> CommandPayload:
        if method is DiagramModel.configure:
            configuration = self.registry.get_diagram(info.id).configuration
            return cast(CommandPayload, configuration.__class__)
        if method is DiagramModel.update_element:
            return self.mutation_payloads.element(info.diagram_type.__name__, self.objects.elements(info))
        if method is DiagramModel.update_relation:
            return self.mutation_payloads.relation(info.diagram_type.__name__, self.objects.relations(info))
        if method is DiagramModel.update_annotation:
            return self.mutation_payloads.annotation(info.diagram_type.__name__, self.objects.annotations(info))
        if method is DiagramModel.move_element:
            return self.mutation_payloads.move_element(info.diagram_type.__name__, self.objects.elements(info))
        return CommandPayloadSchema(self._payload_schema(method), ())

    def validate(
        self,
        diagram: DiagramModel,
        command_name: str,
        payload: Mapping[str, object],
    ) -> ValidatedCommandPayload:
        try:
            return self.payload(diagram.kind, command_name).model_validate(payload)
        except ValidationError as error:
            raise ValueError(f"Command '{command_name}' has an invalid payload: {error}") from error

    def _methods(self, info: DiagramInfo) -> dict[str, Callable[..., ChangeReport | None]]:
        commands = {
            name: cast(Callable[..., ChangeReport | None], method)
            for name, method in info.diagram_type.__dict__.items()
            if not name.startswith("_")
            if callable(method)
            if self._is_command(cast(Callable[..., ChangeReport | None], method))
        }
        commands[DiagramModel.configure.__name__] = DiagramModel.configure
        if self.objects.elements(info):
            commands[DiagramModel.update_element.__name__] = DiagramModel.update_element
            commands[DiagramModel.move_element.__name__] = DiagramModel.move_element
            commands[DiagramModel.reorder_elements.__name__] = DiagramModel.reorder_elements
            commands[DiagramModel.remove_element.__name__] = DiagramModel.remove_element
        if self.objects.relations(info):
            commands[DiagramModel.update_relation.__name__] = DiagramModel.update_relation
            commands[DiagramModel.remove_relation.__name__] = DiagramModel.remove_relation
        if self.objects.annotations(info):
            commands[DiagramModel.update_annotation.__name__] = DiagramModel.update_annotation
            commands[DiagramModel.remove_annotation.__name__] = DiagramModel.remove_annotation
        return commands

    def _is_command(self, method: Callable[..., ChangeReport | None]) -> bool:
        return_type = get_type_hints(method).get("return")
        return return_type in {ChangeReport, type(None)}

    def _payload_schema(
        self,
        method: Callable[..., ChangeReport | None],
    ) -> CoreSchema:
        hints = get_type_hints(method, include_extras=True)
        fields: dict[str, core_schema.TypedDictField] = {}
        for parameter in signature(method).parameters.values():
            if parameter.name == "self":
                continue
            annotation = self._payload_annotation(parameter, hints)
            field_schema = TypeAdapter[object](annotation).core_schema
            required = parameter.default is Parameter.empty
            if not required:
                field_schema = core_schema.with_default_schema(field_schema, default=parameter.default)
            fields[parameter.name] = core_schema.typed_dict_field(field_schema, required=required)
        return core_schema.typed_dict_schema(fields, extra_behavior="forbid")

    def _payload_annotation(
        self,
        parameter: Parameter,
        hints: Mapping[str, object],
    ) -> object:
        annotation = hints.get(parameter.name)
        if annotation is None:
            raise TypeError(f"Command parameter '{parameter.name}' has no type annotation.")
        if parameter.kind is Parameter.VAR_POSITIONAL:
            if get_origin(annotation) is Annotated:
                item, *metadata = get_args(annotation)
                return Annotated[tuple[item, ...], *metadata]
            return tuple[annotation, ...]
        return annotation
