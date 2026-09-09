import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from wireup import injectable


@dataclass(frozen=True, slots=True)
class MermaidSchemaLock:
    mermaid_version: str
    schema_url: str
    sha256: str


@dataclass(frozen=True, slots=True)
class MermaidDiagramConfig:
    config_key: str
    schema_definition: str
    schema: dict[str, Any]


@injectable
@dataclass(frozen=True, slots=True)
class MermaidSchemaStore:
    root: Path = field(default=Path(__file__).parent / "compatibility", init=False)

    @property
    def version(self) -> str:
        return self.lock().mermaid_version

    def lock(self) -> MermaidSchemaLock:
        payload = cast(dict[str, str], json.loads((self.root / "schema.lock.json").read_text(encoding="utf-8")))
        return MermaidSchemaLock(**payload)

    def load(self) -> dict[str, Any]:
        path = self.root / "schemas" / "config.schema.json"
        content = path.read_bytes()
        lock = self.lock()
        checksum = hashlib.sha256(content).hexdigest()
        if checksum != lock.sha256:
            raise ValueError(
                "Mermaid schema version mismatch: authority 'schema.lock.json' "
                f"expected checksum '{lock.sha256}', consumer '{path.name}' observed '{checksum}'."
            )
        return cast(dict[str, Any], json.loads(content))

    def diagram_configs(self) -> tuple[MermaidDiagramConfig, ...]:
        schema = self.load()
        properties = cast(dict[str, dict[str, str]], schema["properties"])
        definitions = cast(dict[str, dict[str, Any]], schema["$defs"])
        diagrams: list[MermaidDiagramConfig] = []
        for config_key, property_schema in properties.items():
            reference = property_schema.get("$ref", "")
            prefix = "#/$defs/"
            if not reference.startswith(prefix):
                continue
            schema_definition = reference.removeprefix(prefix)
            if not schema_definition.endswith("DiagramConfig"):
                continue
            diagrams.append(MermaidDiagramConfig(config_key, schema_definition, definitions[schema_definition]))
        return tuple(sorted(diagrams, key=lambda item: item.config_key))
