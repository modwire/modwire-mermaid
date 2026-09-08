import mermaiden.diagrams.state.annotations
from mermaiden import Application
from mermaiden.diagrams.eventmodeling.diagram import EventModelingDiagram
from mermaiden.diagrams.journey.diagram import Journey
from mermaiden.diagrams.sequence.annotations import NotePosition
from mermaiden.diagrams.sequence.diagram import SequenceDiagram
from mermaiden.diagrams.sequence.elements import ParticipantKind
from mermaiden.diagrams.sequence.relations import ControlKind, MessageKind
from mermaiden.diagrams.state.diagram import StateDiagram
from mermaiden.diagrams.swimlane.diagram import SwimlaneDiagram
from mermaiden.diagrams.timeline.diagram import Timeline

from .models import DiagramFixture


def build_behavioral_fixtures(application: Application) -> tuple[DiagramFixture, ...]:
    sequence = application.create_diagram("sequenceDiagram")
    assert isinstance(sequence, SequenceDiagram)
    sequence.add_box("clients", "Clients", "#E3F2FD")
    sequence.add_participant("user", "User", ParticipantKind.ACTOR, "clients")
    sequence.add_participant("web", "Web", ParticipantKind.BOUNDARY, "clients")
    sequence.add_box("backend", "Backend", "#F3E5F5")
    sequence.add_participant("api", "API", ParticipantKind.CONTROL, "backend")
    sequence.add_participant("database", "Database", ParticipantKind.DATABASE, "backend")
    sequence.add_participant("events", "Events", ParticipantKind.QUEUE)
    sequence.add_participant("worker", "Worker", ParticipantKind.ENTITY, created=True)
    sequence.autonumber("number")
    sequence.add_message("request", "user", "web", "Open", MessageKind.SOLID, activate=True)
    sequence.add_message("forward", "web", "api", "Forward", MessageKind.OPEN)
    sequence.create("create_worker", "worker")
    sequence.add_message("start_worker", "api", "worker", "Start job")
    sequence.control("loop", ControlKind.LOOP, "retry")
    sequence.add_message("query", "api", "database", "Query", MessageKind.DOTTED)
    sequence.control("parallel", ControlKind.PAR, "effects")
    sequence.add_message("publish", "api", "events", "Publish", MessageKind.DOTTED_OPEN)
    sequence.control("end_parallel", ControlKind.END)
    sequence.control("end_loop", ControlKind.END)
    sequence.deactivate("deactivate_web", "web")
    sequence.destroy("destroy_worker", "worker")
    sequence.add_message("stop_worker", "api", "worker", "Stop job")
    sequence.add_note("user_note", "Caller", "user", position=NotePosition.LEFT)
    sequence.add_note("web_note", "Gateway", "web", position=NotePosition.RIGHT)
    sequence.add_note("sequence_note", "Asynchronous", "api", "events", position=NotePosition.OVER)

    swimlane = application.create_diagram("swimlane-beta")
    assert isinstance(swimlane, SwimlaneDiagram)
    swimlane.add_lane("customer", "Customer")
    swimlane.add_lane("support", "Support")
    swimlane.add_lane("engineering", "Engineering")
    swimlane.add_start("request", "Request service", "customer")
    swimlane.add_activity("triage", "Triage request", "support")
    swimlane.add_decision("known", "Known issue?", "support")
    swimlane.add_activity("answer", "Send answer", "support")
    swimlane.add_activity("investigate", "Investigate issue", "engineering")
    swimlane.add_connector("handoff", "Handoff", "engineering")
    swimlane.add_end("receive", "Receive update", "customer")
    swimlane.add_flow("request_triage", "request", "triage")
    swimlane.add_flow("triage_known", "triage", "known")
    swimlane.add_conditional_flow("known_answer", "known", "answer", "Yes")
    swimlane.add_conditional_flow("known_investigate", "known", "investigate", "No")
    swimlane.add_flow("investigate_handoff", "investigate", "handoff")
    swimlane.add_flow("handoff_answer", "handoff", "answer")
    swimlane.add_flow("answer_receive", "answer", "receive")

    state = application.create_diagram("stateDiagram-v2")
    assert isinstance(state, StateDiagram)
    state.add_state("still", "Still")
    state.add_state("moving", "Moving")
    state.add_state("crash", "Crash")
    state.add_initial("initial")
    state.add_final("final")
    state.add_choice("decision", "Route")
    state.add_fork("fork", "Fork")
    state.add_join("join", "Join")
    state.add_composite("active", "Active")
    state.add_initial("active_initial", "active")
    state.add_final("active_final", "active")
    state.add_state("num_lock_off", "Num lock off", "active")
    state.add_state("num_lock_on", "Num lock on", "active")
    state.add_state("caps_lock_off", "Caps lock off", "active")
    state.add_transition("start_still", "initial", "still")
    state.add_transition("still_moving", "still", "moving", "accelerate")
    state.add_transition("moving_decision", "moving", "decision")
    state.add_transition("decision_active", "decision", "active", "continue")
    state.add_transition("decision_crash", "decision", "crash", "fail")
    state.add_transition("active_fork", "active", "fork")
    state.add_transition("fork_still", "fork", "still")
    state.add_transition("fork_crash", "fork", "crash")
    state.add_transition("still_join", "still", "join")
    state.add_transition("crash_join", "crash", "join")
    state.add_transition("end_join", "join", "final")
    state.add_transition("start_num_lock", "active_initial", "num_lock_off", composite_id="active")
    state.add_transition("num_lock_toggle", "num_lock_off", "num_lock_on", "toggle", "active")
    state.add_transition("end_num_lock", "num_lock_on", "active_final", composite_id="active")
    state.add_transition("start_caps_lock", "active_initial", "caps_lock_off", composite_id="active")
    state.add_transition("end_caps_lock", "caps_lock_off", "active_final", composite_id="active")
    state.add_note(
        "moving_note",
        "moving",
        "A moving system",
        mermaiden.diagrams.state.annotations.NotePosition.RIGHT,
    )

    timeline = application.create_diagram("timeline")
    assert isinstance(timeline, Timeline)
    timeline.set_title("Mermaiden history")
    timeline.add_section("foundation", "Foundation")
    timeline.add_period("2024", "2024", "foundation")
    timeline.add_event("prototype", "Prototype", "2024")
    timeline.add_event("release", "First release", "2024")

    journey = application.create_diagram("journey")
    assert isinstance(journey, Journey)
    journey.set_title("Working day")
    journey.add_section("work", "Go to work")
    journey.add_task("tea", "Make tea", 5, ("Me",), "work")
    journey.add_task("work_task", "Do work", 1, ("Me", "Cat"), "work")

    eventmodeling = application.create_diagram("eventmodeling")
    assert isinstance(eventmodeling, EventModelingDiagram)
    eventmodeling.add_swimlane("checkout", "Checkout")
    eventmodeling.add_actor("cart_ui", "Cart UI", "checkout")
    eventmodeling.add_command("add_item", "Add item", "checkout")
    eventmodeling.add_event("item_added", "Item added", "checkout")
    eventmodeling.add_view("cart_items", "Cart items", "checkout")
    eventmodeling.add_flow("submit", "cart_ui", "add_item")
    eventmodeling.add_flow("record", "add_item", "item_added")
    eventmodeling.add_flow("project", "item_added", "cart_items")

    builder = build_behavioral_fixtures.__name__
    return tuple(
        DiagramFixture(diagram, builder) for diagram in (sequence, swimlane, state, timeline, journey, eventmodeling)
    )
