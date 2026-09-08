from dataclasses import dataclass

from wireup import injectable

from ...core.domain import ChangeReport
from ...diagrams.catalog.service import DiagramCatalog
from ...diagrams.domain import DiagramCommandFeature, DiagramModel, MermaidDiagramConfiguration
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
        return self._invoke(operation, payload, self.catalog.command_feature(diagram.kind, command.operation))

    def _invoke(
        self,
        operation: object,
        payload: ValidatedCommandPayload,
        command: DiagramCommandFeature,
    ) -> ChangeReport | None:
        values = payload.model_dump(exclude_unset=True)
        positional = ()
        if command.variadic is not None:
            names = tuple(command.parameters)
            variadic_index = names.index(command.variadic)
            variadic_values = values.pop(command.variadic)
            if not isinstance(variadic_values, tuple):
                raise UnknownCommand("Variadic command arguments must be a tuple.")
            positional = tuple(values.pop(name) for name in names[:variadic_index]) + variadic_values
        if not callable(operation):
            raise UnknownCommand("Command operation is not callable.")
        result = operation(*positional, **values)
        if result is not None and not isinstance(result, ChangeReport):
            raise UnknownCommand("Command is not a mutation.")
        return result
