from collections.abc import Mapping
from dataclasses import dataclass

from wireup import injectable

from ...diagrams.application import DiagramsApplication
from ...diagrams.catalog.service import DiagramCatalog
from ..application import MermaidApplication
from ..templates import MermaidTemplateOwnership
from .configuration import ConfigurationViolation, DiagramConfigurationContract, MermaidConfiguration
from .parser import MermaidSyntaxValidator, MermaidSyntaxViolation
from .schema import MermaidSchemaLock, MermaidSchemaStore


@dataclass(frozen=True, slots=True)
class DiagramCompatibility:
    diagram_id: str
    configuration: DiagramConfigurationContract
    violations: tuple[ConfigurationViolation, ...]
    schema_supported: bool

    @property
    def config_key(self) -> str:
        return self.configuration.config_key

    @property
    def schema_definition(self) -> str:
        return self.configuration.schema_definition

    @property
    def valid(self) -> bool:
        return self.schema_supported and not self.violations


@dataclass(frozen=True, slots=True)
class MissingDiagramCompatibility:
    config_key: str
    schema_definition: str


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    lock: MermaidSchemaLock
    diagrams: tuple[DiagramCompatibility, ...]
    missing_diagrams: tuple[MissingDiagramCompatibility, ...]
    syntax_violations: tuple[MermaidSyntaxViolation, ...] = ()

    @property
    def valid(self) -> bool:
        return (
            all(diagram.valid for diagram in self.diagrams) and not self.missing_diagrams and not self.syntax_violations
        )

    def diagram_valid(self, diagram: DiagramCompatibility) -> bool:
        return diagram.valid and all(violation.diagram_id != diagram.diagram_id for violation in self.syntax_violations)


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class MermaidCompatibilityService:
    syntax: MermaidSyntaxValidator
    registry: DiagramsApplication
    renderer: MermaidApplication
    schemas: MermaidSchemaStore
    catalog: DiagramCatalog
    templates: MermaidTemplateOwnership

    def inspect(self) -> CompatibilityReport:
        return self._inspect({})

    def verify(self, sources: Mapping[str, str]) -> CompatibilityReport:
        return self._inspect(sources)

    def _inspect(self, sources: Mapping[str, str]) -> CompatibilityReport:
        self.catalog.validate()
        self.templates.validate()
        lock = self.schemas.lock()
        configuration = MermaidConfiguration(self.schemas.load())
        diagrams: list[DiagramCompatibility] = []
        upstream_configs = self.schemas.diagram_configs()
        upstream_by_key = {item.config_key: item for item in upstream_configs}
        registered = self.registry.available()
        registered_keys = {item.config_key for item in registered}
        missing = [
            MissingDiagramCompatibility(item.config_key, item.schema_definition)
            for item in upstream_configs
            if item.config_key not in registered_keys
        ]
        validation_sources: dict[str, str] = {}
        for info in registered:
            upstream = upstream_by_key.get(info.config_key)
            if upstream is None:
                continue
            source = self.renderer.render(self.registry.get_diagram(info.id))
            local = configuration.local_contract(info.config_key, info.schema_definition, source)
            validation_sources[info.id] = sources.get(info.id, source)
            diagrams.append(
                DiagramCompatibility(
                    info.id,
                    local,
                    configuration.validate(local),
                    configuration.supports(local, upstream),
                )
            )
        syntax_violations = self.syntax.validate(validation_sources) if sources else ()
        return CompatibilityReport(lock, tuple(diagrams), tuple(missing), syntax_violations)
