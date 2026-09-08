from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ...core.domain import DiagramView
from ..application import MermaidApplication
from .cli import MermaidCli
from .domain import (
    MermaidCliResult,
    MermaidRenderDiagnostic,
    MermaidRenderDiagnosticCode,
    MermaidRenderReport,
)


@injectable
@dataclass(frozen=True, slots=True)
class MermaidRenderValidator:
    renderer: MermaidApplication
    cli: MermaidCli

    @property
    def mermaid_version(self) -> str:
        return self.cli.version

    def validate(self, diagram: DiagramView) -> MermaidRenderReport:
        validation = diagram.validate()
        if not validation.can_commit:
            return MermaidRenderReport(
                diagram.kind,
                self.mermaid_version,
                diagnostics=(
                    MermaidRenderDiagnostic(
                        MermaidRenderDiagnosticCode.DIAGRAM_INVALID,
                        "Diagram violates blocking constraints.",
                        "\n".join(
                            f"{violation.code} [{violation.path}]: {violation.message}"
                            for violation in validation.blocking
                        ),
                    ),
                ),
            )
        try:
            source = self.renderer.render(diagram)
        except Exception as error:
            return MermaidRenderReport(
                diagram.kind,
                self.mermaid_version,
                diagnostics=(
                    MermaidRenderDiagnostic(
                        MermaidRenderDiagnosticCode.SOURCE_GENERATION_FAILED,
                        "Mermaid source generation failed.",
                        str(error),
                    ),
                ),
            )
        return self.validate_sources({diagram.kind: source})[0]

    def validate_sources(self, sources: Mapping[str, str]) -> tuple[MermaidRenderReport, ...]:
        result = self.cli.render(sources)
        return tuple(self.report(diagram_id, result) for diagram_id in sources)

    def report(self, diagram_id: str, result: MermaidCliResult) -> MermaidRenderReport:
        if result.timed_out:
            return self.failure(
                diagram_id,
                MermaidRenderDiagnosticCode.RENDER_TIMEOUT,
                "Mermaid CLI timed out.",
                result.output,
            )
        if result.return_code is None:
            return self.failure(
                diagram_id,
                MermaidRenderDiagnosticCode.RENDERER_UNAVAILABLE,
                "Mermaid CLI could not be started.",
                result.output,
            )
        if result.return_code:
            return self.failure(
                diagram_id,
                MermaidRenderDiagnosticCode.RENDER_FAILED,
                self.message(result.output),
                result.output,
            )
        if diagram_id not in result.svgs:
            return self.failure(
                diagram_id,
                MermaidRenderDiagnosticCode.SVG_MISSING,
                "Mermaid completed without producing an SVG.",
            )
        svg = result.svgs[diagram_id]
        if not svg.strip():
            return self.failure(
                diagram_id,
                MermaidRenderDiagnosticCode.SVG_EMPTY,
                "Mermaid produced an empty SVG.",
            )
        if "Syntax error in text" in svg:
            return self.failure(
                diagram_id,
                MermaidRenderDiagnosticCode.SVG_ERROR,
                "Mermaid produced a syntax-error SVG.",
                svg,
            )
        return MermaidRenderReport(diagram_id, self.mermaid_version, svg=svg)

    def failure(
        self,
        diagram_id: str,
        code: MermaidRenderDiagnosticCode,
        message: str,
        details: str = "",
    ) -> MermaidRenderReport:
        return MermaidRenderReport(
            diagram_id,
            self.mermaid_version,
            diagnostics=(MermaidRenderDiagnostic(code, message, details),),
        )

    def message(self, output: str) -> str:
        lines = tuple(line.strip() for line in output.splitlines() if line.strip())
        parse_error = next((line for line in lines if line.startswith("Error: Parse error on line ")), "")
        if parse_error:
            line = parse_error.removeprefix("Error: Parse error on line ").rstrip(":")
            expected = next((item for item in lines if " got " in item), "")
            token = expected.rsplit(" got ", 1)[-1].strip("'.") if expected else "unknown token"
            return f"syntax error on line {line} (got {token})"
        return lines[0].removeprefix("Error: ") if lines else "Mermaid rendering failed without diagnostic output."
