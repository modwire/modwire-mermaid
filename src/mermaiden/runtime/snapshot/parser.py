from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from .domain import SNAPSHOT_VERSION, DiagramSnapshot, SnapshotError, SnapshotTypeRegistry
from .schema import DiagramSnapshotSchema
from .value_validator import SnapshotValueValidator


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class DiagramSnapshotParser:
    values: SnapshotValueValidator
    schema: DiagramSnapshotSchema
    types: SnapshotTypeRegistry

    version = SNAPSHOT_VERSION

    def parse(self, payload: Mapping[str, object]) -> DiagramSnapshot:
        try:
            value = payload["version"]
        except KeyError as error:
            raise SnapshotError("Snapshot is malformed at '$.version'.") from error
        if type(value) is not int:
            raise SnapshotError("Snapshot is malformed at '$.version': the version must be an integer.")
        version = value
        if version != self.version:
            raise SnapshotError(f"Unsupported snapshot version '{version}'; expected version '{self.version}'.")
        self.schema.validate(payload)
        try:
            snapshot = DiagramSnapshot(
                version=version,
                kind=self.values.string(payload["kind"], "kind"),
                draft=self.values.boolean(payload["draft"], "draft"),
                configuration=self.values.mapping(payload["configuration"], "configuration"),
                elements=self.values.objects(payload["elements"], "elements"),
                relations=self.values.objects(payload["relations"], "relations"),
                annotations=self.values.objects(payload["annotations"], "annotations"),
                properties=self.values.mapping(payload["properties"], "properties"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SnapshotError("Snapshot is malformed.") from error
        self.types.contract(snapshot.kind)
        return snapshot
