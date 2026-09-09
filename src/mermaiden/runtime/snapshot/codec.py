from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ...core.domain import Diagram
from ..diagrams.state import DiagramData
from .builder import DiagramSnapshotBuilder
from .domain import SNAPSHOT_VERSION, DiagramSnapshot
from .hydrator import DiagramSnapshotHydrator
from .parser import DiagramSnapshotParser


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class DiagramSnapshotCodec:
    builder: DiagramSnapshotBuilder
    parser: DiagramSnapshotParser
    hydrator: DiagramSnapshotHydrator

    version = SNAPSHOT_VERSION

    def snapshot(self, diagram: Diagram) -> DiagramSnapshot:
        return self.builder.build(diagram)

    def restore(self, payload: Mapping[str, object]) -> DiagramSnapshot:
        return self.parser.parse(payload)

    def hydrate(self, snapshot: DiagramSnapshot, diagram: Diagram) -> DiagramData:
        return self.hydrator.hydrate(snapshot, diagram)
