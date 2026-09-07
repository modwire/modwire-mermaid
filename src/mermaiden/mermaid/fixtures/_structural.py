from ...diagrams.application import DiagramsApplication
from ...diagrams.architecture.configuration import ArchitectureDiagramConfiguration
from ...diagrams.architecture.diagram import Architecture
from ...diagrams.architecture.relations import AlignmentAxis, Port
from ...diagrams.block.diagram import BlockDiagram
from ...diagrams.classdiagram.diagram import ClassDiagram
from ...diagrams.classdiagram.relations import ClassRelationKind
from ...diagrams.classdiagram.values.members import ClassAttribute, ClassMethod, ClassType
from ...diagrams.domain import DiagramModel
from ...diagrams.flowchart.diagram import Flowchart
from ...diagrams.treeview.diagram import TreeView


def build_structural_fixtures(registry: DiagramsApplication) -> dict[str, DiagramModel]:
    flowchart = registry.get_diagram("flowchart")
    assert isinstance(flowchart, Flowchart)
    flowchart.add_group("entry", "Entry")
    flowchart.add_group("process", "Process")
    flowchart.add_start("start", "Start", "entry")
    flowchart.add_decision("ready", "Ready?", "entry")
    flowchart.add_action("work", "Work", "process")
    flowchart.add_node("node", "Node", "process")
    flowchart.add_input_output("input", "Input", "process")
    flowchart.add_data_store("data", "Data", "process")
    flowchart.add_document("document", "Document", "process")
    flowchart.add_subprocess("subprocess", "Subprocess", "process")
    flowchart.add_junction("junction", "Junction", "process")
    flowchart.add_end("end", "End", "process")
    flowchart.add_flow("start_ready", "start", "ready")
    flowchart.add_conditional_flow("ready_work", "ready", "work", "yes")
    flowchart.add_flow("work_node", "work", "node")
    flowchart.add_flow("node_input", "node", "input")
    flowchart.add_flow("input_data", "input", "data")
    flowchart.add_flow("data_document", "data", "document")
    flowchart.add_flow("document_subprocess", "document", "subprocess")
    flowchart.add_flow("subprocess_junction", "subprocess", "junction")
    flowchart.add_flow("junction_end", "junction", "end")
    flowchart.add_note("start_note", "Start process", ("start",))
    flowchart.add_note("work_note", "Process work", ("work",))
    flowchart.add_note("end_note", "Finish process", ("end",))

    treeview = registry.get_diagram("treeView-beta")
    assert isinstance(treeview, TreeView)
    for id, label in (("root", "root"), ("source", "src"), ("package", "mermaiden"), ("tests", "tests")):
        treeview.add_directory(id, label)
    treeview.add_file("readme", "README.md")
    treeview.add_item("overview", "Overview")
    treeview.add_annotation("source_note", "source", icon="folder")
    treeview.add_branch("root_source", "root", "source")
    treeview.add_annotation("tests_note", "tests", icon="test")
    treeview.add_branch("root_tests", "root", "tests")
    treeview.add_branch("source_package", "source", "package")
    treeview.add_branch("root_readme", "root", "readme")
    treeview.add_branch("root_overview", "root", "overview")
    treeview.add_annotation("readme_note", "readme", highlight=True, description="Documentation")

    classes = registry.get_diagram("classDiagram")
    assert isinstance(classes, ClassDiagram)
    classes.add_namespace("domain", "Domain", comment="Domain types")
    classes.add_class(
        "Animal",
        "Animal species",
        attributes=(ClassAttribute(name="name", type=ClassType(name="String")),),
        methods=(ClassMethod(name="sound", return_type=ClassType(name="void")),),
        annotations=("abstract",),
        parent_id="domain",
    )
    classes.add_class("Duck", "Duck", parent_id="domain")
    classes.add_class("Pond", "Pond", parent_id="domain")
    classes.add_relation("inherits", "Animal", "Duck", ClassRelationKind.INHERITANCE, "extends")
    classes.add_relation("hosts", "Pond", "Duck", ClassRelationKind.AGGREGATION, "hosts", "1", "*")
    classes.add_relation("depends", "Duck", "Pond", ClassRelationKind.DEPENDENCY, "visits")
    classes.add_note("animal_note", "Animal", "Base type")
    classes.add_note("duck_note", "Duck", "Concrete type")
    classes.add_note("pond_note", "Pond", "Aggregate")

    architecture = registry.get_diagram("architecture-beta")
    assert isinstance(architecture, Architecture)
    architecture.configure(ArchitectureDiagramConfiguration(node_separation=96, seed=7))
    architecture.add_group("clients", "Clients", columns=2)
    architecture.add_group("platform", "Platform", columns=1)
    architecture.add_group("data", "Data", columns=2)
    architecture.add_service("web", "Web", "clients")
    architecture.add_service("api", "API", "platform")
    architecture.add_junction("events", "Events", "platform")
    architecture.add_service("database", "Database", "data")
    architecture.add_edge("web_api", "web", "api", Port.RIGHT, Port.LEFT, 'HTTPS "mTLS"')
    architecture.add_edge("api_events", "api", "events", Port.BOTTOM, Port.TOP)
    architecture.add_edge("api_database", "api", "database", Port.RIGHT, Port.LEFT)
    architecture.add_alignment("request_row", AlignmentAxis.ROW, ("web", "api"))
    architecture.add_note("web_note", "web", "Client gateway")
    architecture.add_note("api_note", "api", "Public API")
    architecture.add_note("database_note", "database", "Persistent storage")

    block = registry.get_diagram("block")
    assert isinstance(block, BlockDiagram)
    block.set_columns(3)
    block.add_block("frontend", "Frontend")
    block.add_space("gap")
    block.add_group("backend", "Backend", columns=2)
    block.add_block("api", "API", parent_id="backend")
    block.add_block("database", "Database", parent_id="backend")

    return {
        "flowchart": flowchart,
        "treeview": treeview,
        "classdiagram": classes,
        "architecture": architecture,
        "block": block,
    }
