from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property

from wireup import injectable

from ...domain import CommandPayload, ValidatedCommandPayload
from ..application import DiagramsApplication
from ..domain import DiagramCommandFeature, DiagramInfo, DiagramModel
from .commands import DiagramCommandCatalog
from .models import DiagramDescription
from .objects import DiagramObjectCatalog


@injectable(lifetime="scoped")
@dataclass(frozen=True)
class DiagramCatalog:
    registry: DiagramsApplication
    objects: DiagramObjectCatalog
    commands: DiagramCommandCatalog

    def describe(self, diagram_id: str) -> DiagramDescription:
        self.registry.get(diagram_id)
        return self._descriptions[diagram_id]

    @cached_property
    def _descriptions(self) -> dict[str, DiagramDescription]:
        return {info.id: self._describe(info) for info in self.registry}

    def _describe(self, info: DiagramInfo) -> DiagramDescription:
        diagram = self.registry.get_diagram(info.id)
        elements = self.objects.elements(info)
        return DiagramDescription(
            id=info.id,
            name=info.name,
            elements=self.objects.schemas(elements),
            relations=self.objects.schemas(self.objects.relations(info)),
            annotations=self.objects.schemas(self.objects.annotations(info)),
            placements=self.objects.placements(diagram, elements),
            commands={
                name: self.commands.payload(info.id, name).model_json_schema() for name in self.commands.names(info)
            },
        )

    def validate(self) -> None:
        if len(self._descriptions) != len(self.registry.available()):
            raise RuntimeError("Diagram catalog is incomplete.")

    def command_names(self, info: DiagramInfo) -> tuple[str, ...]:
        return self.commands.names(info)

    def command_payload(self, diagram_id: str, command_name: str) -> CommandPayload:
        return self.commands.payload(diagram_id, command_name)

    def command_feature(self, diagram_id: str, command_name: str) -> DiagramCommandFeature:
        return self.commands.feature(diagram_id, command_name)

    def validate_command(
        self,
        diagram: DiagramModel,
        command_name: str,
        payload: Mapping[str, object],
    ) -> ValidatedCommandPayload:
        return self.commands.validate(diagram, command_name, payload)
