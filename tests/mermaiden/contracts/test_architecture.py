import subprocess
import sys
from pathlib import Path

from mermaiden.core.naming import ClassName


class HTTPServerIsValid:
    pass


class C4ContextRule:
    pass


class TestArchitecture:
    def test_class_names_have_one_acronym_and_digit_aware_policy(self) -> None:
        assert ClassName(HTTPServerIsValid).snake_case == "http_server_is_valid"
        assert ClassName(C4ContextRule).snake_case == "c4_context_rule"

    def test_sibling_feature_import_fixture_breaks_the_architecture_contract(self) -> None:
        fixture = Path(__file__).parents[2] / "fixtures" / "import_linter_sibling"
        result = subprocess.run(
            (str(Path(sys.executable).with_name("lint-imports")), "--config", ".importlinter", "--no-cache"),
            cwd=fixture,
            capture_output=True,
            check=False,
            text=True,
        )

        assert result.returncode == 1
        assert "Sibling features do not import each other BROKEN" in result.stdout
