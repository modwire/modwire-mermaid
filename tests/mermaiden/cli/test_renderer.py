import json
from pathlib import Path

from mermaiden import Application


def test_node_lock_uses_the_supported_mermaid_version() -> None:
    root = Path(__file__).parents[3]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    with Application.create() as application:
        version = application.mermaid_version

    assert package["devDependencies"]["@mermaid-js/mermaid-cli"] == version
    assert package_lock["packages"][""]["devDependencies"]["@mermaid-js/mermaid-cli"] == version
    assert package_lock["packages"]["node_modules/@mermaid-js/mermaid-cli"]["version"] == version
