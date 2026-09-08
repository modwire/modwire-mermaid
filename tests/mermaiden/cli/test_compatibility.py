from mermaiden import Application
from mermaiden.cli import MermaidenCli
from tests.fixtures.catalog import FixtureCatalog


def test_application_validates_every_registered_diagram_against_pinned_mermaid_schema() -> None:
    with Application.create() as application, MermaidenCli.create() as cli:
        report = cli.compatibility_report()
        expected = tuple(
            (info.id, info.config_key, info.schema_definition) for info in application.available_diagrams()
        )
        upstream = {item.config_key: item for item in cli.mermaid_diagram_configs()}

    assert report.lock.mermaid_version == "11.16.0"
    assert report.valid
    assert not report.missing_diagrams
    assert tuple((item.diagram_id, item.config_key, item.schema_definition) for item in report.diagrams) == expected
    configurations = {item.diagram_id: item.configuration.values for item in report.diagrams}
    assert all(
        values == {"wrap": True}
        for diagram_id, values in configurations.items()
        if diagram_id
        not in {
            "architecture-beta",
            "block",
            "C4Context",
            "cynefin-beta",
            "erDiagram",
            "eventmodeling",
            "gantt",
            "gitGraph",
            "ishikawa-beta",
            "kanban",
            "mindmap",
            "packet",
            "pie",
            "radar-beta",
            "railroad-ebnf-beta",
            "requirementDiagram",
            "stateDiagram-v2",
            "swimlane-beta",
            "venn-beta",
            "wardley-beta",
        }
    )
    assert configurations["architecture-beta"] == {
        "wrap": True,
        "architecture": {
            "useMaxWidth": True,
            "padding": 40,
            "iconSize": 80,
            "fontSize": 16,
            "randomize": False,
            "nodeSeparation": 75,
            "idealEdgeLengthMultiplier": 1.5,
            "edgeElasticity": 0.45,
            "numIter": 2500,
            "seed": 1,
        },
    }
    assert configurations["C4Context"] == {
        "wrap": True,
        "c4": {
            "diagramMarginX": 50,
            "diagramMarginY": 10,
            "c4ShapeMargin": 50,
            "c4ShapePadding": 20,
            "width": 216,
            "height": 60,
            "boxMargin": 10,
            "useMaxWidth": True,
            "c4ShapeInRow": 4,
            "nextLinePaddingX": 0,
            "c4BoundaryInRow": 2,
            "messageFontSize": 12,
        },
    }
    assert configurations["swimlane-beta"] == {
        "wrap": True,
        "swimlane": {
            "lineHops": "arc",
            "ignoreCrossLaneEdges": True,
            "optimizeRanksByCrossings": True,
            "automaticLaneOrdering": False,
        },
    }
    assert configurations["stateDiagram-v2"] == {
        "wrap": True,
        "state": {"titleTopMargin": 25, "useMaxWidth": True, "defaultRenderer": "dagre-wrapper"},
    }
    assert configurations["requirementDiagram"]["requirement"]["useMaxWidth"] is True
    assert configurations["mindmap"]["mindmap"] == {
        "useMaxWidth": True,
        "padding": 10,
        "maxNodeWidth": 200,
        "layoutAlgorithm": "cose-bilkent",
    }
    assert configurations["pie"]["pie"]["donutHole"] == 0
    assert configurations["block"]["block"]["padding"] == 8
    assert configurations["erDiagram"]["er"]["useMaxWidth"] is True
    assert configurations["gantt"]["gantt"]["weekday"] == "sunday"
    assert configurations["gitGraph"]["gitGraph"]["mainBranchName"] == "main"
    assert configurations["packet"]["packet"]["bitsPerRow"] == 32
    assert configurations["radar-beta"]["radar"]["curveTension"] == 0.17
    assert configurations["venn-beta"]["venn"] == {
        "width": 800,
        "height": 450,
        "padding": 8,
        "useDebugLayout": False,
    }
    assert all(
        item.configuration.schema_definition == upstream[item.configuration.config_key].schema_definition
        for item in report.diagrams
    )


def test_application_validates_populated_compatibility_fixtures_with_one_parser_run() -> None:
    with Application.create() as application, MermaidenCli.create() as cli:
        report = cli.verify_compatibility(FixtureCatalog(application).render())

    assert report.valid
    assert not report.syntax_violations


def test_application_lists_diagram_configs_from_mermaid_schema() -> None:
    with MermaidenCli.create() as cli:
        configs = cli.mermaid_diagram_configs()

    mindmap = next(item for item in configs if item.config_key == "mindmap")
    assert mindmap.schema_definition == "MindmapDiagramConfig"
    assert mindmap.schema["type"] == "object"
