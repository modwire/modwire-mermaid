from dataclasses import dataclass
from enum import StrEnum

from mermaiden.diagrams.domain import DiagramModel


@dataclass(frozen=True, slots=True)
class DiagramFixture:
    diagram: DiagramModel
    builder: str

    @property
    def id(self) -> str:
        return self.diagram.definition.syntax


class FixtureIssueKind(StrEnum):
    MISSING = "missing"
    DUPLICATE = "duplicate"
    EXTRA = "extra"
    UNPOPULATED = "unpopulated"


@dataclass(frozen=True, slots=True)
class FixtureIssue:
    kind: FixtureIssueKind
    diagram_id: str
    message: str


class FixtureCoverageError(RuntimeError):
    def __init__(self, issues: tuple[FixtureIssue, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))


def has_semantic_statement(source: str) -> bool:
    body = source.split("---\n", 2)[-1]
    return len(tuple(line for line in body.splitlines() if line.strip())) > 1
