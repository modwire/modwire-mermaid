import importlib.metadata
import json
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from typing import Any, cast

from wireup import create_sync_container, injectable

from mermaiden import Application


@injectable
class InstalledWheelConsumerService:
    pass


class InstalledWheelSmoke:
    def run(self) -> None:
        self.verify_sdist(Path(sys.argv[1]))
        self.verify_distribution_license()
        with self.verify_consumer_wireup_scan() as application:
            self.verify_application(application)
        self.verify_durable_draft_workflow()
        with tempfile.TemporaryDirectory(prefix="mermaiden-installed-") as temporary:
            self.verify_cli(Path(temporary))

    def verify_sdist(self, archive_path: Path) -> None:
        with tarfile.open(archive_path) as archive:
            names = archive.getnames()
            pyproject_name = next(name for name in names if name.endswith("/pyproject.toml"))
            pyproject = tomllib.loads(archive.extractfile(pyproject_name).read().decode())
            includes = pyproject["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
            contents = {Path(*Path(name).parts[1:]) for name in names if len(Path(name).parts) > 1}

        missing = [
            include
            for include in includes
            if not any(path == Path(include) or path.is_relative_to(include) for path in contents)
        ]
        if missing:
            raise RuntimeError(f"Source distribution is missing configured content: {', '.join(missing)}.")
        if Path("LICENSE") not in contents:
            raise RuntimeError("Source distribution is missing the proprietary license terms.")

    def verify_distribution_license(self) -> None:
        distribution = importlib.metadata.distribution("mermaiden")
        if distribution.metadata["License-Expression"] != "LicenseRef-Proprietary":
            raise RuntimeError("Installed distribution does not declare the proprietary license.")
        if not any(path.parts[-2:] == ("licenses", "LICENSE") for path in distribution.files or ()):
            raise RuntimeError("Installed distribution is missing the proprietary license terms.")

    def verify_consumer_wireup_scan(self) -> Application:
        container = create_sync_container(injectables=[sys.modules[__name__]], config={})
        try:
            container.get(InstalledWheelConsumerService)
        finally:
            container.close()
        return Application.create()

    def verify_application(self, application: Application) -> None:
        if not application.mermaid_version:
            raise RuntimeError("The installed package does not expose its pinned Mermaid version.")
        if not any(info.id == "block" for info in application.available_diagrams()):
            raise RuntimeError("The installed diagram catalog does not contain 'block'.")
        description = application.diagram_description("block")
        expected_commands = {
            "add_group",
            "add_block",
            "update_element",
            "move_element",
            "reorder_elements",
            "remove_element",
        }
        if not expected_commands <= set(description.commands):
            raise RuntimeError("The installed diagram catalog does not expose the public CRUD commands.")

        diagram = application.create_diagram("block")
        application.execute(diagram, "add_group", {"id": "source", "label": "Source"})
        application.execute(diagram, "add_group", {"id": "target", "label": "Target"})
        application.execute(diagram, "add_block", {"id": "first", "label": "First", "parent_id": "source"})
        application.execute(diagram, "add_block", {"id": "second", "label": "Second", "parent_id": "source"})
        application.execute(diagram, "add_block", {"id": "third", "label": "Third", "parent_id": "source"})
        application.execute(
            diagram,
            "update_element",
            {"id": "first", "kind": "block_node", "changes": {"label": "Updated First"}},
        )
        application.execute(
            diagram,
            "move_element",
            {"id": "first", "kind": "block_node", "parent_id": "target", "position": 0},
        )
        application.execute(
            diagram,
            "reorder_elements",
            {"parent_id": "source", "element_ids": ["third", "second"]},
        )
        application.execute(diagram, "remove_element", {"id": "second"})

        snapshot = application.snapshot(diagram).to_dict()
        restored = application.restore(snapshot)
        if application.snapshot(restored).to_dict() != snapshot:
            raise RuntimeError("The installed package did not preserve the public snapshot.")
        source = application.render(restored)
        if "Updated First" not in source or "Second" in source:
            raise RuntimeError("The installed package did not render the applied CRUD operations.")

        classes = application.create_diagram("classDiagram")
        application.execute(classes, "add_class", {"id": "caller", "label": "Caller"})
        application.execute(classes, "add_class", {"id": "dependency", "label": "Dependency"})
        application.execute(
            classes,
            "add_relation",
            {
                "id": "uses",
                "source_id": "caller",
                "target_id": "dependency",
                "relation_kind": "dependency",
            },
        )
        restored_classes = application.restore(application.snapshot(classes).to_dict())
        if "c_v_caller ..> c_v_dependency" not in application.render(restored_classes):
            raise RuntimeError("The installed package reversed class relation source and target endpoints.")

    def verify_durable_draft_workflow(self) -> None:
        with Application.create() as application:
            diagram = application.create_diagram("flowchart")
            persisted = self.persist(application, diagram)

        with Application.create() as application:
            diagram = application.restore(persisted)
            application.execute(diagram, "add_start", {"id": "start", "label": "Start"})
            persisted = self.persist(application, diagram)

        with Application.create() as application:
            diagram = application.restore(persisted)
            try:
                application.execute(
                    diagram,
                    "add_flow",
                    {"id": "invalid", "source_id": "start", "target_id": "missing"},
                )
            except RuntimeError:
                pass
            else:
                raise RuntimeError("The installed package accepted an invalid draft operation.")
            if application.snapshot(diagram).to_dict() != persisted:
                raise RuntimeError("A failed operation altered the last successfully persisted draft state.")

            application.execute(diagram, "add_end", {"id": "end", "label": "End"})
            persisted = self.persist(application, diagram)

        with Application.create() as application:
            diagram = application.restore(persisted)
            application.execute(
                diagram,
                "add_flow",
                {"id": "path", "source_id": "start", "target_id": "end"},
            )
            persisted = self.persist(application, diagram)

        with Application.create() as application:
            restored = application.restore(persisted)
            if "e_v_start r_v_path@--> e_v_end" not in application.render(restored):
                raise RuntimeError("The installed package did not render the completed restored flowchart.")

    def persist(self, application: Application, diagram: Any) -> dict[str, object]:
        encoded = json.dumps(application.snapshot(diagram).to_dict())
        if "mermaiden." in encoded:
            raise RuntimeError("The installed package leaked Python module paths into its snapshot contract.")
        return cast(dict[str, object], json.loads(encoded))

    def verify_cli(self, temporary: Path) -> None:
        help_result = self.run_cli(temporary, "--help")
        if "compat" not in help_result.stdout:
            raise RuntimeError("The installed CLI help does not expose compatibility validation.")

        self.run_cli(temporary, "compat")

    def run_cli(self, temporary: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (sys.executable, "-I", "-m", "mermaiden.cli", *arguments),
            cwd=temporary,
            check=True,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    InstalledWheelSmoke().run()
