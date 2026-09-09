from pathlib import Path

from mermaiden import Application
from tests.fixtures.catalog import FixtureCatalog


def test_mermaid_preview_writes_syntax_ordered_fixtures(tmp_path: Path) -> None:
    output = tmp_path / "preview" / "index.html"
    with Application.create() as application:
        sources = FixtureCatalog(application).render()
        result = application.write_preview(sources, output)
        mermaid_version = application.mermaid_version

    assert result == output
    document = output.read_text(encoding="utf-8")
    assert tuple(document.index(f"<h2>{diagram_id}</h2>") for diagram_id in sources) == tuple(
        sorted(document.index(f"<h2>{diagram_id}</h2>") for diagram_id in sources)
    )
    assert (
        f'import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@{mermaid_version}/dist/mermaid.esm.min.mjs";'
        in document
    )
