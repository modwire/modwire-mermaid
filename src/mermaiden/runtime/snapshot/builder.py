from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from wireup import injectable

from ...core.domain import Diagram
from .configuration import DiagramConfigurationReader
from .domain import SNAPSHOT_VERSION, DiagramSnapshot, SnapshotTypeRegistry
from .value_encoder import SnapshotValueEncoder


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class DiagramSnapshotBuilder:
    values: SnapshotValueEncoder
    configurations: DiagramConfigurationReader
    types: SnapshotTypeRegistry

    def build(self, diagram: Diagram) -> DiagramSnapshot:
        contract = self.types.contract(diagram.kind)
        return DiagramSnapshot(
            version=SNAPSHOT_VERSION,
            kind=diagram.kind,
            draft=not diagram.validate().can_commit,
            configuration=cast(
                Mapping[str, object],
                self.values.encode(self.configurations.read(diagram), contract.owner),
            ),
            elements=tuple(
                cast(Mapping[str, object], self.values.encode(item, contract.owner)) for item in diagram.root_elements
            ),
            relations=tuple(
                cast(Mapping[str, object], self.values.encode(item, contract.owner))
                for item in diagram.find_relations("")
            ),
            annotations=tuple(
                cast(Mapping[str, object], self.values.encode(item, contract.owner))
                for item in diagram.find_annotations("")
            ),
            properties={
                name: self.values.encode(getattr(diagram, name), contract.owner) for name in contract.properties
            },
        )
