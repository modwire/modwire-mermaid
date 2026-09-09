from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from pathlib import Path

from wireup import injectable

from .schema import MermaidSchemaStore


@injectable
@dataclass(frozen=True, slots=True)
class MermaidPreview:
    schemas: MermaidSchemaStore

    def write_sources(self, sources: Mapping[str, str], output: Path) -> Path:
        sections = "\n".join(self._source_section(name, source) for name, source in sources.items())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self._document(sections), encoding="utf-8")
        return output

    def _source_section(self, name: str, source: str) -> str:
        return f'<section><h2>{escape(name)}</h2><pre class="mermaid">{escape(source)}</pre></section>'

    def _document(self, sections: str) -> str:
        return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>Mermaid previews</title>
<style>body {{ font-family: sans-serif; margin: 2rem; }} section {{ margin-block: 3rem; }}</style>
<body>
{sections}
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@{self.schemas.version}/dist/mermaid.esm.min.mjs";
mermaid.initialize({{ startOnLoad: true }});
</script>
</body>
</html>
"""
