import argparse
from collections.abc import Mapping
from types import TracebackType

from wireup import ScopedSyncContainer

from .bootstrap import process_scope
from .mermaid.compatibility import CompatibilityReport, MermaidCompatibilityService
from .mermaid.schema import MermaidDiagramConfig, MermaidSchemaStore


class MermaidenCli:
    def __init__(self, scope: ScopedSyncContainer) -> None:
        self._scope = scope
        self._closed = False

    @classmethod
    def create(cls) -> "MermaidenCli":
        return cls(process_scope())

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True

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
        return self._scope.get(MermaidSchemaStore).diagram_configs()

    def compatibility_report(self) -> CompatibilityReport:
        self._ensure_open()
        return self._scope.get(MermaidCompatibilityService).inspect()

    def verify_compatibility(self, sources: Mapping[str, str]) -> CompatibilityReport:
        self._ensure_open()
        return self._scope.get(MermaidCompatibilityService).verify(sources)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Mermaiden CLI is closed.")


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_subparsers(dest="command", required=True).add_parser("compat")
    parser.parse_args()
    with MermaidenCli.create() as cli:
        report = cli.compatibility_report()
        for diagram in report.diagrams:
            print(f"{diagram.diagram_id}: {'valid' if report.diagram_valid(diagram) else 'invalid'}")
        for diagram in report.missing_diagrams:
            print(f"{diagram.config_key}: not implemented ({diagram.schema_definition})")
        if not report.valid:
            raise SystemExit(1)


if __name__ == "__main__":
    run()
