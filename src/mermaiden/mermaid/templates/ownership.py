from dataclasses import dataclass
from functools import cached_property

from wireup import injectable

from ...diagrams.application import DiagramsApplication
from ...diagrams.catalog.service import DiagramCatalog
from .renderer import MermaidTemplateRenderer


@injectable(lifetime="scoped")
@dataclass(frozen=True)
class MermaidTemplateOwnership:
    templates: MermaidTemplateRenderer
    registry: DiagramsApplication
    catalog: DiagramCatalog

    def validate(self) -> None:
        _ = self._validation

    @cached_property
    def _validation(self) -> None:
        for info in self.registry.available():
            diagram = self.catalog.describe(info.id)
            prefix = f"templates/syntax/{diagram.id}"
            for kind in diagram.elements:
                self.templates.require(f"{prefix}/elements/{kind}.mmd.j2")
            for kind in diagram.relations:
                self.templates.require(f"{prefix}/relations/{kind}.mmd.j2")
            for kind in diagram.annotations:
                self.templates.require(f"{prefix}/annotations/{kind}.mmd.j2")
