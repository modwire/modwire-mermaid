from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from mermaiden import Application
from mermaiden.diagrams.domain import DiagramModel
from tests.fixtures import catalog
from tests.fixtures.catalog import FixtureCatalog
from tests.fixtures.models import DiagramFixture, FixtureCoverageError, FixtureIssueKind


def test_exposes_one_populated_fixture_for_every_registered_diagram() -> None:
    with Application.create() as application:
        expected = tuple(info.id for info in application.available_diagrams())
        diagrams = FixtureCatalog(application).render()

    assert tuple(diagrams) == expected
    assert all(source.startswith("---\nconfig:\n") for source in diagrams.values())
    assert all(source.endswith("\n") for source in diagrams.values())


def test_writes_syntax_named_fixtures_without_changing_source(tmp_path: Path) -> None:
    with Application.create() as application:
        fixtures = FixtureCatalog(application)
        expected = fixtures.render()
        paths = fixtures.write(tmp_path)

    assert tuple(path.name for path in paths) == tuple(f"{diagram_id}.mmd" for diagram_id in expected)
    assert {path.stem: path.read_text(encoding="utf-8") for path in paths} == expected


def test_reports_every_fixture_coverage_problem_together(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclass(frozen=True)
    class Definition:
        syntax: str

    @dataclass(frozen=True)
    class Diagram:
        definition: Definition

    @dataclass(frozen=True)
    class Info:
        id: str

    class FakeApplication:
        def available_diagrams(self) -> tuple[Info, ...]:
            return (Info("duplicate"), Info("missing"), Info("unpopulated"))

        def render(self, diagram: Diagram) -> str:
            statement = "" if diagram.definition.syntax == "unpopulated" else "value\n"
            return f"---\nconfig: {{}}\n---\n{diagram.definition.syntax}\n{statement}"

    def fixture(diagram_id: str, builder: str) -> DiagramFixture:
        diagram = cast(DiagramModel, cast(object, Diagram(Definition(diagram_id))))
        return DiagramFixture(diagram, builder)

    def build(_application: Application) -> tuple[DiagramFixture, ...]:
        return (
            fixture("duplicate", "first_builder"),
            fixture("duplicate", "second_builder"),
            fixture("extra", "extra_builder"),
            fixture("unpopulated", "empty_builder"),
        )

    def empty(_application: Application) -> tuple[DiagramFixture, ...]:
        return ()

    monkeypatch.setattr(catalog, "build_structural_fixtures", build)
    monkeypatch.setattr(catalog, "build_behavioral_fixtures", empty)
    monkeypatch.setattr(catalog, "build_analytical_fixtures", empty)
    monkeypatch.setattr(catalog, "build_specialized_fixtures", empty)
    fixtures = FixtureCatalog(cast(Application, cast(object, FakeApplication())))

    _, issues = fixtures.inspect()

    assert tuple(issue.kind for issue in issues) == (
        FixtureIssueKind.MISSING,
        FixtureIssueKind.DUPLICATE,
        FixtureIssueKind.EXTRA,
        FixtureIssueKind.UNPOPULATED,
    )
    assert "first_builder, second_builder" in issues[1].message
    with pytest.raises(FixtureCoverageError) as error:
        fixtures.render()
    assert error.value.issues == issues
