from pathlib import Path

from mermaiden import Application
from mermaiden.mermaid.domain import MermaidPreview
from tests.fixtures.catalog import FixtureCatalog


def test_mermaid_preview_writes_syntax_ordered_fixtures(tmp_path: Path) -> None:
    output = tmp_path / "preview" / "index.html"
    with Application.create() as application:
        sources = FixtureCatalog(application).render()
        result = MermaidPreview().write_sources(sources, output)

    assert result == output
    preview = output.read_text(encoding="utf-8")
    assert tuple(preview.index(f"<h2>{diagram_id}</h2>") for diagram_id in sources) == tuple(
        sorted(preview.index(f"<h2>{diagram_id}</h2>") for diagram_id in sources)
    )
    assert 'import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";' in preview
