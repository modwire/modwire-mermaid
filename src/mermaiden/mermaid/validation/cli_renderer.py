import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from wireup import injectable

from .cli import MermaidCli
from .domain import MERMAID_VERSION, MermaidCliResult


@injectable(as_type=MermaidCli)
@dataclass(frozen=True, slots=True)
class MermaidCliRenderer:
    version: str = field(default=MERMAID_VERSION, init=False)
    timeout_seconds: int = field(default=60, init=False)

    def render(self, sources: Mapping[str, str]) -> MermaidCliResult:
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
            return MermaidCliResult(process.returncode, svgs, output)

    def markdown(self, sources: Mapping[str, str]) -> str:
        return "\n".join(f"## {diagram_id}\n```mermaid\n{source}```" for diagram_id, source in sources.items())
