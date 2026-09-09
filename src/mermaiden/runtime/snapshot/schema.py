import json
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from wireup import injectable

from .domain import SNAPSHOT_VERSION, SnapshotError, SnapshotTypeRegistry


@injectable(lifetime="scoped")
@dataclass(frozen=True)
class DiagramSnapshotSchema:
    types: SnapshotTypeRegistry

    @cached_property
    def document(self) -> Mapping[str, object]:
        path = Path(__file__).with_name(f"schema.v{SNAPSHOT_VERSION}.json")
        try:
            value: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise SnapshotError(f"Snapshot schema '{path.name}' is unavailable: {error}") from error
        if not isinstance(value, dict):
            raise SnapshotError(f"Snapshot schema '{path.name}' must contain an object.")
        try:
            document = cast(dict[str, Any], value)
            Draft202012Validator.check_schema(document)
        except SchemaError as error:
            raise SnapshotError(f"Snapshot schema '{path.name}' is invalid: {error.message}") from error
        fingerprint = document.get("x-registry-fingerprint")
        if fingerprint != self.types.fingerprint:
            raise SnapshotError(
                f"Snapshot schema '{path.name}' does not match the registered snapshot contract; "
                "bump the snapshot version and generate its schema artifact."
            )
        return cast(Mapping[str, object], document)

    def validate(self, payload: Mapping[str, object]) -> None:
        validator: Any = Draft202012Validator(cast(Any, self.document))
        try:
            validator.validate(cast(Any, payload))
        except ValidationError as error:
            path = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
            raise SnapshotError(f"Snapshot is malformed at '{path}': {error.message}") from error
        else:
            return
