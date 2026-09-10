import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class TestDocumentation:
    def test_local_links_and_repository_paths_exist(self) -> None:
        documents = (ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md")))

        for document in documents:
            content = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^]]+]\((?!https?://|mailto:|#)([^)#]+)(?:#[^)]+)?\)", content):
                path = (document.parent / target).resolve()
                assert path.is_relative_to(ROOT), f"{document}: local link escapes the repository: {target}"
                assert path.exists(), f"{document}: local link does not exist: {target}"
            for target in re.findall(
                r"`((?:(?:src|tests|scripts|docs|\.github)/[^`\s]+)|(?:Makefile|pyproject\.toml|uv\.lock|package-lock\.json|README\.md|CONTRIBUTING\.md))`",
                content,
            ):
                assert (ROOT / target).exists(), f"{document}: repository path does not exist: {target}"

    def test_every_documented_make_command_exists(self) -> None:
        documents = (ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md")))
        documented = {
            target
            for document in documents
            for target in re.findall(r"\bmake ([a-z][a-z0-9-]*)", document.read_text(encoding="utf-8"))
        }
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        available = set(re.findall(r"^([a-z][a-z0-9-]*):", makefile, flags=re.MULTILINE))

        assert documented <= available, f"documented Make targets do not exist: {sorted(documented - available)}"

    def test_python_examples_execute_without_drift(self, successful_mermaid_render: None) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        examples = re.findall(
            r"<!-- executable-example:([a-z-]+):start -->\s*```python\n(.*?)```\s*"
            r"<!-- executable-example:\1:end -->",
            readme,
            flags=re.DOTALL,
        )

        assert len(examples) == readme.count("```python")
        assert {name for name, _source in examples} == {"application", "discovery", "mutations"}
        for name, source in examples:
            exec(compile(source, f"README.md:{name}", "exec"), {})

    def test_sdist_include_paths_are_intentional_tracked_content(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        includes = project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]

        for include in includes:
            path = ROOT / include
            assert path.exists(), f"sdist include does not exist: {include}"
            tracked = subprocess.run(
                ("git", "ls-files", include),
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            assert tracked.strip(), f"sdist include is not tracked: {include}"

    def test_distribution_is_explicitly_proprietary(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

        assert project["license"] == "LicenseRef-Proprietary"
        assert project["license-files"] == ["LICENSE"]
        assert not any(classifier.startswith("License ::") for classifier in project["classifiers"])
        assert "All rights reserved" in license_text
        assert "No license or other rights are granted" in license_text
        assert "Any unauthorized use is strictly prohibited" in license_text

    def test_obsolete_documentation_claims_are_absent(self) -> None:
        documents = (ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md")))
        content = "\n".join(document.read_text(encoding="utf-8") for document in documents)

        for obsolete in ("make docs", "make verify", "MermaidRenderer", "VOCABULARY.md"):
            assert obsolete not in content
        assert "make diagrams-test" in content
        assert "make diagrams-preview" in (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "make diagrams-test" not in (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
