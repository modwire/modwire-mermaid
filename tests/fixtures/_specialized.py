from mermaiden import Application
from mermaiden.diagrams.c4.configuration import C4ContextDiagramConfiguration
from mermaiden.diagrams.c4.diagram import C4ContextDiagram
from mermaiden.diagrams.c4.relations import RelationshipDirection
from mermaiden.diagrams.cynefin.diagram import CynefinDiagram
from mermaiden.diagrams.cynefin.elements import DomainKind
from mermaiden.diagrams.gantt.diagram import Gantt
from mermaiden.diagrams.gantt.elements import DateStart, DurationFinish, TaskStatus
from mermaiden.diagrams.gitgraph.diagram import GitGraphDiagram
from mermaiden.diagrams.ishikawa.diagram import IshikawaDiagram
from mermaiden.diagrams.kanban.diagram import KanbanDiagram
from mermaiden.diagrams.railroad.diagram import RailroadDiagram
from mermaiden.diagrams.wardley.diagram import WardleyDiagram
from mermaiden.diagrams.wardley.elements import ComponentDecorator

from .models import DiagramFixture


def build_specialized_fixtures(application: Application) -> tuple[DiagramFixture, ...]:
    gantt = application.create_diagram("gantt")
    assert isinstance(gantt, Gantt)
    gantt.set_title("Release plan")
    gantt.add_section("delivery", "Delivery")
    gantt.add_task(
        "design",
        "Design",
        "delivery",
        status=TaskStatus.DONE,
        start=DateStart(date="2026-08-01"),
        finish=DurationFinish(amount=2),
    )

    gitgraph = application.create_diagram("gitGraph")
    assert isinstance(gitgraph, GitGraphDiagram)
    gitgraph.add_commit("initial", "ZERO", tag="v1.0.0")
    gitgraph.add_branch("develop", "develop", 1)
    gitgraph.checkout("checkout_develop", "develop")
    gitgraph.add_commit("feature", "FEATURE", "HIGHLIGHT")
    gitgraph.checkout("checkout_main", "main")
    gitgraph.add_commit("release", "RELEASE", tag="v1.1.0")

    c4 = application.create_diagram("C4Context")
    assert isinstance(c4, C4ContextDiagram)
    c4.configure(C4ContextDiagramConfiguration(c4_shape_in_row=3, next_line_padding_x=12, message_font_size=16))
    c4.add_person("customer", "Customer", "A personal banking customer")
    c4.add_system("banking", "Internet Banking System", "Provides online banking", "Python")
    c4.add_database("accounts", "Accounts Database", "Stores account balances", "PostgreSQL")
    c4.add_queue("notifications", "Notifications", "Publishes account events", "Kafka")
    c4.add_relationship("uses", "customer", "banking", "Uses")
    c4.add_relationship("reads", "banking", "accounts", "Reads account data", RelationshipDirection.RIGHT)
    c4.add_relationship("publishes", "banking", "notifications", "Publishes events")
    c4.add_relationship("audits", "accounts", "notifications", "Audits events")
    c4.set_relationship_label_offset("uses", 16, 8)
    c4.set_relationship_label_offset("reads", -20, 12)
    c4.set_relationship_label_offset("publishes", -12, -8)
    c4.set_relationship_label_offset("audits", 4, 4)
    c4.set_relationship_label_offset("audits", 0, 0)

    ishikawa = application.create_diagram("ishikawa-beta")
    assert isinstance(ishikawa, IshikawaDiagram)
    ishikawa.add_effect("blurry_photo", "Blurry photo")
    ishikawa.add_category("process", "Process")
    ishikawa.add_cause("focus", "Out of focus", "process")
    ishikawa.add_cause("shutter", "Shutter speed too slow", "process")
    ishikawa.add_category("equipment", "Equipment")
    ishikawa.add_category("lens", "Lens", "equipment")
    ishikawa.add_cause("damaged_lens", "Damaged lens", "lens")

    cynefin = application.create_diagram("cynefin-beta")
    assert isinstance(cynefin, CynefinDiagram)
    cynefin.add_item("investigate", "Investigate root cause", DomainKind.COMPLEX)
    cynefin.add_item("analyze", "Analyze performance data", DomainKind.COMPLICATED)
    cynefin.add_item("restart", "Restart service", DomainKind.CLEAR)
    cynefin.add_item("contain", "Contain the incident", DomainKind.CHAOTIC)
    cynefin.add_item("classify", "Classify the situation", DomainKind.CONFUSION)
    cynefin.add_transition("pattern", "investigate", "analyze", "Pattern identified")

    kanban = application.create_diagram("kanban")
    assert isinstance(kanban, KanbanDiagram)
    kanban.add_column("todo", "Todo")
    kanban.add_column("doing", "In progress")
    kanban.add_task("docs", "Create documentation", "todo", ticket="MC-2037", priority="High")
    kanban.add_task("render", "Create renderer", "doing", assigned="knsv")

    railroad = application.create_diagram("railroad-ebnf-beta")
    assert isinstance(railroad, RailroadDiagram)
    railroad.add_rule("alternative", "alternative")
    railroad.add_alternative("choices", "alternative")
    railroad.add_special("first_choice", "first", "choices")
    railroad.add_special("second_choice", "second", "choices")
    railroad.add_rule("optional", "optional")
    railroad.add_optional("optional_value", "optional")
    railroad.add_terminal("literal", "value", "optional_value")
    railroad.add_rule("repetition", "repetition")
    railroad.add_repetition("repeated_values", "repetition")
    railroad.add_non_terminal("reference", "value", "repeated_values")
    railroad.add_rule("group", "group")
    railroad.add_group("grouped_value", "group")
    railroad.add_special("group_member", "grouped", "grouped_value")

    wardley = application.create_diagram("wardley-beta")
    assert isinstance(wardley, WardleyDiagram)
    wardley.add_anchor("business", "Business", 0.95, 0.63)
    wardley.add_component("tea", "Cup of Tea", 0.79, 0.61, (ComponentDecorator.BUILD,))
    wardley.add_component("water", "Hot Water", 0.52, 0.8)
    wardley.add_dependency("business_tea", "business", "tea")
    wardley.add_dependency("tea_water", "tea", "water")
    wardley.add_evolution("water_evolve", "water", 0.89)

    builder = build_specialized_fixtures.__name__
    return tuple(
        DiagramFixture(diagram, builder)
        for diagram in (gantt, gitgraph, c4, ishikawa, cynefin, kanban, railroad, wardley)
    )
