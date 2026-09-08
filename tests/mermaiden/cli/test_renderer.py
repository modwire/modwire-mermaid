import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from mermaiden import Application
from mermaiden.mermaid.validation import MERMAID_VERSION


def test_renderer_uses_the_lock_installed_cli_and_reports_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command: list[str] = []

    def timeout(arguments: Sequence[str], **_options: Any) -> None:
        command.extend(arguments)
        raise subprocess.TimeoutExpired(arguments, 60)

    monkeypatch.setattr(subprocess, "run", timeout)
    application = Application.create()
    diagram = application.create_diagram("sequenceDiagram")
    application.execute(diagram, "add_participant", {"id": "example", "label": "Example"})

    report = application.validate_render(diagram)

    assert command[0] == "mmdc"
    assert "npx" not in command
    assert report.diagnostics[0].code == "render_timeout"
    assert "60-second timeout" in report.diagnostics[0].details


def test_node_lock_uses_the_supported_mermaid_version() -> None:
    root = Path(__file__).parents[3]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    schema_lock = json.loads(
        (root / "src/mermaiden/mermaid/compatibility/schema.lock.json").read_text(encoding="utf-8")
    )

    assert package["devDependencies"]["@mermaid-js/mermaid-cli"] == MERMAID_VERSION
    assert schema_lock["mermaid_version"] == MERMAID_VERSION
