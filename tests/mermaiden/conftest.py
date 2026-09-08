from collections.abc import Mapping

import pytest

from mermaiden.mermaid.validation import MermaidCliRenderer, MermaidCliResult


@pytest.fixture
def successful_mermaid_render(monkeypatch: pytest.MonkeyPatch) -> None:
    def render(
        _renderer: MermaidCliRenderer,
        sources: Mapping[str, str],
    ) -> MermaidCliResult:
        svgs = {
            diagram_id: f'<svg xmlns="http://www.w3.org/2000/svg"><text>{diagram_id}</text></svg>'
            for diagram_id in sources
        }
        return MermaidCliResult(0, svgs)

    monkeypatch.setattr(MermaidCliRenderer, "render", render)
