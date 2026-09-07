from wireup import injectable

from ....core.domain import ConstraintDiagram, Violation
from ..annotations import ClassNote
from ..constraints import ClassDiagramConstraint
from ..elements import Class


@injectable(as_type=ClassDiagramConstraint, qualifier="classdiagram_notes")
class ClassNotesTargetClasses(ClassDiagramConstraint):
    @property
    def code(self) -> str:
        return "structure.class_notes_target_classes"

    def visit(self, diagram: ConstraintDiagram) -> tuple[Violation, ...]:
        classes = {item.id for item in diagram.walk_elements("") if isinstance(item, Class)}
        return tuple(
            self.violation("Class notes must target exactly one class.", path=f"annotations.{item.id}.targets")
            for item in diagram.find_annotations("")
            if isinstance(item, ClassNote) and any(target.id not in classes for target in item.targets)
        )
