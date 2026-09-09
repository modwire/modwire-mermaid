from dataclasses import dataclass
from typing import cast

from pydantic import TypeAdapter, ValidationError
from wireup import injectable

from ...core.domain import Annotation, Diagram, Element, Relation
from ..diagrams.state import DiagramData
from .configuration import DiagramConfigurationReader
from .domain import DiagramSnapshot, SnapshotError, SnapshotTypeRegistry
from .value_decoder import SnapshotValueDecoder


@injectable(lifetime="scoped")
@dataclass(frozen=True, slots=True)
class DiagramSnapshotHydrator:
    values: SnapshotValueDecoder
    configurations: DiagramConfigurationReader
    types: SnapshotTypeRegistry

    def hydrate(self, snapshot: DiagramSnapshot, diagram: Diagram) -> DiagramData:
        contract = self.types.contract(snapshot.kind)
        current_configuration = self.configurations.read(diagram)
        configuration = self.values.decode(snapshot.configuration, contract, type(current_configuration))
        if type(configuration) is not type(current_configuration):
            raise SnapshotError(f"Snapshot configuration is not valid for diagram '{diagram.kind}'.")
        object.__setattr__(diagram, "configuration", configuration)
        try:
            elements = tuple(self.values.decode(item, contract, Element) for item in snapshot.elements)
            relations = tuple(self.values.decode(item, contract, Relation) for item in snapshot.relations)
            annotations = tuple(self.values.decode(item, contract, Annotation) for item in snapshot.annotations)
        except SnapshotError as error:
            raise SnapshotError(f"Snapshot objects are invalid: {error}") from error
        expected_properties = set(contract.properties)
        received_properties = set(snapshot.properties)
        if received_properties != expected_properties:
            missing = sorted(expected_properties - received_properties)
            extra = sorted(received_properties - expected_properties)
            details = [*(f"missing '{name}'" for name in missing), *(f"unsupported '{name}'" for name in extra)]
            raise SnapshotError(f"Snapshot properties are invalid: {', '.join(details)}.")
        for name, value in snapshot.properties.items():
            try:
                decoded = self.values.decode(value, contract, contract.properties[name])
                validated = cast(object, TypeAdapter(contract.properties[name]).validate_python(decoded))
            except (TypeError, ValueError, SnapshotError, ValidationError) as error:
                raise SnapshotError(f"Snapshot property '{name}' is invalid: {error}") from error
            object.__setattr__(diagram, name, validated)
        return DiagramData(elements, relations, annotations)
