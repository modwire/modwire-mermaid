from collections.abc import Mapping
from pathlib import Path
from types import TracebackType

from wireup import ScopedSyncContainer

from .bootstrap import process_scope
from .core.domain import ChangeRejected, ChangeReport, Diagram
from .diagrams.application import DiagramsApplication
from .diagrams.catalog.models import DiagramDescription
from .diagrams.catalog.service import DiagramCatalog
from .diagrams.domain import DiagramInfo, DiagramModel
from .diagrams.services.diagram_factory import DiagramFactory
from .diagrams.services.persistence import DiagramPersistenceApplication
from .domain import CommandPayload, DiagramCommand, UnknownCommand
from .mermaid.application import MermaidApplication
from .mermaid.schema import MermaidSchemaStore
from .mermaid.services.preview import MermaidPreviewApplication
from .mermaid.validation import MermaidRenderReport, MermaidRenderValidator
from .mutations.commands.application import DiagramCommandApplication
from .runtime.snapshot import DiagramSnapshot

__all__ = ["Application", "ChangeRejected", "DiagramCommand", "UnknownCommand"]


class Application:
    def __init__(self, scope: ScopedSyncContainer) -> None:
        self._scope = scope
        self._closed = False

    def available_diagrams(self) -> tuple[DiagramInfo, ...]:
        self._ensure_open()
        return self._scope.get(DiagramsApplication).available()

    def diagram_info(self, diagram_id: str) -> DiagramInfo:
        self._ensure_open()
        return self._scope.get(DiagramsApplication).get(diagram_id)

    def diagram_description(self, diagram_id: str) -> DiagramDescription:
        self._ensure_open()
        return self._scope.get(DiagramCatalog).describe(diagram_id)

    def command_payload(self, diagram_id: str, command_name: str) -> CommandPayload:
        self._ensure_open()
        return self._scope.get(DiagramCatalog).command_payload(diagram_id, command_name)

    def create_diagram(self, diagram_id: str) -> DiagramModel:
        self._ensure_open()
        return self._scope.get(DiagramFactory).create(diagram_id)

    def apply(self, diagram: DiagramModel, command: DiagramCommand) -> ChangeReport | None:
        self._ensure_open()
        return self._scope.get(DiagramCommandApplication).apply(diagram, command)

    def execute(
        self,
        diagram: DiagramModel,
        operation: str,
        arguments: Mapping[str, object],
    ) -> ChangeReport | None:
        return self.apply(diagram, DiagramCommand(operation, arguments))

    def snapshot(self, diagram: DiagramModel) -> DiagramSnapshot:
        self._ensure_open()
        return self._scope.get(DiagramPersistenceApplication).snapshot(diagram)

    def restore(self, payload: Mapping[str, object]) -> DiagramModel:
        self._ensure_open()
        return self._scope.get(DiagramPersistenceApplication).restore(payload)

    def render(self, diagram: Diagram) -> str:
        self._ensure_open()
        report = diagram.validate()
        if not report.can_commit:
            details = "; ".join(item.message for item in report.blocking)
            raise RuntimeError(f"Cannot render invalid diagram '{diagram.kind}': {details}")
        return self._scope.get(MermaidApplication).render(diagram)

    def validate_render(self, diagram: Diagram) -> MermaidRenderReport:
        self._ensure_open()
        return self._scope.get(MermaidRenderValidator).validate(diagram)

    @property
    def mermaid_version(self) -> str:
        self._ensure_open()
        return self._scope.get(MermaidSchemaStore).version

    def write_preview(self, sources: Mapping[str, str], output: Path) -> Path:
        self._ensure_open()
        return self._scope.get(MermaidPreviewApplication).write_sources(sources, output)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

    def __enter__(self) -> "Application":
        self._ensure_open()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Application is closed.")

    @classmethod
    def create(cls) -> "Application":
        return cls(process_scope())
