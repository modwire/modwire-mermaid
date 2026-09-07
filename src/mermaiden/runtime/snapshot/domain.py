from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

SNAPSHOT_VERSION = 4
TRANSIENT_DIAGRAM_FIELDS: Final = frozenset({"runtime", "structure", "constraints", "configuration", "mutations"})


class SnapshotError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DiagramSnapshot:
    version: int
    kind: str
    draft: bool
    configuration: Mapping[str, object]
    elements: tuple[Mapping[str, object], ...]
    relations: tuple[Mapping[str, object], ...]
    annotations: tuple[Mapping[str, object], ...]
    properties: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "kind": self.kind,
            "draft": self.draft,
            "configuration": dict(self.configuration),
            "elements": list(self.elements),
            "relations": list(self.relations),
            "annotations": list(self.annotations),
            "properties": dict(self.properties),
        }
