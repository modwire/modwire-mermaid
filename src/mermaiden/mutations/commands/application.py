from collections.abc import Callable
from dataclasses import dataclass
from inspect import signature

from wireup import injectable

from ...core.domain import ChangeReport
from ...diagrams.catalog.service import DiagramCatalog
from ...diagrams.domain import DiagramModel, MermaidDiagramConfiguration
from ...domain import DiagramCommand, UnknownCommand, ValidatedCommandPayload


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class DiagramCommandApplication:
    catalog: DiagramCatalog

    def apply(self, diagram: DiagramModel, command: DiagramCommand) -> ChangeReport | None:
        operation = getattr(diagram, command.operation, None)
        if command.operation.startswith("_") or not callable(operation):
            raise UnknownCommand(f"Command '{command.operation}' is not supported for '{diagram.kind}'.")
        try:
            payload = self.catalog.validate_command(diagram, command.operation, command.arguments)
        except (KeyError, ValueError) as error:
            raise UnknownCommand(f"Command '{command.operation}' has invalid arguments: {error}") from error
        if isinstance(payload, MermaidDiagramConfiguration):
            diagram.configure(payload)
            return None
        return self._invoke(operation, payload)

    def _invoke(
        self,
        operation: Callable[..., object],
        payload: ValidatedCommandPayload,
    ) -> ChangeReport | None:
        parameters = tuple(signature(operation).parameters.values())
        values = payload.model_dump(exclude_unset=True)
        variadic = next((item for item in parameters if item.kind is item.VAR_POSITIONAL), None)
        positional = ()
        if variadic is not None:
            variadic_values = values.pop(variadic.name)
            if not isinstance(variadic_values, tuple):
                raise UnknownCommand("Variadic command arguments must be a tuple.")
            positional = (
                tuple(
                    values.pop(item.name)
                    for item in parameters
                    if item.kind in {item.POSITIONAL_ONLY, item.POSITIONAL_OR_KEYWORD}
                )
                + variadic_values
            )
        result = operation(*positional, **values)
        if result is not None and not isinstance(result, ChangeReport):
            raise UnknownCommand("Command is not a mutation.")
        return result
