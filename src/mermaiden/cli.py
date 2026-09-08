import argparse
from pathlib import Path
from types import TracebackType

from wireup import SyncContainer

from .bootstrap import create_container
from .mermaid.compatibility import CompatibilityReport, MermaidCompatibilityService
from .mermaid.compatibility.schema import MermaidDiagramConfig, MermaidSchemaStore
from .mermaid.fixtures import DiagramFixtures
from .mermaid.services.preview import MermaidPreviewApplication


class MermaidenCli:
    def __init__(self, container: SyncContainer) -> None:
        self._container = container
        self._closed = False

    @classmethod
    def create(cls) -> "MermaidenCli":
        return cls(create_container())

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._container.close()

    def __enter__(self) -> "MermaidenCli":
        self._ensure_open()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.close()

    def mermaid_diagram_configs(self) -> tuple[MermaidDiagramConfig, ...]:
        self._ensure_open()
        with self._container.enter_scope() as scope:
            return scope.get(MermaidSchemaStore).diagram_configs()

    def rendered_diagrams(self) -> dict[str, str]:
        self._ensure_open()
        with self._container.enter_scope() as scope:
            return scope.get(DiagramFixtures).render()

    def write_fixtures(self, output: Path) -> tuple[Path, ...]:
        output.mkdir(parents=True, exist_ok=True)
        self._ensure_open()
        with self._container.enter_scope() as scope:
            diagrams = scope.get(DiagramFixtures).render()
        return tuple(self._write_source(output, name, source) for name, source in diagrams.items())

    def write_preview(self, output: Path) -> Path:
        self._ensure_open()
        with self._container.enter_scope() as scope:
            preview = scope.get(MermaidPreviewApplication)
            diagrams = scope.get(DiagramFixtures).render()
            return preview.write_sources(diagrams, output)

    def compatibility_report(self) -> CompatibilityReport:
        self._ensure_open()
        with self._container.enter_scope() as scope:
            return scope.get(MermaidCompatibilityService).inspect()

    def verify_compatibility(self) -> CompatibilityReport:
        self._ensure_open()
        with self._container.enter_scope() as scope:
            return scope.get(MermaidCompatibilityService).verify()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Mermaiden CLI is closed.")

    def _write_source(self, output: Path, name: str, source: str) -> Path:
        path = output / f"{name}.mmd"
        path.write_text(source, encoding="utf-8")
        return path

    @classmethod
    def run(cls) -> None:
        parser = argparse.ArgumentParser()
        commands = parser.add_subparsers(dest="command", required=True)
        fixtures = commands.add_parser("fixtures")
        fixtures.add_argument("--output", "-o", type=Path, default=Path(".dev/preview"))
        preview = commands.add_parser("preview")
        preview.add_argument("--output", "-o", type=Path, default=Path(".dev/preview/index.html"))
        commands.add_parser("compat")
        arguments = parser.parse_args()
        with cls.create() as cli:
            if arguments.command == "fixtures":
                for path in cli.write_fixtures(arguments.output):
                    print(path)
            if arguments.command == "preview":
                print(cli.write_preview(arguments.output))
            if arguments.command == "compat":
                report = cli.verify_compatibility()
                for diagram in report.diagrams:
                    print(f"{diagram.diagram_id}: {'valid' if report.diagram_valid(diagram) else 'invalid'}")
                for diagram in report.missing_diagrams:
                    print(f"{diagram.config_key}: not implemented ({diagram.schema_definition})")
                for violation in report.syntax_violations:
                    print(f"{violation.diagram_id}: {violation.message}")
                if not report.valid:
                    raise SystemExit(1)


if __name__ == "__main__":
    MermaidenCli.run()
