from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ..validation import MermaidRenderValidator


@dataclass(frozen=True, slots=True)
class MermaidSyntaxViolation:
    diagram_id: str
    message: str


@injectable
@dataclass(frozen=True, slots=True)
class MermaidSyntaxValidator:
    renderer: MermaidRenderValidator

    @property
    def version(self) -> str:
        return self.renderer.mermaid_version

    def validate(self, sources: Mapping[str, str]) -> tuple[MermaidSyntaxViolation, ...]:
        violations = tuple(
            MermaidSyntaxViolation(diagram_id, "source has no diagram content")
            for diagram_id, source in sources.items()
            if not self.has_content(source)
        )
        if violations:
            return violations
        reports = self.renderer.validate_sources(sources)
        failures = tuple(report for report in reports if not report.success)
        if failures and len(failures) == len(reports) and len({item.diagnostics for item in failures}) == 1:
            return (MermaidSyntaxViolation("all", failures[0].diagnostics[0].message),)
        return tuple(
            MermaidSyntaxViolation(report.diagram_id, diagnostic.message)
            for report in failures
            for diagnostic in report.diagnostics
        )

    def has_content(self, source: str) -> bool:
        body = source.split("---\n", 2)[-1]
        return len(tuple(line for line in body.splitlines() if line.strip())) > 1
