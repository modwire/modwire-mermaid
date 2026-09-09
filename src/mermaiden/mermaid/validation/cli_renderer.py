import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from wireup import injectable

from ..schema import MermaidSchemaStore
from .cli import MermaidCli
from .domain import MermaidCliResult


@injectable(as_type=MermaidCli)
@dataclass(frozen=True, slots=True)
class MermaidCliRenderer:
    schemas: MermaidSchemaStore
    timeout_seconds: int = field(default=60, init=False)

    @property
    def version(self) -> str:
        return self.schemas.version

    def render(self, sources: Mapping[str, str]) -> MermaidCliResult:
        try:
            version = subprocess.run(
                ("mmdc", "--version"),
                capture_output=True,
                check=False,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return MermaidCliResult(
                None,
                {},
                f"Mermaid CLI exceeded the {self.timeout_seconds}-second timeout while reading its version.",
                timed_out=True,
            )
        except OSError as error:
            return MermaidCliResult(None, {}, str(error))
        if version.returncode:
            return MermaidCliResult(version.returncode, {}, version.stderr.strip() or version.stdout.strip())
        observed_version = version.stdout.strip() or "<empty>"
        if observed_version != self.version:
            return MermaidCliResult(0, {}, observed_version=observed_version)
        with tempfile.TemporaryDirectory(prefix="mermaiden-") as temporary:
            root = Path(temporary)
            input_path = root / "diagrams.md"
            output_path = root / "diagrams.rendered.md"
            input_path.write_text(self.markdown(sources), encoding="utf-8")
            try:
                process = subprocess.run(
                    (
                        "mmdc",
                        "-i",
                        str(input_path),
                        "-o",
                        str(output_path),
                    ),
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                return MermaidCliResult(
                    None,
                    {},
                    f"Mermaid CLI exceeded the {self.timeout_seconds}-second timeout.",
                    timed_out=True,
                )
            except OSError as error:
                return MermaidCliResult(None, {}, str(error))
            svgs = {
                diagram_id: path.read_text(encoding="utf-8")
                for index, diagram_id in enumerate(sources, start=1)
                if (path := root / f"diagrams.rendered-{index}.svg").exists()
            }
            output = process.stderr.strip() or process.stdout.strip()
            return MermaidCliResult(process.returncode, svgs, output, observed_version=observed_version)

    def markdown(self, sources: Mapping[str, str]) -> str:
        return "\n".join(f"## {diagram_id}\n```mermaid\n{source}```" for diagram_id, source in sources.items())
