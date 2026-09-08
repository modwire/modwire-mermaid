from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from wireup import injectable

from ...core.domain import ChangeReport, Container, Element
from ..domain import DiagramDefinition, DiagramModel
from .annotations import Notes
from .configuration import FlowchartDiagramConfiguration
from .constraints.domain import FlowchartConstraint
from .elements import (
    Action,
    DataStore,
    Decision,
    Direction,
    Document,
    End,
    FlowGroup,
    FlowNode,
    InputOutput,
    Junction,
    Start,
    Subprocess,
)
from .relations import ConditionalFlow, Flow


@injectable(as_type=DiagramModel, qualifier="flowchart", lifetime="transient")
@dataclass(frozen=True, slots=True)
class Flowchart(DiagramModel):
    constraints: Sequence[FlowchartConstraint]
    configuration: FlowchartDiagramConfiguration = field(default_factory=FlowchartDiagramConfiguration, init=False)
    direction: Direction = field(default=Direction.TOP_DOWN, init=False)
    definition: ClassVar[DiagramDefinition] = DiagramDefinition(
        "flowchart",
        "Flowchart",
        "flowchart",
        "FlowchartDiagramConfig",
    )

    def accepts_parent(self, element_type: type[Element], parent_type: type[Container] | None) -> bool:
        return (element_type is FlowGroup or issubclass(element_type, FlowNode)) and (
            parent_type is None or parent_type is FlowGroup
        )

    def add_group(
        self,
        id: str,
        label: str,
        parent_id: str = "",
        direction: Direction | None = None,
    ) -> ChangeReport:
        return self._add_element(
            f"add flow group '{id}'",
            FlowGroup(id=id, label=label, elements=(), direction=direction),
            parent_id,
        )

    def add_node(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(FlowNode(id=id, label=label), parent_id, "node")

    def add_start(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(Start(id=id, label=label), parent_id, "start")

    def add_end(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(End(id=id, label=label), parent_id, "end")

    def add_action(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(Action(id=id, label=label), parent_id, "action")

    def add_decision(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(Decision(id=id, label=label), parent_id, "decision")

    def add_input_output(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(InputOutput(id=id, label=label), parent_id, "input/output")

    def add_data_store(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(DataStore(id=id, label=label), parent_id, "data store")

    def add_document(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(Document(id=id, label=label), parent_id, "document")

    def add_subprocess(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(Subprocess(id=id, label=label), parent_id, "subprocess")

    def add_junction(self, id: str, label: str, parent_id: str = "") -> ChangeReport:
        return self._add_node(Junction(id=id, label=label), parent_id, "junction")

    def add_flow(
        self,
        id: str,
        source_id: str,
        target_id: str,
        label: str = "",
    ) -> ChangeReport:
        return self._add_relation(f"add flow '{id}'", Flow(id=id, element_ids=(source_id, target_id), label=label))

    def add_conditional_flow(
        self,
        id: str,
        source_id: str,
        target_id: str,
        condition: str,
    ) -> ChangeReport:
        return self._add_relation(
            f"add conditional flow '{id}'",
            ConditionalFlow(id=id, element_ids=(source_id, target_id), label=condition),
        )

    def add_note(
        self,
        id: str,
        text: str,
        element_ids: Sequence[str] = (),
    ) -> ChangeReport:
        return self._annotate(
            f"add note '{id}'",
            Notes(),
            id,
            {"text": text},
            element_ids,
        )

    def remove_flow(self, id: str) -> ChangeReport:
        return self.remove_relation(id)

    def _add_node(self, node: FlowNode, parent_id: str, kind: str) -> ChangeReport:
        return self._add_element(f"add {kind} '{node.id}'", node, parent_id)
