import pytest

from mermaiden.cli import MermaidenCli


def test_cli_owns_its_container_and_rejects_use_after_close() -> None:
    cli = MermaidenCli.create()

    with cli as active:
        assert active.mermaid_diagram_configs()

    cli.close()

    with pytest.raises(RuntimeError, match="Mermaiden CLI is closed"):
        cli.mermaid_diagram_configs()
