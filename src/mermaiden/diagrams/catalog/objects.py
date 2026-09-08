from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ...core.domain import Annotation, ClassifiedValueModel, Container, Diagram, Element, Relation
from ..application import DiagramsApplication
from ..domain import DiagramInfo
from .models import ElementPlacement


@injectable(lifetime="scoped")
@dataclass(frozen=True)
class DiagramObjectCatalog:
    registry: DiagramsApplication

    def elements(self, info: DiagramInfo) -> dict[str, type[Element]]:
        types = sorted(self.registry.get_diagram(info.id).feature.elements, key=lambda item: item.__name__)
        return {item.kind_for(): item for item in types}

    def relations(self, info: DiagramInfo) -> dict[str, type[Relation]]:
        types = sorted(self.registry.get_diagram(info.id).feature.relations, key=lambda item: item.__name__)
        return {item.kind_for(): item for item in types}

    def annotations(self, info: DiagramInfo) -> dict[str, type[Annotation]]:
        types = sorted(self.registry.get_diagram(info.id).feature.annotations, key=lambda item: item.__name__)
        return {item.kind_for(): item for item in types}

    def placements(
        self,
        diagram: Diagram,
        element_types: Mapping[str, type[Element]],
    ) -> dict[str, ElementPlacement]:
        container_types = {
            kind: element_type for kind, element_type in element_types.items() if issubclass(element_type, Container)
        }
        placements: dict[str, ElementPlacement] = {}
        for kind, element_type in element_types.items():
            allowed = (
                *(("$root",) if diagram.accepts_parent(element_type, None) else ()),
                *(
                    parent_kind
                    for parent_kind, parent_type in container_types.items()
                    if diagram.accepts_parent(element_type, parent_type)
                ),
            )
            if not allowed:
                raise ValueError(f"Element '{diagram.kind}.{kind}' has no placement policy.")
            placements[kind] = ElementPlacement(allowed_parents=allowed)
        return placements

    def schemas(
        self,
        object_types: Mapping[str, type[ClassifiedValueModel]],
    ) -> dict[str, Mapping[str, object]]:
        return {kind: object_type.model_json_schema() for kind, object_type in object_types.items()}
