from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from importlib import import_module
from importlib.util import find_spec
from inspect import getmembers, isclass

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
        return self._element_types[info.id]

    def relations(self, info: DiagramInfo) -> dict[str, type[Relation]]:
        return self._relation_types[info.id]

    def annotations(self, info: DiagramInfo) -> dict[str, type[Annotation]]:
        return self._annotation_types[info.id]

    @cached_property
    def _element_types(self) -> dict[str, dict[str, type[Element]]]:
        return {info.id: self._models(info, "elements", Element) for info in self.registry}

    @cached_property
    def _relation_types(self) -> dict[str, dict[str, type[Relation]]]:
        return {info.id: self._models(info, "relations", Relation) for info in self.registry}

    @cached_property
    def _annotation_types(self) -> dict[str, dict[str, type[Annotation]]]:
        return {info.id: self._models(info, "annotations", Annotation) for info in self.registry}

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

    def _models[ObjectT: ClassifiedValueModel](
        self,
        info: DiagramInfo,
        collection_name: str,
        parent: type[ObjectT],
    ) -> dict[str, type[ObjectT]]:
        package = info.diagram_type.__module__.removesuffix(".diagram")
        module_name = f"{package}.{collection_name}"
        if find_spec(module_name) is None:
            return {}
        module = import_module(module_name)
        return {
            item.kind_for(): item
            for _, item in getmembers(module, isclass)
            if item.__module__ == module.__name__
            if issubclass(item, parent)
            if item is not parent
        }
