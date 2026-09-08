import ast
from pathlib import Path

SOURCE_ROOT = Path(__file__).parents[3] / "src" / "mermaiden"
DIAGRAM_ROOT = SOURCE_ROOT / "diagrams"


class TestFeatureDescriptors:
    def test_every_diagram_family_declares_one_feature(self) -> None:
        for path in DIAGRAM_ROOT.glob("*/diagram.py"):
            module = ast.parse(path.read_text())
            diagrams = [
                node
                for node in module.body
                if isinstance(node, ast.ClassDef)
                and any(isinstance(base, ast.Name) and base.id == "DiagramModel" for base in node.bases)
            ]
            assert len(diagrams) == 1, path
            features = [
                node
                for node in diagrams[0].body
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "feature"
            ]
            assert len(features) == 1, path

    def test_catalog_and_command_execution_do_not_discover_features_reflectively(self) -> None:
        paths = (
            DIAGRAM_ROOT / "catalog" / "commands.py",
            DIAGRAM_ROOT / "catalog" / "objects.py",
            SOURCE_ROOT / "mutations" / "commands" / "application.py",
        )
        forbidden = ("__dict__", "find_spec", "getmembers", "get_type_hints", "import_module", "signature(")
        for path in paths:
            source = path.read_text()
            assert all(item not in source for item in forbidden), path
