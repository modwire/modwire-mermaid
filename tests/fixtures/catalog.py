from dataclasses import dataclass
from pathlib import Path

from mermaiden import Application

from ._analytical import build_analytical_fixtures
from ._behavioral import build_behavioral_fixtures
from ._specialized import build_specialized_fixtures
from ._structural import build_structural_fixtures
from .models import FixtureCoverageError, FixtureIssue, FixtureIssueKind, has_semantic_statement


@dataclass(frozen=True, slots=True)
class FixtureCatalog:
    application: Application

    def inspect(self) -> tuple[dict[str, str], tuple[FixtureIssue, ...]]:
        fixtures = (
            *build_structural_fixtures(self.application),
            *build_behavioral_fixtures(self.application),
            *build_analytical_fixtures(self.application),
            *build_specialized_fixtures(self.application),
        )
        registered = {info.id for info in self.application.available_diagrams()}
        builders: dict[str, list[str]] = {}
        for fixture in fixtures:
            builders.setdefault(fixture.id, []).append(fixture.builder)

        missing = tuple(
            FixtureIssue(FixtureIssueKind.MISSING, diagram_id, f"missing fixture '{diagram_id}'")
            for diagram_id in sorted(registered - builders.keys())
        )
        duplicate = tuple(
            FixtureIssue(
                FixtureIssueKind.DUPLICATE,
                diagram_id,
                f"duplicate fixture '{diagram_id}' from builders: {', '.join(names)}",
            )
            for diagram_id, names in sorted(builders.items())
            if len(names) > 1
        )
        extra = tuple(
            FixtureIssue(FixtureIssueKind.EXTRA, diagram_id, f"extra fixture '{diagram_id}'")
            for diagram_id in sorted(builders.keys() - registered)
        )
        rendered = tuple((fixture, self.application.render(fixture.diagram)) for fixture in fixtures)
        unpopulated = tuple(
            FixtureIssue(
                FixtureIssueKind.UNPOPULATED,
                fixture.id,
                f"unpopulated fixture '{fixture.id}' from builder: {fixture.builder}",
            )
            for fixture, source in rendered
            if not has_semantic_statement(source)
        )
        issues = (*missing, *duplicate, *extra, *unpopulated)
        if duplicate:
            return {}, issues
        return {fixture.id: source for fixture, source in sorted(rendered, key=lambda item: item[0].id)}, issues

    def render(self) -> dict[str, str]:
        sources, issues = self.inspect()
        if issues:
            raise FixtureCoverageError(issues)
        return sources

    def write(self, output: Path) -> tuple[Path, ...]:
        output.mkdir(parents=True, exist_ok=True)
        sources = self.render()
        paths = tuple(output / f"{diagram_id}.mmd" for diagram_id in sources)
        for path, source in zip(paths, sources.values(), strict=True):
            path.write_text(source, encoding="utf-8")
        return paths
