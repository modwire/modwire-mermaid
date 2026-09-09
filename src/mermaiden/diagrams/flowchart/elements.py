import mermaiden.diagrams.shared.direction

from ...core.domain import Container, Entity


class FlowNode(Entity):
    pass


class Start(FlowNode):
    pass


class End(FlowNode):
    pass


class Action(FlowNode):
    pass


class Decision(FlowNode):
    pass


class InputOutput(FlowNode):
    pass


class DataStore(FlowNode):
    pass


class Document(FlowNode):
    pass


class Subprocess(FlowNode):
    pass


class Junction(FlowNode):
    pass


class FlowGroup(Container):
    direction: mermaiden.diagrams.shared.direction.Direction | None = None
