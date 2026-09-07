from wireup import injectable

from ....core.domain import ConstraintDiagram, Violation
from ..constraints import ClassDiagramConstraint
from ..elements import ClassNamespace


@injectable(as_type=ClassDiagramConstraint, qualifier="classdiagram_namespaces")
class ClassNamespacesHaveChildren(ClassDiagramConstraint):
    def visit(self, diagram: ConstraintDiagram) -> tuple[Violation, ...]:
        return tuple(
            self.violation(
                f"Namespace '{item.id}' requires a class before it can render.", path=f"elements.{item.id}.elements"
            )
            for item in diagram.walk_elements("")
            if isinstance(item, ClassNamespace) and not item.elements
        )
